"use server";

import { revalidatePath } from "next/cache";
import { staffActor } from "@/lib/admin";
import { deleteMedia, deleteMediaMany, mediaUsedIn, updateMediaDetails, type MediaUse } from "@/lib/media";
import { PostError } from "@/lib/posts";

export type MediaActionResult = { ok: true; message: string } | { ok: false; error: string };

const failure = (error: unknown): MediaActionResult => {
  if (error instanceof PostError) return { ok: false, error: error.message };
  throw error;
};

export async function saveMediaDetailsAction(id: string, details: { alt: string; title: string; caption: string; description: string }): Promise<MediaActionResult> {
  const actor = await staffActor();
  try {
    await updateMediaDetails(actor, id, details);
    revalidatePath("/admin/media");
    return { ok: true, message: "Saved." };
  } catch (error) {
    return failure(error);
  }
}

export async function deleteMediaAction(id: string): Promise<MediaActionResult> {
  const actor = await staffActor();
  try {
    await deleteMedia(actor, id);
    revalidatePath("/admin/media");
    return { ok: true, message: "File deleted." };
  } catch (error) {
    return failure(error);
  }
}

export async function bulkDeleteMediaAction(ids: string[]): Promise<MediaActionResult> {
  const actor = await staffActor();
  if (!Array.isArray(ids) || ids.some((id) => typeof id !== "string")) return { ok: false, error: "Nothing selected." };
  const { deleted, skipped } = await deleteMediaMany(actor, ids);
  revalidatePath("/admin/media");
  if (skipped.length === 0) return { ok: true, message: `${deleted} file(s) deleted.` };
  return { ok: deleted > 0, ...(deleted > 0 ? { message: `${deleted} deleted; ${skipped.length} skipped because they are still in use.` } : { error: `Nothing deleted: ${skipped[0]!.reason}` }) } as MediaActionResult;
}

export async function mediaUsedInAction(id: string): Promise<MediaUse[]> {
  await staffActor();
  return mediaUsedIn(id);
}
