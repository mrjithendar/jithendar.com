import "server-only";
import { createHash } from "node:crypto";
import { eq, sql } from "drizzle-orm";
import { z } from "zod";
import { getDb, schema } from "@/db";
import { rowsOf } from "@/db/rows";
import { auditSafe } from "../audit";
import { PracticeError } from "./errors";
import { getPracticeSettings } from "./settings";

/** Practice preferences, the opt-in leaderboard, and account data export/deletion for this module. */

const prefsInput = z.object({
  roles: z.array(z.string().regex(/^[a-z0-9-]{1,60}$/)).max(20).optional(),
  leaderboardOptIn: z.boolean().optional(),
  publicName: z
    .string()
    .trim()
    .max(40)
    .regex(/^[\p{L}\p{N} ._-]*$/u, "Use letters, numbers, spaces, dots, dashes or underscores.")
    .optional(),
  editor: z.object({ theme: z.enum(["system", "light", "dark"]).optional(), fontSize: z.number().int().min(11).max(24).optional(), runtime: z.string().max(40).optional() }).optional(),
});

export async function updatePreferences(userId: string, raw: unknown) {
  const parsed = prefsInput.safeParse(raw);
  if (!parsed.success) throw new PracticeError(parsed.error.issues[0]?.message ?? "Invalid preferences.", 400, "invalid");
  const v = parsed.data;
  const db = await getDb();
  await db.insert(schema.practiceProfile).values({ userId }).onConflictDoNothing();
  const [current] = await db.select().from(schema.practiceProfile).where(eq(schema.practiceProfile.userId, userId));
  await db
    .update(schema.practiceProfile)
    .set({
      ...(v.roles ? { roles: v.roles } : {}),
      ...(v.leaderboardOptIn !== undefined ? { leaderboardOptIn: v.leaderboardOptIn } : {}),
      ...(v.publicName !== undefined ? { publicName: v.publicName || null } : {}),
      ...(v.editor ? { preferences: { ...current!.preferences, editor: { ...((current!.preferences.editor as object) ?? {}), ...v.editor } } } : {}),
      updatedAt: new Date(),
    })
    .where(eq(schema.practiceProfile.userId, userId));
}

export async function getPreferences(userId: string) {
  const db = await getDb();
  const [p] = await db.select().from(schema.practiceProfile).where(eq(schema.practiceProfile.userId, userId));
  return { roles: p?.roles ?? [], leaderboardOptIn: p?.leaderboardOptIn ?? false, publicName: p?.publicName ?? "", editor: (p?.preferences.editor as Record<string, unknown> | undefined) ?? {} };
}

/** Opt-in leaderboard. Shows a chosen public name (or an anonymous handle) — never emails or account ids. */
export async function leaderboard(limit = 50) {
  if (!(await getPracticeSettings()).leaderboard.enabled) return null;
  const db = await getDb();
  const rows = rowsOf<{ user_id: string; public_name: string | null; xp: number; current_streak: number; last_active_day: string | null; solved: number }>(
    await db.execute(sql`select pp.user_id, pp.public_name, pp.xp, pp.current_streak, pp.last_active_day,
        (select count(*)::int from practice_progress pr where pr.user_id = pp.user_id and pr.status = 'solved') as solved
      from practice_profile pp where pp.leaderboard_opt_in and pp.xp > 0 order by pp.xp desc, solved desc limit ${limit}`),
  );
  return rows.map((r, i) => ({
    rank: i + 1,
    name: r.public_name || `Coder ${createHash("sha256").update(r.user_id).digest("hex").slice(0, 6)}`,
    xp: r.xp,
    solved: r.solved,
    streak: r.current_streak,
    handle: createHash("sha256").update(`lb:${r.user_id}`).digest("hex").slice(0, 10),
  }));
}

/** Everything this module stores about a user, as JSON (Account → privacy export). */
export async function exportPracticeData(userId: string) {
  const db = await getDb();
  const q = async (table: string) => rowsOf<Record<string, unknown>>(await db.execute(sql`select * from ${sql.identifier(table)} where user_id = ${userId}`));
  const data = {
    exportedAt: new Date().toISOString(),
    profile: await q("practice_profile"),
    progress: await q("practice_progress"),
    skills: await q("practice_skill"),
    sessions: await q("practice_session"),
    submissions: await q("practice_submission"),
    bookmarks: await q("practice_bookmark"),
    notes: await q("practice_note"),
    achievements: await q("practice_achievement"),
    activity: await q("practice_activity_event"),
    aiUsage: await q("practice_ai_usage"),
  };
  await auditSafe({ id: userId, label: userId }, "practice.data_export", userId);
  return data;
}

/** Delete this module's data for a user (the site account itself is deleted from Account settings). */
export async function deletePracticeData(userId: string) {
  const db = await getDb();
  await db.transaction(async (tx) => {
    for (const table of ["practice_activity_event", "practice_achievement", "practice_note", "practice_bookmark", "practice_skill", "practice_progress", "practice_submission", "practice_session", "practice_profile"]) {
      await tx.execute(sql`delete from ${sql.identifier(table)} where user_id = ${userId}`);
    }
    await tx.execute(sql`update practice_ai_usage set user_id = null where user_id = ${userId}`);
  });
  await auditSafe({ id: userId, label: userId }, "practice.data_deleted", userId);
}

/** Retention (scheduler, daily): drop old activity events and the code of old submissions. */
export async function applyRetention(now = new Date()) {
  const s = await getPracticeSettings();
  const db = await getDb();
  await db.execute(sql`delete from practice_activity_event where created_at < ${new Date(now.getTime() - s.retention.activityDays * 86_400_000).toISOString()}`);
  await db.execute(sql`update practice_submission set code = '' where code <> '' and created_at < ${new Date(now.getTime() - s.retention.codeDays * 86_400_000).toISOString()}`);
  await db.execute(sql`delete from practice_ai_usage where created_at < ${new Date(now.getTime() - 400 * 86_400_000).toISOString()}`);
}
