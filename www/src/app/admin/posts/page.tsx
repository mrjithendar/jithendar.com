import { and, count, desc, eq, ilike, isNotNull, isNull, or, sql } from "drizzle-orm";
import Link from "next/link";
import { AdminHeader } from "@/components/admin/ui";
import { Input, Select } from "@/components/ui/form";
import { getDb, schema } from "@/db";
import { redirect } from "next/navigation";
import { staffActor } from "@/lib/admin";
import { bundledPostsNotImported, importBundledPost } from "@/lib/bundled-posts";
import { formatDateTime } from "@/lib/dates";
import { PostError } from "@/lib/posts";
import { postCounts } from "@/lib/posts";
import { requireRole } from "@/lib/session";
import { BulkPosts } from "./BulkPosts";

export const metadata = { title: "Posts" };

type Search = { q?: string; status?: string; collection?: string; page?: string; error?: string };
const PAGE_SIZE = 25;
const STATUSES = [
  ["", "All"],
  ["draft", "Drafts"],
  ["review", "In review"],
  ["scheduled", "Scheduled"],
  ["published", "Published"],
  ["archived", "Archived"],
  ["trash", "Trash"],
] as const;

/** Import a post file from content/ as a draft and open it in the editor. */
async function importBundled(form: FormData) {
  "use server";
  const actor = await staffActor();
  let id: string;
  try {
    id = await importBundledPost(actor, String(form.get("collection")), String(form.get("slug")));
  } catch (error) {
    if (error instanceof PostError) redirect(`/admin/posts?error=${encodeURIComponent(error.message)}`);
    throw error;
  }
  redirect(`/admin/posts/${id}`);
}

const like = (q: string) => `%${q.replace(/[%_\\]/g, "\\$&")}%`;

export default async function PostsPage({ searchParams }: { searchParams: Promise<Search> }) {
  const user = await requireRole("admin", "author");
  const { q = "", status = "", collection = "", page: rawPage, error } = await searchParams;
  const page = Math.max(1, Math.floor(Number(rawPage) || 1));
  const db = await getDb();
  const where = and(
    user.role === "author" ? eq(schema.post.authorId, user.id) : undefined,
    status === "trash" ? isNotNull(schema.post.deletedAt) : isNull(schema.post.deletedAt),
    status && status !== "trash" ? eq(schema.post.status, status) : undefined,
    collection ? eq(schema.post.collection, collection) : undefined,
    q.trim() ? or(ilike(schema.post.title, like(q.trim())), ilike(schema.post.slug, like(q.trim()))) : undefined,
  );
  const [rows, [total], counts] = await Promise.all([
    db
      .select({ post: schema.post, author: schema.user.name })
      .from(schema.post)
      .leftJoin(schema.user, eq(schema.user.id, schema.post.authorId))
      .where(where)
      .orderBy(desc(sql`coalesce(${schema.post.deletedAt}, ${schema.post.savedAt})`))
      .limit(PAGE_SIZE)
      .offset((page - 1) * PAGE_SIZE),
    db.select({ n: count() }).from(schema.post).where(where),
    postCounts(),
  ]);
  const bundled = status === "trash" ? [] : await bundledPostsNotImported();
  const pages = Math.max(1, Math.ceil((total?.n ?? 0) / PAGE_SIZE));
  const href = (over: Partial<Search>) => {
    const p = new URLSearchParams(Object.entries({ q, status, collection, ...over }).filter(([, v]) => v) as [string, string][]);
    const s = p.toString();
    return s ? `/admin/posts?${s}` : "/admin/posts";
  };
  const allCount = Object.entries(counts).filter(([k]) => k !== "trash").reduce((n, [, c]) => n + c, 0);

  return (
    <>
      <AdminHeader
        title="Posts"
        description="Write, review, schedule and publish articles, news and projects."
        actions={<Link href="/admin/posts/new" className="inline-flex items-center rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-on-accent">New post</Link>}
      />
      {error && <p role="alert" className="mb-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-200">{error}</p>}
      {bundled.length > 0 && (
        <div className="mb-6 rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-950 dark:border-sky-500/30 dark:bg-sky-500/10 dark:text-sky-100">
          <p>Post files in <code className="text-xs">content/</code> that are not in the admin yet (the database imports them only at first setup):</p>
          <ul className="mt-2 space-y-1.5">
            {bundled.map((b) => (
              <li key={`${b.collection}/${b.slug}`} className="flex flex-wrap items-center gap-2">
                <form action={importBundled}>
                  <input type="hidden" name="collection" value={b.collection} />
                  <input type="hidden" name="slug" value={b.slug} />
                  <button type="submit" className="font-semibold underline">Import as draft</button>
                </form>
                <span>{b.title}</span>
                <span className="font-mono text-xs opacity-70">/{b.collection}/{b.slug}</span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs opacity-80">Imported posts open in the editor as drafts; nothing is published until you publish it.</p>
        </div>
      )}
      <nav aria-label="Filter by status" className="-mx-1 mb-4 flex gap-1 overflow-x-auto px-1 pb-1 text-sm">
        {STATUSES.map(([value, label]) => (
          <Link key={value} href={href({ status: value, page: undefined })} aria-current={status === value ? "page" : undefined}
            className={`shrink-0 rounded-full px-3 py-1.5 font-medium ${status === value ? "bg-fg text-canvas" : "text-slate-600 hover:bg-white dark:text-slate-300 dark:hover:bg-white/5"}`}>
            {label} <span className="opacity-60">({value ? (counts[value] ?? 0) : allCount})</span>
          </Link>
        ))}
      </nav>
      <form className="mb-6 grid gap-3 sm:grid-cols-[1fr_180px_auto]">
        <input type="hidden" name="status" value={status} />
        <Input name="q" defaultValue={q} placeholder="Search title or slug" aria-label="Search posts" />
        <Select name="collection" defaultValue={collection} aria-label="Section">
          <option value="">All sections</option>
          <option value="blog">Articles</option>
          <option value="news">News</option>
          <option value="projects">Projects</option>
        </Select>
        <button type="submit" className="min-h-11 rounded-xl border border-line-strong px-4 text-sm font-semibold">Search</button>
      </form>
      <BulkPosts
        trash={status === "trash"}
        rows={rows.map(({ post, author }) => ({
          id: post.id,
          title: post.title,
          collection: post.collection,
          slug: post.slug,
          status: post.status,
          category: post.category,
          author: author ?? "—",
          saved: formatDateTime((post.deletedAt ?? post.savedAt).toISOString()),
          scheduledFor: post.status === "scheduled" && post.publishedAt ? formatDateTime(post.publishedAt.toISOString()) : null,
          cover: post.featuredImage?.src ?? null,
        }))}
      />
      {pages > 1 && (
        <nav aria-label="Pages" className="mt-6 flex items-center justify-between gap-4 text-sm">
          {page > 1 ? <Link href={href({ page: String(page - 1) })} className="rounded-lg px-3 py-2 font-medium underline">← Newer</Link> : <span />}
          <span className="text-slate-500">Page {page} of {pages}</span>
          {page < pages ? <Link href={href({ page: String(page + 1) })} className="rounded-lg px-3 py-2 font-medium underline">Older →</Link> : <span />}
        </nav>
      )}
    </>
  );
}
