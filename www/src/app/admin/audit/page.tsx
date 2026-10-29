import Link from "next/link";
import { AdminHeader, Card, Stat, StatusPill, Table, td, th } from "@/components/admin/ui";
import { Button, buttonClass, Input, Select } from "@/components/ui/form";
import { SEVERITIES } from "@/lib/audit";
import { AUDIT_CATEGORIES, AUDIT_PERIODS, parseAuditFilter, queryAudit, type AuditFilter } from "@/lib/audit-query";
import { formatDateTime } from "@/lib/dates";
import { securityOverview } from "@/lib/security";
import { requireRole } from "@/lib/session";

export const metadata = { title: "Audit log" };

const PAGE_SIZE = 100;

function qs(f: AuditFilter, over: Partial<Record<keyof AuditFilter, string | number>> = {}) {
  const merged: Record<string, string | number> = { q: f.q, severity: f.severity, category: f.category, ip: f.ip, days: f.days === "30" ? "" : f.days, page: f.page > 1 ? f.page : "", ...over };
  const s = new URLSearchParams(Object.entries(merged).filter(([, v]) => v !== "" && v !== undefined).map(([k, v]) => [k, String(v)])).toString();
  return s ? `?${s}` : "";
}

/** Short, readable summary of an entry's detail (the full JSON is in the title and the CSV export). */
function summary(detail: unknown): string {
  if (!detail || typeof detail !== "object") return "";
  return Object.entries(detail as Record<string, unknown>)
    .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : String(v)}`)
    .join(" · ");
}

export default async function AuditPage({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  await requireRole("admin");
  const filter = parseAuditFilter(await searchParams);
  const [{ rows, total }, sec] = await Promise.all([queryAudit(filter, PAGE_SIZE), securityOverview(24)]);
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <>
      <AdminHeader
        title="Audit log"
        description="Every change made from the admin or the API, and every sign-in: successful, failed, rate-limited or blocked by Turnstile, with the client IP and browser."
        actions={<a href={`/api/admin/audit${qs(filter, { page: "" })}`} className={buttonClass("secondary")} download>Export CSV</a>}
      />

      <section aria-labelledby="sec-title" className="mb-8 space-y-4">
        <h2 id="sec-title" className="text-lg font-semibold text-fg">Security, last 24 hours</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Stat label="Failed sign-ins" value={sec.failedLogins} hint={<Link className="underline" href={`/admin/audit${qs({ ...filter, page: 1 }, { q: "auth.login_failed", days: "1", ip: "", category: "", severity: "" })}`}>Show</Link>} />
          <Stat label="Rate-limited / Turnstile blocked" value={`${sec.rateLimited} / ${sec.captchaFailed}`} />
          <Stat label="IPs with failures" value={sec.uniqueFailingIps} />
          <Stat label="Successful sign-ins" value={sec.successfulLogins} />
        </div>

        {sec.findings.length > 0 ? (
          <Card>
            <h3 className="font-semibold text-fg">Needs a look</h3>
            <ul className="mt-3 divide-y divide-line">
              {sec.findings.map((f, i) => (
                <li key={i} className="flex flex-col gap-1 py-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
                  <div className="min-w-0">
                    <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-fg">
                      <StatusPill status={f.severity} />
                      <span className="[overflow-wrap:anywhere]">{f.title}</span>
                    </p>
                    <p className="mt-1 text-sm text-fg-muted">{f.detail}</p>
                  </div>
                  <Link href={`/admin/audit?${f.filter}&days=1`} className="shrink-0 text-sm underline">Entries</Link>
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-fg-subtle">
              Heuristics, not verdicts. To block an address, add it to Traefik&apos;s IP deny list or Cloudflare WAF; to protect an account, ban it in Users or ask the owner to change the password.
            </p>
          </Card>
        ) : (
          <p className="text-sm text-fg-muted">No brute-force, credential-stuffing or suspicious sign-in patterns in the last 24 hours.</p>
        )}

        {(sec.topIps.length > 0 || sec.topAccounts.length > 0) && (
          <div className="grid gap-4 lg:grid-cols-2">
            {sec.topIps.length > 0 && (
              <Table head={<tr><th className={th}>IP address</th><th className={th}>Failures</th><th className={th}>Accounts</th><th className={th}>Last seen</th></tr>}>
                {sec.topIps.map((r) => (
                  <tr key={r.ip}>
                    <td className={`${td} font-mono text-xs`} title={r.lastAgent ?? ""}><Link href={`/admin/audit?ip=${encodeURIComponent(r.ip)}&days=1`} className="underline">{r.ip}</Link></td>
                    <td className={td}>{r.failures}</td>
                    <td className={td}>{r.accounts}</td>
                    <td className={`${td} whitespace-nowrap`}>{formatDateTime(r.lastSeen)}</td>
                  </tr>
                ))}
              </Table>
            )}
            {sec.topAccounts.length > 0 && (
              <Table head={<tr><th className={th}>Account tried</th><th className={th}>Failures</th><th className={th}>From IPs</th><th className={th}>Last seen</th></tr>}>
                {sec.topAccounts.map((a) => (
                  <tr key={a.account}>
                    <td className={`${td} [overflow-wrap:anywhere]`}><Link href={`/admin/audit?q=${encodeURIComponent(a.account)}&days=1`} className="underline">{a.account}</Link></td>
                    <td className={td}>{a.failures}</td>
                    <td className={td}>{a.ips}</td>
                    <td className={`${td} whitespace-nowrap`}>{formatDateTime(a.lastSeen)}</td>
                  </tr>
                ))}
              </Table>
            )}
          </div>
        )}
      </section>

      <h2 className="mb-3 text-lg font-semibold text-fg">Entries</h2>
      <form className="mb-4 grid gap-2 rounded-xl border border-line bg-surface p-3 sm:grid-cols-2 lg:grid-cols-[minmax(0,2fr)_repeat(3,minmax(0,1fr))_minmax(0,1fr)_auto]" role="search" aria-label="Filter audit log">
        <div>
          <label className="sr-only" htmlFor="a-q">Search</label>
          <Input id="a-q" name="q" type="search" defaultValue={filter.q} placeholder="Action, actor, target or IP" />
        </div>
        <div>
          <label className="sr-only" htmlFor="a-cat">Category</label>
          <Select id="a-cat" name="category" defaultValue={filter.category}>
            <option value="">All categories</option>
            {Object.entries(AUDIT_CATEGORIES).map(([k, c]) => <option key={k} value={k}>{c.label}</option>)}
          </Select>
        </div>
        <div>
          <label className="sr-only" htmlFor="a-sev">Severity</label>
          <Select id="a-sev" name="severity" defaultValue={filter.severity}>
            <option value="">Any severity</option>
            {SEVERITIES.map((s) => <option key={s} value={s}>{s[0]!.toUpperCase() + s.slice(1)} and above</option>)}
          </Select>
        </div>
        <div>
          <label className="sr-only" htmlFor="a-days">Period</label>
          <Select id="a-days" name="days" defaultValue={filter.days}>
            {Object.entries(AUDIT_PERIODS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </Select>
        </div>
        <div>
          <label className="sr-only" htmlFor="a-ip">IP address</label>
          <Input id="a-ip" name="ip" defaultValue={filter.ip} placeholder="IP address" spellCheck={false} />
        </div>
        <div className="flex gap-2">
          <Button type="submit" variant="secondary">Filter</Button>
          <Link href="/admin/audit" className={buttonClass("ghost")}>Reset</Link>
        </div>
      </form>
      <p className="mb-3 text-sm text-fg-subtle">{total} matching entr{total === 1 ? "y" : "ies"}. Times are local; the CSV uses UTC.</p>

      <Table head={<tr><th className={th}>When</th><th className={th}>Severity</th><th className={th}>Actor</th><th className={th}>Action</th><th className={th}>Target</th><th className={th}>IP / client</th><th className={th}>Details</th></tr>}>
        {rows.length === 0 && <tr><td className={td} colSpan={7}>No entries.</td></tr>}
        {rows.map((r) => (
          <tr key={r.id}>
            <td className={`${td} whitespace-nowrap`}>{formatDateTime(r.createdAt.toISOString())}</td>
            <td className={td}><StatusPill status={r.severity} /></td>
            <td className={`${td} max-w-[12rem] truncate`} title={r.actor}>{r.actor}</td>
            <td className={`${td} whitespace-nowrap font-mono text-xs`}>{r.action}</td>
            <td className={`${td} max-w-[14rem] truncate`} title={r.target ?? ""}>{r.target}</td>
            <td className={`${td} max-w-[12rem]`}>
              {r.ip ? <Link href={`/admin/audit${qs({ ...filter, page: 1 }, { ip: r.ip })}`} className="font-mono text-xs underline">{r.ip}</Link> : <span className="text-xs">—</span>}
              {r.userAgent && <span className="block truncate text-xs text-fg-subtle" title={r.userAgent}>{r.userAgent}</span>}
            </td>
            <td className={`${td} max-w-sm truncate font-mono text-xs`} title={r.detail ? JSON.stringify(r.detail) : ""}>{summary(r.detail)}</td>
          </tr>
        ))}
      </Table>

      {pages > 1 && (
        <nav aria-label="Pages" className="mt-6 flex items-center justify-between gap-4 text-sm">
          {filter.page > 1 ? <Link href={`/admin/audit${qs(filter, { page: filter.page - 1 })}`} className="underline">← Newer</Link> : <span />}
          <span className="text-fg-subtle">Page {filter.page} of {pages}</span>
          {filter.page < pages ? <Link href={`/admin/audit${qs(filter, { page: filter.page + 1 })}`} className="underline">Older →</Link> : <span />}
        </nav>
      )}
    </>
  );
}
