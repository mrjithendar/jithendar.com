import "server-only";
import { desc, eq, sql } from "drizzle-orm";
import { getDb, schema } from "@/db";
import { rowsOf } from "@/db/rows";
import { masteryLevel } from "./achievements";
import { recommend, weakTopics } from "./adaptive";
import { listRoles, listTopics, publishedProblems } from "./catalog";
import { getDailyChallenge } from "./daily";
import { practiceDay, previousDay } from "./progress";
import { DIFFICULTIES, SKILL_AREAS, type SkillArea } from "./types";

/**
 * Dashboard numbers. Definitions (also shown in the UI):
 * - attempted: problems with at least one run or submission
 * - solved: accepted without revealing the solution ("independent"); assisted solves are counted separately
 * - independent solve rate: solved / attempted
 * - correctness: accepted submissions / graded submissions (infrastructure errors excluded)
 * - average execution attempts: (runs + submissions) per attempted problem
 * - average solving time: first attempt → first accepted submission, independent solves only
 * - practice time: estimated from activity — gaps between consecutive actions, each capped at 10 minutes
 * - streak: consecutive days (Asia/Kolkata) with at least one graded submission
 */
export const METRIC_DEFINITIONS: Record<string, string> = {
  attempted: "Problems you ran or submitted at least once.",
  solved: "Accepted without revealing the solution. Hints are allowed and recorded.",
  assisted: "Accepted after revealing the solution. Not counted as solved.",
  solveRate: "Independently solved ÷ attempted.",
  correctness: "Accepted submissions ÷ graded submissions (runs and infrastructure errors excluded).",
  attemptsPerProblem: "Runs plus submissions per attempted problem.",
  avgSolveTime: "Time from your first attempt to your first accepted submission, independent solves only.",
  practiceTime: "Estimated from your activity: the gaps between consecutive actions, each counted up to 10 minutes.",
  streak: "Consecutive days (India Standard Time) with at least one graded submission.",
};

const GAP_CAP_SECONDS = 600;

export async function dashboard(userId: string) {
  const db = await getDb();
  const [problems, topics, roles] = await Promise.all([publishedProblems(), listTopics(), listRoles()]);
  const progress = await db.select().from(schema.practiceProgress).where(eq(schema.practiceProgress.userId, userId));
  const [profile] = await db.select().from(schema.practiceProfile).where(eq(schema.practiceProfile.userId, userId));
  const skills = await db.select().from(schema.practiceSkill).where(eq(schema.practiceSkill.userId, userId));
  const byId = new Map(problems.map((p) => [p.id, p]));

  const attempted = progress.length;
  const solved = progress.filter((p) => p.status === "solved");
  const assisted = progress.filter((p) => p.status === "solved_assisted").length;
  const [subs] = rowsOf<{ graded: number; accepted: number }>(
    await db.execute(sql`select count(*) filter (where verdict is not null and verdict not in ('infrastructure_error', 'cancelled'))::int as graded,
      count(*) filter (where verdict = 'accepted')::int as accepted from practice_submission where user_id = ${userId} and kind = 'submit'`),
  );
  const solveTimes = solved.map((p) => p.solveMs).filter((x): x is number => typeof x === "number");
  const [time] = rowsOf<{ seconds: number }>(
    await db.execute(sql`select coalesce(sum(least(extract(epoch from gap), ${GAP_CAP_SECONDS})), 0)::float as seconds from (
      select created_at - lag(created_at) over (order by created_at) as gap from practice_activity_event where user_id = ${userId}) g where gap is not null`),
  );
  const today = practiceDay();
  const streakAlive = profile && (profile.lastActiveDay === today || profile.lastActiveDay === previousDay(today));

  const overview = {
    attempted,
    solved: solved.length,
    assisted,
    solveRate: attempted ? Math.round((solved.length / attempted) * 100) : 0,
    correctness: subs?.graded ? Math.round((subs.accepted / subs.graded) * 100) : 0,
    gradedSubmissions: subs?.graded ?? 0,
    attemptsPerProblem: attempted ? Math.round((progress.reduce((n, p) => n + p.runs + p.submits, 0) / attempted) * 10) / 10 : 0,
    avgSolveMinutes: solveTimes.length ? Math.round(solveTimes.reduce((a, b) => a + b, 0) / solveTimes.length / 6000) / 10 : null,
    practiceMinutes: Math.round(Number(time?.seconds ?? 0) / 60),
    currentStreak: streakAlive ? profile!.currentStreak : 0,
    longestStreak: profile?.longestStreak ?? 0,
    xp: profile?.xp ?? 0,
  };

  // Skill areas (topics roll up into the twelve areas).
  const areaOf = new Map(topics.map((t) => [t.slug, t.area as SkillArea]));
  const areas = Object.fromEntries(Object.keys(SKILL_AREAS).map((a) => [a, { attempts: 0, passes: 0, independent: 0 }])) as Record<SkillArea, { attempts: number; passes: number; independent: number }>;
  for (const s of skills) {
    const area = areaOf.get(s.topic);
    if (!area || !areas[area]) continue;
    areas[area].attempts += s.attempts;
    areas[area].passes += s.passes;
    areas[area].independent += s.independentPasses;
  }
  const skillAreas = (Object.keys(SKILL_AREAS) as SkillArea[]).map((a) => ({ area: a, label: SKILL_AREAS[a], ...areas[a], rate: areas[a].attempts ? Math.round((areas[a].passes / areas[a].attempts) * 100) : null }));

  const status = new Map(progress.map((p) => [p.problemId, p.status]));
  const rolePerf = roles.map((r) => {
    const inRole = problems.filter((p) => p.roles.includes(r.slug));
    const s = inRole.filter((p) => status.get(p.id) === "solved").length;
    return {
      slug: r.slug,
      name: r.name,
      total: inRole.length,
      attempted: inRole.filter((p) => status.has(p.id)).length,
      solved: s,
      assisted: inRole.filter((p) => status.get(p.id) === "solved_assisted").length,
      mastery: masteryLevel(s, inRole.length),
    };
  });
  const preferred = profile?.roles ?? [];
  const roleRows = rolePerf.filter((r) => r.attempted > 0 || preferred.includes(r.slug));

  const difficulty = DIFFICULTIES.map((d) => ({
    difficulty: d,
    total: problems.filter((p) => p.difficulty === d).length,
    attempted: progress.filter((p) => byId.get(p.problemId)?.difficulty === d).length,
    solved: progress.filter((p) => p.status === "solved" && byId.get(p.problemId)?.difficulty === d).length,
  }));

  const heatmap = rowsOf<{ day: string; n: number }>(
    await db.execute(sql`select to_char(created_at at time zone 'Asia/Kolkata', 'YYYY-MM-DD') as day, count(*)::int as n
      from practice_activity_event where user_id = ${userId} and type in ('submission_graded', 'run_completed') and created_at > now() - interval '371 days' group by 1`),
  );

  const weekly = rowsOf<{ week: string; graded: number; accepted: number; seconds: number }>(
    await db.execute(sql`with e as (select created_at, type, detail, created_at - lag(created_at) over (order by created_at) as gap from practice_activity_event where user_id = ${userId})
      select to_char(date_trunc('week', created_at at time zone 'Asia/Kolkata'), 'YYYY-MM-DD') as week,
        count(*) filter (where type = 'submission_graded' and detail->>'verdict' not in ('infrastructure_error', 'cancelled'))::int as graded,
        count(*) filter (where type = 'submission_graded' and detail->>'verdict' = 'accepted')::int as accepted,
        coalesce(sum(least(extract(epoch from gap), ${GAP_CAP_SECONDS})), 0)::float as seconds
      from e where created_at > now() - interval '12 weeks' group by 1 order by 1`),
  ).map((w) => ({ week: w.week, minutes: Math.round(w.seconds / 60), graded: w.graded, accepted: w.accepted, accuracy: w.graded ? Math.round((w.accepted / w.graded) * 100) : null }));

  const monthly = rowsOf<{ month: string; attempted: number; solved: number; avg_ms: number | null }>(
    await db.execute(sql`select to_char(date_trunc('month', first_attempt_at at time zone 'Asia/Kolkata'), 'YYYY-MM') as month, count(*)::int as attempted,
      count(*) filter (where status = 'solved')::int as solved, avg(solve_ms) filter (where status = 'solved')::float as avg_ms
      from practice_progress where user_id = ${userId} and first_attempt_at > now() - interval '12 months' group by 1 order by 1`),
  ).map((m) => ({ month: m.month, attempted: m.attempted, solved: m.solved, completionRate: m.attempted ? Math.round((m.solved / m.attempted) * 100) : 0, avgSolveMinutes: m.avg_ms ? Math.round(m.avg_ms / 6000) / 10 : null }));

  const assessments = rowsOf<{ id: string; mode: string; completed_at: Date | string; percent: number | null }>(
    await db.execute(sql`select id, mode, completed_at, (score->>'percent')::int as percent from practice_session
      where user_id = ${userId} and mode in ('timed', 'mock') and status in ('completed', 'expired') order by completed_at desc limit 12`),
  ).map((a) => ({ id: a.id, mode: a.mode, date: new Date(a.completed_at).toISOString(), percent: a.percent ?? 0 }));

  const recent = await db
    .select({ type: schema.practiceActivityEvent.type, detail: schema.practiceActivityEvent.detail, createdAt: schema.practiceActivityEvent.createdAt, slug: schema.practiceProblem.slug, title: schema.practiceProblem.title })
    .from(schema.practiceActivityEvent)
    .leftJoin(schema.practiceProblem, eq(schema.practiceProblem.id, schema.practiceActivityEvent.problemId))
    .where(eq(schema.practiceActivityEvent.userId, userId))
    .orderBy(desc(schema.practiceActivityEvent.createdAt))
    .limit(12);

  const topicName = new Map(topics.map((t) => [t.slug, t.name]));
  const weakest = weakTopics(skills)
    .slice(0, 5)
    .map((s) => ({ topic: s.topic, name: topicName.get(s.topic) ?? s.topic, attempts: s.attempts, passes: s.passes }));
  const unfinished = progress
    .filter((p) => p.status === "attempted")
    .sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime())
    .slice(0, 5)
    .map((p) => byId.get(p.problemId))
    .filter(Boolean);
  const recommendations = await recommend(userId, 3);
  const daily = await getDailyChallenge().catch(() => null);
  const pathRole = roles.find((r) => preferred.includes(r.slug)) ?? null;

  return {
    overview,
    skillAreas,
    roles: roleRows,
    difficulty,
    heatmap,
    weekly,
    monthly,
    assessments,
    recent: recent.map((r) => ({ ...r, createdAt: r.createdAt.toISOString() })),
    weakest,
    unfinished: unfinished as (typeof problems)[number][],
    recommendations,
    daily: daily ? { ...daily, solved: progress.some((p) => p.problemId === daily.problemId && p.status === "solved") } : null,
    learningPath: pathRole ? { role: pathRole.name, slug: pathRole.slug, steps: pathRole.learningPath } : null,
    preferredRoles: preferred,
    leaderboardOptIn: profile?.leaderboardOptIn ?? false,
    publicName: profile?.publicName ?? "",
  };
}
