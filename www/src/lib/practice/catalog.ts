import "server-only";
import { and, asc, count, eq } from "drizzle-orm";
import { getDb, schema } from "@/db";
import { onInvalidate } from "../cache-bus";
import { notFound } from "./errors";
import { ensurePracticeSeeded } from "./seed";
import { DIFFICULTIES, type Comparator, type Difficulty, type ProblemSummary, type PublicProblem } from "./types";

/**
 * Public catalog reads. Everything returned here may be shown to guests: never hints, solutions, hidden tests
 * or the expected output of tests that are not examples (examples are part of the problem statement).
 */
export type RoleRow = typeof schema.practiceRole.$inferSelect;
export type TopicRow = typeof schema.practiceTopic.$inferSelect;

type Cache = { roles?: Promise<RoleRow[]>; topics?: Promise<TopicRow[]>; problems?: Promise<(ProblemSummary & { id: string })[]> };
let cache: Cache = {};
onInvalidate("practice", () => {
  cache = {};
});
export function invalidateCatalog() {
  cache = {};
}

const rank = (d: string) => DIFFICULTIES.indexOf(d as Difficulty);

export async function listRoles(opts: { includeHidden?: boolean } = {}): Promise<RoleRow[]> {
  await ensurePracticeSeeded();
  cache.roles ??= (async () => (await getDb()).select().from(schema.practiceRole).orderBy(asc(schema.practiceRole.sort), asc(schema.practiceRole.name)))();
  const roles = await cache.roles;
  return opts.includeHidden ? roles : roles.filter((r) => r.status === "active");
}

export async function getRole(slug: string): Promise<RoleRow | null> {
  return (await listRoles()).find((r) => r.slug === slug) ?? null;
}

export async function listTopics(): Promise<TopicRow[]> {
  await ensurePracticeSeeded();
  cache.topics ??= (async () => (await getDb()).select().from(schema.practiceTopic).orderBy(asc(schema.practiceTopic.sort)))();
  return cache.topics;
}

/** All published problems (small: hundreds), filtered in memory. */
export async function publishedProblems(): Promise<(ProblemSummary & { id: string })[]> {
  await ensurePracticeSeeded();
  cache.problems ??= (async () => {
    const db = await getDb();
    const rows = await db
      .select({
        id: schema.practiceProblem.id,
        slug: schema.practiceProblem.slug,
        title: schema.practiceProblem.title,
        difficulty: schema.practiceProblem.difficulty,
        roles: schema.practiceProblem.roles,
        topics: schema.practiceProblem.topics,
        minutes: schema.practiceProblem.estimatedMinutes,
      })
      .from(schema.practiceProblem)
      .where(eq(schema.practiceProblem.status, "published"));
    return rows
      .map((r) => ({ ...r, difficulty: r.difficulty as Difficulty }))
      .sort((a, b) => rank(a.difficulty) - rank(b.difficulty) || a.title.localeCompare(b.title));
  })();
  return cache.problems;
}

export type ProblemFilter = { role?: string; difficulty?: string; topic?: string; q?: string };

export function filterProblems<T extends ProblemSummary>(problems: T[], f: ProblemFilter): T[] {
  const q = f.q?.trim().toLowerCase();
  return problems.filter(
    (p) =>
      (!f.role || p.roles.includes(f.role)) &&
      (!f.difficulty || p.difficulty === f.difficulty) &&
      (!f.topic || p.topics.includes(f.topic)) &&
      (!q || p.title.toLowerCase().includes(q) || p.slug.includes(q) || p.topics.some((t) => t.includes(q))),
  );
}

export async function listProblems(f: ProblemFilter = {}): Promise<(ProblemSummary & { id: string })[]> {
  return filterProblems(await publishedProblems(), f);
}

export type ProblemRecord = { problem: typeof schema.practiceProblem.$inferSelect; version: typeof schema.practiceProblemVersion.$inferSelect };

/** Problem and its current version (published only, unless preview is allowed). */
export async function getProblemRecord(slug: string, opts: { allowUnpublished?: boolean; version?: number } = {}): Promise<ProblemRecord> {
  await ensurePracticeSeeded();
  const db = await getDb();
  const [problem] = await db.select().from(schema.practiceProblem).where(eq(schema.practiceProblem.slug, slug));
  if (!problem || (problem.status !== "published" && !opts.allowUnpublished)) throw notFound();
  const [version] = await db
    .select()
    .from(schema.practiceProblemVersion)
    .where(and(eq(schema.practiceProblemVersion.problemId, problem.id), eq(schema.practiceProblemVersion.version, opts.version ?? problem.currentVersion)));
  if (!version) throw notFound();
  return { problem, version };
}

export async function getProblemRecordById(id: string, version?: number): Promise<ProblemRecord> {
  const db = await getDb();
  const [problem] = await db.select().from(schema.practiceProblem).where(eq(schema.practiceProblem.id, id));
  if (!problem) throw notFound();
  const [v] = await db
    .select()
    .from(schema.practiceProblemVersion)
    .where(and(eq(schema.practiceProblemVersion.problemId, id), eq(schema.practiceProblemVersion.version, version ?? problem.currentVersion)));
  if (!v) throw notFound();
  return { problem, version: v };
}

/** The public statement: examples only (with their expected output), plus test counts. */
export async function toPublicProblem({ problem, version }: ProblemRecord): Promise<PublicProblem> {
  const db = await getDb();
  const examples = await db
    .select({
      args: schema.practiceTestCase.args,
      kwargs: schema.practiceTestCase.kwargs,
      expected: schema.practiceTestCase.expected,
      explanation: schema.practiceTestCase.explanation,
      label: schema.practiceTestCase.label,
    })
    .from(schema.practiceTestCase)
    .where(
      and(
        eq(schema.practiceTestCase.problemId, problem.id),
        eq(schema.practiceTestCase.version, version.version),
        eq(schema.practiceTestCase.isExample, true),
        eq(schema.practiceTestCase.visibility, "public"),
      ),
    )
    .orderBy(asc(schema.practiceTestCase.ordinal));
  const counts = await db
    .select({ visibility: schema.practiceTestCase.visibility, n: count() })
    .from(schema.practiceTestCase)
    .where(and(eq(schema.practiceTestCase.problemId, problem.id), eq(schema.practiceTestCase.version, version.version)))
    .groupBy(schema.practiceTestCase.visibility);
  const n = (v: string) => Number(counts.find((c) => c.visibility === v)?.n ?? 0);
  return {
    id: problem.id,
    slug: problem.slug,
    title: version.title,
    difficulty: problem.difficulty as Difficulty,
    roles: problem.roles,
    topics: problem.topics,
    minutes: problem.estimatedMinutes,
    version: version.version,
    description: version.description,
    constraints: version.constraints,
    io: version.io,
    entrypoint: version.entrypoint,
    starterCode: version.starterCode,
    prelude: version.prelude,
    comparator: version.comparator as Comparator,
    examples: examples.map((e) => ({ args: e.args, kwargs: e.kwargs, expected: e.expected, explanation: e.explanation, label: e.label })),
    hintCount: version.hints.length,
    publicTestCount: n("public"),
    hiddenTestCount: n("hidden"),
  };
}

export async function getPublicProblem(slug: string): Promise<PublicProblem> {
  return toPublicProblem(await getProblemRecord(slug));
}

/** Catalog numbers for the landing page. */
export async function catalogStats() {
  const problems = await publishedProblems();
  const byDifficulty = Object.fromEntries(DIFFICULTIES.map((d) => [d, problems.filter((p) => p.difficulty === d).length])) as Record<Difficulty, number>;
  const roles = await listRoles();
  const byRole = Object.fromEntries(roles.map((r) => [r.slug, problems.filter((p) => p.roles.includes(r.slug)).length]));
  return { total: problems.length, byDifficulty, byRole };
}

