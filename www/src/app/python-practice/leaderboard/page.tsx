import type { Metadata } from "next";
import Link from "next/link";
import { Container } from "@/components/Container";
import { PageHeader } from "@/components/PageHeader";
import { absoluteUrl } from "@/config/site";
import { leaderboard } from "@/lib/practice/profile";

export const metadata: Metadata = { title: "Leaderboard", description: "Opt-in leaderboard of Python practice XP.", alternates: { canonical: absoluteUrl("/python-practice/leaderboard") } };

export default async function LeaderboardPage() {
  const rows = await leaderboard(50);
  return (
    <>
      <PageHeader title="Leaderboard" description="Only people who opted in appear here, under the name they chose. XP comes from independent solves verified by the grader." />
      <Container className="py-8">
        {rows === null ? (
          <p className="text-fg-muted">The leaderboard is turned off.</p>
        ) : rows.length === 0 ? (
          <p className="text-fg-muted">Nobody has joined yet. Opt in from your <Link href="/python-practice/dashboard#privacy" className="underline">dashboard</Link>.</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-line bg-surface">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-line text-fg-subtle">
                <tr>
                  <th className="px-4 py-2 font-medium">#</th>
                  <th className="px-4 py-2 font-medium">Name</th>
                  <th className="px-4 py-2 text-right font-medium">XP</th>
                  <th className="px-4 py-2 text-right font-medium">Solved</th>
                  <th className="px-4 py-2 text-right font-medium">Streak</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {rows.map((r) => (
                  <tr key={r.handle}>
                    <td className="px-4 py-2 tabular-nums text-fg-subtle">{r.rank}</td>
                    <td className="px-4 py-2 font-medium text-fg">{r.name}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{r.xp}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{r.solved}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{r.streak} d</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Container>
    </>
  );
}
