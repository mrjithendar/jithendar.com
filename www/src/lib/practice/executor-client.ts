import "server-only";
import { createHash, createHmac } from "node:crypto";
import { PracticeError } from "./errors";
import { executorEnv } from "./settings";

/** HTTP client for the practice executor service (executor/app/main.py). Mirrors its request/response shapes. */

export type RunnerTest = {
  id: string;
  status: "ok" | "error" | "timeout" | "memory" | "crash" | "skipped";
  output?: unknown;
  output_repr?: string;
  unserializable?: string;
  stdout?: string;
  stderr?: string;
  output_truncated?: boolean;
  error?: { type: string; message: string; traceback?: string };
  duration_ms?: number;
  wall_ms?: number;
  memory_kb?: number;
};
export type RunnerResult = {
  status: "completed" | "syntax_error" | "missing_entrypoint" | "load_error" | "internal_error";
  python?: string;
  load?: { status: string; error?: { type: string; message: string; line?: number; offset?: number; traceback?: string } };
  tests: RunnerTest[];
};
export type ExecutorJob = { id: string; status: "queued" | "running" | "done" | "failed" | "cancelled"; queue_position?: number | null; result?: RunnerResult | null; error?: string | null };
export type JobRequest = {
  idempotency_key: string;
  user: string;
  runtime: string;
  code: string;
  entrypoint: string;
  prelude: string;
  tests: { id: string; args: unknown[]; kwargs: Record<string, unknown> }[];
  limits: { per_test_seconds: number; total_seconds: number; memory_mb: number; output_bytes: number };
  purpose: "run" | "submit" | "validate";
};

/** Pseudonymous user reference for the executor (quotas, abuse detection): never the real user id or email. */
export function userRef(userId: string): string {
  const key = process.env.PRACTICE_USER_HASH_KEY || process.env.SETTINGS_ENCRYPTION_KEY || "development-only-practice-key";
  return createHmac("sha256", key).update(userId).digest("hex").slice(0, 32);
}

export const idempotencyRef = (s: string) => createHash("sha256").update(s).digest("hex").slice(0, 48);

async function call<T>(method: string, path: string, body?: unknown, fetchImpl: typeof fetch = fetch): Promise<T> {
  const env = executorEnv();
  if (!env) throw new PracticeError("Code execution is not configured.", 503, "execution_disabled");
  let res: Response;
  try {
    res = await fetchImpl(`${env.url}${path}`, {
      method,
      headers: { Authorization: `Bearer ${env.token}`, "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(8000),
    });
  } catch {
    throw new PracticeError("The code runner is unreachable. Try again shortly.", 503, "executor_unavailable", 5);
  }
  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  if (res.ok) return data as T;
  const retry = Number(res.headers.get("retry-after")) || undefined;
  const code = (data as { error?: string } | null)?.error;
  if (res.status === 429) {
    const message =
      code === "busy" ? "Your previous run is still in progress." : code === "blocked" ? "Too many runs hit resource limits. Try again later." : "You're running code too often. Wait a moment.";
    throw new PracticeError(message, 429, code ?? "rate_limited", retry);
  }
  if (res.status === 503) throw new PracticeError("The code runner is busy. Try again shortly.", 503, "executor_busy", retry ?? 5);
  if (res.status === 404) throw new PracticeError("The run expired. Run it again.", 404, "job_not_found");
  throw new PracticeError(`The code runner rejected the request (HTTP ${res.status}).`, 502, "executor_error");
}

export const submitJob = (req: JobRequest, f?: typeof fetch) => call<ExecutorJob>("POST", "/v1/jobs", req, f);
export const getJob = (id: string, f?: typeof fetch) => call<ExecutorJob>("GET", `/v1/jobs/${encodeURIComponent(id)}`, undefined, f);
export const cancelJob = (id: string, f?: typeof fetch) => call<ExecutorJob>("DELETE", `/v1/jobs/${encodeURIComponent(id)}`, undefined, f);
export type ExecutorStatus = { queued: number; running: number; dispatchers: Record<string, number>; stats: Record<string, number>; backend: string; runtimes: string[]; runtime_class: string };
export const executorStatus = (f?: typeof fetch) => call<ExecutorStatus>("GET", "/v1/status", undefined, f);
