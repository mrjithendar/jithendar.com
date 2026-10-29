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

/** Current OpenTelemetry trace/span ids, if a span is active (no-op when tracing is off). */
function traceFields(): Fields {
  try {
    // Loaded lazily so the logger works in any runtime and in tests.
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const api = require("@opentelemetry/api") as typeof import("@opentelemetry/api");
    const ctx = api.trace.getActiveSpan()?.spanContext();
    return ctx && api.isSpanContextValid(ctx) ? { traceId: ctx.traceId, spanId: ctx.spanId } : {};
  } catch {
    return {};
  }
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
  if (level === "error" || level === "warn") console.error(line);
  else console.log(line);
}

export const log = {
  debug: (msg: string, fields?: Fields) => write("debug", msg, fields),
  info: (msg: string, fields?: Fields) => write("info", msg, fields),
  warn: (msg: string, fields?: Fields) => write("warn", msg, fields),
  error: (msg: string, fields?: Fields) => write("error", msg, fields),
};
