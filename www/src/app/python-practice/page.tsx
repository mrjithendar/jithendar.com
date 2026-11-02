import type { Metadata } from "next";
import Link from "next/link";
import { Container } from "@/components/Container";
import { CategoryIcon } from "@/components/icons";
import { DifficultyBadge } from "@/components/practice/Badges";
import { StartPracticeForm } from "@/components/practice/StartPracticeForm";
import { buttonClass } from "@/components/ui/form";
import { absoluteUrl } from "@/config/site";
import { catalogStats, listRoles, listTopics } from "@/lib/practice/catalog";
import { getDailyChallenge } from "@/lib/practice/daily";
import { executionAvailable } from "@/lib/practice/settings";
import { DIFFICULTIES, DIFFICULTY_INFO, MODE_INFO, MODES } from "@/lib/practice/types";

export const metadata: Metadata = {
  title: "Python practice for engineers",
  description: "Practise Python for DevOps, SRE, platform, cloud, AWS, AI, GenAI, data and backend roles: 100+ original problems, timed assessments, mock interviews and progress tracking.",
  alternates: { canonical: absoluteUrl("/python-practice") },
};

export default async function PracticeHome() {
  const [roles, topics, stats, daily, canRun] = await Promise.all([listRoles(), listTopics(), catalogStats(), getDailyChallenge().catch(() => null), executionAvailable()]);
  return (
    <>
      <div className="border-b border-line bg-surface-muted">
        <Container className="py-12 sm:py-16">
          <p className="eyebrow">Interview preparation</p>
          <h1 className="mt-2 max-w-3xl text-display font-bold text-fg">Python practice built around the job you do</h1>
          <p className="mt-4 max-w-2xl text-lg leading-relaxed text-fg-muted">
            {stats.total} original problems for {roles.length} engineering roles — log analysis and Kubernetes for SREs, Boto3-style automation for cloud engineers, retrieval and resilient model
            gateways for AI engineers — graded against hidden tests in an isolated sandbox.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link href="/python-practice/roles" className={buttonClass("primary", "lg")}>
              Choose your role
            </Link>
            <Link href="/python-practice/problems" className={buttonClass("secondary", "lg")}>
              Browse problems
            </Link>
          </div>
          {!canRun && <p className="mt-4 text-sm text-fg-subtle">Running code is being set up. Problems, hints and reference solutions are available now.</p>}
        </Container>
      </div>
      <Container className="space-y-section py-section">
        {daily && (
          <section aria-labelledby="daily" className="rounded-xl border border-line bg-surface p-5 sm:p-6">
            <p className="eyebrow" id="daily">
              Daily challenge · {daily.day}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <Link href={`/python-practice/problems/${daily.slug}`} className="text-xl font-semibold text-fg hover:underline">
                {daily.title}
              </Link>
              <DifficultyBadge difficulty={daily.difficulty as (typeof DIFFICULTIES)[number]} />
            </div>
            <p className="mt-2 text-sm text-fg-muted">Solve it today to extend your streak and earn 20 bonus XP.</p>
          </section>
        )}

        <section aria-labelledby="roles-h">
          <h2 id="roles-h" className="text-heading font-semibold text-fg">
            Engineering roles
          </h2>
          <ul className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {roles.map((r) => (
              <li key={r.slug}>
                <Link href={`/python-practice/roles#${r.slug}`} className="flex h-full gap-3 rounded-xl border border-line bg-surface p-4 hover:border-line-strong">
                  <CategoryIcon name={r.icon} className="mt-0.5 h-5 w-5 shrink-0 text-accent-text" />
                  <span>
                    <span className="block font-semibold text-fg">{r.name}</span>
                    <span className="block text-sm text-fg-subtle">{stats.byRole[r.slug] ?? 0} problems</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="levels-h">
          <h2 id="levels-h" className="text-heading font-semibold text-fg">
            Difficulty levels
          </h2>
          <ul className="mt-6 grid gap-4 md:grid-cols-5">
            {DIFFICULTIES.map((d) => (
              <li key={d} className="rounded-xl border border-line bg-surface p-4">
                <div className="flex items-center justify-between">
                  <DifficultyBadge difficulty={d} />
                  <span className="text-sm text-fg-subtle">{stats.byDifficulty[d]}</span>
                </div>
                <p className="mt-3 text-sm leading-6 text-fg-muted">{DIFFICULTY_INFO[d].criteria}</p>
                <p className="mt-2 text-xs text-fg-subtle">{DIFFICULTY_INFO[d].minutes}</p>
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="modes-h" className="grid gap-8 lg:grid-cols-[1fr_1.3fr]">
          <div>
            <h2 id="modes-h" className="text-heading font-semibold text-fg">
              Ways to practise
            </h2>
            <dl className="mt-6 space-y-4">
              {MODES.map((m) => (
                <div key={m}>
                  <dt className="font-semibold text-fg">{MODE_INFO[m].label}</dt>
                  <dd className="text-[0.9375rem] leading-7 text-fg-muted">{MODE_INFO[m].description}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div className="rounded-xl border border-line bg-surface p-5 sm:p-6">
            <h3 className="font-semibold text-fg">Start a session</h3>
            <div className="mt-4">
              <StartPracticeForm roles={roles.map((r) => ({ slug: r.slug, name: r.name }))} topics={topics.map((t) => ({ slug: t.slug, name: t.name }))} compact />
            </div>
          </div>
        </section>
      </Container>
    </>
  );
}
