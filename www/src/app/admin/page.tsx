import Link from "next/link";
import type { ReactNode } from "react";
import { AdminHeader, Card, StatusPill } from "@/components/admin/ui";
import { buttonClass } from "@/components/ui/form";
import { dashboardData } from "@/lib/dashboard";
import { formatDateTime } from "@/lib/dates";
import { requireRole } from "@/lib/session";

export const metadata = { title: "Dashboard" };

const size = (n: number) => (n > 1024 ** 3 ? `${(n / 1024 ** 3).toFixed(2)} GB` : `${(n / 1024 ** 2).toFixed(1)} MB`);
const excerpt = (s: string, n = 110) => (s.length > n ? `${s.slice(0, n).trimEnd()}…` : s);

/** A dashboard card: a headline number, a few supporting facts and where to act on it. */
function Widget({ title, value, children, href, cta, tone }: { title: string; value: ReactNode; children?: ReactNode; href?: string; cta?: string; tone?: "attention" }) {
  return (
    <Card className={tone === "attention" ? "border-amber-300 dark:border-amber-500/40" : ""}>
      <p className="text-sm text-fg-subtle">{title}</p>
      <p className="mt-1.5 text-3xl font-semibold tracking-tight text-fg tabular-nums">{value}</p>
      {children && <div className="mt-3 space-y-1 text-sm text-fg-muted">{children}</div>}
      {href && <Link href={href} className="mt-3 inline-block text-sm font-medium underline">{cta ?? "Open"}</Link>}
    </Card>
  );
}

function Panel({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <Card>
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="font-semibold text-fg">{title}</h2>
        {action}
      </div>
      {children}
    </Card>
  );
}

const Empty = ({ children }: { children: ReactNode }) => <p className="text-sm text-fg-subtle">{children}</p>;

export default async function AdminDashboard() {
  const user = await requireRole("admin", "author");
  const d = await dashboardData(user);
  const c = d.counts;
  const s = d.site;
  const attention = d.moderation.pending + d.moderation.reported + (s?.unreadMessages ?? 0) + (s?.security.findings.length ?? 0);

  return (
    <>
      <AdminHeader
        title={`Welcome, ${user.name.split(" ")[0]}`}
        description={attention > 0 ? `${attention} item(s) need attention across the publication.` : "Nothing needs attention right now."}
        actions={
          <>
            <Link href="/admin/posts/new" className={buttonClass()}>New post</Link>
            <Link href="/admin/pages/new" className={buttonClass("secondary")}>New page</Link>
            <Link href="/admin/media" className={buttonClass("secondary")}>Upload media</Link>
          </>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Widget title="Published" value={c.published ?? 0} href="/admin/posts?status=published" cta="All posts">
          <p>{Object.entries(d.byCollection).map(([k, n]) => `${n} ${k}`).join(" · ") || "Nothing published yet"}</p>
          <p>{c.scheduled ?? 0} scheduled · {c.trash ?? 0} in trash</p>
        </Widget>
        <Widget title="Drafts & review" value={(c.draft ?? 0) + (c.review ?? 0)} href="/admin/posts?status=review" cta="Review queue" tone={(c.review ?? 0) > 0 ? "attention" : undefined}>
          <p>{c.draft ?? 0} draft(s) · {c.review ?? 0} waiting for review</p>
        </Widget>
        <Widget title="Comments to moderate" value={d.moderation.pending + d.moderation.reported} href="/admin/comments" cta="Moderate" tone={d.moderation.pending + d.moderation.reported > 0 ? "attention" : undefined}>
          <p>{d.moderation.pending} pending · {d.moderation.reported} reported</p>
          <p>{d.comments.week} new this week · {d.comments.approved} published in total</p>
        </Widget>
        <Widget title="Media library" value={d.media.files} href={d.media.noAlt ? "/admin/media?alt=missing" : "/admin/media"} cta={d.media.noAlt ? "Fix missing alt text" : "Open library"} tone={d.media.noAlt ? "attention" : undefined}>
          <p>{size(d.media.bytes)} · {d.media.week} added this week</p>
          <p className={d.media.noAlt ? "font-medium text-amber-700 dark:text-amber-300" : ""}>{d.media.noAlt} image(s) without alt text</p>
        </Widget>
        {s && (
          <>
            <Widget title="Accounts" value={s.users.total} href="/admin/users" cta="Manage users">
              <p>{s.users.week} new this week</p>
              <p>{s.users.admins} admin(s) · {s.users.authors} author(s){s.users.banned ? ` · ${s.users.banned} banned` : ""}</p>
            </Widget>
            <Widget title="New messages" value={s.unreadMessages} href="/admin/messages" cta="Inbox" tone={s.unreadMessages ? "attention" : undefined} />
            <Widget title="Failed sign-ins (24 h)" value={s.security.failedLogins} href="/admin/audit" cta="Audit log" tone={s.security.findings.length ? "attention" : undefined}>
              <p>{s.security.uniqueFailingIps} IP(s) · {s.security.rateLimited} rate-limited · {s.security.captchaFailed} blocked by Turnstile</p>
              <p className={s.security.findings.length ? "font-medium text-amber-700 dark:text-amber-300" : ""}>
                {s.security.findings.length ? `${s.security.findings.length} pattern(s) worth a look` : "No suspicious patterns"}
              </p>
            </Widget>
            <Widget title="Sign-ins (24 h)" value={s.security.successfulLogins} />
          </>
        )}
      </div>

      {s && s.security.findings.length > 0 && (
        <Card className="mt-6 border-red-300 dark:border-red-500/40">
          <h2 className="font-semibold text-fg">Security</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {s.security.findings.slice(0, 4).map((f, i) => (
              <li key={i} className="flex flex-wrap items-center gap-2">
                <StatusPill status={f.severity} />
                <span className="text-fg [overflow-wrap:anywhere]">{f.title}</span>
                <Link href={`/admin/audit?${f.filter}&days=1`} className="text-fg-subtle underline">Entries</Link>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Panel title="Your drafts" action={<Link href="/admin/posts?status=draft" className="text-sm underline">All drafts</Link>}>
          {d.myDrafts.length === 0 ? (
            <Empty>No drafts. <Link href="/admin/posts/new" className="underline">Start a post</Link>.</Empty>
          ) : (
            <ul className="divide-y divide-line text-sm">
              {d.myDrafts.map((x) => (
                <li key={x.id} className="flex items-center justify-between gap-3 py-2.5">
                  <Link href={`/admin/posts/${x.id}`} className="min-w-0 truncate font-medium text-fg hover:underline">{x.title || "Untitled"}</Link>
                  <span className="flex shrink-0 items-center gap-2 text-xs text-fg-subtle"><StatusPill status={x.status} /> {formatDateTime(x.savedAt.toISOString())}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Scheduled" action={<Link href="/admin/posts?status=scheduled" className="text-sm underline">All scheduled</Link>}>
          {d.upcoming.length === 0 ? (
            <Empty>Nothing scheduled.</Empty>
          ) : (
            <ul className="divide-y divide-line text-sm">
              {d.upcoming.map((x) => (
                <li key={x.id} className="flex items-center justify-between gap-3 py-2.5">
                  <Link href={`/admin/posts/${x.id}`} className="min-w-0 truncate font-medium text-fg hover:underline">{x.title}</Link>
                  <span className="shrink-0 text-xs text-fg-subtle">{x.publishedAt ? formatDateTime(x.publishedAt.toISOString()) : "—"}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Recently published">
          {d.recentPublished.length === 0 ? (
            <Empty>Nothing published yet.</Empty>
          ) : (
            <ul className="divide-y divide-line text-sm">
              {d.recentPublished.map((x) => (
                <li key={x.id} className="flex items-center justify-between gap-3 py-2.5">
                  <span className="min-w-0">
                    <Link href={`/admin/posts/${x.id}`} className="block truncate font-medium text-fg hover:underline">{x.title}</Link>
                    <span className="text-xs text-fg-subtle">{x.publishedAt ? formatDateTime(x.publishedAt.toISOString()) : ""} · {x.comments} comment(s)</span>
                  </span>
                  <a href={`/${x.collection}/${x.slug}`} target="_blank" rel="noopener" className="shrink-0 text-xs underline">View</a>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Latest comments" action={<Link href="/admin/comments" className="text-sm underline">Moderate</Link>}>
          {d.recentComments.length === 0 ? (
            <Empty>No comments yet.</Empty>
          ) : (
            <ul className="divide-y divide-line text-sm">
              {d.recentComments.map((x) => (
                <li key={x.id} className="py-2.5">
                  <p className="flex flex-wrap items-center gap-2 text-xs text-fg-subtle">
                    <span className="font-medium text-fg">{x.author}</span> on <Link href={`/admin/posts/${x.postId}`} className="max-w-[16rem] truncate underline">{x.post}</Link>
                    <StatusPill status={x.status} />
                  </p>
                  <p className="mt-1 text-fg-muted [overflow-wrap:anywhere]">{excerpt(x.body)}</p>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        {s && (
          <Panel title="Site health" action={<Link href="/admin/system" className="text-sm underline">System status</Link>}>
            <ul className="divide-y divide-line text-sm">
              {s.health.map((h) => (
                <li key={h.label} className="flex items-center justify-between gap-3 py-2.5">
                  <Link href={h.href} className="font-medium text-fg hover:underline">{h.label}</Link>
                  <span className="flex min-w-0 items-center gap-2 text-xs text-fg-subtle">
                    <span className="truncate">{h.detail}{"at" in h && h.at ? ` · ${formatDateTime(h.at)}` : ""}</span>
                    <StatusPill status={h.ok ? "ok" : "not configured"} />
                  </span>
                </li>
              ))}
            </ul>
          </Panel>
        )}

        {s && s.activity.length > 0 && (
          <Panel title="Recent activity" action={<Link href="/admin/audit" className="text-sm underline">Audit log</Link>}>
            <ul className="divide-y divide-line text-sm">
              {s.activity.map((e) => (
                <li key={e.id} className="flex flex-wrap justify-between gap-2 py-2.5">
                  <span className="min-w-0">
                    <span className="font-mono text-xs text-accent-text">{e.action}</span> <span className="text-fg-muted [overflow-wrap:anywhere]">{e.target}</span>
                  </span>
                  <span className="text-xs text-fg-subtle">{e.actor} · {formatDateTime(e.createdAt.toISOString())}</span>
                </li>
              ))}
            </ul>
          </Panel>
        )}
      </div>
    </>
  );
}
