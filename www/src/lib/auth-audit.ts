import "server-only";
import { and, count, eq, gt, sql } from "drizzle-orm";
import { getDb, schema } from "@/db";
import { auditSafe, requestInfoFrom, type RequestInfo, type Severity } from "./audit";

/**
 * Sign-in auditing. Successful sign-ins come from Better Auth's session hook (every method: password, Google,
 * GitHub); failures are read from the response of /api/auth/* in the route handler, because rate-limit and
 * Turnstile rejections never reach Better Auth's own hooks. Passwords are never read or stored.
 */

const CAPTCHA_CODES = new Set(["VERIFICATION_FAILED", "MISSING_RESPONSE"]);
const EMAIL = /^[^\s@]{1,64}@[^\s@]{1,255}$/;

/** Body fields worth reading before the request is handled (only on these POST endpoints). */
export const WATCHED_POSTS = new Set(["/sign-in/email", "/sign-up/email", "/request-password-reset", "/change-password"]);

const cleanEmail = (v: unknown) => (typeof v === "string" && EMAIL.test(v.trim()) ? v.trim().toLowerCase() : null);

async function errorCode(res: Response): Promise<string> {
  try {
    const body = (await res.clone().json()) as { code?: unknown; message?: unknown };
    return String(body.code ?? body.message ?? "").slice(0, 80);
  } catch {
    return "";
  }
}

/** The email in a watched request body, read from a clone (the handler still gets the original). */
export async function emailFromRequest(request: Request, path: string): Promise<string | null> {
  if (request.method !== "POST" || !WATCHED_POSTS.has(path)) return null;
  try {
    return cleanEmail(((await request.clone().json()) as { email?: unknown }).email);
  } catch {
    return null;
  }
}

/** Record failed, blocked and sensitive auth requests. Never throws. */
export async function auditAuthResponse(input: { path: string; method: string; request: Request; response: Response; email: string | null }) {
  const { path, response: res, email } = input;
  const req = requestInfoFrom(input.request.headers);
  const who = { id: null, label: email ?? "anonymous" };
  const status = res.status;

  if (status === 429) {
    await auditSafe(who, "auth.rate_limited", email ?? path, { path, retryAfter: res.headers.get("x-retry-after") ?? res.headers.get("retry-after") }, { request: req });
    return;
  }
  if (path === "/sign-in/email" && status >= 400) {
    const code = await errorCode(res);
    if (CAPTCHA_CODES.has(code)) return auditSafe(who, "auth.captcha_failed", email ?? path, { path, code }, { request: req });
    if (code === "BANNED_USER") return auditSafe(who, "auth.banned_login", email ?? "", { code }, { request: req });
    const prior = email ? await recentFailures({ email }) : 0;
    const fromIp = req.ip ? await recentFailures({ ip: req.ip }) : 0;
    // Five or more in 15 minutes for one address or from one IP looks like guessing, not a typo.
    const severity: Severity = prior >= 4 || fromIp >= 9 ? "critical" : "warning";
    return auditSafe(who, "auth.login_failed", email ?? "", { code: code || `HTTP_${status}`, failuresLast15m: { account: prior + 1, ip: fromIp + 1 } }, { request: req, severity });
  }
  if (path === "/sign-up/email" && status >= 400) {
    const code = await errorCode(res);
    if (CAPTCHA_CODES.has(code)) return auditSafe(who, "auth.captcha_failed", email ?? path, { path, code }, { request: req });
    return auditSafe(who, "auth.signup_failed", email ?? "", { code: code || `HTTP_${status}` }, { request: req, severity: "notice" });
  }
  if (path === "/request-password-reset" && status < 500) {
    return auditSafe(who, "auth.password_reset_requested", email ?? "", {}, { request: req });
  }
  if (path === "/change-password") {
    if (status < 400) return auditSafe({ id: null, label: "signed-in user" }, "auth.password_changed", undefined, {}, { request: req });
    // A wrong current password from inside a signed-in session can mean a stolen session.
    return auditSafe({ id: null, label: "signed-in user" }, "auth.password_change_failed", undefined, { code: await errorCode(res) }, { request: req, severity: "warning" });
  }
  if (path.startsWith("/callback/") && status >= 300 && status < 400) {
    const location = res.headers.get("location") ?? "";
    const error = location.includes("error=") ? new URL(location, "https://x").searchParams.get("error") : null;
    if (error) return auditSafe(who, "auth.social_failed", path.slice("/callback/".length), { error: error.slice(0, 80) }, { request: req });
  }
}

/** Failed password sign-ins in the last 15 minutes for an address or from an IP. */
export async function recentFailures(by: { email?: string; ip?: string }, windowMs = 15 * 60_000): Promise<number> {
  const db = await getDb();
  const a = schema.auditLog;
  const [{ n } = { n: 0 }] = await db
    .select({ n: count() })
    .from(a)
    .where(and(eq(a.action, "auth.login_failed"), gt(a.createdAt, new Date(Date.now() - windowMs)), by.email ? eq(a.target, by.email) : undefined, by.ip ? eq(a.ip, by.ip) : undefined));
  return Number(n);
}

/**
 * A successful sign-in (any method). Flags sign-ins from an IP this account has not used in 90 days, and
 * success right after a run of failures (a guessed password looks exactly like that).
 */
export async function auditLogin(session: { userId: string; ipAddress?: string | null; userAgent?: string | null; impersonatedBy?: string | null }, path: string | undefined) {
  try {
    const db = await getDb();
    const [u] = await db.select({ email: schema.user.email, name: schema.user.name, role: schema.user.role }).from(schema.user).where(eq(schema.user.id, session.userId));
    if (!u) return;
    const req: RequestInfo = { ip: session.ipAddress?.slice(0, 64) ?? null, userAgent: session.userAgent?.slice(0, 300) ?? null };
    if (session.impersonatedBy) {
      await auditSafe({ id: session.impersonatedBy, label: "admin" }, "user.impersonate", session.userId, { email: u.email }, { request: req });
      return;
    }
    const a = schema.auditLog;
    const [seen] = req.ip
      ? await db
          .select({ n: count() })
          .from(a)
          .where(and(eq(a.action, "auth.login"), eq(a.actorId, session.userId), eq(a.ip, req.ip), gt(a.createdAt, sql`now() - interval '90 days'`)))
      : [{ n: 1 }];
    const [any] = await db.select({ n: count() }).from(a).where(and(eq(a.action, "auth.login"), eq(a.actorId, session.userId)));
    const newIp = Number(any?.n ?? 0) > 0 && Number(seen?.n ?? 0) === 0;
    const priorFailures = await recentFailures({ email: u.email.toLowerCase() }, 60 * 60_000);
    const method = path === "/sign-in/email" ? "password" : path === "/sign-up/email" ? "sign-up" : path?.startsWith("/callback/") ? path.slice("/callback/".length) : (path ?? "unknown");
    const staff = u.role === "admin" || u.role === "author";
    const severity: Severity = priorFailures >= 3 ? "warning" : newIp && staff ? "warning" : newIp ? "notice" : "info";
    await auditSafe({ id: session.userId, label: u.email }, "auth.login", session.userId, { method, role: u.role, ...(newIp ? { newIp: true } : {}), ...(priorFailures ? { failuresBefore: priorFailures } : {}) }, { request: req, severity });
  } catch {
    /* never block sign-in on auditing */
  }
}
