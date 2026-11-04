import { SpanStatusCode, trace, type Attributes, type Span } from "@opentelemetry/api";

/**
 * Custom OpenTelemetry spans for work Next.js does not trace by itself: background jobs, email, and the AWS SDK
 * clients (R2, SES, Bedrock; `fetch` is already traced by @vercel/otel). No-ops when no tracer is registered
 * (tests, scripts). Attributes must stay low-cardinality and free of personal data: no URLs, emails, SQL or
 * object keys (the collector's privacy filter drops some of these anyway).
 * No `server-only` import: instrumentation.ts and the logger load this outside the React server layer.
 */

const tracer = () => trace.getTracer("jithendar-com");

/** Errors that answer the caller with a 4xx (PostError, PracticeError, …) are outcomes, not failures. */
export function expectedStatus(error: unknown): number | null {
  const status = (error as { status?: unknown } | null)?.status;
  return typeof status === "number" && status >= 400 && status < 500 ? status : null;
}

/** redirect(), notFound() and friends throw; they must be rethrown untouched and never logged as errors. */
export function isNextControlFlow(error: unknown): boolean {
  const digest = (error as { digest?: unknown } | null)?.digest;
  return typeof digest === "string" && (digest.startsWith("NEXT_") || digest === "DYNAMIC_SERVER_USAGE" || digest === "BAILOUT_TO_CLIENT_SIDE_RENDERING");
}

function errorType(error: unknown): string {
  if (error instanceof Error) return error.constructor?.name && error.constructor.name !== "Object" ? error.constructor.name : error.name;
  return "NonError";
}

/** Mark a span as failed (unexpected errors only; 4xx outcomes and Next control flow keep the span OK). */
export function markSpanError(span: Span | undefined, error: unknown) {
  if (!span || isNextControlFlow(error)) return;
  span.setAttribute("error.type", errorType(error));
  if (expectedStatus(error)) return;
  span.recordException(error instanceof Error ? error : new Error(String(error)));
  span.setStatus({ code: SpanStatusCode.ERROR });
}

/** Run `fn` in a child span of the current one (or a new trace for background work). Errors are recorded and rethrown. */
export function withSpan<T>(name: string, attributes: Attributes, fn: (span: Span) => Promise<T>): Promise<T> {
  return tracer().startActiveSpan(name, { attributes }, async (span) => {
    try {
      return await fn(span);
    } catch (error) {
      markSpanError(span, error);
      throw error;
    } finally {
      span.end();
    }
  });
}

/** The active trace id (32 hex), if a span is recording. Shown to users as an error reference. */
export function currentTraceId(): string | undefined {
  const ctx = trace.getActiveSpan()?.spanContext();
  return ctx && ctx.traceId !== "00000000000000000000000000000000" ? ctx.traceId : undefined;
}

type AwsClient = { middlewareStack?: { add: (...args: never[]) => void } };
type AwsNext = (args: unknown) => Promise<{ response?: { statusCode?: number } }>;

/** One span per AWS SDK call (`r2.PutObject`, `ses.SendEmail`, …), with the HTTP status of the answer. */
export function traceAwsClient<C extends AwsClient>(client: C, service: string): C {
  if (!client.middlewareStack) return client; // test doubles
  const add = client.middlewareStack.add as unknown as (mw: (next: AwsNext, context: { commandName?: string }) => AwsNext, opts: { step: "initialize"; name: string }) => void;
  add.call(
    client.middlewareStack,
    (next, context) => (args) => {
      const operation = (context.commandName ?? "Unknown").replace(/Command$/, "");
      return withSpan(`${service}.${operation}`, { "rpc.system": "aws-api", "rpc.service": service, "rpc.method": operation }, async (span) => {
        const out = await next(args);
        if (out.response?.statusCode) span.setAttribute("http.status_code", out.response.statusCode);
        return out;
      });
    },
    { step: "initialize", name: "jithendarTracing" },
  );
  return client;
}
