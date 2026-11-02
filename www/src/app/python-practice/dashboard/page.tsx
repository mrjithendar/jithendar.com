import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";
import { Container } from "@/components/Container";
import { DifficultyBadge } from "@/components/practice/Badges";
import { ActivityHeatmap, MeterRows, TimeBars } from "@/components/practice/Charts";
import { PrivacyForm } from "@/components/practice/PrivacyForm";
import { listRoles } from "@/lib/practice/catalog";
import { dashboard, METRIC_DEFINITIONS } from "@/lib/practice/dashboard";
import { practiceDay } from "@/lib/practice/progress";
import { DIFFICULTY_INFO, type Difficulty } from "@/lib/practice/types";
import { requireUser } from "@/lib/session";

export const metadata: Metadata = { title: "Dashboard", robots: { index: false, follow: false } };

const EVENT_LABELS: Record<string, string> = {
  session_started: "Started a session",
  session_resumed: "Resumed a session",
  session_completed: "Completed a session",
  assessment_completed: "Completed an assessment",
  code_submitted: "Submitted",
  test_execution_requested: "Ran tests",
  submission_graded: "Submission graded",
  run_completed: "Run finished",
  hint_requested: "Opened a hint",
  solution_revealed: "Revealed a solution",
  question_skipped: "Skipped a question",
  question_bookmarked: "Bookmarked",
  achievement_earned: "Earned a badge",
  ai_assistance: "Asked the AI tutor",
  rate_limited: "Hit a rate limit",
};

function Tile({ label, value, def }: { label: string; value: ReactNode; def: string }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-4" title={def}>
      <p className="text-sm text-fg-subtle">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-fg">{value}</p>
    </div>
  );
}

function Card({ title, children, id }: { title: string; children: ReactNode; id?: string }) {
  return (
    <section id={id} className="scroll-mt-24 rounded-xl border border-line bg-surface p-5">
      <h2 className="font-semibold text-fg">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

export default async function DashboardPage() {
  const user = await requireUser("/python-practice/dashboard");
  const [d, roles] = await Promise.all([dashboard(user.id), listRoles()]);
  const o = d.overview;
  return (
    <Container className="space-y-6 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-title font-bold text-fg">Your dashboard</h1>
          <p className="mt-1 text-fg-muted">{o.xp} XP · {o.currentStreak}-day streak (longest {o.longestStreak})</p>
        </div>
        <Link href="/python-practice" className="text-sm font-medium text-accent-text underline">
          Start practising
        </Link>
      </div>

      <section aria-label="Overview" className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-5">
        <Tile label="Attempted" value={o.attempted} def={METRIC_DEFINITIONS.attempted!} />
        <Tile label="Solved independently" value={o.solved} def={METRIC_DEFINITIONS.solved!} />
        <Tile label="Solved with solution" value={o.assisted} def={METRIC_DEFINITIONS.assisted!} />
        <Tile label="Independent solve rate" value={`${o.solveRate}%`} def={METRIC_DEFINITIONS.solveRate!} />
        <Tile label="Correctness" value={o.gradedSubmissions ? `${o.correctness}%` : "—"} def={METRIC_DEFINITIONS.correctness!} />
        <Tile label="Attempts per problem" value={o.attemptsPerProblem || "—"} def={METRIC_DEFINITIONS.attemptsPerProblem!} />
        <Tile label="Average solve time" value={o.avgSolveMinutes !== null ? `${o.avgSolveMinutes} min` : "—"} def={METRIC_DEFINITIONS.avgSolveTime!} />
        <Tile label="Practice time" value={`${Math.floor(o.practiceMinutes / 60)} h ${o.practiceMinutes % 60} m`} def={METRIC_DEFINITIONS.practiceTime!} />
        <Tile label="Current streak" value={`${o.currentStreak} d`} def={METRIC_DEFINITIONS.streak!} />
        <Tile label="Longest streak" value={`${o.longestStreak} d`} def={METRIC_DEFINITIONS.streak!} />
      </section>
      <details className="text-sm text-fg-muted">
        <summary className="cursor-pointer">How these numbers are defined</summary>
        <dl className="mt-2 grid gap-1 sm:grid-cols-2">
          {Object.entries(METRIC_DEFINITIONS).map(([k, v]) => (
            <div key={k}>
              <dt className="inline font-medium text-fg">{k}: </dt>
              <dd className="inline">{v}</dd>
            </div>
          ))}
        </dl>
      </details>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card title="Activity">
            <ActivityHeatmap days={d.heatmap} today={practiceDay()} />
          </Card>
          <div className="grid gap-6 md:grid-cols-2">
            <Card title="Weekly practice time (minutes)">
              <TimeBars label="Minutes practised per week, last 12 weeks" unit="min" data={d.weekly.map((w) => ({ key: w.week, value: w.minutes, caption: `Week of ${w.week}` }))} />
            </Card>
            <Card title="Weekly accuracy (% accepted)">
              <TimeBars label="Share of graded submissions accepted per week" unit="%" data={d.weekly.map((w) => ({ key: w.week, value: w.accuracy, caption: `Week of ${w.week}` }))} />
            </Card>
            <Card title="Monthly completion rate (%)">
              <TimeBars label="Problems solved independently ÷ attempted, by month first attempted" unit="%" data={d.monthly.map((m) => ({ key: m.month, value: m.completionRate }))} />
            </Card>
            <Card title="Average solve time by month (minutes)">
              <TimeBars label="Average minutes from first attempt to first accepted submission" unit="min" data={d.monthly.map((m) => ({ key: m.month, value: m.avgSolveMinutes }))} />
            </Card>
          </div>
          <Card title="Skill performance">
            <MeterRows rows={d.skillAreas.map((s) => ({ label: s.label, value: s.rate, detail: s.attempts ? `${s.passes}/${s.attempts} accepted` : "not practised" }))} />
          </Card>
          <Card title="By difficulty">
            <MeterRows rows={d.difficulty.map((x) => ({ label: DIFFICULTY_INFO[x.difficulty as Difficulty].label, value: x.total ? Math.round((x.solved / x.total) * 100) : 0, detail: `${x.solved} solved · ${x.attempted} tried · ${x.total}` }))} />
          </Card>
          <Card title="By role">
            {d.roles.length ? (
              <MeterRows rows={d.roles.map((r) => ({ label: r.name, value: r.mastery.percent, detail: `${r.mastery.level} · ${r.solved}/${r.total}` }))} />
            ) : (
              <p className="text-sm text-fg-muted">Pick your roles below or practise a role to see progress here.</p>
            )}
          </Card>
          <Card title="Assessment scores">
            {d.assessments.length ? (
              <TimeBars label="Timed assessment and mock interview scores, oldest to newest" unit="%" data={[...d.assessments].reverse().map((a) => ({ key: a.id, value: a.percent, caption: `${a.mode} · ${a.date.slice(0, 10)}` }))} />
            ) : (
              <p className="text-sm text-fg-muted">No timed assessments or mock interviews yet.</p>
            )}
          </Card>
        </div>
        <div className="space-y-6">
          <Card title="Recommended next">
            <ul className="space-y-3">
              {d.recommendations.map((r) => (
                <li key={r.problem.id}>
                  <Link href={`/python-practice/problems/${r.problem.slug}`} className="font-medium text-fg hover:underline">
                    {r.problem.title}
                  </Link>{" "}
                  <DifficultyBadge difficulty={r.problem.difficulty} />
                  <p className="mt-0.5 text-sm text-fg-muted">{r.reason}</p>
                </li>
              ))}
            </ul>
          </Card>
          {d.daily && (
            <Card title="Today's daily challenge">
              <Link href={`/python-practice/problems/${d.daily.slug}`} className="font-medium text-fg hover:underline">
                {d.daily.title}
              </Link>
              <p className="mt-1 text-sm text-fg-muted">{d.daily.solved ? "Solved — nice." : "Not solved yet. A new challenge appears at midnight IST."}</p>
            </Card>
          )}
          <Card title="Weakest topics">
            {d.weakest.length ? (
              <ul className="space-y-1 text-sm">
                {d.weakest.map((w) => (
                  <li key={w.topic}>
                    <Link href={`/python-practice/problems?topic=${w.topic}`} className="text-fg hover:underline">
                      {w.name}
                    </Link>{" "}
                    <span className="text-fg-muted">
                      — {w.passes}/{w.attempts} accepted
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-fg-muted">No weak topics recorded yet.</p>
            )}
          </Card>
          <Card title="Unfinished">
            {d.unfinished.length ? (
              <ul className="space-y-1 text-sm">
                {d.unfinished.map((p) => (
                  <li key={p.id}>
                    <Link href={`/python-practice/problems/${p.slug}`} className="text-fg hover:underline">
                      {p.title}
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-fg-muted">Nothing left half-done.</p>
            )}
          </Card>
          {d.learningPath && (
            <Card title={`Learning path: ${d.learningPath.role}`}>
              <ol className="list-decimal space-y-1 pl-5 text-sm text-fg-muted">
                {d.learningPath.steps.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ol>
            </Card>
          )}
          <Card title="Recent activity">
            <ul className="space-y-1.5 text-sm">
              {d.recent.map((e, i) => (
                <li key={i} className="flex justify-between gap-2">
                  <span className="text-fg">
                    {EVENT_LABELS[e.type] ?? e.type}
                    {e.title ? `: ${e.title}` : ""}
                  </span>
                  <span className="shrink-0 text-fg-subtle">{new Date(e.createdAt).toLocaleDateString("en-GB", { timeZone: "Asia/Kolkata" })}</span>
                </li>
              ))}
              {!d.recent.length && <li className="text-fg-muted">No activity yet.</li>}
            </ul>
          </Card>
        </div>
      </div>
      <Card title="Privacy, leaderboard and data" id="privacy">
        <PrivacyForm roles={roles.map((r) => ({ slug: r.slug, name: r.name }))} initial={{ roles: d.preferredRoles, leaderboardOptIn: d.leaderboardOptIn, publicName: d.publicName }} />
      </Card>
    </Container>
  );
}
