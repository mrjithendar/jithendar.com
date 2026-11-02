import "server-only";
import { and, asc, eq } from "drizzle-orm";
import { getDb, schema } from "@/db";
import type { PracticeTestResult } from "@/db/schema";
import { outputsEqual } from "./compare";
import type { JobRequest, RunnerResult, RunnerTest } from "./executor-client";
import type { Comparator, Verdict } from "./types";

/**
 * The trusted grader. This is the only runtime module that reads hidden test cases and expected outputs
 * (tests/practice-boundaries.test.ts enforces it). The sandbox receives the code and the inputs only; outputs
 * come back and are compared here. Results shown to users carry details for public tests only.
 */

export type Kind = "run" | "submit" | "validate";
type TestRow = typeof schema.practiceTestCase.$inferSelect;
type VersionRow = typeof schema.practiceProblemVersion.$inferSelect;
export type CustomTest = { args: unknown[]; kwargs?: Record<string, unknown> };

/** Tests of a run in a stable order: runs use public tests, submissions and validation use all of them. */
export async function testsFor(problemId: string, version: number, kind: Kind): Promise<TestRow[]> {
  const db = await getDb();
  const rows = await db
    .select()
    .from(schema.practiceTestCase)
    .where(and(eq(schema.practiceTestCase.problemId, problemId), eq(schema.practiceTestCase.version, version)))
    .orderBy(asc(schema.practiceTestCase.ordinal));
  return kind === "run" ? rows.filter((t) => t.visibility === "public") : rows;
}

const OUTPUT_BYTES = 16_384;

/** The executor request. Test ids are positional (t0, t1, …, then c0… for custom inputs): they reveal nothing. */
export function buildJob(
  v: VersionRow,
  tests: TestRow[],
  opts: { code: string; runtime: string; user: string; idempotencyKey: string; purpose: Kind; custom?: CustomTest[]; caps: { perTestSeconds: number; totalSeconds: number; memoryMb: number } },
): JobRequest {
  const custom = opts.custom ?? [];
  return {
    idempotency_key: opts.idempotencyKey,
    user: opts.user,
    runtime: opts.runtime,
    code: opts.code,
    entrypoint: v.entrypoint,
    prelude: v.prelude,
    tests: [...tests.map((t, i) => ({ id: `t${i}`, args: t.args, kwargs: t.kwargs })), ...custom.map((c, i) => ({ id: `c${i}`, args: c.args, kwargs: c.kwargs ?? {} }))],
    limits: {
      per_test_seconds: Math.min(v.limits.perTestSeconds, opts.caps.perTestSeconds),
      total_seconds: Math.min(v.limits.totalSeconds, opts.caps.totalSeconds),
      memory_mb: Math.min(v.limits.memoryMb, opts.caps.memoryMb),
      output_bytes: OUTPUT_BYTES,
    },
    purpose: opts.purpose,
  };
}

export type Graded = {
  verdict: Verdict;
  passed: number;
  total: number;
  results: PracticeTestResult[];
  custom: PracticeTestResult[];
  loadError: { type: string; message: string; line?: number; offset?: number } | null;
  maxMs: number | null;
  maxMemoryKb: number | null;
  pythonVersion: string | null;
};

const clip = (s: string | undefined, n: number) => (s && s.length > n ? `${s.slice(0, n)}…` : s);

function statusOf(t: RunnerTest | undefined, expected: unknown, comparator: Comparator, tolerance: number): PracticeTestResult["status"] {
  if (!t) return "skipped";
  if (t.status === "ok") return t.unserializable === undefined && outputsEqual(t.output, expected, comparator, tolerance) ? "passed" : "failed";
  if (t.status === "timeout") return "timeout";
  if (t.status === "memory") return "memory";
  if (t.status === "skipped") return "skipped";
  return "error";
}

/** Compare the sandbox's outputs with the expected values and produce user-safe results. */
export function grade(v: VersionRow, tests: TestRow[], result: RunnerResult, customCount = 0): Graded {
  const base = { pythonVersion: result.python ?? null };
  if (result.status !== "completed") {
    const err = result.load?.error;
    const verdict: Verdict = result.status === "syntax_error" ? "syntax_error" : result.status === "missing_entrypoint" ? "missing_entrypoint" : result.status === "internal_error" ? "infrastructure_error" : "runtime_error";
    return {
      ...base,
      verdict,
      passed: 0,
      total: tests.length,
      results: [],
      custom: [],
      loadError: err ? { type: err.type, message: clip(err.message, 1000) ?? "", ...(err.line ? { line: err.line } : {}), ...(err.offset ? { offset: err.offset } : {}) } : { type: "Error", message: "The code could not be loaded." },
      maxMs: null,
      maxMemoryKb: null,
    };
  }
  const byId = new Map(result.tests.map((t) => [t.id, t]));
  const tolerance = typeof v.tolerance === "number" ? v.tolerance : 1e-6;
  const comparator = v.comparator as Comparator;
  let maxMs = 0;
  let maxMem = 0;
  const results: PracticeTestResult[] = tests.map((test, i) => {
    const t = byId.get(`t${i}`);
    const status = statusOf(t, test.expected, comparator, tolerance);
    maxMs = Math.max(maxMs, t?.duration_ms ?? 0);
    maxMem = Math.max(maxMem, t?.memory_kb ?? 0);
    if (test.visibility === "hidden") return { index: i, visibility: "hidden", status };
    return {
      index: i,
      visibility: "public",
      status,
      args: test.args,
      kwargs: test.kwargs,
      expected: test.expected,
      ...(t?.status === "ok" && t.unserializable === undefined ? { actual: t.output } : {}),
      ...(t?.output_repr ? { actualRepr: clip(t.output_repr, 2000) } : {}),
      ...(t?.unserializable ? { error: { type: "UncomparableOutput", message: t.unserializable } } : {}),
      ...(t?.stdout ? { stdout: clip(t.stdout, 2000) } : {}),
      ...(t?.error ? { error: { type: t.error.type, message: clip(t.error.message, 1000) ?? "", traceback: clip(t.error.traceback, 3000) } } : {}),
      ...(t?.duration_ms !== undefined ? { ms: Math.round(t.duration_ms * 100) / 100 } : {}),
    };
  });
  const custom: PracticeTestResult[] = Array.from({ length: customCount }, (_, i) => {
    const t = byId.get(`c${i}`);
    return {
      index: i,
      visibility: "public",
      status: !t ? "skipped" : t.status === "ok" ? "passed" : t.status === "timeout" ? "timeout" : t.status === "memory" ? "memory" : "error",
      ...(t?.output !== undefined ? { actual: t.output } : {}),
      ...(t?.output_repr ? { actualRepr: clip(t.output_repr, 2000) } : {}),
      ...(t?.stdout ? { stdout: clip(t.stdout, 2000) } : {}),
      ...(t?.error ? { error: { type: t.error.type, message: clip(t.error.message, 1000) ?? "", traceback: clip(t.error.traceback, 3000) } } : {}),
    };
  });
  const passed = results.filter((r) => r.status === "passed").length;
  const firstBad = results.find((r) => r.status !== "passed");
  const verdict: Verdict = !firstBad
    ? "accepted"
    : firstBad.status === "timeout" || firstBad.status === "skipped"
      ? "timeout"
      : firstBad.status === "memory"
        ? "memory"
        : firstBad.status === "error" && !(firstBad.error?.type === "UncomparableOutput")
          ? "runtime_error"
          : "wrong_answer";
  return { ...base, verdict, passed, total: tests.length, results, custom, loadError: null, maxMs: maxMs || null, maxMemoryKb: maxMem || null };
}
