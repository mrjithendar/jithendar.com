import "server-only";
import { randomInt } from "node:crypto";
import { and, asc, count, eq, lte, sql } from "drizzle-orm";
import { z } from "zod";
import { getDb, schema, type Db } from "@/db";
import type { PracticeSessionConfig } from "@/db/schema";
import { recommend } from "./adaptive";
import { publishedProblems } from "./catalog";
import { getDailyChallenge } from "./daily";
import { PracticeError } from "./errors";
import { recordEvent } from "./progress";
import { reviewCode } from "./review";
import { DIFFICULTIES, MODES, type Mode } from "./types";

/**
 * Practice sessions. Deadlines are stored on the server when the session starts; the browser only displays
 * the remaining time it is given, so refreshing or reconnecting cannot extend it. Expired sessions are
 * finalised on the next read and by the background sweep.
 */

export const sessionInput = z.object({
  mode: z.enum(MODES),
  roles: z.array(z.string().max(60)).max(20).default([]),
  difficulties: z.array(z.enum(DIFFICULTIES)).max(5).default([]),
  topics: z.array(z.string().max(60)).max(30).default([]),
  count: z.coerce.number().int().min(1).max(10).default(3),
  durationMinutes: z.coerce.number().int().min(5).max(180).nullish(),
  includeFailed: z.boolean().default(false),
  excludeSolved: z.boolean().default(true),
});

export type SessionItemView = { position: number; slug: string; title: string; difficulty: string; status: string; hintsUsed: number; solutionRevealed: boolean; passed: number; total: number; score: number; feedback: Record<string, unknown> | null };
export type SessionView = {
  id: string;
  mode: Mode;
  status: string;
  config: PracticeSessionConfig;
  startedAt: string;
  deadlineAt: string | null;
  remainingMs: number | null;
  completedAt: string | null;
  currentIndex: number;
  items: SessionItemView[];
  score: Record<string, unknown> | null;
  rationale: string[];
};

function shuffle<T>(items: T[]): T[] {
  const a = [...items];
  for (let i = a.length - 1; i > 0; i--) {
    const j = randomInt(i + 1);
    [a[i], a[j]] = [a[j]!, a[i]!];
  }
  return a;
}

export async function createSession(userId: string, raw: unknown): Promise<{ id: string }> {
  const parsed = sessionInput.safeParse(raw);
  if (!parsed.success) throw new PracticeError(parsed.error.issues[0]?.message ?? "Invalid session settings.", 400, "invalid");
  const input = parsed.data;
  const db = await getDb();
  const [active] = await db
    .select({ n: count() })
    .from(schema.practiceSession)
    .where(and(eq(schema.practiceSession.userId, userId), eq(schema.practiceSession.status, "active")));
  if (Number(active?.n ?? 0) >= 5) throw new PracticeError("You have five sessions in progress. Finish or end one first.", 409, "too_many_sessions");

  const problems = await publishedProblems();
  const progress = await db.select().from(schema.practiceProgress).where(eq(schema.practiceProgress.userId, userId));
  const status = new Map(progress.map((p) => [p.problemId, p.status]));
  let picked: typeof problems = [];
  let rationale: string[] = [];

  if (input.mode === "daily") {
    const daily = await getDailyChallenge();
    if (!daily) throw new PracticeError("There is no daily challenge today.", 404, "not_found");
    picked = problems.filter((p) => p.id === daily.problemId);
    rationale = [`Daily challenge for ${daily.day}.`];
  } else if (input.mode === "adaptive") {
    const recs = await recommend(userId, input.count, { roles: input.roles });
    picked = recs.map((r) => r.problem);
    rationale = recs.map((r) => `${r.problem.title}: ${r.reason}`);
  } else {
    let pool = problems.filter(
      (p) =>
        (!input.roles.length || p.roles.some((r) => input.roles.includes(r))) &&
        (!input.difficulties.length || input.difficulties.includes(p.difficulty)) &&
        (!input.topics.length || p.topics.some((t) => input.topics.includes(t))),
    );
    if (input.excludeSolved) pool = pool.filter((p) => !["solved", "solved_assisted"].includes(status.get(p.id) ?? ""));
    const failed = input.includeFailed ? shuffle(pool.filter((p) => status.get(p.id) === "attempted")) : [];
    const rest = shuffle(pool.filter((p) => !failed.includes(p)));
    picked = [...failed, ...rest].slice(0, input.count);
    if (failed.length) rationale = [`Includes ${Math.min(failed.length, input.count)} problem(s) you attempted but haven't solved.`];
  }
  if (!picked.length) throw new PracticeError("No problems match these settings. Widen the roles, difficulties or topics.", 404, "no_problems");

  const duration = input.mode === "timed" ? (input.durationMinutes ?? 30) : input.mode === "mock" ? (input.durationMinutes ?? 45) : null;
  const versions = await db.select({ id: schema.practiceProblem.id, v: schema.practiceProblem.currentVersion }).from(schema.practiceProblem);
  const versionOf = new Map(versions.map((r) => [r.id, r.v]));
  const config: PracticeSessionConfig = {
    roles: input.roles,
    difficulties: input.difficulties,
    topics: input.topics,
    count: picked.length,
    durationMinutes: duration,
    includeFailed: input.includeFailed,
    excludeSolved: input.excludeSolved,
  };
  return db.transaction(async (tx) => {
    const now = new Date();
    const [session] = await tx
      .insert(schema.practiceSession)
      .values({ userId, mode: input.mode, config, startedAt: now, deadlineAt: duration ? new Date(now.getTime() + duration * 60_000) : null, rationale })
      .returning({ id: schema.practiceSession.id });
    await tx.insert(schema.practiceSessionItem).values(picked.map((p, i) => ({ sessionId: session!.id, position: i, problemId: p.id, version: versionOf.get(p.id) ?? 1 })));
    await recordEvent(tx, { userId, type: "session_started", sessionId: session!.id, detail: { mode: input.mode, count: picked.length, durationMinutes: duration } });
    return { id: session!.id };
  });
}

/** Session score: average item score; mock sessions add the rubric. Stored on the session when it ends. */
export async function scoreSession(tx: Db, session: typeof schema.practiceSession.$inferSelect): Promise<Record<string, unknown>> {
  const items = await tx.select().from(schema.practiceSessionItem).where(eq(schema.practiceSessionItem.sessionId, session.id)).orderBy(asc(schema.practiceSessionItem.position));
  const total = items.reduce((n, i) => n + i.score, 0);
  const percent = items.length ? Math.round(total / items.length) : 0;
  return { percent, solved: items.filter((i) => i.score >= 50).length, items: items.length, skipped: items.filter((i) => i.status === "skipped").length };
}

async function mockFeedback(tx: Db, session: typeof schema.practiceSession.$inferSelect) {
  const items = await tx.select().from(schema.practiceSessionItem).where(eq(schema.practiceSessionItem.sessionId, session.id));
  for (const item of items) {
    if (!item.bestSubmissionId) continue;
    const [sub] = await tx.select().from(schema.practiceSubmission).where(eq(schema.practiceSubmission.id, item.bestSubmissionId));
    if (!sub) continue;
    const runs = await tx
      .select({ results: schema.practiceSubmission.results })
      .from(schema.practiceSubmission)
      .where(and(eq(schema.practiceSubmission.sessionId, session.id), eq(schema.practiceSubmission.problemId, item.problemId), eq(schema.practiceSubmission.kind, "run"), lte(schema.practiceSubmission.createdAt, sub.createdAt)));
    const [v] = await tx
      .select({ limits: schema.practiceProblemVersion.limits })
      .from(schema.practiceProblemVersion)
      .where(and(eq(schema.practiceProblemVersion.problemId, item.problemId), eq(schema.practiceProblemVersion.version, item.version)));
    const feedback = reviewCode({
      code: sub.code,
      verdict: sub.verdict,
      passed: sub.passed,
      total: sub.total,
      maxMs: sub.maxMs,
      perTestSeconds: v?.limits.perTestSeconds ?? 2,
      runsBeforeSubmit: runs.length,
      customInputsTried: runs.reduce((n, r) => n + r.results.filter((x) => x.custom).length, 0),
    });
    await tx
      .update(schema.practiceSessionItem)
      .set({ feedback })
      .where(and(eq(schema.practiceSessionItem.sessionId, item.sessionId), eq(schema.practiceSessionItem.position, item.position)));
  }
}

/** End a session once (completed by the user, or expired by the deadline). */
export async function finalizeSession(sessionId: string, status: "completed" | "expired"): Promise<void> {
  const db = await getDb();
  await db.transaction(async (tx) => {
    const [session] = await tx
      .update(schema.practiceSession)
      .set({ status, completedAt: new Date() })
      .where(and(eq(schema.practiceSession.id, sessionId), eq(schema.practiceSession.status, "active")))
      .returning();
    if (!session) return;
    if (session.mode === "mock") await mockFeedback(tx, session);
    const score = await scoreSession(tx, session);
    await tx.update(schema.practiceSession).set({ score }).where(eq(schema.practiceSession.id, sessionId));
    await recordEvent(tx, { userId: session.userId, type: session.mode === "timed" || session.mode === "mock" ? "assessment_completed" : "session_completed", sessionId, detail: { status, ...score } });
    if (session.mode === "timed" || session.mode === "mock") {
      const { awardBadges } = await import("./achievements");
      await awardBadges(tx, session.userId, null);
    }
  });
}

/** Background sweep: finalise sessions whose deadline has passed. */
export async function expireSessions(now = new Date()): Promise<number> {
  const db = await getDb();
  const due = await db
    .select({ id: schema.practiceSession.id })
    .from(schema.practiceSession)
    .where(and(eq(schema.practiceSession.status, "active"), lte(schema.practiceSession.deadlineAt, now)))
    .limit(100);
  for (const s of due) await finalizeSession(s.id, "expired");
  return due.length;
}

export async function getSession(userId: string, id: string, opts: { resumed?: boolean } = {}): Promise<SessionView> {
  if (!z.uuid().safeParse(id).success) throw new PracticeError("Session not found.", 404, "not_found");
  const db = await getDb();
  let [session] = await db.select().from(schema.practiceSession).where(eq(schema.practiceSession.id, id));
  if (!session || session.userId !== userId) throw new PracticeError("Session not found.", 404, "not_found");
  if (session.status === "active" && session.deadlineAt && session.deadlineAt.getTime() <= Date.now()) {
    await finalizeSession(id, "expired");
    [session] = await db.select().from(schema.practiceSession).where(eq(schema.practiceSession.id, id));
  } else if (session.status === "active" && opts.resumed) {
    await recordEvent(db, { userId, type: "session_resumed", sessionId: id });
  }
  const items = await db
    .select({
      position: schema.practiceSessionItem.position,
      slug: schema.practiceProblem.slug,
      title: schema.practiceProblem.title,
      difficulty: schema.practiceProblem.difficulty,
      status: schema.practiceSessionItem.status,
      hintsUsed: schema.practiceSessionItem.hintsUsed,
      solutionRevealed: schema.practiceSessionItem.solutionRevealed,
      passed: schema.practiceSessionItem.passed,
      total: schema.practiceSessionItem.total,
      score: schema.practiceSessionItem.score,
      feedback: schema.practiceSessionItem.feedback,
    })
    .from(schema.practiceSessionItem)
    .innerJoin(schema.practiceProblem, eq(schema.practiceProblem.id, schema.practiceSessionItem.problemId))
    .where(eq(schema.practiceSessionItem.sessionId, id))
    .orderBy(asc(schema.practiceSessionItem.position));
  const s = session!;
  return {
    id: s.id,
    mode: s.mode as Mode,
    status: s.status,
    config: s.config,
    startedAt: s.startedAt.toISOString(),
    deadlineAt: s.deadlineAt?.toISOString() ?? null,
    remainingMs: s.status === "active" && s.deadlineAt ? Math.max(0, s.deadlineAt.getTime() - Date.now()) : null,
    completedAt: s.completedAt?.toISOString() ?? null,
    currentIndex: s.currentIndex,
    items,
    score: s.score,
    rationale: s.rationale,
  };
}

const actionInput = z.object({ action: z.enum(["goto", "skip", "finish", "abandon"]), position: z.coerce.number().int().min(0).max(50).optional() });

export async function sessionAction(userId: string, id: string, raw: unknown): Promise<SessionView> {
  const parsed = actionInput.safeParse(raw);
  if (!parsed.success) throw new PracticeError("Invalid action.", 400, "invalid");
  const view = await getSession(userId, id);
  if (view.status !== "active") throw new PracticeError("This session has ended.", 409, "session_closed");
  const db = await getDb();
  const { action, position } = parsed.data;
  if (action === "goto" || action === "skip") {
    const pos = position ?? view.currentIndex;
    if (!view.items.some((i) => i.position === pos)) throw new PracticeError("No such question.", 400, "invalid");
    if (action === "skip") {
      const item = view.items.find((i) => i.position === pos)!;
      if (item.status === "pending") {
        await db
          .update(schema.practiceSessionItem)
          .set({ status: "skipped" })
          .where(and(eq(schema.practiceSessionItem.sessionId, id), eq(schema.practiceSessionItem.position, pos)));
        const [p] = await db.select({ id: schema.practiceProblem.id }).from(schema.practiceProblem).where(eq(schema.practiceProblem.slug, item.slug));
        await recordEvent(db, { userId, type: "question_skipped", sessionId: id, problemId: p?.id ?? null, detail: { position: pos } });
      }
    }
    const next = action === "skip" ? Math.min(pos + 1, view.items.length - 1) : pos;
    await db.update(schema.practiceSession).set({ currentIndex: next }).where(eq(schema.practiceSession.id, id));
  } else if (action === "finish") {
    await finalizeSession(id, "completed");
  } else {
    await db
      .update(schema.practiceSession)
      .set({ status: "abandoned", completedAt: new Date() })
      .where(and(eq(schema.practiceSession.id, id), eq(schema.practiceSession.status, "active")));
  }
  return getSession(userId, id);
}

export async function listSessions(userId: string, limit = 20) {
  const db = await getDb();
  const { rowsOf } = await import("@/db/rows");
  return rowsOf<{ id: string; mode: string; status: string; started_at: Date | string; completed_at: Date | string | null; score: Record<string, unknown> | null; items: number }>(
    await db.execute(sql`select s.id, s.mode, s.status, s.started_at, s.completed_at, s.score, (select count(*)::int from practice_session_item i where i.session_id = s.id) as items
      from practice_session s where s.user_id = ${userId} order by s.started_at desc limit ${limit}`),
  ).map((r) => ({ ...r, started_at: new Date(r.started_at).toISOString(), completed_at: r.completed_at ? new Date(r.completed_at).toISOString() : null }));
}
