import { eq } from "drizzle-orm";
import { notFound } from "next/navigation";
import { getDb, schema } from "@/db";
import { actorOf } from "@/lib/admin";
import { imageGenerationStatus } from "@/lib/image-generation";
import { getAutosave } from "@/lib/revisions";
import { requireRole } from "@/lib/session";
import { bundledPages, pageRowToForm } from "@/lib/site-pages";
import { PageEditor } from "../PageEditor";

export const metadata = { title: "Edit page" };

export default async function EditPage({ params }: { params: Promise<{ slug: string }> }) {
  const user = await requireRole("admin", "author");
  const { slug } = await params;
  const db = await getDb();
  const [row] = await db.select().from(schema.page).where(eq(schema.page.slug, slug));
  if (!row || row.deletedAt) notFound();
  const [autosave, bundled, imageGeneration] = await Promise.all([getAutosave(actorOf(user), "page", slug), bundledPages(), imageGenerationStatus()]);
  const initial = pageRowToForm(row);
  const draft = bundled.get(slug);
  return (
    <PageEditor
      originalSlug={row.slug}
      initial={initial}
      version={row.version}
      autosaved={autosave ? { value: pageRowToForm(autosave.payload), savedAt: autosave.savedAt.toISOString(), baseVersion: autosave.baseVersion } : null}
      bundled={draft && draft.body.trim() !== initial.body.trim() ? draft : null}
      imageGeneration={imageGeneration}
    />
  );
}
