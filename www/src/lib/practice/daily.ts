import "server-only";
import { createHash } from "node:crypto";
import { and, desc, eq, gte } from "drizzle-orm";
import { getDb, schema, type Db } from "@/db";
import { publishedProblems } from "./catalog";
import { practiceDay } from "./progress";

/**
 * One curated question per day. An admin can pin a problem for a date; otherwise the first request of the day
 * picks one deterministically (hash of the date) among eligible problems not used in the last 60 days, and
 * stores it so every replica and every visitor sees the same one.
 */
export async function getDailyChallenge(day = practiceDay(), tx?: Db): Promise<{ day: string; problemId: string; slug: string; title: string; difficulty: string } | null> {
  const db = tx ?? (await getDb());
  const existing = await lookup(db, day);
  if (existing) return existing;
  const problems = await publishedProblems();
  if (!problems.length) return null;
  const eligible = new Set(
    (
      await db
        .select({ id: schema.practiceProblem.id })
        .from(schema.practiceProblem)
        .where(and(eq(schema.practiceProblem.status, "published"), eq(schema.practiceProblem.dailyEligible, true)))
    ).map((r) => r.id),
  );
  const since = new Date(`${day}T00:00:00Z`);
  since.setUTCDate(since.getUTCDate() - 60);
  const recent = new Set(
    (await db.select({ id: schema.practiceDailyChallenge.problemId }).from(schema.practiceDailyChallenge).where(gte(schema.practiceDailyChallenge.day, since.toISOString().slice(0, 10)))).map((r) => r.id),
  );
  const pool = problems.filter((p) => eligible.has(p.id) && !recent.has(p.id)).sort((a, b) => a.slug.localeCompare(b.slug));
  const candidates = pool.length ? pool : problems.filter((p) => eligible.has(p.id));
  if (!candidates.length) return null;
  const index = parseInt(createHash("sha256").update(`daily:${day}`).digest("hex").slice(0, 8), 16) % candidates.length;
  await db.insert(schema.practiceDailyChallenge).values({ day, problemId: candidates[index]!.id }).onConflictDoNothing();
  return lookup(db, day);
}

async function lookup(db: Db, day: string) {
  const [row] = await db
    .select({ day: schema.practiceDailyChallenge.day, problemId: schema.practiceDailyChallenge.problemId, slug: schema.practiceProblem.slug, title: schema.practiceProblem.title, difficulty: schema.practiceProblem.difficulty })
    .from(schema.practiceDailyChallenge)
    .innerJoin(schema.practiceProblem, eq(schema.practiceProblem.id, schema.practiceDailyChallenge.problemId))
    .where(eq(schema.practiceDailyChallenge.day, day));
  return row ?? null;
}

export async function recentDailies(limit = 14) {
  const db = await getDb();
  return db
    .select({ day: schema.practiceDailyChallenge.day, slug: schema.practiceProblem.slug, title: schema.practiceProblem.title, chosenBy: schema.practiceDailyChallenge.chosenBy })
    .from(schema.practiceDailyChallenge)
    .innerJoin(schema.practiceProblem, eq(schema.practiceProblem.id, schema.practiceDailyChallenge.problemId))
    .orderBy(desc(schema.practiceDailyChallenge.day))
    .limit(limit);
}

/** Days on which the user solved that day's challenge (daily completion history). */
export async function dailyCompletions(userId: string, limit = 60): Promise<string[]> {
  const db = await getDb();
  const { sql } = await import("drizzle-orm");
  const { rowsOf } = await import("@/db/rows");
  const rows = rowsOf<{ day: string }>(
    await db.execute(sql`select d.day from practice_daily_challenge d
      where exists (select 1 from practice_submission s where s.user_id = ${userId} and s.problem_id = d.problem_id and s.verdict = 'accepted'
        and to_char(s.created_at at time zone 'Asia/Kolkata', 'YYYY-MM-DD') = d.day)
      order by d.day desc limit ${limit}`),
  );
  return rows.map((r) => r.day);
}
