import "server-only";
import { and, asc, desc, eq, ne, sql } from "drizzle-orm";
import { z } from "zod";
import { getDb, schema } from "@/db";
import { rowsOf } from "@/db/rows";
import { audit } from "../audit";
import { broadcastInvalidate } from "../cache-bus";
import type { Actor } from "../posts";
import { aiUsageSummary } from "./ai/tutor";
import { invalidateCatalog, listRoles, listTopics } from "./catalog";
import { outputsEqual } from "./compare";
import { PracticeError } from "./errors";
import { buildJob, testsFor } from "./evaluator";
import { executorStatus, getJob, submitJob, userRef } from "./executor-client";
import { contentHash } from "./seed";
import { executionAvailable, getPracticeSettings } from "./settings";
import { COMPARATORS, DIFFICULTIES, type Comparator } from "./types";

/**
 * Admin → Python practice. Staff (admins and authors) manage problems, roles, topics and the daily
 * challenge; settings are admin-only (settings.ts). Every change is written to the audit log (practice.*).
 * Saving a problem always creates a new immutable version, so old submissions stay interpretable.
 */

function staffOnly(actor: Actor) {
  if (actor.role !== "admin" && actor.role !== "author") throw new PracticeError("Only staff can manage practice content.", 403, "forbidden");
}

function changed() {
  invalidateCatalog();
  broadcastInvalidate("practice");
}

const lines = z.preprocess((v) => (typeof v === "string" ? v.split("\n").map((s) => s.trim()).filter(Boolean) : v), z.array(z.string().max(500)).max(30));

export const testCaseInput = z.object({
  visibility: z.enum(["public", "hidden"]),
  example: z.boolean().default(false),
  args: z.array(z.unknown()).max(50).default([]),
  kwargs: z.record(z.string(), z.unknown()).default({}),
  expected: z.unknown().optional(),
  explanation: z.string().max(1000).default(""),
  label: z.string().max(120).default(""),
});

export const problemInput = z.object({
  slug: z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, "Use lowercase words separated by hyphens.").max(80),
  title: z.string().trim().min(5).max(120),
  difficulty: z.enum(DIFFICULTIES),
  roles: z.array(z.string()).min(1, "Pick at least one role.").max(20),
  topics: z.array(z.string()).min(1, "Pick at least one topic.").max(20),
  minutes: z.coerce.number().int().min(1).max(240),
  dailyEligible: z.boolean().default(true),
  description: z.string().trim().min(40, "Describe the problem in at least 40 characters.").max(8000),
  constraints: lines,
  ioInput: z.string().max(500).default(""),
  ioOutput: z.string().max(500).default(""),
  entrypoint: z.string().regex(/^[A-Za-z_][A-Za-z0-9_]{0,63}$/, "The entry point must be a Python identifier."),
  starterCode: z.string().min(1).max(20_000),
  prelude: z.string().max(20_000).default(""),
  comparator: z.enum(COMPARATORS),
  tolerance: z.coerce.number().min(0).max(1).default(1e-6),
  hints: z.array(z.string().trim().min(1).max(2000)).length(3, "Write exactly three hints: concept, approach, pseudocode."),
  solution: z.object({
    code: z.string().min(1).max(20_000),
    explanation: z.string().trim().min(1).max(5000),
    time: z.string().trim().min(1).max(200),
    space: z.string().trim().min(1).max(200),
    alternatives: lines,
    edgeCases: lines,
    production: lines,
  }),
  limits: z.object({ perTestSeconds: z.coerce.number().min(0.5).max(5), totalSeconds: z.coerce.number().min(2).max(20), memoryMb: z.coerce.number().int().min(64).max(256) }),
  tests: z.array(testCaseInput).min(1).max(60),
  note: z.string().max(500).default(""),
  allowDuplicate: z.boolean().default(false),
});
export type ProblemInput = z.infer<typeof problemInput>;

const defines = (code: string, name: string) => new RegExp(`^\\s*(?:async\\s+)?(?:def|class)\\s+${name}\\b`, "m").test(code) || new RegExp(`^${name}\\s*=`, "m").test(code);

/** Quality checks shared by save and publish. */
export function qualityIssues(p: ProblemInput, known: { roles: Set<string>; topics: Set<string> }): string[] {
  const issues: string[] = [];
  for (const r of p.roles) if (!known.roles.has(r)) issues.push(`Unknown role "${r}".`);
  for (const t of p.topics) if (!known.topics.has(t)) issues.push(`Unknown topic "${t}".`);
  if (!p.tests.some((t) => t.visibility === "public" && t.example)) issues.push("Add at least one public example.");
  if (p.tests.filter((t) => t.visibility === "hidden").length < 2) issues.push("Add at least two hidden tests.");
  if (!defines(p.starterCode, p.entrypoint)) issues.push(`The starter code must define ${p.entrypoint}.`);
  if (!defines(p.solution.code, p.entrypoint)) issues.push(`The reference solution must define ${p.entrypoint}.`);
  if (p.starterCode.trim() === p.solution.code.trim()) issues.push("The starter code is the solution.");
  if (/\b(import\s+(socket|subprocess|ctypes)|os\.system|open\()/.test(p.solution.code)) issues.push("The reference solution uses I/O the sandbox does not allow (sockets, subprocesses, files).");
  return issues;
}

function shingles(text: string): Set<string> {
  const words = text.toLowerCase().match(/[a-z0-9]+/g) ?? [];
  return new Set(words.slice(0, Math.max(0, words.length - 2)).map((_, i) => words.slice(i, i + 3).join(" ")));
}

/** Problems whose title + statement overlap this one by more than half (3-word shingles, Jaccard). */
export async function findDuplicates(slug: string, title: string, description: string): Promise<{ slug: string; title: string; similarity: number }[]> {
  const db = await getDb();
  const others = rowsOf<{ slug: string; title: string; description: string }>(
    await db.execute(sql`select p.slug, v.title, v.description from practice_problem p join practice_problem_version v on v.problem_id = p.id and v.version = p.current_version
      where p.slug <> ${slug} and p.status <> 'archived'`),
  );
  const mine = shingles(`${title} ${description}`);
  return others
    .map((o) => {
      const theirs = shingles(`${o.title} ${o.description}`);
      const inter = [...mine].filter((s) => theirs.has(s)).length;
      const union = new Set([...mine, ...theirs]).size;
      return { slug: o.slug, title: o.title, similarity: union ? inter / union : 0 };
    })
    .filter((o) => o.similarity > 0.5)
    .sort((a, b) => b.similarity - a.similarity);
}

export async function listAdminProblems(filter: { status?: string; q?: string } = {}) {
  const db = await getDb();
  const rows = await db
    .select({
      id: schema.practiceProblem.id,
      slug: schema.practiceProblem.slug,
      title: schema.practiceProblem.title,
      difficulty: schema.practiceProblem.difficulty,
      status: schema.practiceProblem.status,
      source: schema.practiceProblem.source,
      roles: schema.practiceProblem.roles,
      version: schema.practiceProblem.currentVersion,
      updatedAt: schema.practiceProblem.updatedAt,
    })
    .from(schema.practiceProblem)
    .where(filter.status ? eq(schema.practiceProblem.status, filter.status) : undefined)
    .orderBy(asc(schema.practiceProblem.title));
  const q = filter.q?.trim().toLowerCase();
  return q ? rows.filter((r) => r.title.toLowerCase().includes(q) || r.slug.includes(q)) : rows;
}

/** Everything the editor needs, including hidden tests (staff only). */
export async function getAdminProblem(id: string) {
  const db = await getDb();
  const [problem] = await db.select().from(schema.practiceProblem).where(eq(schema.practiceProblem.id, id));
  if (!problem) throw new PracticeError("Problem not found.", 404, "not_found");
  const [version] = await db
    .select()
    .from(schema.practiceProblemVersion)
    .where(and(eq(schema.practiceProblemVersion.problemId, id), eq(schema.practiceProblemVersion.version, problem.currentVersion)));
  const tests = await testsFor(id, problem.currentVersion, "validate");
  const versions = await db
    .select({ version: schema.practiceProblemVersion.version, note: schema.practiceProblemVersion.note, createdAt: schema.practiceProblemVersion.createdAt, createdBy: schema.practiceProblemVersion.createdBy })
    .from(schema.practiceProblemVersion)
    .where(eq(schema.practiceProblemVersion.problemId, id))
    .orderBy(desc(schema.practiceProblemVersion.version));
  const stats = rowsOf<{ submits: number; accepted: number; users: number }>(
    await db.execute(sql`select count(*)::int as submits, count(*) filter (where verdict = 'accepted')::int as accepted, count(distinct user_id)::int as users
      from practice_submission where problem_id = ${id} and kind = 'submit'`),
  )[0];
  return { problem, version: version!, tests, versions, stats };
}

export async function saveProblem(actor: Actor, id: string | null, raw: unknown): Promise<string> {
  staffOnly(actor);
  const parsed = problemInput.safeParse(raw);
  if (!parsed.success) throw new PracticeError(`Check the problem: ${parsed.error.issues.map((i) => `${i.path.join(".") || "input"}: ${i.message}`).join("; ")}`);
  const p = parsed.data;
  const [roles, topics] = await Promise.all([listRoles({ includeHidden: true }), listTopics()]);
  const issues = qualityIssues(p, { roles: new Set(roles.map((r) => r.slug)), topics: new Set(topics.map((t) => t.slug)) });
  if (issues.length) throw new PracticeError(`Quality checks failed: ${issues.join(" ")}`, 400, "quality");
  if (!p.allowDuplicate) {
    const dups = await findDuplicates(p.slug, p.title, p.description);
    if (dups.length) throw new PracticeError(`This looks like a duplicate of ${dups.map((d) => `"${d.title}" (${Math.round(d.similarity * 100)}%)`).join(", ")}. Tick "allow similar problem" to save anyway.`, 409, "duplicate");
  }
  const db = await getDb();
  const savedId = await db.transaction(async (tx) => {
    const clash = await tx
      .select({ id: schema.practiceProblem.id })
      .from(schema.practiceProblem)
      .where(id ? and(eq(schema.practiceProblem.slug, p.slug), ne(schema.practiceProblem.id, id)) : eq(schema.practiceProblem.slug, p.slug));
    if (clash.length) throw new PracticeError("Another problem already uses that slug.", 409, "slug_taken");
    let problemId = id;
    let version = 1;
    const now = new Date();
    const fields = { slug: p.slug, title: p.title, difficulty: p.difficulty, roles: p.roles, topics: p.topics, estimatedMinutes: p.minutes, dailyEligible: p.dailyEligible, source: "admin", updatedAt: now };
    if (!problemId) {
      const [row] = await tx.insert(schema.practiceProblem).values({ ...fields, status: "draft", createdBy: actor.id }).returning({ id: schema.practiceProblem.id });
      problemId = row!.id;
    } else {
      const [current] = await tx.select().from(schema.practiceProblem).where(eq(schema.practiceProblem.id, problemId)).for("update");
      if (!current) throw new PracticeError("Problem not found.", 404, "not_found");
      version = current.currentVersion + 1;
    }
    const body = {
      title: p.title,
      description: p.description,
      entrypoint: p.entrypoint,
      starterCode: p.starterCode,
      prelude: p.prelude,
      comparator: p.comparator,
      tolerance: p.tolerance,
      constraints: p.constraints,
      io: { input: p.ioInput, output: p.ioOutput },
      hints: p.hints,
      solution: p.solution,
      limits: p.limits,
    };
    await tx.insert(schema.practiceProblemVersion).values({ problemId, version, ...body, contentHash: contentHash({ ...body, tests: p.tests }), note: p.note || (version === 1 ? "Created." : "Edited."), createdBy: actor.id });
    await tx.insert(schema.practiceTestCase).values(
      p.tests.map((t, i) => ({ problemId: problemId!, version, ordinal: i, visibility: t.visibility, isExample: t.visibility === "public" && t.example, label: t.label, explanation: t.explanation, args: t.args, kwargs: t.kwargs, expected: t.expected === undefined ? null : t.expected })),
    );
    if (version > 1) await tx.update(schema.practiceProblem).set({ ...fields, currentVersion: version }).where(eq(schema.practiceProblem.id, problemId));
    return problemId;
  });
  await audit(actor, "practice.problem.save", p.slug, { id: savedId, tests: p.tests.length, hidden: p.tests.filter((t) => t.visibility === "hidden").length });
  changed();
  return savedId;
}

export async function setProblemStatus(actor: Actor, id: string, status: "draft" | "published" | "archived"): Promise<void> {
  staffOnly(actor);
  const db = await getDb();
  const { problem, tests } = await getAdminProblem(id);
  if (status === "published") {
    if (tests.some((t) => t.expected === null)) throw new PracticeError("Some tests have no expected output. Validate with “fill expected outputs” or enter them first.", 400, "quality");
    if (!tests.some((t) => t.visibility === "public" && t.isExample)) throw new PracticeError("Add at least one public example before publishing.", 400, "quality");
  }
  await db
    .update(schema.practiceProblem)
    .set({ status, updatedAt: new Date(), ...(status === "published" && !problem.publishedAt ? { publishedAt: new Date() } : {}) })
    .where(eq(schema.practiceProblem.id, id));
  await audit(actor, status === "archived" ? "practice.problem.archive" : `practice.problem.${status === "published" ? "publish" : "unpublish"}`, problem.slug);
  changed();
}

/**
 * Run the reference solution against every test in the sandbox. Reports mismatches; with fillExpected, saves a
 * new version whose expected outputs are the reference solution's (for tests entered without them).
 */
export async function validateProblem(actor: Actor, id: string, opts: { fillExpected?: boolean } = {}) {
  staffOnly(actor);
  if (!(await executionAvailable())) throw new PracticeError("Code execution is not enabled, so the reference solution cannot be run. Enter expected outputs by hand, or enable execution first.", 503, "execution_disabled");
  const settings = await getPracticeSettings();
  const { problem, version, tests } = await getAdminProblem(id);
  const job = buildJob(version, tests, { code: version.solution.code, runtime: settings.execution.defaultRuntime, user: userRef(`admin:${actor.id}`), idempotencyKey: `validate${crypto.randomUUID().replace(/-/g, "")}`, purpose: "validate", caps: settings.execution });
  const created = await submitJob(job);
  let result = created.result;
  for (let i = 0; i < 60 && !result; i++) {
    await new Promise((r) => setTimeout(r, 500));
    const j = await getJob(created.id);
    if (j.status === "failed" || j.status === "cancelled") throw new PracticeError(`Validation could not run: ${j.error ?? j.status}.`, 502, "executor_error");
    result = j.result ?? undefined;
  }
  if (!result) throw new PracticeError("Validation timed out.", 504, "timeout");
  if (result.status !== "completed") return { ok: false, problems: [`The reference solution did not load: ${result.load?.error?.type ?? result.status}: ${result.load?.error?.message ?? ""}`], filled: false };
  const byId = new Map(result.tests.map((t) => [t.id, t]));
  const problems: string[] = [];
  const outputs: unknown[] = [];
  tests.forEach((t, i) => {
    const r = byId.get(`t${i}`);
    if (!r || r.status !== "ok" || r.unserializable) {
      problems.push(`Test ${i + 1}: the reference solution ${r?.status ?? "did not run"}${r?.error ? ` (${r.error.type}: ${r.error.message})` : ""}${r?.unserializable ? ` (${r.unserializable})` : ""}.`);
      outputs.push(undefined);
      return;
    }
    outputs.push(r.output);
    if (t.expected !== null && !outputsEqual(r.output, t.expected, version.comparator as Comparator, version.tolerance)) problems.push(`Test ${i + 1}: expected ${JSON.stringify(t.expected).slice(0, 200)} but the reference solution returned ${JSON.stringify(r.output).slice(0, 200)}.`);
  });
  let filled = false;
  if (opts.fillExpected && !problems.some((p) => p.includes("did not run") || p.includes("the reference solution error"))) {
    const missing = tests.some((t) => t.expected === null);
    if (missing) {
      const db = await getDb();
      await db.transaction(async (tx) => {
        const next = problem.currentVersion + 1;
        await tx.insert(schema.practiceProblemVersion).values({ ...version, version: next, note: "Expected outputs filled from the reference solution.", createdBy: actor.id, createdAt: new Date() });
        await tx.insert(schema.practiceTestCase).values(tests.map((t, i) => ({ problemId: id, version: next, ordinal: t.ordinal, visibility: t.visibility, isExample: t.isExample, label: t.label, explanation: t.explanation, args: t.args, kwargs: t.kwargs, expected: t.expected ?? outputs[i] ?? null })));
        await tx.update(schema.practiceProblem).set({ currentVersion: next, updatedAt: new Date() }).where(eq(schema.practiceProblem.id, id));
      });
      filled = true;
      changed();
    }
  }
  await audit(actor, "practice.problem.validate", problem.slug, { ok: problems.length === 0, problems: problems.length, filled });
  return { ok: problems.length === 0, problems, filled };
}

// --- Roles, topics, daily challenge ---------------------------------------------------------------------

const percent = z.coerce.number().int().min(0).max(100);
const roleInput = z.object({
  slug: z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/).max(60),
  name: z.string().trim().min(2).max(80),
  description: z.string().trim().min(10).max(500),
  icon: z.string().max(30).default("code"),
  competencies: lines,
  learningPath: lines,
  topics: z.preprocess((v) => (typeof v === "string" ? v.split(/[,\s]+/).filter(Boolean) : v), z.array(z.string()).max(30)),
  scenarios: lines,
  libraries: z.preprocess((v) => (typeof v === "string" ? v.split(",").map((s) => s.trim()).filter(Boolean) : v), z.array(z.string().max(60)).max(30)),
  mix: z.object({ beginner: percent, easy: percent, medium: percent, hard: percent, expert: percent }),
  sort: z.coerce.number().int().min(0).max(10_000).default(100),
  status: z.enum(["active", "hidden"]).default("active"),
});

export async function saveRole(actor: Actor, original: string | null, raw: unknown): Promise<void> {
  staffOnly(actor);
  const parsed = roleInput.safeParse(raw);
  if (!parsed.success) throw new PracticeError(`Check the role: ${parsed.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("; ")}`);
  const r = parsed.data;
  const values = { slug: r.slug, name: r.name, description: r.description, icon: r.icon, competencies: r.competencies, learningPath: r.learningPath, topics: r.topics, scenarios: r.scenarios, libraries: r.libraries, difficultyMix: r.mix, sort: r.sort, status: r.status, updatedAt: new Date() };
  const db = await getDb();
  await db.transaction(async (tx) => {
    if (original && original !== r.slug) {
      await tx.update(schema.practiceRole).set(values).where(eq(schema.practiceRole.slug, original));
      await tx.execute(sql`update practice_problem set roles = array_replace(roles, ${original}, ${r.slug})`);
      await tx.execute(sql`update practice_profile set roles = array_replace(roles, ${original}, ${r.slug})`);
    } else if (original) {
      await tx.update(schema.practiceRole).set(values).where(eq(schema.practiceRole.slug, original));
    } else {
      const inserted = await tx.insert(schema.practiceRole).values(values).onConflictDoNothing().returning();
      if (!inserted.length) throw new PracticeError("A role with that slug already exists.", 409, "slug_taken");
    }
  });
  await audit(actor, "practice.role.save", r.slug, { original });
  changed();
}

const topicInput = z.object({ slug: z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/).max(60), name: z.string().trim().min(2).max(80), area: z.string().max(40), description: z.string().max(500).default(""), sort: z.coerce.number().int().min(0).max(10_000).default(100) });

export async function saveTopic(actor: Actor, raw: unknown): Promise<void> {
  staffOnly(actor);
  const parsed = topicInput.safeParse(raw);
  if (!parsed.success) throw new PracticeError(`Check the topic: ${parsed.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("; ")}`);
  const { SKILL_AREAS } = await import("./types");
  if (!(parsed.data.area in SKILL_AREAS)) throw new PracticeError("Pick one of the skill areas.");
  const db = await getDb();
  await db
    .insert(schema.practiceTopic)
    .values(parsed.data)
    .onConflictDoUpdate({ target: schema.practiceTopic.slug, set: { name: parsed.data.name, area: parsed.data.area, description: parsed.data.description, sort: parsed.data.sort } });
  await audit(actor, "practice.topic.save", parsed.data.slug);
  changed();
}

export async function setDailyChallenge(actor: Actor, day: string, slug: string): Promise<void> {
  staffOnly(actor);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) throw new PracticeError("Use a date like 2026-11-03.");
  const db = await getDb();
  const [problem] = await db.select({ id: schema.practiceProblem.id, status: schema.practiceProblem.status }).from(schema.practiceProblem).where(eq(schema.practiceProblem.slug, slug));
  if (!problem || problem.status !== "published") throw new PracticeError("Pick a published problem.", 400, "not_found");
  await db
    .insert(schema.practiceDailyChallenge)
    .values({ day, problemId: problem.id, chosenBy: actor.id })
    .onConflictDoUpdate({ target: schema.practiceDailyChallenge.day, set: { problemId: problem.id, chosenBy: actor.id } });
  await audit(actor, "practice.daily.set", day, { slug });
}

// --- Operations overview ---------------------------------------------------------------------------------

export async function adminOverview() {
  const db = await getDb();
  const problems = rowsOf<{ status: string; n: number }>(await db.execute(sql`select status, count(*)::int as n from practice_problem group by status`));
  const verdicts = rowsOf<{ verdict: string | null; n: number }>(
    await db.execute(sql`select coalesce(verdict, status) as verdict, count(*)::int as n from practice_submission where created_at > now() - interval '24 hours' group by 1 order by 2 desc`),
  );
  const [queue] = rowsOf<{ pending: number; avg_ms: number | null; users: number }>(
    await db.execute(sql`select count(*) filter (where status in ('queued', 'running'))::int as pending,
      avg(extract(epoch from (finished_at - created_at)) * 1000) filter (where finished_at is not null)::float as avg_ms,
      count(distinct user_id)::int as users from practice_submission where created_at > now() - interval '24 hours'`),
  );
  const abuse = rowsOf<{ email: string; timeouts: number; limited: number; infra: number }>(
    await db.execute(sql`select u.email,
        count(*) filter (where s.verdict in ('timeout', 'memory'))::int as timeouts,
        (select count(*)::int from practice_activity_event e where e.user_id = u.id and e.type = 'rate_limited' and e.created_at > now() - interval '1 hour') as limited,
        count(*) filter (where s.verdict = 'infrastructure_error')::int as infra
      from practice_submission s join "user" u on u.id = s.user_id
      where s.created_at > now() - interval '1 hour' group by u.id, u.email
      having count(*) filter (where s.verdict in ('timeout', 'memory')) >= 10 or count(*) >= 100
      order by 2 desc limit 20`),
  );
  const [active] = rowsOf<{ sessions: number; learners: number }>(
    await db.execute(sql`select (select count(*)::int from practice_session where status = 'active') as sessions,
      (select count(distinct user_id)::int from practice_activity_event where created_at > now() - interval '7 days') as learners`),
  );
  const executor = await executorStatus().then(
    (s) => ({ ok: true as const, ...s }),
    (e: unknown) => ({ ok: false as const, error: (e as Error).message }),
  );
  return {
    problems: Object.fromEntries(problems.map((p) => [p.status, p.n])) as Record<string, number>,
    verdicts,
    queue: { pending: queue?.pending ?? 0, avgMs: queue?.avg_ms ?? null, users: queue?.users ?? 0 },
    abuse,
    active: active ?? { sessions: 0, learners: 0 },
    executor,
    ai: await aiUsageSummary(1),
  };
}
