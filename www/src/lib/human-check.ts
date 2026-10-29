import "server-only";
import { eq } from "drizzle-orm";
import { getDb, schema } from "@/db";
import { getSettings } from "./settings";

/**
 * Remembered human verification for signed-in readers. Passing Cloudflare Turnstile (password sign-in, sign-up
 * or a comment) stamps user.human_verified_at; comments skip the check while that is younger than
 * general.discussion.humanCheckHours (Admin → Appearance). Staff are never asked. Rate limits, duplicate
 * detection and moderation still apply to every comment.
 */
export async function needsHumanCheck(user: { id: string; role: string }, now = Date.now()): Promise<boolean> {
  if (user.role === "admin" || user.role === "author") return false;
  const hours = (await getSettings()).discussion.humanCheckHours ?? 24;
  if (hours <= 0) return true;
  const db = await getDb();
  const [u] = await db.select({ at: schema.user.humanVerifiedAt }).from(schema.user).where(eq(schema.user.id, user.id));
  return !u?.at || now - u.at.getTime() > hours * 3_600_000;
}

export async function rememberHuman(userId: string, at = new Date()) {
  const db = await getDb();
  await db.update(schema.user).set({ humanVerifiedAt: at }).where(eq(schema.user.id, userId));
}
