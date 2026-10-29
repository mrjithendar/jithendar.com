import "server-only";
import { eq } from "drizzle-orm";
import { getDb, schema } from "@/db";
import { audit } from "./audit";
import { articleRow } from "./content/import";
import { contentRoot, loadContent } from "./content/load";
import { log } from "./log";
import type { Actor } from "./posts";
import { PostError } from "./posts";

/**
 * Posts shipped in content/{blog,news,projects}/*.mdx are imported into Postgres only once, by /setup. Files
 * added later (new drafts) are listed here so an editor can import them; nothing is ever imported or
 * published automatically.
 */
export type BundledPost = { collection: string; slug: string; title: string; status: string };

export async function bundledPostsNotImported(): Promise<BundledPost[]> {
  let articles;
  try {
    articles = loadContent(contentRoot()).articles;
  } catch (err) {
    log.warn("bundled content unavailable", { err });
    return [];
  }
  const db = await getDb();
  const existing = new Set((await db.select({ c: schema.post.collection, s: schema.post.slug }).from(schema.post)).map((r) => `${r.c}/${r.s}`));
  return articles
    .filter((a) => !existing.has(`${a.collection}/${a.slug}`))
    .map((a) => ({ collection: a.collection, slug: a.slug, title: a.frontmatter.title, status: a.frontmatter.status }));
}

/**
 * Import one bundled post as a draft (whatever its frontmatter says) so it goes through review and publishing
 * in the editor. The byline is the file's author when that profile exists, otherwise the importing user.
 */
export async function importBundledPost(actor: Actor, collection: string, slug: string): Promise<string> {
  if (actor.role !== "admin" && actor.role !== "author") throw new PostError("Not allowed.", 403);
  const article = loadContent(contentRoot()).articles.find((a) => a.collection === collection && a.slug === slug);
  if (!article) throw new PostError("That file is not in the bundled content.", 404);
  const db = await getDb();
  const [profile] = await db.select({ userId: schema.authorProfile.userId }).from(schema.authorProfile).where(eq(schema.authorProfile.slug, article.frontmatter.author));
  // Authors import under their own name; admins keep the byline from the file.
  const authorId = actor.role === "admin" && profile ? profile.userId : actor.id;
  const [row] = await db
    .insert(schema.post)
    .values({ ...articleRow(article, authorId), status: "draft", publishedAt: null })
    .onConflictDoNothing()
    .returning({ id: schema.post.id });
  if (!row) throw new PostError(`A post at /${collection}/${slug} already exists.`, 409);
  await audit(actor, "post.import", `${collection}/${slug}`, { from: `content/${collection}/${slug}.mdx` });
  return row.id;
}
