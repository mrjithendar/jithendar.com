import type { Metadata } from "next";
import Link from "next/link";
import { Container } from "@/components/Container";
import { PageHeader } from "@/components/PageHeader";
import { listSessions } from "@/lib/practice/sessions";
import { listSubmissions } from "@/lib/practice/submissions";
import { MODE_INFO, VERDICTS, type Mode, type Verdict } from "@/lib/practice/types";
import { requireUser } from "@/lib/session";

export const metadata: Metadata = { title: "History", robots: { index: false, follow: false } };

export default async function HistoryPage({ searchParams }: { searchParams: Promise<{ page?: string }> }) {
  const user = await requireUser("/python-practice/history");
  const page = Math.max(1, Number((await searchParams).page) || 1);
  const [subs, sessions] = await Promise.all([listSubmissions(user.id, { page }), page === 1 ? listSessions(user.id) : Promise.resolve([])]);
  return (
    <>
      <PageHeader title="History" description="Your sessions and every run and submission. Private to you." />
      <Container className="space-y-10 py-8">
        {sessions.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold text-fg">Sessions</h2>
            <ul className="mt-3 divide-y divide-line rounded-xl border border-line bg-surface text-sm">
              {sessions.map((s) => (
                <li key={s.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                  <Link href={`/python-practice/session/${s.id}`} className="font-medium text-fg hover:underline">
                    {MODE_INFO[s.mode as Mode]?.label ?? s.mode}
                  </Link>
                  <span className="text-fg-muted">{s.items} question(s)</span>
                  <span className="text-fg-muted">{s.status === "active" ? "In progress — resume" : s.score ? `${String(s.score.percent ?? 0)}%` : s.status}</span>
                  <span className="ml-auto text-fg-subtle">{new Date(s.started_at).toLocaleString("en-GB", { timeZone: "Asia/Kolkata" })}</span>
                </li>
              ))}
            </ul>
          </section>
        )}
        <section>
          <h2 className="text-lg font-semibold text-fg">Runs and submissions</h2>
          {subs.items.length === 0 ? (
            <p className="mt-3 text-fg-muted">Nothing yet. <Link href="/python-practice/problems" className="underline">Pick a problem</Link>.</p>
          ) : (
            <div className="mt-3 overflow-x-auto rounded-xl border border-line bg-surface">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-line text-fg-subtle">
                  <tr>
                    <th className="px-4 py-2 font-medium">Problem</th>
                    <th className="px-4 py-2 font-medium">Type</th>
                    <th className="px-4 py-2 font-medium">Result</th>
                    <th className="px-4 py-2 font-medium">Tests</th>
                    <th className="px-4 py-2 font-medium">When (IST)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {subs.items.map((s) => (
                    <tr key={s.id}>
                      <td className="px-4 py-2">
                        <Link href={`/python-practice/problems/${s.slug}`} className="text-fg hover:underline">
                          {s.title}
                        </Link>
                      </td>
                      <td className="px-4 py-2 text-fg-muted">{s.kind === "submit" ? "Submit" : "Run"}</td>
                      <td className={`px-4 py-2 ${s.verdict === "accepted" ? "text-emerald-700 dark:text-emerald-300" : "text-fg"}`}>
                        {s.verdict ? VERDICTS[s.verdict as Verdict] : s.status}
                        {s.kind === "submit" && s.verdict === "accepted" && !s.independent ? " (with solution)" : ""}
                        {s.hints_used ? ` · ${s.hints_used} hint(s)` : ""}
                      </td>
                      <td className="px-4 py-2 tabular-nums text-fg-muted">
                        {s.passed}/{s.total}
                      </td>
                      <td className="px-4 py-2 text-fg-subtle">{new Date(s.created_at).toLocaleString("en-GB", { timeZone: "Asia/Kolkata" })}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="mt-4 flex gap-3 text-sm">
            {page > 1 && <Link href={`/python-practice/history?page=${page - 1}`} className="underline">Newer</Link>}
            {subs.hasMore && <Link href={`/python-practice/history?page=${page + 1}`} className="underline">Older</Link>}
          </div>
        </section>
      </Container>
    </>
  );
}
