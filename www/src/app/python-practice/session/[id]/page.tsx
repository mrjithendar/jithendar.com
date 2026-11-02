import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Container } from "@/components/Container";
import { SessionBar } from "@/components/practice/SessionBar";
import { Workspace } from "@/components/practice/Workspace";
import { buttonClass } from "@/components/ui/form";
import { renderCommentMarkdown } from "@/lib/comment-markdown";
import { getProblemRecordById, listRoles, listTopics, toPublicProblem } from "@/lib/practice/catalog";
import { PracticeError } from "@/lib/practice/errors";
import { userProblemView } from "@/lib/practice/progress";
import { DIMENSION_LABELS, type Feedback } from "@/lib/practice/review";
import { getSession } from "@/lib/practice/sessions";
import { aiConfigured, executionAvailable, getPracticeSettings } from "@/lib/practice/settings";
import { MODE_INFO } from "@/lib/practice/types";
import { requireUser } from "@/lib/session";
import { getDb, schema } from "@/db";
import { and, eq } from "drizzle-orm";

export const metadata: Metadata = { title: "Session", robots: { index: false, follow: false } };

export default async function SessionPage({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<{ q?: string }> }) {
  const { id } = await params;
  const { q } = await searchParams;
  const user = await requireUser(`/python-practice/session/${id}`);
  let session;
  try {
    session = await getSession(user.id, id, { resumed: true });
  } catch (e) {
    if (e instanceof PracticeError && e.status === 404) notFound();
    throw e;
  }

  if (session.status !== "active") {
    const percent = (session.score?.percent as number | undefined) ?? 0;
    return (
      <Container className="py-section">
        <h1 className="text-title font-bold text-fg">{MODE_INFO[session.mode].label} {session.status === "expired" ? "— time is up" : "complete"}</h1>
        <p className="mt-3 text-lg text-fg-muted">
          Score: <strong className="text-fg">{percent}%</strong> · {String(session.score?.solved ?? 0)} of {session.items.length} solved
          {session.status === "abandoned" ? " · ended early" : ""}
        </p>
        <p className="mt-2 text-sm text-fg-subtle">Each question scores 100 when accepted (minus 10 per hint), up to 60 for partially passing tests, and 0 if the solution was revealed.</p>
        <ol className="mt-8 space-y-4">
          {session.items.map((it) => {
            const fb = it.feedback as Feedback | null;
            return (
              <li key={it.position} className="rounded-xl border border-line bg-surface p-5">
                <div className="flex flex-wrap items-center gap-3">
                  <Link href={`/python-practice/problems/${it.slug}`} className="font-semibold text-fg hover:underline">
                    {it.position + 1}. {it.title}
                  </Link>
                  <span className="text-sm text-fg-muted">
                    {it.status === "skipped" ? "Skipped" : it.status === "pending" ? "Not submitted" : `${it.passed}/${it.total} tests`} · {it.score} points
                    {it.hintsUsed ? ` · ${it.hintsUsed} hint(s)` : ""}
                    {it.solutionRevealed ? " · solution revealed" : ""}
                  </span>
                </div>
                {fb && (
                  <div className="mt-4">
                    <p className="text-sm font-medium text-fg">Interview feedback (automated heuristics; correctness comes from the tests): {fb.overall}/100</p>
                    <dl className="mt-2 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
                      {(Object.keys(DIMENSION_LABELS) as (keyof typeof DIMENSION_LABELS)[]).map((d) => (
                        <div key={d}>
                          <dt className="font-medium text-fg">
                            {DIMENSION_LABELS[d]}: {fb.scores[d]}/5
                          </dt>
                          <dd className="text-fg-muted">{fb.notes[d].join(" ")}</dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                )}
              </li>
            );
          })}
        </ol>
        <div className="mt-8 flex gap-3">
          <Link href="/python-practice/dashboard" className={buttonClass("primary")}>
            Dashboard
          </Link>
          <Link href="/python-practice" className={buttonClass("secondary")}>
            New session
          </Link>
        </div>
      </Container>
    );
  }

  const position = Math.min(Math.max(Number.isFinite(Number(q)) && q !== undefined ? Number(q) : session.currentIndex, 0), session.items.length - 1);
  const db = await getDb();
  const [item] = await db.select().from(schema.practiceSessionItem).where(and(eq(schema.practiceSessionItem.sessionId, id), eq(schema.practiceSessionItem.position, position)));
  const record = await getProblemRecordById(item!.problemId, item!.version);
  const problem = await toPublicProblem(record);
  const [roles, topics, settings, canRun, state] = await Promise.all([listRoles({ includeHidden: true }), listTopics(), getPracticeSettings(), executionAvailable(), userProblemView(user.id, problem.slug).catch(() => null)]);
  // In assessments, a solution revealed earlier in guided practice stays hidden until the session ends.
  const assessment = session.mode === "timed" || session.mode === "mock";
  return (
    <>
      {session.rationale.length > 0 && session.mode === "adaptive" && (
        <details className="border-b border-line bg-surface px-4 py-2 text-sm text-fg-muted">
          <summary className="cursor-pointer">Why these questions?</summary>
          <ul className="mt-2 list-disc pl-5">
            {session.rationale.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </details>
      )}
      <Workspace
        key={`${id}-${position}`}
        problem={problem}
        descriptionHtml={renderCommentMarkdown(problem.description)}
        roleNames={Object.fromEntries(roles.map((r) => [r.slug, r.name]))}
        topicNames={Object.fromEntries(topics.map((t) => [t.slug, t.name]))}
        execution={{ enabled: canRun, runtimes: settings.execution.runtimes.filter((r) => r.enabled).map(({ id: rid, label }) => ({ id: rid, label })), defaultRuntime: settings.execution.defaultRuntime }}
        aiEnabled={aiConfigured(settings) && !assessment}
        initialState={state && assessment ? { ...state, solution: null, hints: session.mode === "mock" ? [] : state.hints } : state}
        session={{ id, mode: session.mode, active: true }}
        header={<SessionBar id={id} mode={session.mode} remainingMs={session.remainingMs} current={position} items={session.items.map((i) => ({ position: i.position, title: i.title, status: i.status }))} />}
      />
    </>
  );
}
