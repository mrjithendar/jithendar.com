import "server-only";
import { and, count, eq, sql } from "drizzle-orm";
import { schema, type Db } from "@/db";
import { rowsOf } from "@/db/rows";

/**
 * Badges. Each is computed from verified server-side records (graded submissions, progress written by the
 * grader, server-computed streaks) — never from values sent by the browser.
 */
export type Badge = { id: string; name: string; description: string; tier: "bronze" | "silver" | "gold" };

export const BADGES: Badge[] = [
  { id: "python-beginner", name: "Python Beginner", description: "Solve your first problem without revealing the solution.", tier: "bronze" },
  { id: "ten-solved", name: "Ten Down", description: "Solve 10 problems independently.", tier: "bronze" },
  { id: "fifty-solved", name: "Half Century", description: "Solve 50 problems independently.", tier: "silver" },
  { id: "hundred-solved", name: "100 Problems Solved", description: "Solve 100 problems independently.", tier: "gold" },
  { id: "streak-7", name: "7-Day Streak", description: "Submit code on 7 consecutive days.", tier: "bronze" },
  { id: "streak-30", name: "30-Day Streak", description: "Submit code on 30 consecutive days.", tier: "gold" },
  { id: "async-specialist", name: "Async Python Specialist", description: "Independently solve 5 asyncio or concurrency problems.", tier: "silver" },
  { id: "devops-automation-expert", name: "DevOps Automation Expert", description: "Independently solve 10 DevOps Engineer problems.", tier: "silver" },
  { id: "rag-engineer", name: "RAG Engineer", description: "Independently solve 3 retrieval (RAG) problems.", tier: "silver" },
  { id: "api-expert", name: "API Expert", description: "Independently solve 5 HTTP API, pagination, validation or rate-limiting problems.", tier: "silver" },
  { id: "kubernetes-automation-specialist", name: "Kubernetes Automation Specialist", description: "Independently solve 4 Kubernetes problems.", tier: "silver" },
  { id: "expert-solver", name: "Expert Solver", description: "Independently solve an expert-level problem.", tier: "gold" },
  { id: "no-hints-ten", name: "Unassisted", description: "Solve 10 problems without hints or solutions.", tier: "silver" },
  { id: "assessment-ace", name: "Assessment Ace", description: "Score 80% or more in a timed assessment or mock interview.", tier: "gold" },
];

type Facts = { solved: number; noHints: number; longestStreak: number; byTopic: Record<string, number>; byRole: Record<string, number>; expert: number; bestAssessment: number };

async function facts(tx: Db, userId: string): Promise<Facts> {
  const solvedRows = rowsOf<{ topics: string[]; roles: string[]; difficulty: string; hints_used: number }>(
    await tx.execute(sql`select p.topics, p.roles, p.difficulty, pr.hints_used from practice_progress pr join practice_problem p on p.id = pr.problem_id
      where pr.user_id = ${userId} and pr.status = 'solved'`),
  );
  const byTopic: Record<string, number> = {};
  const byRole: Record<string, number> = {};
  for (const r of solvedRows) {
    for (const t of r.topics) byTopic[t] = (byTopic[t] ?? 0) + 1;
    for (const role of r.roles) byRole[role] = (byRole[role] ?? 0) + 1;
  }
  const [profile] = await tx.select({ longest: schema.practiceProfile.longestStreak }).from(schema.practiceProfile).where(eq(schema.practiceProfile.userId, userId));
  const [best] = rowsOf<{ best: number | null }>(
    await tx.execute(sql`select max((score->>'percent')::numeric) as best from practice_session where user_id = ${userId} and mode in ('timed', 'mock') and status in ('completed', 'expired')`),
  );
  return {
    solved: solvedRows.length,
    noHints: solvedRows.filter((r) => r.hints_used === 0).length,
    longestStreak: profile?.longest ?? 0,
    byTopic,
    byRole,
    expert: solvedRows.filter((r) => r.difficulty === "expert").length,
    bestAssessment: Number(best?.best ?? 0),
  };
}

const sumTopics = (f: Facts, topics: string[]) => topics.reduce((n, t) => n + (f.byTopic[t] ?? 0), 0);

const RULES: Record<string, (f: Facts) => boolean> = {
  "python-beginner": (f) => f.solved >= 1,
  "ten-solved": (f) => f.solved >= 10,
  "fifty-solved": (f) => f.solved >= 50,
  "hundred-solved": (f) => f.solved >= 100,
  "streak-7": (f) => f.longestStreak >= 7,
  "streak-30": (f) => f.longestStreak >= 30,
  "async-specialist": (f) => sumTopics(f, ["asyncio", "concurrency"]) >= 5,
  "devops-automation-expert": (f) => (f.byRole["devops-engineer"] ?? 0) >= 10,
  "rag-engineer": (f) => (f.byTopic.rag ?? 0) >= 3,
  "api-expert": (f) => sumTopics(f, ["http-apis", "pagination", "validation", "rate-limiting"]) >= 5,
  "kubernetes-automation-specialist": (f) => (f.byTopic.kubernetes ?? 0) >= 4,
  "expert-solver": (f) => f.expert >= 1,
  "no-hints-ten": (f) => f.noHints >= 10,
  "assessment-ace": (f) => f.bestAssessment >= 80,
};

/** Award every badge whose rule now holds; returns the newly earned badge ids. Idempotent. */
export async function awardBadges(tx: Db, userId: string, eventId: string | null): Promise<string[]> {
  const f = await facts(tx, userId);
  const have = new Set((await tx.select({ badge: schema.practiceAchievement.badge }).from(schema.practiceAchievement).where(eq(schema.practiceAchievement.userId, userId))).map((r) => r.badge));
  const earned = BADGES.filter((b) => !have.has(b.id) && RULES[b.id]?.(f)).map((b) => b.id);
  if (!earned.length) return [];
  const inserted = await tx
    .insert(schema.practiceAchievement)
    .values(earned.map((badge) => ({ userId, badge, eventId })))
    .onConflictDoNothing()
    .returning({ badge: schema.practiceAchievement.badge });
  if (inserted.length) {
    await tx.insert(schema.practiceActivityEvent).values(inserted.map((r) => ({ userId, type: "achievement_earned", detail: { badge: r.badge } })));
  }
  return inserted.map((r) => r.badge);
}

export async function badgeCount(tx: Db, userId: string): Promise<number> {
  const [row] = await tx.select({ n: count() }).from(schema.practiceAchievement).where(and(eq(schema.practiceAchievement.userId, userId)));
  return Number(row?.n ?? 0);
}

/** Role mastery from the share of a role's problems solved independently. */
export function masteryLevel(solved: number, total: number): { level: "Novice" | "Practitioner" | "Advanced" | "Master"; percent: number } {
  const percent = total ? Math.round((solved / total) * 100) : 0;
  return { level: percent >= 80 ? "Master" : percent >= 50 ? "Advanced" : percent >= 25 ? "Practitioner" : "Novice", percent };
}
