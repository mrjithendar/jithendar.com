/**
 * Send content/{blog,news,projects}/*.mdx to the live site through /api/v1/posts, so a new article needs no
 * image build or deploy. New files become drafts; a file whose post is still a draft or in review updates it.
 * Published, scheduled and archived posts are only changed with --update-live (their status never changes).
 * Nothing is ever published: review and publish in Admin → Posts.
 *
 *   JITHENDAR_API_KEY=jk_… npm run push-post -- content/blog/my-post.mdx [more.mdx] [--dry-run] [--update-live]
 *
 * The key needs the posts:read and posts:write scopes (Admin → API keys). JITHENDAR_SITE_URL or --site picks
 * another site (default https://jithendar.com).
 */
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { collections, type Collection } from "../src/config/taxonomy";
import { splitFrontmatter } from "../src/lib/content/frontmatter";
import { articleRow } from "../src/lib/content/import";
import { collectionSchema } from "../src/lib/content/schema";

type Fetch = typeof fetch;
type RemotePost = { id: string; collection: string; slug: string; status: string };
export type PushOptions = { site: string; apiKey?: string; dryRun?: boolean; updateLive?: boolean; publicDir?: string; fetch?: Fetch; log?: (line: string) => void };
export type PushResult = { file: string; action: "created" | "updated" | "would create" | "would update" | "skipped"; id?: string; reason?: string };

const EDITABLE = new Set(["draft", "review"]);

/** The API body for one MDX file: everything the editor stores except status, publication date and author. */
export function draftPayload(file: string) {
  const collection = path.basename(path.dirname(file));
  if (!(collections as readonly string[]).includes(collection)) throw new Error(`${file}: must be in content/${collections.join("|")}/`);
  const { data, body } = splitFrontmatter(fs.readFileSync(file, "utf8"));
  const parsed = collectionSchema(collection as Collection).safeParse(data);
  if (!parsed.success) throw new Error(`${file}:\n  ${parsed.error.issues.map((i) => `${i.path.join(".") || "(root)"}: ${i.message}`).join("\n  ")}`);
  const fm = parsed.data;
  if (path.basename(file, ".mdx") !== fm.slug) throw new Error(`${file}: slug must match the file name`);
  const row = articleRow({ collection: collection as Collection, slug: fm.slug, path: `/${collection}/${fm.slug}`, frontmatter: fm, body, file }, "");
  const { authorId: _a, status: _s, publishedAt: _p, updatedAt: _u, ...fields } = row;
  void [_a, _s, _p, _u];
  return { ...fields, updatedAt: fm.updatedAt ?? null };
}

/** Site-relative /images/… paths a post refers to (body and cover). */
export function localImages(payload: { body: string; featuredImage: { src: string } | null }): string[] {
  const refs = new Set<string>();
  for (const m of payload.body.matchAll(/\/images\/[^\s)"'<>\]]+/g)) refs.add(m[0]);
  if (payload.featuredImage?.src.startsWith("/images/")) refs.add(payload.featuredImage.src);
  return [...refs];
}

async function call<T>(f: Fetch, site: string, apiKey: string, url: string, init: RequestInit = {}): Promise<T> {
  const res = await f(`${site}${url}`, { ...init, headers: { authorization: `Bearer ${apiKey}`, "content-type": "application/json", ...init.headers } });
  const text = await res.text();
  const parsed = text ? (JSON.parse(text) as { data?: T; error?: { message: string; issues?: string[] } }) : {};
  if (!res.ok) throw new Error(`${init.method ?? "GET"} ${url}: ${res.status} ${parsed.error?.message ?? text}${parsed.error?.issues?.length ? `\n  ${parsed.error.issues.join("\n  ")}` : ""}`);
  return parsed.data as T;
}

export async function pushPosts(files: string[], opts: PushOptions): Promise<PushResult[]> {
  const f = opts.fetch ?? fetch;
  const log = opts.log ?? console.log;
  const site = opts.site.replace(/\/+$/, "");
  const publicDir = opts.publicDir ?? path.join(process.cwd(), "public");
  if (!opts.apiKey && !opts.dryRun) throw new Error("Set JITHENDAR_API_KEY (Admin → API keys, scopes posts:read + posts:write), or use --dry-run.");

  // Everything is checked before anything is sent, so a bad file in a batch changes nothing.
  const payloads = files.map((file) => ({ file, payload: draftPayload(file) }));
  for (const { file, payload } of payloads) {
    for (const src of localImages(payload)) {
      if (!fs.existsSync(path.join(publicDir, src))) throw new Error(`${file}: ${src} does not exist in public/`);
      const res = await f(`${site}${src}`, { method: "HEAD" });
      if (!res.ok) {
        throw new Error(`${file}: ${src} is not on ${site} yet (HTTP ${res.status}). Files in public/ ship only with an image build: upload it in Admin → Media and use its /media/… URL, or deploy once.`);
      }
    }
  }

  const existing = new Map<string, Map<string, RemotePost>>();
  const lookup = async (collection: string, slug: string) => {
    if (!opts.apiKey) return undefined;
    if (!existing.has(collection)) {
      const bySlug = new Map<string, RemotePost>();
      for (let offset = 0; ; offset += 200) {
        const page = await call<RemotePost[]>(f, site, opts.apiKey, `/api/v1/posts?collection=${collection}&limit=200&offset=${offset}`);
        for (const p of page) bySlug.set(p.slug, p);
        if (page.length < 200) break;
      }
      existing.set(collection, bySlug);
    }
    return existing.get(collection)!.get(slug);
  };

  const results: PushResult[] = [];
  for (const { file, payload } of payloads) {
    const url = `/${payload.collection}/${payload.slug}`;
    const current = await lookup(payload.collection, payload.slug);
    let result: PushResult;
    if (current && !EDITABLE.has(current.status) && !opts.updateLive) {
      result = { file, action: "skipped", id: current.id, reason: `${url} is ${current.status}; rerun with --update-live to change it` };
    } else if (opts.dryRun) {
      result = { file, action: current ? "would update" : "would create", id: current?.id };
    } else if (current) {
      await call(f, site, opts.apiKey!, `/api/v1/posts/${current.id}`, { method: "PATCH", body: JSON.stringify(payload) });
      result = { file, action: "updated", id: current.id };
    } else {
      const created = await call<RemotePost>(f, site, opts.apiKey!, "/api/v1/posts", { method: "POST", body: JSON.stringify({ ...payload, status: "draft" }) });
      result = { file, action: "created", id: created.id };
    }
    log(`${result.action.padEnd(12)} ${url}${result.id ? `  ${site}/admin/posts/${result.id}` : ""}${result.reason ? `  (${result.reason})` : ""}`);
    results.push(result);
  }
  return results;
}

async function main(argv: string[]) {
  const flags = new Set(argv.filter((a) => a.startsWith("--") && !a.startsWith("--site=")));
  const unknown = [...flags].filter((a) => a !== "--dry-run" && a !== "--update-live");
  const files = argv.filter((a) => !a.startsWith("--"));
  if (unknown.length || files.length === 0) {
    console.error("Usage: npm run push-post -- <content/…/post.mdx>… [--dry-run] [--update-live] [--site=https://…]");
    process.exit(2);
  }
  const site = argv.find((a) => a.startsWith("--site="))?.slice(7) ?? process.env.JITHENDAR_SITE_URL ?? "https://jithendar.com";
  const results = await pushPosts(files, { site, apiKey: process.env.JITHENDAR_API_KEY, dryRun: flags.has("--dry-run"), updateLive: flags.has("--update-live") });
  if (results.some((r) => r.action === "skipped")) process.exitCode = 1;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main(process.argv.slice(2)).catch((err: Error) => {
    console.error(err.message);
    process.exit(1);
  });
}
