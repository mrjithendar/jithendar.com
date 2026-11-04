import { log } from "./log";
import { currentTraceId, expectedStatus, isNextControlFlow } from "./trace";

/**
 * Error handling for route handlers and server actions. Expected failures (PostError, PracticeError, any error
 * with a 4xx `status`) are answered by the caller with their own message. Everything else goes through
 * `reportError`: one `level=error` log line (stack, route, request id, trace id; the active span is marked
 * failed) and a short reference for the visitor. The reference is the trace id, which is kept by the log
 * collector and finds both the Loki lines and the Jaeger trace; without tracing it falls back to the request id.
 * Internals (messages, stacks, SQL) never reach the response.
 */

export type ErrorRef = { reference: string | undefined; requestId: string | undefined; traceId: string | undefined };

type HeaderSource = Request | Headers | { get(name: string): string | null } | null | undefined;

export function requestIdOf(source: HeaderSource): string | undefined {
  const headers = source instanceof Request ? source.headers : source;
  return headers?.get("x-request-id") ?? undefined;
}

/** The current request's id inside a server action or server component (undefined outside a request). */
export async function currentRequestId(): Promise<string | undefined> {
  try {
    const { headers } = await import("next/headers");
    return requestIdOf(await headers());
  } catch {
    return undefined;
  }
}

/** Log an unexpected failure once and return the reference to show to the visitor. */
export function reportError(msg: string, error: unknown, fields: Record<string, unknown> & { requestId?: string } = {}): ErrorRef {
  const traceId = currentTraceId();
  log.error(msg, { ...fields, err: error, status: fields.status ?? 500, outcome: "error" });
  return { reference: traceId ?? fields.requestId, requestId: fields.requestId, traceId };
}

/** "Something went wrong." plus the reference, for messages shown in the UI. */
export function withReference(message: string, ref: ErrorRef): string {
  return ref.reference ? `${message} Reference: ${ref.reference}` : message;
}

const NO_STORE = { "Cache-Control": "no-store", "X-Robots-Tag": "noindex" };

/** The JSON body of an unexpected 500 for /api/*: `{ error, code: "internal", reference }`. */
export function internalErrorResponse(ref: ErrorRef, message = "Something went wrong. The error has been logged."): Response {
  return Response.json(
    { error: message, code: "internal", reference: ref.reference },
    { status: 500, headers: { ...NO_STORE, ...(ref.requestId ? { "x-request-id": ref.requestId } : {}) } },
  );
}

type Handler = (...args: never[]) => Promise<Response> | Response;

/**
 * Wrap a route handler: unexpected errors become a logged, referenced JSON 500 instead of Next's empty 500.
 * Known 4xx errors that escape are answered as `{ error, code }` with their status. Next's redirect()/notFound()
 * pass through.
 */
export function handleErrors<F extends Handler>(name: string, fn: F): (...args: Parameters<F>) => Promise<Response> {
  return async (...args) => {
    try {
      return await fn(...args);
    } catch (error) {
      if (isNextControlFlow(error)) throw error;
      const status = expectedStatus(error);
      if (status) {
        const code = (error as { code?: unknown }).code;
        return Response.json({ error: (error as Error).message, ...(typeof code === "string" ? { code } : {}) }, { status, headers: NO_STORE });
      }
      const first: unknown = args[0];
      const request = first instanceof Request ? first : undefined;
      return internalErrorResponse(reportError(`${name} failed`, error, routeFields(request)));
    }
  };
}

/** The request fields every error line carries (path without the query string). */
export function routeFields(request: Request | undefined): { method?: string; route?: string; requestId?: string } {
  if (!request) return {};
  return { method: request.method, route: new URL(request.url).pathname, requestId: requestIdOf(request) };
}
