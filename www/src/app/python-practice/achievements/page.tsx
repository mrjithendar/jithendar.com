import { eq } from "drizzle-orm";
import type { Metadata } from "next";
import { Container } from "@/components/Container";
import { PageHeader } from "@/components/PageHeader";
import { absoluteUrl } from "@/config/site";
import { getDb, schema } from "@/db";
import { BADGES } from "@/lib/practice/achievements";
import { getSessionUser } from "@/lib/session";

export const metadata: Metadata = { title: "Achievements", description: "Badges for Python practice milestones.", alternates: { canonical: absoluteUrl("/python-practice/achievements") } };

const TIER = { bronze: "Bronze", silver: "Silver", gold: "Gold" } as const;

export default async function AchievementsPage() {
  const user = await getSessionUser();
  const earned = new Map<string, Date>();
  if (user) {
    const db = await getDb();
    for (const a of await db.select().from(schema.practiceAchievement).where(eq(schema.practiceAchievement.userId, user.id))) earned.set(a.badge, a.earnedAt);
  }
  return (
    <>
      <PageHeader title="Achievements" description={user ? `${earned.size} of ${BADGES.length} earned. Badges are awarded from graded results, never from anything your browser reports.` : "Badges are awarded from graded results. Sign in to start earning them."} />
      <Container className="py-8">
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {BADGES.map((b) => {
            const at = earned.get(b.id);
            return (
              <li key={b.id} className={`rounded-xl border p-5 ${at ? "border-accent bg-accent-soft" : "border-line bg-surface"}`}>
                <p className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">{TIER[b.tier]}</p>
                <p className="mt-1 font-semibold text-fg">{b.name}</p>
                <p className="mt-1 text-sm text-fg-muted">{b.description}</p>
                <p className="mt-3 text-sm text-fg">{at ? `Earned ${at.toLocaleDateString("en-GB", { timeZone: "Asia/Kolkata" })}` : user ? "Not yet" : ""}</p>
              </li>
            );
          })}
        </ul>
      </Container>
    </>
  );
}
