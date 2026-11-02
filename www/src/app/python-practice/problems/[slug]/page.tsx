import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { JsonLd } from "@/components/JsonLd";
import { Workspace } from "@/components/practice/Workspace";
import { absoluteUrl } from "@/config/site";
import { renderCommentMarkdown } from "@/lib/comment-markdown";
import { getPublicProblem, listRoles, listTopics } from "@/lib/practice/catalog";
import { PracticeError } from "@/lib/practice/errors";
import { userProblemView } from "@/lib/practice/progress";
import { aiConfigured, executionAvailable, getPracticeSettings } from "@/lib/practice/settings";
import { getSessionUser } from "@/lib/session";

type Props = { params: Promise<{ slug: string }> };

async function load(slug: string) {
  try {
    return await getPublicProblem(slug);
  } catch (e) {
    if (e instanceof PracticeError && e.status === 404) notFound();
    throw e;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const p = await load((await params).slug);
  const plain = p.description.replace(/[`*_#>\[\]]/g, "").replace(/\s+/g, " ").trim();
  return { title: p.title, description: plain.slice(0, 155), alternates: { canonical: absoluteUrl(`/python-practice/problems/${p.slug}`) } };
}

export default async function ProblemPage({ params }: Props) {
  const { slug } = await params;
  const problem = await load(slug);
  const user = await getSessionUser();
  const [roles, topics, settings, canRun, state] = await Promise.all([listRoles({ includeHidden: true }), listTopics(), getPracticeSettings(), executionAvailable(), user ? userProblemView(user.id, slug) : null]);
  return (
    <>
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "LearningResource",
          name: problem.title,
          learningResourceType: "Coding exercise",
          educationalLevel: problem.difficulty,
          programmingLanguage: "Python",
          url: absoluteUrl(`/python-practice/problems/${problem.slug}`),
          timeRequired: `PT${problem.minutes}M`,
          isAccessibleForFree: true,
        }}
      />
      <Workspace
        problem={problem}
        descriptionHtml={renderCommentMarkdown(problem.description)}
        roleNames={Object.fromEntries(roles.map((r) => [r.slug, r.name]))}
        topicNames={Object.fromEntries(topics.map((t) => [t.slug, t.name]))}
        execution={{ enabled: canRun, runtimes: settings.execution.runtimes.filter((r) => r.enabled).map(({ id, label }) => ({ id, label })), defaultRuntime: settings.execution.defaultRuntime }}
        aiEnabled={aiConfigured(settings)}
        initialState={state}
      />
    </>
  );
}
