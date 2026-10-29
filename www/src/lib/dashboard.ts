import "server-only";
import { and, desc, eq, sql } from "drizzle-orm";
import { getDb, schema } from "@/db";
import { rowsOf } from "@/db/rows";
import { recentRuns } from "./backups";
import { moderationCounts } from "./comments";
import { activeProviders, resolveGeminiImageConfig } from "./integrations";
import { emailSummary } from "./mail";
import { postCounts } from "./posts";
import { securityOverview } from "./security";
import { storageReady } from "./storage";
import { turnstileKeys } from "./turnstile";

/** Everything the admin dashboard shows, in one round of parallel queries. Admin-only parts are null for authors. */
export async function dashboardData(user: { id: string; role: string }) {
  const db = await getDb();
  const admin = user.role === "admin";
  const p = schema.post;

  const [counts, moderation, byCollection, [comments7d], [media], myDrafts, upcoming, recentPublished, recentComments] = await Promise.all([
    postCounts(),
    moderationCounts(),
    db
      .select({ collection: p.collection, n: sql<number>`count(*)::int` })
      .from(p)
      .where(and(eq(p.status, "published"), sql`${p.deletedAt} is null`))
      .groupBy(p.collection),
    db
      .select({ n: sql<number>`count(*) filter (where ${schema.comment.createdAt} > now() - interval '7 days')::int`, total: sql<number>`count(*) filter (where ${schema.comment.status} = 'approved')::int` })
      .from(schema.comment),
    db
      .select({
        files: sql<number>`count(*)::int`,
        bytes: sql<number>`coalesce(sum(${schema.media.sizeBytes}), 0)::bigint`,
        noAlt: sql<number>`count(*) filter (where ${schema.media.kind} = 'images' and ${schema.media.alt} = '')::int`,
        week: sql<number>`count(*) filter (where ${schema.media.createdAt} > now() - interval '7 days')::int`,
      })
      .from(schema.media)
      .where(eq(schema.media.status, "ready")),
    db
      .select({ id: p.id, title: p.title, status: p.status, savedAt: p.savedAt })
      .from(p)
      .where(and(eq(p.authorId, user.id), sql`${p.status} in ('draft', 'review')`, sql`${p.deletedAt} is null`))
      .orderBy(desc(p.savedAt))
      .limit(5),
    db
      .select({ id: p.id, title: p.title, publishedAt: p.publishedAt })
      .from(p)
      .where(and(eq(p.status, "scheduled"), sql`${p.deletedAt} is null`))
      .orderBy(p.publishedAt)
      .limit(5),
    db
      .select({ id: p.id, title: p.title, collection: p.collection, slug: p.slug, publishedAt: p.publishedAt, comments: sql<number>`(select count(*)::int from comment c where c.post_id = ${p.id} and c.status = 'approved')` })
      .from(p)
      .where(and(eq(p.status, "published"), sql`${p.deletedAt} is null`, sql`${p.publishedAt} <= now()`))
      .orderBy(desc(p.publishedAt))
      .limit(5),
    db
      .select({ id: schema.comment.id, body: schema.comment.body, status: schema.comment.status, createdAt: schema.comment.createdAt, author: schema.user.name, post: p.title, postId: p.id })
      .from(schema.comment)
      .innerJoin(schema.user, eq(schema.user.id, schema.comment.userId))
      .innerJoin(p, eq(p.id, schema.comment.postId))
      .where(sql`${schema.comment.deletedAt} is null`)
      .orderBy(desc(schema.comment.createdAt))
      .limit(5),
  ]);

  const adminOnly = admin
    ? await Promise.all([
        db.execute(sql`select count(*)::int as total,
            count(*) filter (where created_at > now() - interval '7 days')::int as week,
            count(*) filter (where role = 'admin')::int as admins,
            count(*) filter (where role = 'author')::int as authors,
            count(*) filter (where banned)::int as banned
          from "user"`),
        db.select({ n: sql<number>`count(*)::int` }).from(schema.contactMessage).where(eq(schema.contactMessage.status, "new")),
        db.select().from(schema.auditLog).orderBy(desc(schema.auditLog.createdAt)).limit(8),
        securityOverview(24),
        recentRuns(1),
        storageReady(),
        emailSummary(),
        activeProviders(),
        resolveGeminiImageConfig(),
        turnstileKeys(),
      ])
    : null;

  let site = null;
  if (adminOnly) {
    const [usersRaw, [unread], activity, security, [lastBackup], storage, email, providers, gemini, turnstile] = adminOnly;
    const users = rowsOf<{ total: number; week: number; admins: number; authors: number; banned: number }>(usersRaw)[0];
    site = {
      users: { total: Number(users?.total ?? 0), week: Number(users?.week ?? 0), admins: Number(users?.admins ?? 0), authors: Number(users?.authors ?? 0), banned: Number(users?.banned ?? 0) },
      unreadMessages: Number(unread?.n ?? 0),
      activity,
      security,
      health: [
        { label: "Media storage (R2)", ok: storage, detail: storage ? "Connected" : "Not configured", href: "/admin/storage" },
        { label: "Email", ok: email.active !== "disabled" || email.envFallback, detail: email.envFallback ? "SMTP (deployment)" : email.active === "disabled" ? "Disabled" : email.active.toUpperCase(), href: "/admin/storage" },
        { label: "Turnstile", ok: Boolean(turnstile.siteKey && turnstile.secret), detail: turnstile.production ? "Production keys" : "Test keys", href: "/admin/advanced" },
        { label: "Social sign-in", ok: providers.length > 0, detail: providers.length ? providers.map((x) => (x === "github" ? "GitHub" : "Google")).join(", ") : "Off", href: "/admin/integrations" },
        { label: "Image generation", ok: Boolean(gemini), detail: gemini ? gemini.model : "Off", href: "/admin/integrations" },
        {
          label: "Backups",
          ok: lastBackup?.status === "success",
          detail: lastBackup ? lastBackup.status : "Never run",
          at: lastBackup?.startedAt.toISOString(),
          href: "/admin/backups",
        },
      ],
    };
  }

  return {
    counts,
    moderation,
    byCollection: Object.fromEntries(byCollection.map((r) => [r.collection, Number(r.n)])) as Record<string, number>,
    comments: { week: Number(comments7d?.n ?? 0), approved: Number(comments7d?.total ?? 0) },
    media: { files: Number(media?.files ?? 0), bytes: Number(media?.bytes ?? 0), noAlt: Number(media?.noAlt ?? 0), week: Number(media?.week ?? 0) },
    myDrafts,
    upcoming,
    recentPublished,
    recentComments,
    site,
  };
}
