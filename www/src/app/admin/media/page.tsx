import { and, count, desc, eq, gte, ilike, lt, or, sql, type SQL } from "drizzle-orm";
import Link from "next/link";
import { Flash, type FlashParams } from "@/components/admin/Flash";
import { AdminHeader, Card } from "@/components/admin/ui";
import { Alert, Button, Input, Select } from "@/components/ui/form";
import { getDb, schema } from "@/db";
import { rowsOf } from "@/db/rows";
import { mediaSrc, mediaUsage, MEDIA_DETAIL_LIMITS } from "@/lib/media";
import { requireRole } from "@/lib/session";
import { MEDIA_KINDS, storageReady } from "@/lib/storage";
import { MediaLibrary, type LibraryItem } from "./MediaLibrary";
import { MediaUploader } from "./MediaUploader";

export const metadata = { title: "Media" };

const PAGE_SIZE = 48;
const MONTH = /^\d{4}-(0[1-9]|1[0-2])$/;
const TZ = "Asia/Kolkata";

const size = (n: number) => (n > 1024 * 1024 * 1024 ? `${(n / 1024 ** 3).toFixed(2)} GB` : n > 1024 * 1024 ? `${(n / 1024 / 1024).toFixed(1)} MB` : `${Math.round(n / 1024)} KB`);

/** The Markdown an author pastes to use the file. */
function snippet(m: { id: string; filename: string; kind: string; alt: string }) {
  const src = mediaSrc(m);
  if (m.kind === "images") return `![${m.alt}](${src})`;
  if (m.kind === "videos") return `::video{src="${src}"}`;
  if (m.kind === "audio") return `::audio{src="${src}"}`;
  return `[${m.alt || m.filename}](${src})`;
}

const monthLabel = (ym: string) => new Date(`${ym}-15T00:00:00Z`).toLocaleDateString("en-GB", { month: "long", year: "numeric", timeZone: "UTC" });

/**
 * Media library, modelled on WordPress: grid or list view, filters by type, month and missing alt text, search,
 * attachment details (alt text, title, caption, description, where it is used), bulk delete, drag-and-drop upload.
 */
export default async function MediaPage({ searchParams }: { searchParams: FlashParams }) {
  await requireRole("admin", "author");
  const sp = await searchParams;
  const kind = MEDIA_KINDS.find((k) => k === sp.kind);
  const month = sp.month && MONTH.test(sp.month) ? sp.month : undefined;
  const q = (sp.q ?? "").trim().slice(0, 100);
  const missingAlt = sp.alt === "missing";
  const view = sp.view === "list" ? "list" : "grid";
  const page = Math.max(1, Math.floor(Number(sp.page) || 1));
  const m = schema.media;
  const like = q ? `%${q.replace(/[%_\\]/g, "\\$&")}%` : undefined;
  const monthStart = month ? sql`(${`${month}-01`}::date::timestamp at time zone ${TZ})` : undefined;
  const where: SQL | undefined = and(
    eq(m.status, "ready"),
    kind ? eq(m.kind, kind) : undefined,
    like ? or(ilike(m.filename, like), ilike(m.alt, like), ilike(m.title, like), ilike(m.caption, like)) : undefined,
    missingAlt ? and(eq(m.kind, "images"), eq(m.alt, "")) : undefined,
    monthStart ? and(gte(m.createdAt, monthStart), lt(m.createdAt, sql`${monthStart} + interval '1 month'`)) : undefined,
  );

  const db = await getDb();
  const [rows, [total], ready, months, [totals]] = await Promise.all([
    db
      .select({ media: m, uploader: schema.user.name })
      .from(m)
      .leftJoin(schema.user, eq(schema.user.id, m.uploadedBy))
      .where(where)
      .orderBy(desc(m.createdAt))
      .limit(PAGE_SIZE)
      .offset((page - 1) * PAGE_SIZE),
    db.select({ n: count() }).from(m).where(where),
    storageReady(),
    db
      .execute(sql`select to_char(created_at at time zone ${TZ}, 'YYYY-MM') as ym, count(*)::int as n from media where status = 'ready' group by 1 order by 1 desc limit 60`)
      .then((r) => rowsOf<{ ym: string; n: number }>(r)),
    db
      .select({
        files: count(),
        bytes: sql<number>`coalesce(sum(${m.sizeBytes}), 0)::bigint`,
        noAlt: sql<number>`count(*) filter (where ${m.kind} = 'images' and ${m.alt} = '')::int`,
      })
      .from(m)
      .where(eq(m.status, "ready")),
  ]);
  const pages = Math.max(1, Math.ceil((total?.n ?? 0) / PAGE_SIZE));
  const usage = await mediaUsage(rows.map((r) => r.media.id));
  const items: LibraryItem[] = rows.map(({ media: x, uploader }) => ({
    id: x.id,
    src: mediaSrc(x),
    filename: x.filename,
    kind: x.kind,
    contentType: x.contentType,
    alt: x.alt,
    title: x.title,
    caption: x.caption,
    description: x.description,
    width: x.width,
    height: x.height,
    size: size(x.sizeBytes),
    visibility: x.visibility,
    onLegacyStorage: x.storageBackend !== "r2",
    uploadedAt: x.createdAt.toISOString(),
    uploadedBy: uploader ?? "—",
    uses: usage.get(x.id) ?? 0,
    snippet: snippet(x),
  }));

  const params = (over: Record<string, string | undefined>) => {
    const merged = { kind, month, q: q || undefined, alt: missingAlt ? "missing" : undefined, view: view === "list" ? "list" : undefined, page: undefined, ...over };
    const qs = new URLSearchParams(Object.entries(merged).filter((e): e is [string, string] => Boolean(e[1]))).toString();
    return qs ? `/admin/media?${qs}` : "/admin/media";
  };
  const noAlt = Number(totals?.noAlt ?? 0);

  return (
    <>
      <AdminHeader
        title="Media library"
        description={
          <>
            {totals?.files ?? 0} file(s) · {size(Number(totals?.bytes ?? 0))} in Cloudflare R2. Links (<code className="text-xs">/media/…</code>) never change, even if the storage does.
          </>
        }
      />
      <Flash ok={sp.ok} error={sp.error} />
      {ready ? (
        <Card className="mb-6">
          <MediaUploader />
        </Card>
      ) : (
        <div className="mb-6">
          <Alert tone="info">
            Uploads are disabled until media storage is configured. <Link href="/admin/storage" className="font-semibold underline">Configure Cloudflare R2</Link>.
          </Alert>
        </div>
      )}

      {noAlt > 0 && !missingAlt && (
        <div className="mb-6">
          <Alert tone="info">
            {noAlt} image(s) have no alt text, so screen readers and search engines cannot describe them.{" "}
            <Link href={params({ alt: "missing", kind: undefined })} className="font-semibold underline">Review them</Link>.
          </Alert>
        </div>
      )}

      <form className="mb-6 flex flex-wrap items-end gap-2 rounded-xl border border-line bg-surface p-3" role="search" aria-label="Filter media">
        {view === "list" && <input type="hidden" name="view" value="list" />}
        <label className="sr-only" htmlFor="f-kind">Type</label>
        <div className="w-full min-[420px]:w-44">
          <Select id="f-kind" name="kind" defaultValue={kind ?? ""}>
            <option value="">All media items</option>
            {MEDIA_KINDS.map((k) => <option key={k} value={k}>{k[0]!.toUpperCase() + k.slice(1)}</option>)}
          </Select>
        </div>
        <label className="sr-only" htmlFor="f-month">Month</label>
        <div className="w-full min-[420px]:w-52">
          <Select id="f-month" name="month" defaultValue={month ?? ""}>
            <option value="">All dates</option>
            {months.map((x) => <option key={x.ym} value={x.ym}>{monthLabel(x.ym)} ({x.n})</option>)}
          </Select>
        </div>
        <label className="flex min-h-10 items-center gap-2 px-2 text-sm text-fg-muted">
          <input type="checkbox" name="alt" value="missing" defaultChecked={missingAlt} /> Missing alt text
        </label>
        <div className="ml-auto flex min-w-0 flex-1 gap-2 sm:max-w-xs">
          <label className="sr-only" htmlFor="f-q">Search media</label>
          <Input id="f-q" name="q" type="search" defaultValue={q} placeholder="Search media…" />
          <Button type="submit" variant="secondary">Filter</Button>
        </div>
      </form>

      <MediaLibrary
        items={items}
        view={view}
        viewHrefs={{ grid: params({ view: undefined, page: page > 1 ? String(page) : undefined }), list: params({ view: "list", page: page > 1 ? String(page) : undefined }) }}
        limits={MEDIA_DETAIL_LIMITS}
        total={total?.n ?? 0}
        filtered={Boolean(kind || month || q || missingAlt)}
        clearHref="/admin/media"
      />

      {pages > 1 && (
        <nav aria-label="Pages" className="mt-8 flex items-center justify-between gap-4 text-sm">
          {page > 1 ? <Link href={params({ page: page - 1 > 1 ? String(page - 1) : undefined })} className="rounded-lg px-3 py-2 font-medium underline">← Newer</Link> : <span />}
          <span className="text-fg-subtle">Page {page} of {pages}</span>
          {page < pages ? <Link href={params({ page: String(page + 1) })} className="rounded-lg px-3 py-2 font-medium underline">Older →</Link> : <span />}
        </nav>
      )}
    </>
  );
}
