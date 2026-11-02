import type { Metadata } from "next";
import Link from "next/link";
import { Container } from "@/components/Container";
import { CategoryIcon } from "@/components/icons";
import { PageHeader } from "@/components/PageHeader";
import { StartPracticeForm } from "@/components/practice/StartPracticeForm";
import { absoluteUrl } from "@/config/site";
import { catalogStats, listRoles, listTopics } from "@/lib/practice/catalog";
import { DIFFICULTIES, DIFFICULTY_INFO } from "@/lib/practice/types";

export const metadata: Metadata = {
  title: "Engineering roles",
  description: "Python competencies, learning paths, interview scenarios and practice problems for 20 engineering roles.",
  alternates: { canonical: absoluteUrl("/python-practice/roles") },
};

export default async function RolesPage() {
  const [roles, topics, stats] = await Promise.all([listRoles(), listTopics(), catalogStats()]);
  const topicName = new Map(topics.map((t) => [t.slug, t.name]));
  return (
    <>
      <PageHeader
        title="Choose your engineering focus"
        description="Each role lists the Python it needs, a learning path, typical interview scenarios and its problems. Practise one role or mix several."
        crumbs={[
          { name: "Python practice", path: "/python-practice" },
          { name: "Roles", path: "/python-practice/roles" },
        ]}
      />
      <Container className="py-section">
        <div className="space-y-8">
          {roles.map((r) => (
            <section key={r.slug} id={r.slug} aria-labelledby={`${r.slug}-h`} className="scroll-mt-24 rounded-xl border border-line bg-surface p-5 sm:p-6">
              <div className="flex flex-wrap items-start gap-3">
                <CategoryIcon name={r.icon} className="mt-1 h-6 w-6 text-accent-text" />
                <div className="min-w-0 flex-1">
                  <h2 id={`${r.slug}-h`} className="text-xl font-semibold text-fg">
                    {r.name}
                  </h2>
                  <p className="mt-1 text-[0.9375rem] text-fg-muted">{r.description}</p>
                </div>
                <Link href={`/python-practice/problems?role=${r.slug}`} className="text-sm font-medium text-accent-text underline">
                  {stats.byRole[r.slug] ?? 0} problems
                </Link>
              </div>
              <div className="mt-5 grid gap-6 text-sm md:grid-cols-3">
                <div>
                  <h3 className="font-semibold text-fg">Python competencies</h3>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-fg-muted">
                    {r.competencies.map((c) => (
                      <li key={c}>{c}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="font-semibold text-fg">Learning path</h3>
                  <ol className="mt-2 list-decimal space-y-1 pl-5 text-fg-muted">
                    {r.learningPath.map((c) => (
                      <li key={c}>{c}</li>
                    ))}
                  </ol>
                </div>
                <div>
                  <h3 className="font-semibold text-fg">Interview scenarios</h3>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-fg-muted">
                    {r.scenarios.map((c) => (
                      <li key={c}>{c}</li>
                    ))}
                  </ul>
                </div>
              </div>
              <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2 text-sm text-fg-muted">
                <p>
                  <span className="font-medium text-fg">Topics:</span> {r.topics.map((t) => topicName.get(t) ?? t).join(", ")}
                </p>
                <p>
                  <span className="font-medium text-fg">Libraries:</span> {r.libraries.join(", ")}
                </p>
                <p>
                  <span className="font-medium text-fg">Recommended mix:</span>{" "}
                  {DIFFICULTIES.filter((d) => r.difficultyMix[d])
                    .map((d) => `${DIFFICULTY_INFO[d].label} ${r.difficultyMix[d]}%`)
                    .join(" · ")}
                </p>
              </div>
              <details className="mt-5">
                <summary className="cursor-pointer text-sm font-semibold text-accent-text">Start a {r.name} session</summary>
                <div className="mt-4">
                  <StartPracticeForm roles={roles.map((x) => ({ slug: x.slug, name: x.name }))} topics={topics.map((t) => ({ slug: t.slug, name: t.name }))} initialRoles={[r.slug]} />
                </div>
              </details>
            </section>
          ))}
        </div>
      </Container>
    </>
  );
}
