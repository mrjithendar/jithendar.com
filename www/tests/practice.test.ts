import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { and, eq, sql } from "drizzle-orm";
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { schema, type Db } from "@/db";
import { rowsOf } from "@/db/rows";
import type { SessionUser } from "@/lib/session";
import { freshDb } from "./db-helpers";

vi.mock("server-only", () => ({}));
vi.mock("next/headers", () => ({ headers: async () => new Headers({ "x-forwarded-for": "203.0.113.9" }), cookies: async () => ({ getAll: () => [] }) }));
vi.mock("next/cache", () => ({ revalidatePath: () => {} }));
let currentUser: SessionUser | null = null;
vi.mock("@/lib/session", () => ({ getSessionUser: async () => currentUser, requireUser: async () => currentUser, requireRole: async () => currentUser }));

const { readCatalog, seedPractice, resetPracticeSeed } = await import("@/lib/practice/seed");
const { broadcastInvalidate } = await import("@/lib/cache-bus");
const catalog = await import("@/lib/practice/catalog");
const { outputsEqual, pyRepr, callRepr } = await import("@/lib/practice/compare");
const { grade, testsFor, buildJob } = await import("@/lib/practice/evaluator");
const submissions = await import("@/lib/practice/submissions");
const progress = await import("@/lib/practice/progress");
const sessions = await import("@/lib/practice/sessions");
const admin = await import("@/lib/practice/admin");
const { ground } = await import("@/lib/practice/ai/tutor");
const { weakTopics, comfortLevel, recommend } = await import("@/lib/practice/adaptive");
const { reviewCode } = await import("@/lib/practice/review");
const { savePracticeSettings, DEFAULT_SETTINGS } = await import("@/lib/practice/settings");

const FULL = readCatalog(path.resolve(import.meta.dirname, "../content/python-practice/catalog.generated.json"));
const SUBSET_SLUGS = ["reverse-word-order", "count-word-frequencies", "classify-latency", "paginate-api"];
const SUBSET = { ...FULL, problems: FULL.problems.filter((p) => SUBSET_SLUGS.includes(p.slug)) };
let subsetFile: string;

const userRow = (id: string, role = "user") => ({ id, name: id, email: `${id}@example.com`, role });
const as = (id: string, role: "admin" | "user" = "user"): SessionUser => ({ id, name: id, email: `${id}@example.com`, role, emailVerified: true, image: null, sessionCreatedAt: new Date() });
const adminActor = { id: "admin", role: "admin" as const, label: "admin@example.com" };

// --- A fake executor: records every job and answers with outputs from `solver`. -------------------------------
type Job = { id: string; body: { tests: { id: string; args: unknown[] }[]; code: string; entrypoint: string; prelude: string } };
const jobs: Job[] = [];
let solver: (args: unknown[]) => unknown = () => null;
let executorDown = false;
async function fakeFetch(input: string | URL | Request, init?: RequestInit): Promise<Response> {
  const url = String(input);
  if (!url.startsWith("http://executor.test")) return new Response("unexpected", { status: 500 });
  if (executorDown) throw new TypeError("connection refused");
  if (init?.method === "POST" && url.endsWith("/v1/jobs")) {
    const job = { id: `job${jobs.length + 1}`, body: JSON.parse(String(init.body)) };
    jobs.push(job);
    return Response.json({ id: job.id, status: "queued", created_at: 0, queue_position: 1 }, { status: 202 });
  }
  const m = /\/v1\/jobs\/(\w+)$/.exec(url);
  const job = jobs.find((j) => j.id === m?.[1]);
  if (!job) return Response.json({ detail: "not found" }, { status: 404 });
  const tests = job.body.tests.map((t) => ({ id: t.id, status: "ok", output: solver(t.args), duration_ms: 1.5, memory_kb: 9000 }));
  return Response.json({ id: job.id, status: "done", created_at: 0, result: { status: "completed", python: "3.13.1", tests } });
}

let db: Db;
beforeAll(() => {
  subsetFile = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "practice-")), "catalog.json");
  fs.writeFileSync(subsetFile, JSON.stringify(SUBSET));
  process.env.PRACTICE_CATALOG_PATH = subsetFile;
});
afterAll(() => {
  delete process.env.PRACTICE_CATALOG_PATH;
});

beforeEach(async () => {
  vi.stubGlobal("fetch", fakeFetch);
  process.env.PRACTICE_EXECUTOR_URL = "http://executor.test";
  process.env.PRACTICE_EXECUTOR_TOKEN = "t".repeat(40);
  jobs.length = 0;
  executorDown = false;
  currentUser = null;
  db = await freshDb();
  resetPracticeSeed();
  broadcastInvalidate("practice");
  for (const id of ["admin", "ana", "bo"]) await db.insert(schema.user).values(userRow(id, id === "admin" ? "admin" : "user"));
});

async function enableExecution() {
  await savePracticeSettings(adminActor, { ...DEFAULT_SETTINGS, execution: { ...DEFAULT_SETTINGS.execution, enabled: true }, ai: { ...DEFAULT_SETTINGS.ai, apiKey: "" } });
}

const reverse = (args: unknown[]) => String(args[0]).split(/\s+/).filter(Boolean).reverse().join(" ");

async function submitAndWait(user: string, slug: string, kind: "run" | "submit", key: string, extra: Record<string, unknown> = {}) {
  const created = await submissions.createSubmission(user, { slug, code: "def reverse_words(s):\n    return s\n", kind, idempotencyKey: key, ...extra });
  return submissions.getSubmission(user, created.id);
}

describe("catalog", () => {
  it("the generated catalog has 100 validated problems across all roles and levels", () => {
    expect(FULL.problems.length).toBeGreaterThanOrEqual(100);
    expect(FULL.roles.length).toBe(20);
    for (const d of ["beginner", "easy", "medium", "hard", "expert"]) expect(FULL.problems.some((p) => p.difficulty === d)).toBe(true);
    for (const r of FULL.roles) expect(FULL.problems.filter((p) => p.roles.includes(r.slug)).length).toBeGreaterThanOrEqual(3);
    for (const p of FULL.problems) {
      expect(p.hints).toHaveLength(3);
      expect(p.tests.filter((t) => t.visibility === "hidden").length).toBeGreaterThanOrEqual(2);
      expect(p.tests.some((t) => t.example)).toBe(true);
    }
  });

  it("seeds once, versions changed seed problems, and leaves admin-edited problems alone", async () => {
    expect(await seedPractice(SUBSET)).toEqual({ created: 4, updated: 0 });
    expect(await seedPractice(SUBSET)).toEqual({ created: 0, updated: 0 });
    const changed = { ...SUBSET, problems: SUBSET.problems.map((p) => (p.slug === "reverse-word-order" ? { ...p, title: "Reverse words (v2)", content_hash: "changed" } : p)) };
    expect(await seedPractice(changed)).toEqual({ created: 0, updated: 1 });
    const [row] = await db.select().from(schema.practiceProblem).where(eq(schema.practiceProblem.slug, "reverse-word-order"));
    expect(row!.currentVersion).toBe(2);
    expect((await db.select().from(schema.practiceProblemVersion).where(eq(schema.practiceProblemVersion.problemId, row!.id))).length).toBe(2);
    await db.update(schema.practiceProblem).set({ source: "admin" }).where(eq(schema.practiceProblem.id, row!.id));
    expect(await seedPractice({ ...changed, problems: changed.problems.map((p) => ({ ...p, content_hash: "again" })) })).toEqual({ created: 0, updated: 3 });
  });

  it("public problem views never contain hints, solutions or hidden tests", async () => {
    const p = await catalog.getPublicProblem("reverse-word-order");
    const text = JSON.stringify(p);
    const source = SUBSET.problems.find((x) => x.slug === "reverse-word-order")!;
    expect(text).not.toContain(source.solution.code.trim());
    for (const h of source.hints) expect(text).not.toContain(h);
    expect(p.examples.length).toBe(source.tests.filter((t) => t.example).length);
    expect(p.hiddenTestCount).toBe(source.tests.filter((t) => t.visibility === "hidden").length);
    expect(Object.keys(p)).not.toContain("solution");
  });
});

describe("hidden-test boundary", () => {
  it("only the grader, seeder, catalog (examples) and admin read practice_test_case", () => {
    const root = path.resolve(import.meta.dirname, "../src");
    const files: string[] = [];
    const walk = (d: string) => fs.readdirSync(d, { withFileTypes: true }).forEach((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : /\.tsx?$/.test(e.name) && files.push(path.join(d, e.name))));
    walk(root);
    const users = files.filter((f) => /practiceTestCase|practice_test_case/.test(fs.readFileSync(f, "utf8"))).map((f) => path.relative(root, f));
    expect(users.sort()).toEqual(["db/schema.ts", "lib/practice/admin.ts", "lib/practice/catalog.ts", "lib/practice/evaluator.ts", "lib/practice/seed.ts"]);
    // The catalog only selects examples (is_example and public).
    expect(fs.readFileSync(path.join(root, "lib/practice/catalog.ts"), "utf8")).toMatch(/isExample, true\)[\s\S]*visibility, "public"/);
  });
});

describe("grading", () => {
  it("compares JSON outputs with the configured comparator", () => {
    expect(outputsEqual({ a: [1, 2] }, { a: [1, 2] })).toBe(true);
    expect(outputsEqual(3, 3.0)).toBe(true);
    expect(outputsEqual([1, 2], [2, 1])).toBe(false);
    expect(outputsEqual([1, 2], [2, 1], "unordered")).toBe(true);
    expect(outputsEqual([0.1 + 0.2], [0.3], "float")).toBe(true);
    expect(outputsEqual(true, 1, "float")).toBe(false);
    expect(pyRepr({ __set__: [1, 2] })).toBe("{1, 2}");
    expect(callRepr("f", [[1], "a"], { k: null })).toBe("f([1], 'a', k=None)");
  });

  it("sends inputs but never expected outputs to the sandbox, and hides hidden-test details from users", async () => {
    const rec = await catalog.getProblemRecord("reverse-word-order");
    const tests = await testsFor(rec.problem.id, rec.version.version, "submit");
    const job = buildJob(rec.version, tests, { code: "x", runtime: "python-3.13", user: "u", idempotencyKey: "k", purpose: "submit", caps: DEFAULT_SETTINGS.execution });
    expect(JSON.stringify(job.tests)).not.toContain("expected");
    expect(job.tests.map((t) => t.id)).toEqual(tests.map((_, i) => `t${i}`));
    const result = { status: "completed" as const, tests: tests.map((t, i) => ({ id: `t${i}`, status: "ok" as const, output: i === tests.length - 1 ? "wrong" : t.expected, stdout: "secret print" })) };
    const g = grade(rec.version, tests, result);
    expect(g.verdict).toBe("wrong_answer");
    const hidden = g.results.filter((r) => r.visibility === "hidden");
    expect(hidden.length).toBeGreaterThan(0);
    for (const h of hidden) expect(Object.keys(h).sort()).toEqual(["index", "status", "visibility"]);
    expect(grade(rec.version, tests, { status: "syntax_error", tests: [], load: { status: "syntax_error", error: { type: "SyntaxError", message: "invalid syntax", line: 3 } } }).verdict).toBe("syntax_error");
  });
});

describe("submissions", () => {
  it("refuses to run code until execution is enabled", async () => {
    await catalog.listProblems();
    await expect(submissions.createSubmission("ana", { slug: "reverse-word-order", code: "x", kind: "run", idempotencyKey: "aaaaaaaa1" })).rejects.toMatchObject({ code: "execution_disabled" });
  });

  it("grades an independent solve once, awards XP and a badge, and is idempotent", async () => {
    await enableExecution();
    solver = reverse;
    const done = await submitAndWait("ana", "reverse-word-order", "submit", "key-ana-1");
    expect(done.verdict).toBe("accepted");
    expect(done.independent).toBe(true);
    expect(done.badges).toContain("python-beginner");
    // Same idempotency key → same submission, no second job.
    const again = await submissions.createSubmission("ana", { slug: "reverse-word-order", code: "different", kind: "submit", idempotencyKey: "key-ana-1" });
    expect(again.id).toBe(done.id);
    expect(jobs.length).toBe(1);
    // Polling again does not apply the outcome twice.
    await submissions.getSubmission("ana", done.id);
    const [prog] = await db.select().from(schema.practiceProgress).where(eq(schema.practiceProgress.userId, "ana"));
    expect(prog!.status).toBe("solved");
    expect(prog!.submits).toBe(1);
    const [profile] = await db.select().from(schema.practiceProfile).where(eq(schema.practiceProfile.userId, "ana"));
    expect(profile!.xp).toBe(10);
    expect(profile!.currentStreak).toBe(1);
    // Others can't read it.
    await expect(submissions.getSubmission("bo", done.id)).rejects.toMatchObject({ status: 404 });
  });

  it("records an infrastructure error without touching progress when the executor is down", async () => {
    await enableExecution();
    executorDown = true;
    await expect(submissions.createSubmission("ana", { slug: "reverse-word-order", code: "x", kind: "submit", idempotencyKey: "down-1-longer-key" })).rejects.toMatchObject({ code: "executor_unavailable" });
    const [sub] = await db.select().from(schema.practiceSubmission);
    expect(sub!.verdict).toBe("infrastructure_error");
    const [prog] = await db.select().from(schema.practiceProgress);
    expect(prog?.submits ?? 0).toBe(0);
  });

  it("hints are progressive, and a revealed solution makes a later accept 'assisted' with no XP", async () => {
    await enableExecution();
    await expect(progress.revealHint("bo", "reverse-word-order", 2)).rejects.toMatchObject({ code: "hint_order" });
    expect(await progress.revealHint("bo", "reverse-word-order", 1)).toHaveLength(1);
    expect(await progress.revealHint("bo", "reverse-word-order", 2)).toHaveLength(2);
    const sol = await progress.revealSolution("bo", "reverse-word-order");
    expect(sol.code).toContain("def reverse_words");
    solver = reverse;
    const done = await submitAndWait("bo", "reverse-word-order", "submit", "bo-key-12345");
    expect(done.verdict).toBe("accepted");
    expect(done.independent).toBe(false);
    const [prog] = await db.select().from(schema.practiceProgress).where(eq(schema.practiceProgress.userId, "bo"));
    expect(prog!.status).toBe("solved_assisted");
    expect(prog!.hintsUsed).toBe(2);
    const [profile] = await db.select().from(schema.practiceProfile).where(eq(schema.practiceProfile.userId, "bo"));
    expect(profile!.xp).toBe(0);
    const events = (await db.select().from(schema.practiceActivityEvent).where(eq(schema.practiceActivityEvent.userId, "bo"))).map((e) => e.type);
    expect(events).toEqual(expect.arrayContaining(["hint_requested", "solution_revealed", "code_submitted", "submission_graded"]));
  });

  it("wrong answers count as failures per topic and drive adaptive recommendations", async () => {
    await enableExecution();
    solver = () => "nope";
    const done = await submitAndWait("ana", "reverse-word-order", "submit", "fail-1-longer-key");
    expect(done.verdict).toBe("wrong_answer");
    const skills = await db.select().from(schema.practiceSkill).where(eq(schema.practiceSkill.userId, "ana"));
    expect(skills.every((s) => s.failures === 1 && s.passes === 0)).toBe(true);
    const recs = await recommend("ana", 3);
    expect(recs.length).toBeGreaterThan(0);
    expect(recs.every((r) => r.reason.length > 10)).toBe(true);
  });
});

describe("sessions", () => {
  it("timed sessions keep a server deadline, refuse late submissions and expire on read", async () => {
    await enableExecution();
    const { id } = await sessions.createSession("ana", { mode: "timed", count: 2, durationMinutes: 15 });
    const view = await sessions.getSession("ana", id);
    expect(view.items).toHaveLength(2);
    expect(view.remainingMs).toBeGreaterThan(14 * 60_000);
    await expect(sessions.getSession("bo", id)).rejects.toMatchObject({ status: 404 });
    await expect(progress.revealSolution("ana", view.items[0]!.slug, id)).rejects.toMatchObject({ code: "solution_locked" });
    await db.update(schema.practiceSession).set({ deadlineAt: new Date(Date.now() - 1000) }).where(eq(schema.practiceSession.id, id));
    await expect(submissions.createSubmission("ana", { slug: view.items[0]!.slug, code: "x", kind: "submit", sessionId: id, idempotencyKey: "late-1-longer-key" })).rejects.toMatchObject({ code: "session_closed" });
    const expired = await sessions.getSession("ana", id);
    expect(expired.status).toBe("expired");
    expect(expired.score).toMatchObject({ percent: 0 });
  });

  it("mock interviews disable hints and produce rubric feedback", async () => {
    await enableExecution();
    const { id } = await sessions.createSession("ana", { mode: "mock", count: 1, roles: [], difficulties: ["beginner"] });
    // Pin the randomly chosen question to one the fake executor can answer.
    const rec = await catalog.getProblemRecord("reverse-word-order");
    await db.update(schema.practiceSessionItem).set({ problemId: rec.problem.id, version: rec.version.version }).where(eq(schema.practiceSessionItem.sessionId, id));
    const view = await sessions.getSession("ana", id);
    await expect(progress.revealHint("ana", view.items[0]!.slug, 1, id)).rejects.toMatchObject({ code: "hints_disabled" });
    solver = reverse;
    await submitAndWait("ana", "reverse-word-order", "submit", "mock-1-longer-key", { sessionId: id });
    const done = await sessions.sessionAction("ana", id, { action: "finish" });
    expect(done.status).toBe("completed");
    expect(done.items[0]!.score).toBe(100);
    expect((done.items[0]!.feedback as { scores: Record<string, number> }).scores.correctness).toBe(5);
  });
});

describe("API", () => {
  it("requires a session (401 auth_required) and a same-site origin", async () => {
    const { POST } = await import("@/app/api/practice/run/route");
    const req = (origin: string | null) =>
      new Request("https://jithendar.com/api/practice/run", { method: "POST", headers: { "content-type": "application/json", host: "jithendar.com", ...(origin ? { origin } : {}) }, body: "{}" });
    const guest = await POST(req("https://jithendar.com"));
    expect(guest.status).toBe(401);
    expect(await guest.json()).toMatchObject({ code: "auth_required" });
    currentUser = as("ana");
    expect((await POST(req("https://evil.example"))).status).toBe(403);
    expect((await POST(req(null))).status).toBe(403);
    const bad = await POST(req("https://jithendar.com"));
    expect(bad.status).toBe(400);
  });

  it("guests get 401 for hints and solutions too", async () => {
    const { POST } = await import("@/app/api/practice/problems/[slug]/assist/route");
    const res = await POST(new Request("https://jithendar.com/x", { method: "POST", headers: { "content-type": "application/json", host: "jithendar.com", origin: "https://jithendar.com" }, body: JSON.stringify({ action: "solution", confirm: true }) }), { params: Promise.resolve({ slug: "reverse-word-order" }) });
    expect(res.status).toBe(401);
  });
});

describe("admin", () => {
  const base = () => {
    const src = SUBSET.problems.find((p) => p.slug === "classify-latency")!;
    return {
      slug: "new-problem",
      title: "Brand new practice problem",
      difficulty: "easy",
      roles: ["devops-engineer"],
      topics: ["loops"],
      minutes: 10,
      description: "Compute the total of a list of integers, returning zero for an empty list. A completely fresh statement.",
      constraints: "",
      entrypoint: "total",
      starterCode: "def total(xs):\n    pass\n",
      comparator: "exact",
      hints: ["a", "b", "c"],
      solution: { code: "def total(xs):\n    return sum(xs)\n", explanation: "Sum.", time: "O(n)", space: "O(1)", alternatives: "", edgeCases: "", production: "" },
      limits: { perTestSeconds: 2, totalSeconds: 10, memoryMb: 256 },
      tests: [
        { visibility: "public", example: true, args: [[1, 2]] as unknown[], expected: 3 as unknown },
        { visibility: "hidden", args: [[]], expected: 0 },
        { visibility: "hidden", args: [[5]] },
      ],
      _unused: src.slug,
    };
  };

  it("runs quality checks and duplicate detection, versions edits, and gates publishing on expected outputs", async () => {
    await catalog.listProblems();
    await expect(admin.saveProblem(adminActor, null, { ...base(), hints: ["only one"] })).rejects.toMatchObject({ status: 400 });
    await expect(admin.saveProblem(adminActor, null, { ...base(), starterCode: "def other():\n    pass\n" })).rejects.toThrow(/starter code must define total/);
    const dupSource = SUBSET.problems.find((p) => p.slug === "classify-latency")!;
    await expect(admin.saveProblem(adminActor, null, { ...base(), title: dupSource.title, description: dupSource.description })).rejects.toMatchObject({ code: "duplicate" });
    const id = await admin.saveProblem(adminActor, null, base());
    await expect(admin.setProblemStatus(adminActor, id, "published")).rejects.toThrow(/no expected output/);
    const fixed = base();
    fixed.tests[2] = { visibility: "hidden", example: false, args: [[5]], expected: 5 };
    await admin.saveProblem(adminActor, id, fixed);
    await admin.setProblemStatus(adminActor, id, "published");
    const { problem, versions } = await admin.getAdminProblem(id);
    expect(problem.status).toBe("published");
    expect(versions.map((v) => v.version)).toEqual([2, 1]);
    const audits = rowsOf<{ action: string }>(await db.execute(sql`select action from audit_log where action like 'practice.%'`)).map((a) => a.action);
    expect(audits).toEqual(expect.arrayContaining(["practice.problem.save", "practice.problem.publish"]));
    expect((await catalog.listProblems()).some((p) => p.slug === "new-problem")).toBe(true);
  });

  it("only staff can edit content and only admins can change settings", async () => {
    const user = { id: "ana", role: "user" as const, label: "ana" };
    await expect(admin.saveProblem(user, null, base())).rejects.toMatchObject({ status: 403 });
    await expect(savePracticeSettings({ ...user }, DEFAULT_SETTINGS)).rejects.toMatchObject({ status: 403 });
  });
});

describe("tutor, review and adaptive helpers", () => {
  it("flags answers that contradict the grader and withholds full solutions", () => {
    const answer = { summary: "Your code is correct.", points: [], next_step: "", code: "def solve(x):\n    return x\n" };
    const g = ground(answer, { facts: { verdict: "wrong_answer", passed: 1, total: 5 }, entrypoint: "solve", solutionRevealed: false });
    expect(g.grounding).toMatch(/1 of 5/);
    expect(g.answer.code).toBe("");
    expect(ground(answer, { facts: { verdict: "accepted", passed: 5, total: 5 }, entrypoint: "solve", solutionRevealed: true }).grounding).toBeNull();
  });

  it("scores code with transparent heuristics", () => {
    const fb = reviewCode({ code: "def f(xs):\n    try:\n        return [x for x in xs]\n    except:\n        pass\n", verdict: "accepted", passed: 4, total: 4, maxMs: 1, perTestSeconds: 2, runsBeforeSubmit: 1, customInputsTried: 2 });
    expect(fb.scores.correctness).toBe(5);
    expect(fb.notes.errorHandling.join(" ")).toMatch(/bare `except:`/);
    expect(fb.scores.testing).toBe(4);
  });

  it("finds weak topics and the comfortable level from recorded results", () => {
    expect(weakTopics([{ topic: "asyncio", attempts: 4, passes: 1, failures: 3 }, { topic: "strings", attempts: 4, passes: 4, failures: 0 }]).map((s) => s.topic)).toEqual(["asyncio"]);
    expect(comfortLevel({ beginner: 3, easy: 2, medium: 1 })).toBe("easy");
    expect(comfortLevel({})).toBeNull();
  });
});

describe("data rights", () => {
  it("exports and deletes a user's practice data", async () => {
    await enableExecution();
    solver = reverse;
    await submitAndWait("ana", "reverse-word-order", "submit", "export-1-key");
    const { exportPracticeData, deletePracticeData } = await import("@/lib/practice/profile");
    const data = await exportPracticeData("ana");
    expect(data.submissions.length).toBe(1);
    expect(JSON.stringify(data)).not.toContain("bo@example.com");
    await deletePracticeData("ana");
    expect(await db.select().from(schema.practiceSubmission).where(eq(schema.practiceSubmission.userId, "ana"))).toEqual([]);
    expect(await db.select().from(schema.practiceProgress).where(and(eq(schema.practiceProgress.userId, "ana")))).toEqual([]);
  });
});
