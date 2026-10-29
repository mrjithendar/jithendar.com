import "server-only";
import { sql } from "drizzle-orm";
import { getDb } from "@/db";
import { rowsOf } from "@/db/rows";

/**
 * Patterns in the audit log that suggest an attack, for Admin → Audit log and the dashboard. Heuristics only:
 * they point a person at entries worth reading, they never block anyone (Better Auth's rate limits and
 * Turnstile do that).
 *
 * - brute force: many failed sign-ins from one IP
 * - credential stuffing: one IP trying many different accounts
 * - password spraying / targeted account: one account failing from several IPs
 * - suspicious success: a sign-in right after failures, or a staff sign-in from a new IP
 */
export const THRESHOLDS = { bruteForce: 10, stuffingAccounts: 3, sprayIps: 3, accountFailures: 5 } as const;

export type Finding = { kind: "brute-force" | "credential-stuffing" | "targeted-account" | "suspicious-login" | "privilege-change"; severity: "warning" | "critical"; title: string; detail: string; filter: string };

export type SecurityOverview = {
  hours: number;
  failedLogins: number;
  rateLimited: number;
  captchaFailed: number;
  successfulLogins: number;
  uniqueFailingIps: number;
  topIps: { ip: string; failures: number; accounts: number; lastSeen: string; lastAgent: string | null }[];
  topAccounts: { account: string; failures: number; ips: number; lastSeen: string }[];
  findings: Finding[];
  hourly: { hour: string; failed: number; ok: number }[];
};

export async function securityOverview(hours = 24): Promise<SecurityOverview> {
  const db = await getDb();
  const since = sql`now() - make_interval(hours => ${hours})`;
  const [totals] = rowsOf<{ failed: number; limited: number; captcha: number; ok: number; ips: number }>(
    await db.execute(sql`select
        count(*) filter (where action = 'auth.login_failed')::int as failed,
        count(*) filter (where action = 'auth.rate_limited')::int as limited,
        count(*) filter (where action = 'auth.captcha_failed')::int as captcha,
        count(*) filter (where action = 'auth.login')::int as ok,
        count(distinct ip) filter (where action = 'auth.login_failed')::int as ips
      from audit_log where created_at > ${since} and action like 'auth.%'`),
  );
  const topIps = rowsOf<{ ip: string; failures: number; accounts: number; last_seen: Date | string; last_agent: string | null }>(
    await db.execute(sql`select ip, count(*)::int as failures, count(distinct target)::int as accounts, max(created_at) as last_seen,
        (array_agg(user_agent order by created_at desc))[1] as last_agent
      from audit_log where created_at > ${since} and action in ('auth.login_failed', 'auth.rate_limited', 'auth.captcha_failed') and ip is not null
      group by ip order by failures desc limit 10`),
  );
  const topAccounts = rowsOf<{ account: string; failures: number; ips: number; last_seen: Date | string }>(
    await db.execute(sql`select target as account, count(*)::int as failures, count(distinct ip)::int as ips, max(created_at) as last_seen
      from audit_log where created_at > ${since} and action = 'auth.login_failed' and coalesce(target, '') <> ''
      group by target order by failures desc limit 10`),
  );
  const suspicious = rowsOf<{ actor: string; ip: string | null; detail: Record<string, unknown> | null; created_at: Date | string }>(
    await db.execute(sql`select actor, ip, detail, created_at from audit_log
      where created_at > ${since} and action = 'auth.login' and severity in ('warning', 'critical') order by created_at desc limit 20`),
  );
  const privileged = rowsOf<{ actor: string; action: string; target: string | null; created_at: Date | string }>(
    await db.execute(sql`select actor, action, target, created_at from audit_log
      where created_at > ${since} and severity = 'critical' and action not like 'auth.%' order by created_at desc limit 20`),
  );
  const hourly = rowsOf<{ hour: Date | string; failed: number; ok: number }>(
    await db.execute(sql`select date_trunc('hour', created_at) as hour,
        count(*) filter (where action in ('auth.login_failed', 'auth.rate_limited', 'auth.captcha_failed'))::int as failed,
        count(*) filter (where action = 'auth.login')::int as ok
      from audit_log where created_at > ${since} and action like 'auth.%' group by 1 order by 1`),
  );

  const iso = (d: Date | string) => new Date(d).toISOString();
  const findings: Finding[] = [];
  for (const r of topIps) {
    if (r.accounts >= THRESHOLDS.stuffingAccounts)
      findings.push({ kind: "credential-stuffing", severity: "critical", title: `${r.ip} tried ${r.accounts} different accounts`, detail: `${r.failures} failed or blocked sign-ins. Typical of leaked-password lists being replayed.`, filter: `ip=${encodeURIComponent(r.ip)}` });
    else if (r.failures >= THRESHOLDS.bruteForce)
      findings.push({ kind: "brute-force", severity: "critical", title: `${r.failures} failed sign-ins from ${r.ip}`, detail: "Repeated password guessing from one address.", filter: `ip=${encodeURIComponent(r.ip)}` });
  }
  for (const a of topAccounts) {
    if (a.ips >= THRESHOLDS.sprayIps || a.failures >= THRESHOLDS.accountFailures)
      findings.push({
        kind: "targeted-account",
        severity: a.ips >= THRESHOLDS.sprayIps ? "critical" : "warning",
        title: `${a.account}: ${a.failures} failed sign-ins from ${a.ips} IP(s)`,
        detail: a.ips >= THRESHOLDS.sprayIps ? "Several addresses are trying this account (distributed guessing)." : "Someone keeps getting this account's password wrong.",
        filter: `q=${encodeURIComponent(a.account)}`,
      });
  }
  for (const s of suspicious) {
    const d = s.detail ?? {};
    const why = [d.failuresBefore ? `after ${String(d.failuresBefore)} failed attempt(s)` : "", d.newIp ? "from an IP not seen in 90 days" : ""].filter(Boolean).join(" and ");
    findings.push({ kind: "suspicious-login", severity: "warning", title: `${s.actor} signed in ${why || "with a warning"}`, detail: `${s.ip ?? "unknown IP"} · ${iso(s.created_at)}. Confirm it was them.`, filter: `q=${encodeURIComponent(s.actor)}` });
  }
  for (const p of privileged) {
    findings.push({ kind: "privilege-change", severity: "warning", title: `${p.action} by ${p.actor}`, detail: `${p.target ?? ""} · ${iso(p.created_at)}`, filter: `q=${encodeURIComponent(p.action)}` });
  }

  return {
    hours,
    failedLogins: Number(totals?.failed ?? 0),
    rateLimited: Number(totals?.limited ?? 0),
    captchaFailed: Number(totals?.captcha ?? 0),
    successfulLogins: Number(totals?.ok ?? 0),
    uniqueFailingIps: Number(totals?.ips ?? 0),
    topIps: topIps.map((r) => ({ ip: r.ip, failures: r.failures, accounts: r.accounts, lastSeen: iso(r.last_seen), lastAgent: r.last_agent })),
    topAccounts: topAccounts.map((a) => ({ account: a.account, failures: a.failures, ips: a.ips, lastSeen: iso(a.last_seen) })),
    findings: findings.sort((a, b) => (a.severity === b.severity ? 0 : a.severity === "critical" ? -1 : 1)),
    hourly: hourly.map((h) => ({ hour: iso(h.hour), failed: h.failed, ok: h.ok })),
  };
}
