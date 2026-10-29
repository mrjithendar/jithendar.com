import { getDb, schema } from "@/db";
import { log } from "./log";

export const SEVERITIES = ["info", "notice", "warning", "critical"] as const;
export type Severity = (typeof SEVERITIES)[number];

/**
 * Default severity by action (exact name, then prefix). Warnings and criticals are what Admin → Audit log and
 * the dashboard's security card surface: failed or blocked sign-ins, privilege and credential changes.
 */
const SEVERITY: [string, Severity][] = [
  ["auth.login_failed", "warning"],
  ["auth.rate_limited", "warning"],
  ["auth.captcha_failed", "warning"],
  ["auth.banned_login", "critical"],
  ["auth.social_failed", "notice"],
  ["auth.password_reset_requested", "notice"],
  ["auth.password_changed", "notice"],
  ["auth.signup", "info"],
  ["auth.login", "info"],
  ["user.role", "critical"],
  ["user.ban", "warning"],
  ["user.delete", "warning"],
  ["user.impersonate", "critical"],
  ["user.password", "warning"],
  ["apikey.create", "warning"],
  ["apikey.", "notice"],
  ["integrations.", "warning"],
  ["storage.", "warning"],
  ["email.", "notice"],
  ["backup.download", "warning"],
  ["backup.", "notice"],
  ["site-config.publish", "notice"],
  ["database.", "warning"],
  ["audit.export", "notice"],
];

export function severityOf(action: string): Severity {
  return SEVERITY.find(([k]) => action === k)?.[1] ?? SEVERITY.find(([k]) => k.endsWith(".") && action.startsWith(k))?.[1] ?? "info";
}

export type RequestInfo = { ip: string | null; userAgent: string | null };

/** First address in X-Forwarded-For (set by Traefik), else X-Real-IP. */
export function requestInfoFrom(h: Headers): RequestInfo {
  const ip = h.get("x-forwarded-for")?.split(",")[0]?.trim() || h.get("x-real-ip")?.trim() || null;
  return { ip: ip ? ip.slice(0, 64) : null, userAgent: h.get("user-agent")?.slice(0, 300) ?? null };
}

/** IP and user agent of the current request, when there is one (server actions, route handlers, auth hooks). */
async function currentRequest(): Promise<RequestInfo> {
  try {
    const { headers } = await import("next/headers");
    return requestInfoFrom(await headers());
  } catch {
    return { ip: null, userAgent: null };
  }
}

/** Append-only record of admin/API/auth actions. Never store secrets (or passwords) in `detail`. */
export async function audit(
  actor: { id?: string | null; label: string },
  action: string,
  target?: string,
  detail?: Record<string, unknown>,
  opts: { severity?: Severity; request?: RequestInfo } = {},
) {
  const req = opts.request ?? (await currentRequest());
  const db = await getDb();
  await db.insert(schema.auditLog).values({
    actorId: actor.id ?? null,
    actor: actor.label,
    action,
    target: target ?? null,
    detail: detail ?? null,
    ip: req.ip,
    userAgent: req.userAgent,
    severity: opts.severity ?? severityOf(action),
  });
}

/** Audit without ever failing the caller (auth hooks: a broken audit write must not block sign-in). */
export async function auditSafe(...args: Parameters<typeof audit>) {
  try {
    await audit(...args);
  } catch (err) {
    log.warn("audit write failed", { action: args[1], err });
  }
}
