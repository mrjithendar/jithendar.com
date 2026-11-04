import "server-only";
import { reportError, routeFields } from "../http-errors";
import { isNextControlFlow } from "../trace";
import { getSessionUser, type SessionUser } from "../session";
import { PracticeError } from "./errors";

/**
 * Route-handler plumbing for /api/practice/*. Authorization is decided here, on the server: guests get
 * 401 { code: "auth_required" } (the page then shows the sign-in dialog) — hiding buttons is only a courtesy.
 * State-changing requests must come from this site (Origin check, as in the admin image API).
 */
const HEADERS = { "Cache-Control": "private, no-store", "X-Robots-Tag": "noindex" };

export function json(body: unknown, status = 200, extra: Record<string, string> = {}) {
  return Response.json(body, { status, headers: { ...HEADERS, ...extra } });
}

export function sameOrigin(req: Request): boolean {
  const origin = req.headers.get("origin");
  if (!origin) return false;
  const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host");
  try {
    return new URL(origin).host === host;
  } catch {
    return false;
  }
}

export async function readJson(req: Request): Promise<unknown> {
  if (!req.headers.get("content-type")?.includes("application/json")) throw new PracticeError("Send JSON.", 415, "unsupported_media_type");
  const text = await req.text();
  if (text.length > 200_000) throw new PracticeError("Request too large.", 413, "too_large");
  try {
    return JSON.parse(text);
  } catch {
    throw new PracticeError("Invalid JSON.", 400, "invalid_json");
  }
}

/** Run a handler for a signed-in user; map errors to JSON responses. */
export async function withUser(req: Request, fn: (user: SessionUser) => Promise<Response>, opts: { mutating?: boolean } = {}): Promise<Response> {
  if (opts.mutating && !sameOrigin(req)) return json({ error: "Cross-site request refused.", code: "cross_site" }, 403);
  try {
    const user = await getSessionUser();
    if (!user) return json({ error: "Sign in to use this feature.", code: "auth_required" }, 401);
    return await fn(user);
  } catch (error) {
    if (error instanceof PracticeError) {
      return json({ error: error.message, code: error.code }, error.status, error.retryAfter ? { "Retry-After": String(error.retryAfter) } : {});
    }
    if (isNextControlFlow(error)) throw error;
    const ref = reportError("practice api failed", error, routeFields(req));
    return json({ error: "Something went wrong. The error has been logged.", code: "internal", reference: ref.reference }, 500);
  }
}
