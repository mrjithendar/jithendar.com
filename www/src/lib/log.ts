/**
 * Structured JSON logs, one object per line, for Loki/Grafana:
 *   {"time":"…","level":"info","msg":"post published","event":"post_published","service":"jithendar-com","traceId":"…", …fields}
 * Never pass secrets, passwords, tokens or full request bodies in fields.
 *
 * The cluster's log collector (Alloy) keeps only an allowlist of fields with strict formats and drops the rest,
 * including `msg`: `event`, `level`, `route`, `method`, `status`, `durationMs`, `dependency`, `operation`,
 * `errorType`, `errorCode`, `outcome`, `traceId`. So every line carries `event` (a stable slug of `msg` unless
 * given) and errors carry `errorType`/`errorCode`; use those field names for anything that should reach Loki.
 */
type Level = "debug" | "info" | "warn" | "error";
const order: Record<Level, number> = { debug: 10, info: 20, warn: 30, error: 40 };
const threshold = order[(process.env.LOG_LEVEL as Level) ?? "info"] ?? order.info;

type Fields = Record<string, unknown>;

type OtelApi = typeof import("@opentelemetry/api");
function otel(): OtelApi | null {
  try {
    // Loaded lazily so the logger works in any runtime and in tests.
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    return require("@opentelemetry/api") as OtelApi;
  } catch {
    return null;
  }
}

/** Current OpenTelemetry trace/span ids, if a span is active (no-op when tracing is off). */
function traceFields(): Fields {
  const api = otel();
  const ctx = api?.trace.getActiveSpan()?.spanContext();
  return ctx && api!.isSpanContextValid(ctx) ? { traceId: ctx.traceId, spanId: ctx.spanId } : {};
}

/** An error logged at level error also fails the active span, so Jaeger shows where it happened. */
function markActiveSpan(err: unknown) {
  const api = otel();
  const span = api?.trace.getActiveSpan();
  if (!span) return;
  span.recordException(err instanceof Error ? err : new Error(String(err)));
  span.setStatus({ code: api!.SpanStatusCode.ERROR });
}

/** "comment submitted" → "comment_submitted" (Alloy accepts [A-Za-z][A-Za-z0-9_.:/-]{0,119}). */
export function eventOf(msg: string): string {
  const slug = msg.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 80);
  return /^[a-z]/.test(slug) ? slug : `log_${slug}`.replace(/_+$/, "");
}

function serializeError(error: unknown): Fields {
  if (error instanceof Error) {
    const code = (error as { code?: unknown }).code;
    return {
      errorType: error.constructor?.name && error.constructor.name !== "Object" ? error.constructor.name : error.name,
      ...(typeof code === "string" && /^[A-Za-z0-9_.]{1,80}$/.test(code) ? { errorCode: code } : {}),
      error: { name: error.name, message: error.message, stack: error.stack?.split("\n").slice(0, 6).join("\n") },
    };
  }
  return { errorType: "NonError", error: String(error) };
}

function write(level: Level, msg: string, fields: Fields = {}) {
  if (order[level] < threshold) return;
  const { err, ...rest } = fields;
  if (level === "error" && err !== undefined) markActiveSpan(err);
  const line = JSON.stringify({
    time: new Date().toISOString(),
    level,
    msg,
    event: eventOf(msg),
    service: "jithendar-com",
    version: process.env.GIT_SHA ?? "dev",
    ...traceFields(),
    ...rest,
    ...(err !== undefined ? serializeError(err) : {}),
  });
  // console.* writes one line to stdout/stderr in Node and works in every Next.js runtime.
  if (level === "error" || level === "warn") (original?.error ?? console.error)(line);
  else (original?.log ?? console.log)(line);
}

// The real console methods, kept when jsonConsole() replaces them (until then, console is called as it is now).
let original: { log: (line: string) => void; error: (line: string) => void } | undefined;

/**
 * Production: route console.* from Next.js and libraries through this logger, so every stdout/stderr line is JSON
 * (Next prints unhandled errors as "⨯ Error: …" with a multi-line stack, which the log collector cannot parse).
 * Lines that are already JSON objects (the proxy's access log) pass through unchanged. Called once from
 * instrumentation.ts; LOG_FORMAT=text keeps the plain console.
 */
export function jsonConsole() {
  const c = console as Console & { __json?: boolean };
  if (c.__json || process.env.LOG_FORMAT === "text") return;
  c.__json = true;
  const real = (original = { log: console.log.bind(console), error: console.error.bind(console) });
  const wrap = (level: Level, passthrough: (line: string) => void) => (...args: unknown[]) => {
    if (args.length === 1 && typeof args[0] === "string" && args[0].startsWith("{") && args[0].endsWith("}")) return passthrough(args[0]);
    const err = args.find((a) => a instanceof Error);
    const text = args
      .filter((a) => a !== err)
      .map((a) => (typeof a === "string" ? a : a instanceof Error ? a.message : safeJson(a)))
      .join(" ")
      // Strip ANSI colours and Next's "⨯"/"⚠" prefixes.
      .replace(/\u001b\[[0-9;]*m/g, "")
      .replace(/^[\s⨯⚠○✓]+/, "")
      .trim();
    write(level, (text || (err instanceof Error ? err.message : "console output")).slice(0, 2000), { event: `console_${level}`, ...(err ? { err } : {}) });
  };
  console.log = wrap("info", real.log);
  console.info = wrap("info", real.log);
  console.debug = wrap("debug", real.log);
  console.warn = wrap("warn", real.error);
  console.error = wrap("error", real.error);
}

function safeJson(v: unknown): string {
  try {
    return JSON.stringify(v) ?? String(v);
  } catch {
    return String(v);
  }
}

export const log = {
  debug: (msg: string, fields?: Fields) => write("debug", msg, fields),
  info: (msg: string, fields?: Fields) => write("info", msg, fields),
  warn: (msg: string, fields?: Fields) => write("warn", msg, fields),
  error: (msg: string, fields?: Fields) => write("error", msg, fields),
};
