import "server-only";
import { createHash } from "node:crypto";
import { and, count, eq, gt, inArray, lt, sql } from "drizzle-orm";
import { z } from "zod";
import { getDb, schema } from "@/db";
import { log } from "../log";
import { hit } from "../rate-limit";
import { getProblemRecord, getProblemRecordById } from "./catalog";
import { getDailyChallenge } from "./daily";
import { PracticeError } from "./errors";
import { buildJob, grade, testsFor, type Graded } from "./evaluator";
import { cancelJob, getJob, submitJob, userRef, type ExecutorJob } from "./executor-client";
import { applyOutcome, recordEvent } from "./progress";
import { getPracticeSettings, executorEnv } from "./settings";
import type { Difficulty, Verdict } from "./types";

/**
 * Run and Submit. A submission row is created first (idempotent per user and client key), then the job is
 * handed to the executor. Results are pulled by whoever asks first — the browser polling
 * GET /api/practice/submissions/{id} or the background sweep — and applied exactly once: the transaction that
 * moves the row out of queued/running is the only one that updates progress, XP and badges.
 */

export const runInput = z.object({
  slug: z.string().min(1).max(120),
  code: z.string().max(64_000, "Code is limited to 64 KB."),
  kind: z.enum(["run", "submit"]),
  runtime: z.string().max(40).optional(),
  sessionId: z.uuid().nullish(),
  idempotencyKey: z.string().regex(/^[A-Za-z0-9_-]{8,64}$/),
  custom: z.array(z.object({ args: z.array(z.unknown()).max(20), kwargs: z.record(z.string(), z.unknown()).optional() })).max(5).optional(),
});
export type RunInput = z.infer<typeof runInput>;

export type SubmissionView = {
  id: string;
  kind: "run" | "submit";
  status: "queued" | "running" | "completed" | "error";
  verdict: Verdict | null;
  passed: number;
  total: number;
  results: typeof schema.practiceSubmission.$inferSelect.results;
  custom: typeof schema.practiceSubmission.$inferSelect.results;
  loadError: typeof schema.practiceSubmission.$inferSelect.loadError;
  maxMs: number | null;
  maxMemoryKb: number | null;
  pythonVersion: string | null;
  independent: boolean;
  createdAt: string;
  finishedAt: string | null;
  queuePosition?: number | null;
  badges?: string[];
  xp?: number;
};

type Row = typeof schema.practiceSubmission.$inferSelect;

function view(row: Row, extra: Partial<SubmissionView> = {}): SubmissionView {
  const all = row.results ?? [];
  return {
    id: row.id,
    kind: row.kind as "run" | "submit",
    status: row.status as SubmissionView["status"],
    verdict: (row.verdict as Verdict | null) ?? null,
    passed: row.passed,
    total: row.total,
    results: all.filter((r) => !(r as { custom?: boolean }).custom),
    custom: all.filter((r) => (r as { custom?: boolean }).custom),
    loadError: row.loadError,
    maxMs: row.maxMs,
    maxMemoryKb: row.maxMemoryKb,
    pythonVersion: row.pythonVersion,
    independent: row.independent,
    createdAt: row.createdAt.toISOString(),
    finishedAt: row.finishedAt?.toISOString() ?? null,
    ...extra,
  };
}

async function sessionFor(userId: string, sessionId: string, problemId: string) {
  const db = await getDb();
  const [session] = await db.select().from(schema.practiceSession).where(eq(schema.practiceSession.id, sessionId));
  if (!session || session.userId !== userId) throw new PracticeError("Session not found.", 404, "not_found");
  if (session.status !== "active" || (session.deadlineAt && session.deadlineAt.getTime() <= Date.now())) throw new PracticeError("Time is up for this session.", 409, "session_closed");
  const [item] = await db
    .select()
    .from(schema.practiceSessionItem)
    .where(and(eq(schema.practiceSessionItem.sessionId, sessionId), eq(schema.practiceSessionItem.problemId, problemId)));
  if (!item) throw new PracticeError("That problem is not part of this session.", 400, "not_in_session");
  return { session, item };
}

export async function createSubmission(userId: string, raw: unknown): Promise<SubmissionView> {
  const parsed = runInput.safeParse(raw);
  if (!parsed.success) throw new PracticeError(parsed.error.issues[0]?.message ?? "Invalid request.", 400, "invalid");
  const input = parsed.data;
  const settings = await getPracticeSettings();
  if (!settings.execution.enabled || !executorEnv()) throw new PracticeError("Running code is not enabled yet. You can still read problems, hints and solutions.", 503, "execution_disabled");
  const runtime = input.runtime ?? settings.execution.defaultRuntime;
  if (!settings.execution.runtimes.some((r) => r.id === runtime && r.enabled)) throw new PracticeError("That Python version is not available.", 400, "bad_runtime");

  const db = await getDb();
  const [existing] = await db
    .select()
    .from(schema.practiceSubmission)
    .where(and(eq(schema.practiceSubmission.userId, userId), eq(schema.practiceSubmission.idempotencyKey, input.idempotencyKey)));
  if (existing) return view(existing);

  const quota = input.kind === "run" ? settings.quotas.runsPerHour : settings.quotas.submitsPerHour;
  if (!(await hit(`practice:${input.kind}:${userId}`, quota, 3600))) {
    await recordEvent(db, { userId, type: "rate_limited", detail: { kind: input.kind } });
    throw new PracticeError(`You've reached ${quota} ${input.kind === "run" ? "runs" : "submissions"} this hour. Take a break and try again later.`, 429, "rate_limited", 300);
  }
  const [pending] = await db
    .select({ n: count() })
    .from(schema.practiceSubmission)
    .where(
      and(
        eq(schema.practiceSubmission.userId, userId),
        inArray(schema.practiceSubmission.status, ["queued", "running"]),
        gt(schema.practiceSubmission.createdAt, new Date(Date.now() - 5 * 60_000)),
      ),
    );
  if (Number(pending?.n ?? 0) >= settings.quotas.maxPending) throw new PracticeError("Wait for your current run to finish.", 429, "busy", 2);

  let record = await getProblemRecord(input.slug);
  let sessionItem: Awaited<ReturnType<typeof sessionFor>>["item"] | null = null;
  if (input.sessionId) {
    const s = await sessionFor(userId, input.sessionId, record.problem.id);
    sessionItem = s.item;
    if (s.item.version !== record.version.version) record = await getProblemRecordById(record.problem.id, s.item.version);
  }

  const [progress] = await db
    .select()
    .from(schema.practiceProgress)
    .where(and(eq(schema.practiceProgress.userId, userId), eq(schema.practiceProgress.problemId, record.problem.id)));
  const hintsUsed = Math.max(progress?.hintsUsed ?? 0, sessionItem?.hintsUsed ?? 0);
  const solutionRevealed = Boolean(progress?.solutionRevealedAt) || Boolean(sessionItem?.solutionRevealed);

  const inserted = await db
    .insert(schema.practiceSubmission)
    .values({
      userId,
      problemId: record.problem.id,
      problemVersion: record.version.version,
      sessionId: input.sessionId ?? null,
      kind: input.kind,
      idempotencyKey: input.idempotencyKey,
      code: input.code,
      codeSha256: createHash("sha256").update(input.code).digest("hex"),
      runtime,
      hintsUsed,
      solutionRevealed,
    })
    .onConflictDoNothing()
    .returning();
  if (!inserted.length) {
    const [again] = await db
      .select()
      .from(schema.practiceSubmission)
      .where(and(eq(schema.practiceSubmission.userId, userId), eq(schema.practiceSubmission.idempotencyKey, input.idempotencyKey)));
    return view(again!);
  }
  const row = inserted[0]!;
  await db.insert(schema.practiceExecutionJob).values({ submissionId: row.id });
  await recordEvent(db, {
    userId,
    type: input.kind === "submit" ? "code_submitted" : "test_execution_requested",
    problemId: row.problemId,
    sessionId: row.sessionId,
    submissionId: row.id,
    detail: { runtime, codeBytes: input.code.length, custom: input.custom?.length ?? 0 },
  });

  const tests = await testsFor(record.problem.id, record.version.version, input.kind);
  const job = buildJob(record.version, tests, {
    code: input.code,
    runtime,
    user: userRef(userId),
    idempotencyKey: row.id.replace(/-/g, ""),
    purpose: input.kind,
    custom: input.kind === "run" ? input.custom : undefined,
    caps: settings.execution,
  });
  try {
    const created = await submitJob(job);
    await db.update(schema.practiceExecutionJob).set({ executorJobId: created.id, status: created.status }).where(eq(schema.practiceExecutionJob.submissionId, row.id));
    await db.update(schema.practiceSubmission).set({ status: created.status === "running" ? "running" : "queued" }).where(eq(schema.practiceSubmission.id, row.id));
    return view({ ...row, status: "queued" }, { queuePosition: created.queue_position ?? null });
  } catch (error) {
    const message = error instanceof PracticeError ? error.message : "The code runner is unavailable.";
    await finalize(row.id, { infra: message });
    if (error instanceof PracticeError && (error.status === 429 || error.status === 503)) throw error;
    log.warn("practice job submit failed", { err: error, submission: row.id });
    const [failed] = await db.select().from(schema.practiceSubmission).where(eq(schema.practiceSubmission.id, row.id));
    return view(failed!);
  }
}

/** Move a pending submission to its final state once; apply progress in the same transaction. */
async function finalize(id: string, outcome: { graded: Graded; customCount?: number } | { infra: string } | { cancelled: true }): Promise<{ badges: string[]; xp: number } | null> {
  const db = await getDb();
  // Resolved before the transaction: it may read (and cache) the catalog through its own connection.
  const daily = await getDailyChallenge().catch(() => null);
  return db.transaction(async (tx) => {
    const now = new Date();
    let set: Partial<typeof schema.practiceSubmission.$inferInsert>;
    if ("graded" in outcome) {
      const g = outcome.graded;
      set = {
        status: "completed",
        verdict: g.verdict,
        passed: g.passed,
        total: g.total,
        results: [...g.results, ...g.custom.map((c) => ({ ...c, custom: true }) as typeof c)],
        loadError: g.loadError,
        maxMs: g.maxMs,
        maxMemoryKb: g.maxMemoryKb,
        pythonVersion: g.pythonVersion,
        finishedAt: now,
      };
    } else if ("infra" in outcome) {
      set = { status: "error", verdict: "infrastructure_error", loadError: { type: "ExecutionUnavailable", message: outcome.infra }, finishedAt: now };
    } else {
      set = { status: "error", verdict: "cancelled", finishedAt: now };
    }
    const [row] = await tx
      .update(schema.practiceSubmission)
      .set(set)
      .where(and(eq(schema.practiceSubmission.id, id), inArray(schema.practiceSubmission.status, ["queued", "running"])))
      .returning();
    if (!row) return null; // someone else finalised it
    const independent = row.kind === "submit" && row.verdict === "accepted" && !row.solutionRevealed;
    if (independent) await tx.update(schema.practiceSubmission).set({ independent: true }).where(eq(schema.practiceSubmission.id, id));
    await tx
      .update(schema.practiceExecutionJob)
      .set({ status: "graded" in outcome ? "done" : "infra" in outcome ? "failed" : "cancelled", error: "infra" in outcome ? outcome.infra : null, finishedAt: now })
      .where(eq(schema.practiceExecutionJob.submissionId, id));
    const [problem] = await tx.select().from(schema.practiceProblem).where(eq(schema.practiceProblem.id, row.problemId));
    return applyOutcome(tx, { submission: { ...row, independent }, difficulty: problem!.difficulty as Difficulty, topics: problem!.topics, dailyProblemId: daily?.problemId ?? null }, now);
  });
}

/** Ask the executor about a pending submission and finalise it if the job is over. */
async function refresh(row: Row): Promise<{ row: Row; queuePosition?: number | null; badges?: string[]; xp?: number }> {
  const db = await getDb();
  const [job] = await db.select().from(schema.practiceExecutionJob).where(eq(schema.practiceExecutionJob.submissionId, row.id));
  if (!job?.executorJobId) {
    if (Date.now() - row.createdAt.getTime() > 60_000) await finalize(row.id, { infra: "The run was never queued." });
    return { row: (await db.select().from(schema.practiceSubmission).where(eq(schema.practiceSubmission.id, row.id)))[0]! };
  }
  let remote: ExecutorJob;
  try {
    remote = await getJob(job.executorJobId);
  } catch (error) {
    if (error instanceof PracticeError && error.code === "job_not_found") await finalize(row.id, { infra: "The run expired before its result was collected." });
    else if (Date.now() - row.createdAt.getTime() > 5 * 60_000) await finalize(row.id, { infra: "The code runner did not answer in time." });
    return { row: (await db.select().from(schema.practiceSubmission).where(eq(schema.practiceSubmission.id, row.id)))[0]! };
  }
  let applied: { badges: string[]; xp: number } | null = null;
  if (remote.status === "done" && remote.result) {
    const record = await getProblemRecordById(row.problemId, row.problemVersion);
    const kind = row.kind as "run" | "submit";
    const tests = await testsFor(row.problemId, row.problemVersion, kind);
    const customCount = remote.result.tests.filter((t) => t.id.startsWith("c")).length;
    applied = await finalize(row.id, { graded: grade(record.version, tests, remote.result, customCount) });
  } else if (remote.status === "failed") {
    applied = await finalize(row.id, { infra: remote.error ?? "The sandbox failed to run the code." });
  } else if (remote.status === "cancelled") {
    applied = await finalize(row.id, { cancelled: true });
  } else if (remote.status === "running" && row.status === "queued") {
    await db.update(schema.practiceSubmission).set({ status: "running" }).where(and(eq(schema.practiceSubmission.id, row.id), eq(schema.practiceSubmission.status, "queued")));
  }
  const [fresh] = await db.select().from(schema.practiceSubmission).where(eq(schema.practiceSubmission.id, row.id));
  return { row: fresh!, queuePosition: remote.queue_position ?? null, ...(applied ?? {}) };
}

export async function getSubmission(userId: string, id: string): Promise<SubmissionView> {
  if (!z.uuid().safeParse(id).success) throw new PracticeError("Submission not found.", 404, "not_found");
  const db = await getDb();
  const [row] = await db.select().from(schema.practiceSubmission).where(eq(schema.practiceSubmission.id, id));
  if (!row || row.userId !== userId) throw new PracticeError("Submission not found.", 404, "not_found");
  if (row.status === "queued" || row.status === "running") {
    const r = await refresh(row);
    return view(r.row, { queuePosition: r.queuePosition, ...(r.badges ? { badges: r.badges, xp: r.xp } : {}) });
  }
  return view(row);
}

export async function cancelSubmission(userId: string, id: string): Promise<SubmissionView> {
  const db = await getDb();
  const [row] = await db.select().from(schema.practiceSubmission).where(eq(schema.practiceSubmission.id, id));
  if (!row || row.userId !== userId) throw new PracticeError("Submission not found.", 404, "not_found");
  const [job] = await db.select().from(schema.practiceExecutionJob).where(eq(schema.practiceExecutionJob.submissionId, id));
  if (job?.executorJobId && (row.status === "queued" || row.status === "running")) {
    await cancelJob(job.executorJobId).catch(() => null);
  }
  await finalize(id, { cancelled: true });
  const [fresh] = await db.select().from(schema.practiceSubmission).where(eq(schema.practiceSubmission.id, id));
  return view(fresh!);
}

/** Background sweep (lib/scheduler.ts): collect results nobody polled for, and fail runs stuck for too long. */
export async function sweepPendingSubmissions(now = new Date()): Promise<number> {
  if (!executorEnv()) return 0;
  const db = await getDb();
  const rows = await db
    .select()
    .from(schema.practiceSubmission)
    .where(and(inArray(schema.practiceSubmission.status, ["queued", "running"]), lt(schema.practiceSubmission.createdAt, new Date(now.getTime() - 5_000))))
    .limit(50);
  for (const row of rows) {
    await refresh(row).catch((err) => log.warn("practice sweep failed", { err, submission: row.id }));
  }
  return rows.length;
}

/** History list for /python-practice/history. */
export async function listSubmissions(userId: string, opts: { page?: number; perPage?: number } = {}) {
  const perPage = Math.min(Math.max(opts.perPage ?? 25, 1), 100);
  const page = Math.max(opts.page ?? 1, 1);
  const db = await getDb();
  const rows = await db.execute(sql`select s.id, s.kind, s.verdict, s.status, s.passed, s.total, s.independent, s.hints_used, s.created_at, s.session_id, p.slug, p.title, p.difficulty
    from practice_submission s join practice_problem p on p.id = s.problem_id
    where s.user_id = ${userId} order by s.created_at desc limit ${perPage + 1} offset ${(page - 1) * perPage}`);
  const { rowsOf } = await import("@/db/rows");
  const list = rowsOf<{ id: string; kind: string; verdict: string | null; status: string; passed: number; total: number; independent: boolean; hints_used: number; created_at: Date | string; session_id: string | null; slug: string; title: string; difficulty: string }>(rows);
  return { items: list.slice(0, perPage).map((r) => ({ ...r, created_at: new Date(r.created_at).toISOString() })), hasMore: list.length > perPage, page };
}

/** Code of one of the user's own submissions (history detail). */
export async function submissionCode(userId: string, id: string): Promise<{ code: string; slug: string } | null> {
  const db = await getDb();
  const [row] = await db
    .select({ code: schema.practiceSubmission.code, userId: schema.practiceSubmission.userId, slug: schema.practiceProblem.slug })
    .from(schema.practiceSubmission)
    .innerJoin(schema.practiceProblem, eq(schema.practiceProblem.id, schema.practiceSubmission.problemId))
    .where(eq(schema.practiceSubmission.id, id));
  return row && row.userId === userId ? { code: row.code, slug: row.slug } : null;
}
