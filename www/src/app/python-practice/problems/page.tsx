import { and, eq, inArray } from "drizzle-orm";
import type { Metadata } from "next";
import Link from "next/link";
import { Container } from "@/components/Container";
import { PageHeader } from "@/components/PageHeader";
import { DifficultyBadge, StatusMark } from "@/components/practice/Badges";
import { Button, Input, Select } from "@/components/ui/form";
import { absoluteUrl } from "@/config/site";
import { getDb, schema } from "@/db";
import { listProblems, listRoles, listTopics } from "@/lib/practice/catalog";
import { DIFFICULTIES, DIFFICULTY_INFO } from "@/lib/practice/types";
import { getSessionUser } from "@/lib/session";

export const metadata: Metadata = {
  title: "Problems",
  description: "Original Python problems by role, topic and difficulty, from beginner scripting to expert distributed systems.",
  alternates: { canonical: absoluteUrl("/python-practice/problems") },
};

type Params = { role?: string; difficulty?: string; topic?: string; q?: string; bookmarked?: string };

export default async function ProblemsPage({ searchParams }: { searchParams: Promise<Params> }) {
  const sp = await searchParams;
  const user = await getSessionUser();
  const [roles, topics] = await Promise.all([listRoles(), listTopics()]);
  let problems = await listProblems({ role: sp.role, difficulty: sp.difficulty, topic: sp.topic, q: sp.q });
  const status = new Map<string, string>();
  if (user && problems.length) {
    const db = await getDb();
    const ids = problems.map((p) => p.id);
    for (const p of await db.select({ id: schema.practiceProgress.problemId, s: schema.practiceProgress.status }).from(schema.practiceProgress).where(and(eq(schema.practiceProgress.userId, user.id), inArray(schema.practiceProgress.problemId, ids)))) status.set(p.id, p.s);
    if (sp.bookmarked) {
      const marks = new Set((await db.select({ id: schema.practiceBookmark.problemId }).from(schema.practiceBookmark).where(eq(schema.practiceBookmark.userId, user.id))).map((b) => b.id));
      problems = problems.filter((p) => marks.has(p.id));
    }
  }
  const roleName = new Map(roles.map((r) => [r.slug, r.name]));
  const topicName = new Map(topics.map((t) => [t.slug, t.name]));
  return (
    <>
      <PageHeader title="Problems" description={`${problems.length} problem${problems.length === 1 ? "" : "s"}${sp.role ? ` for ${roleName.get(sp.role) ?? sp.role}` : ""}. Read any of them; sign in to code, run and submit.`} crumbs={[{ name: "Python practice", path: "/python-practice" }, { name: "Problems", path: "/python-practice/problems" }]} />
      <Container className="py-8">
        <form className="grid gap-3 rounded-xl border border-line bg-surface p-4 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1fr_1.4fr_auto]" role="search">
          <Select name="role" defaultValue={sp.role ?? ""} aria-label="Role">
            <option value="">All roles</option>
            {roles.map((r) => (
              <option key={r.slug} value={r.slug}>
                {r.name}
              </option>
            ))}
          </Select>
          <Select name="difficulty" defaultValue={sp.difficulty ?? ""} aria-label="Difficulty">
            <option value="">All levels</option>
            {DIFFICULTIES.map((d) => (
              <option key={d} value={d}>
                {DIFFICULTY_INFO[d].label}
              </option>
            ))}
          </Select>
          <Select name="topic" defaultValue={sp.topic ?? ""} aria-label="Topic">
            <option value="">All topics</option>
            {topics.map((t) => (
              <option key={t.slug} value={t.slug}>
                {t.name}
              </option>
            ))}
          </Select>
          <Input name="q" defaultValue={sp.q ?? ""} placeholder="Search titles" aria-label="Search" />
          <div className="flex items-center gap-3">
            {user && (
              <label className="flex items-center gap-1.5 text-sm text-fg-muted">
                <input type="checkbox" name="bookmarked" value="1" defaultChecked={Boolean(sp.bookmarked)} /> Bookmarked
              </label>
            )}
            <Button type="submit">Filter</Button>
          </div>
        </form>
        {problems.length === 0 ? (
          <p className="mt-8 text-fg-muted">No problems match these filters.</p>
        ) : (
          <ul className="mt-6 divide-y divide-line rounded-xl border border-line bg-surface">
            {problems.map((p) => (
              <li key={p.slug} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3">
                {user && <StatusMark status={status.get(p.id)} />}
                <Link href={`/python-practice/problems/${p.slug}`} className="min-w-0 flex-1 font-medium text-fg hover:underline">
                  {p.title}
                </Link>
                <span className="hidden text-sm text-fg-subtle md:inline">{p.topics.slice(0, 3).map((t) => topicName.get(t) ?? t).join(" · ")}</span>
                <span className="text-sm text-fg-subtle">~{p.minutes} min</span>
                <DifficultyBadge difficulty={p.difficulty} />
              </li>
            ))}
          </ul>
        )}
      </Container>
    </>
  );
}
