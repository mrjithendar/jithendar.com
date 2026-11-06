import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { schema, setDbForTests, type Db } from "@/db";
import { createApiKey } from "@/lib/api-keys";
import { invalidateContent } from "@/lib/content";
import type { Actor } from "@/lib/posts";
import { draftPayload, pushPosts } from "../scripts/push-post";
import { freshDb } from "./db-helpers";

vi.mock("server-only", () => ({}));
const admin: Actor = { id: "admin", role: "admin", label: "a@example.com" };
const site = "https://jithendar.com";

let db: Db;
let dir: string;
let key: string;

function write(collection: string, slug: string, extra = "", body = "Body text.", contentType = "opinion") {
  const file = path.join(dir, "content", collection, `${slug}.mdx`);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(
    file,
    `---\ntitle: A post pushed from a file through the API\nslug: ${slug}\ndescription: A description that is comfortably longer than fifty characters for the schema.\nauthor: test-author\ncategory: ai-engineering\ncontentType: ${contentType}\nstatus: published\npublishedAt: 2026-10-27T18:00:00+05:30\n${extra}---\n${body}\n`,
  );
  return file;
}

/** Routes the script's requests to the real /api/v1 handlers; anything else (image HEADs) answers 404. */
const apiFetch = (live = new Set<string>()) =>
  (async (input: string | URL | Request, init?: RequestInit) => {
    const req = new Request(input, init);
    const { pathname } = new URL(req.url);
    if (pathname === "/api/v1/posts") return (await import("@/app/api/v1/posts/route"))[req.method as "GET" | "POST"](req);
    const m = /^\/api\/v1\/posts\/([^/]+)$/.exec(pathname);
    if (m) return (await import("@/app/api/v1/posts/[id]/route")).PATCH(req, { params: Promise.resolve({ id: m[1]! }) });
    return new Response(null, { status: live.has(pathname) ? 200 : 404 });
  }) as typeof fetch;

beforeEach(async () => {
  db = await freshDb();
  await db.insert(schema.user).values({ id: "admin", name: "A", email: "a@example.com", role: "admin" });
  await db.insert(schema.authorProfile).values({ userId: "admin", slug: "writer", displayName: "A" });
  invalidateContent();
  key = (await createApiKey(admin, { name: "push", scopes: ["posts:read", "posts:write"] })).key;
  dir = fs.mkdtempSync(path.join(os.tmpdir(), "push-post-"));
});
afterEach(() => {
  setDbForTests(undefined);
  fs.rmSync(dir, { recursive: true, force: true });
});

const opts = (extra = {}) => ({ site, apiKey: key, publicDir: path.join(dir, "public"), fetch: apiFetch(), log: () => {}, ...extra });

describe("push-post", () => {
  it("creates a draft whatever the file's status says, then updates it in place", async () => {
    const file = write("blog", "pushed-post");
    const [first] = await pushPosts([file], opts());
    expect(first).toMatchObject({ action: "created" });
    const [row] = await db.select().from(schema.post);
    expect(row).toMatchObject({ slug: "pushed-post", status: "draft", publishedAt: null, authorId: "admin", body: "Body text.\n" });

    write("blog", "pushed-post", "", "Second version.");
    const [second] = await pushPosts([file], opts());
    expect(second).toMatchObject({ action: "updated", id: first!.id });
    const rows = await db.select().from(schema.post);
    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({ status: "draft", body: "Second version.\n" });
  });

  it("leaves live posts alone unless --update-live, and never changes their status", async () => {
    const file = write("blog", "live-post");
    const [created] = await pushPosts([file], opts());
    const { PATCH } = await import("@/app/api/v1/posts/[id]/route");
    await PATCH(
      new Request(`${site}/api/v1/posts/${created!.id}`, { method: "PATCH", headers: { authorization: `Bearer ${key}` }, body: JSON.stringify({ status: "published", publishedAt: "2026-10-27T18:00:00+05:30" }) }),
      { params: Promise.resolve({ id: created!.id! }) },
    );
    write("blog", "live-post", "", "Edited after publishing.");
    expect((await pushPosts([file], opts()))[0]).toMatchObject({ action: "skipped" });
    expect((await db.select().from(schema.post))[0]!.body).toBe("Body text.\n");
    expect((await pushPosts([file], opts({ updateLive: true })))[0]).toMatchObject({ action: "updated" });
    expect((await db.select().from(schema.post))[0]).toMatchObject({ status: "published", body: "Edited after publishing.\n" });
  });

  it("dry run sends nothing", async () => {
    const file = write("news", "dry-news", "sources:\n  - { title: Source, url: https://example.com/a, publisher: Example }\n", "Body text.", "news");
    expect((await pushPosts([file], opts({ dryRun: true })))[0]).toMatchObject({ action: "would create" });
    expect(await db.select().from(schema.post)).toHaveLength(0);
  });

  it("refuses a post whose /images/ file is not deployed yet, before sending anything", async () => {
    const ok = write("blog", "first-post");
    // A real file in public/, so the API's own image check (run in this process) finds it too.
    const file = write("blog", "image-post", "", "![RoboShop AI](/images/roboshop-ai/hero.jpg)");
    const local = { publicDir: path.join(process.cwd(), "public") };
    await expect(pushPosts([ok, file], opts(local))).rejects.toThrow(/not on https:\/\/jithendar.com yet \(HTTP 404\)/);
    expect(await db.select().from(schema.post)).toHaveLength(0);
    await expect(pushPosts([write("blog", "missing-img", "", "![x](/images/nope.png)")], opts(local))).rejects.toThrow(/does not exist in public/);
    const [res] = await pushPosts([file], opts({ ...local, fetch: apiFetch(new Set(["/images/roboshop-ai/hero.jpg"])) }));
    expect(res).toMatchObject({ action: "created" });
  });

  it("validates the file locally and reports API errors", async () => {
    expect(() => draftPayload(write("pages", "about"))).toThrow(/must be in content\/blog\|news\|projects/);
    const bad = write("blog", "bad-post", "", "");
    fs.writeFileSync(bad, fs.readFileSync(bad, "utf8").replace("slug: bad-post", "slug: other-slug"));
    expect(() => draftPayload(bad)).toThrow(/slug must match the file name/);
    await expect(pushPosts([write("blog", "no-key")], { ...opts(), apiKey: undefined })).rejects.toThrow(/JITHENDAR_API_KEY/);
    await expect(pushPosts([write("blog", "remote-img", "", "![x](https://example.com/x.png)")], opts())).rejects.toThrow(/400 [\s\S]*remote image/);
  });
});
