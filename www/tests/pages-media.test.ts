import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { schema, setDbForTests, type Db } from "@/db";
import { getPage, invalidateContent } from "@/lib/content";
import { mediaUsage, mediaUsedIn, updateMediaDetails } from "@/lib/media";
import type { Actor } from "@/lib/posts";
import { savePage } from "@/lib/site-pages";
import { freshDb } from "./db-helpers";

vi.mock("server-only", () => ({}));

const admin: Actor = { id: "admin", role: "admin", label: "admin@example.com" };
const ID = "0b9f3c1e-2a4d-4c6b-8e0f-1a2b3c4d5e6f";
const cover = { src: `/media/${ID}/team.jpg`, alt: "The team at a whiteboard", width: 1600, height: 900 };
const page = { slug: "about", title: "About", description: "A description that is comfortably longer than fifty characters for pages.", body: "Hello" };

let db: Db;
beforeEach(async () => {
  vi.stubEnv("CONTENT_DIR", "");
  delete process.env.CONTENT_DIR;
  db = await freshDb();
  await db.insert(schema.user).values({ id: "admin", name: "Admin", email: "admin@example.com", role: "admin" });
  await db.insert(schema.media).values({ id: ID, filename: "team.jpg", contentType: "image/jpeg", storageKey: `k/${ID}.jpg`, storageBackend: "r2", kind: "images", sizeBytes: 1000, width: 1600, height: 900, alt: "" });
  invalidateContent();
});
afterEach(() => {
  vi.unstubAllEnvs();
  setDbForTests(undefined);
});

describe("pages", () => {
  it("store a featured image and expose it to the public page", async () => {
    await savePage(admin, null, { ...page, featuredImage: cover });
    invalidateContent();
    expect((await getPage("about"))?.frontmatter.featuredImage).toMatchObject({ src: cover.src, alt: cover.alt });
    expect((await mediaUsage([ID])).get(ID)).toBe(1);
    expect(await mediaUsedIn(ID)).toEqual([{ kind: "page", title: "About", editHref: "/admin/pages/about", publicPath: "/about" }]);
  });

  it("refuse a featured image without alt text, unknown images, and body images without alt", async () => {
    await expect(savePage(admin, null, { ...page, featuredImage: { ...cover, alt: "" } })).rejects.toMatchObject({ issues: expect.arrayContaining([expect.stringMatching(/alt text is required/)]) });
    await expect(savePage(admin, null, { ...page, featuredImage: { ...cover, src: "/media/00000000-0000-4000-8000-000000000000/x.jpg" } })).rejects.toMatchObject({ issues: expect.arrayContaining([expect.stringMatching(/not found/)]) });
    await expect(savePage(admin, null, { ...page, body: `![](${cover.src})` })).rejects.toMatchObject({ issues: expect.arrayContaining([expect.stringMatching(/needs alt text/)]) });
  });
});

describe("attachment details", () => {
  it("require alt text for images and keep title, caption and description", async () => {
    await expect(updateMediaDetails(admin, ID, { alt: " ", title: "Team" })).rejects.toThrow(/alt text/);
    await updateMediaDetails(admin, ID, { alt: "The team at a whiteboard", title: "Team", caption: "Planning, October", description: "Photo: our own" });
    const [row] = await db.select().from(schema.media);
    expect(row).toMatchObject({ alt: "The team at a whiteboard", title: "Team", caption: "Planning, October", description: "Photo: our own" });
  });
});
