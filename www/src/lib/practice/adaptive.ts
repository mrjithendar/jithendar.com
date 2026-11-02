import "server-only";
import { eq } from "drizzle-orm";
import { getDb, schema } from "@/db";
import { listTopics, publishedProblems } from "./catalog";
import { DIFFICULTIES, type Difficulty, type ProblemSummary } from "./types";

/**
 * Explainable recommendations from recorded performance only (graded submissions per topic and solved
 * problems). Every pick comes with the reason, phrased from the numbers that produced it.
 */
export type Recommendation = { problem: ProblemSummary & { id: string }; reason: string; topic: string | null };

type Skill = { topic: string; attempts: number; passes: number; failures: number };

/** Topics where the user struggles: at least one failed submission and a pass rate below 70%, worst first. */
export function weakTopics(skills: Skill[]): Skill[] {
  return skills
    .filter((s) => s.attempts > 0 && s.failures > 0 && s.passes / s.attempts < 0.7)
    .sort((a, b) => a.passes / a.attempts - b.passes / b.attempts || b.attempts - a.attempts || a.topic.localeCompare(b.topic));
}

/** The level a user is comfortable at: the hardest difficulty with at least two independent solves. */
export function comfortLevel(solvedByDifficulty: Partial<Record<Difficulty, number>>): Difficulty | null {
  let level: Difficulty | null = null;
  for (const d of DIFFICULTIES) if ((solvedByDifficulty[d] ?? 0) >= 2) level = d;
  return level;
}

const step = (d: Difficulty, by: number): Difficulty => DIFFICULTIES[Math.min(Math.max(DIFFICULTIES.indexOf(d) + by, 0), DIFFICULTIES.length - 1)]!;

export async function recommend(userId: string, n = 3, opts: { roles?: string[] } = {}): Promise<Recommendation[]> {
  const db = await getDb();
  const [skills, progress, profile, problems, topics] = await Promise.all([
    db.select().from(schema.practiceSkill).where(eq(schema.practiceSkill.userId, userId)),
    db.select().from(schema.practiceProgress).where(eq(schema.practiceProgress.userId, userId)),
    db.select().from(schema.practiceProfile).where(eq(schema.practiceProfile.userId, userId)),
    publishedProblems(),
    listTopics(),
  ]);
  const topicName = new Map(topics.map((t) => [t.slug, t.name]));
  const roles = opts.roles?.length ? opts.roles : (profile[0]?.roles ?? []);
  const status = new Map(progress.map((p) => [p.problemId, p.status]));
  const solvedBy: Partial<Record<Difficulty, number>> = {};
  for (const p of problems) if (status.get(p.id) === "solved") solvedBy[p.difficulty] = (solvedBy[p.difficulty] ?? 0) + 1;
  const level = comfortLevel(solvedBy);
  const open = problems.filter((p) => status.get(p.id) !== "solved" && (!roles.length || p.roles.some((r) => roles.includes(r))));
  const chosen = new Set<string>();
  const out: Recommendation[] = [];
  const take = (p: ProblemSummary & { id: string }, reason: string, topic: string | null) => {
    if (chosen.has(p.id) || out.length >= n) return;
    chosen.add(p.id);
    out.push({ problem: p, reason, topic });
  };

  // 1. Weak topics, at or just below the comfortable level (failing a lot → step down).
  for (const s of weakTopics(skills)) {
    const rate = s.passes / s.attempts;
    const target = level ? step(level, rate < 0.4 ? -1 : 0) : "beginner";
    const candidates = open
      .filter((p) => p.topics.includes(s.topic))
      .sort((a, b) => Math.abs(DIFFICULTIES.indexOf(a.difficulty) - DIFFICULTIES.indexOf(target)) - Math.abs(DIFFICULTIES.indexOf(b.difficulty) - DIFFICULTIES.indexOf(target)) || a.title.localeCompare(b.title));
    const pick = candidates[0];
    if (pick) take(pick, `You passed ${s.passes} of ${s.attempts} submissions on ${topicName.get(s.topic) ?? s.topic}; this ${pick.difficulty} problem targets that topic.`, s.topic);
  }

  // 2. Unfinished problems (attempted, not solved).
  for (const p of progress.filter((p) => p.status === "attempted").sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime())) {
    const problem = problems.find((x) => x.id === p.problemId);
    if (problem) take(problem, `You started this problem${p.submits ? ` and submitted ${p.submits} time${p.submits === 1 ? "" : "s"}` : ""} but haven't solved it yet.`, null);
  }

  // 3. The next step up from the comfortable level, in the user's roles.
  const next = level ? step(level, 1) : "beginner";
  for (const p of open.filter((p) => p.difficulty === next).sort((a, b) => a.title.localeCompare(b.title))) {
    take(p, level ? `You've solved ${solvedBy[level]} ${level} problems independently; this ${next} problem is the next step.` : "No practice history yet — a beginner problem to start with.", null);
  }
  for (const p of open) take(p, "More practice in your selected roles.", null);
  return out;
}
