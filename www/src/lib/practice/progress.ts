import "server-only";
import { and, desc, eq, sql } from "drizzle-orm";
import { getDb, schema, type Db } from "@/db";
import type { PracticeSolution } from "@/db/schema";
import { hit } from "../rate-limit";
import { awardBadges } from "./achievements";
import { getProblemRecord } from "./catalog";
import { PracticeError } from "./errors";
import type { Difficulty, Verdict } from "./types";

/** Calendar day in the site's editorial time zone (streaks and the daily challenge use it). */
export function practiceDay(d: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata", year: "numeric", month: "2-digit", day: "2-digit" }).format(d);
}

export function previousDay(day: string): string {
  const d = new Date(`${day}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() - 1);
  return d.toISOString().slice(0, 10);
}

/** XP for a first independent solve: by difficulty, minus 10% per hint level used (at most 30%). Assisted solves earn none. */
export const XP_BY_DIFFICULTY: Record<Difficulty, number> = { beginner: 10, easy: 20, medium: 40, hard: 70, expert: 120 };
export function xpFor(difficulty: Difficulty, hintsUsed: number, dailyBonus: boolean): number {
  const base = XP_BY_DIFFICULTY[difficulty] ?? 10;
  return Math.round(base * (1 - Math.min(hintsUsed, 3) * 0.1)) + (dailyBonus ? 20 : 0);
}

/** Score of one assessment item (0–100): passing earns 100 minus 10 per hint; a revealed solution earns 0; partial credit up to 60. */
export function itemScore(o: { verdict: Verdict; passed: number; total: number; hintsUsed: number; solutionRevealed: boolean }): number {
  if (o.solutionRevealed) return 0;
  if (o.verdict === "accepted") return Math.max(50, 100 - 10 * o.hintsUsed);
  return o.total ? Math.floor((o.passed / o.total) * 60) : 0;
}

export type Tx = Db;

export async function recordEvent(
  tx: Tx,
  e: { userId: string; type: string; problemId?: string | null; sessionId?: string | null; submissionId?: string | null; detail?: Record<string, unknown> },
): Promise<string> {
  const [row] = await tx
    .insert(schema.practiceActivityEvent)
    .values({ userId: e.userId, type: e.type, problemId: e.problemId ?? null, sessionId: e.sessionId ?? null, submissionId: e.submissionId ?? null, detail: e.detail ?? {} })
    .returning({ id: schema.practiceActivityEvent.id });
  return row!.id;
}

async function ensureProfile(tx: Tx, userId: string) {
  await tx.insert(schema.practiceProfile).values({ userId }).onConflictDoNothing();
}

async function touchStreak(tx: Tx, userId: string, now: Date) {
  await ensureProfile(tx, userId);
  const today = practiceDay(now);
  const [p] = await tx.select().from(schema.practiceProfile).where(eq(schema.practiceProfile.userId, userId));
  if (!p || p.lastActiveDay === today) return;
  const current = p.lastActiveDay === previousDay(today) ? p.currentStreak + 1 : 1;
  await tx
    .update(schema.practiceProfile)
    .set({ currentStreak: current, longestStreak: Math.max(current, p.longestStreak), lastActiveDay: today, updatedAt: now })
    .where(eq(schema.practiceProfile.userId, userId));
}

export type Outcome = {
  submission: typeof schema.practiceSubmission.$inferSelect;
  difficulty: Difficulty;
  topics: string[];
  dailyProblemId: string | null;
};

/**
 * Apply a graded submission to progress, skills, XP, streak, session and badges. Called exactly once per
 * submission, inside the transaction that moved it out of queued/running (see submissions.ts finalize).
 */
export async function applyOutcome(tx: Tx, o: Outcome, now = new Date()): Promise<{ badges: string[]; xp: number }> {
  const s = o.submission;
  const graded = s.verdict !== "infrastructure_error" && s.verdict !== "cancelled";
  const accepted = s.verdict === "accepted";
  await tx
    .insert(schema.practiceProgress)
    .values({ userId: s.userId, problemId: s.problemId, firstAttemptAt: s.createdAt })
    .onConflictDoNothing();
  const [progress] = await tx
    .select()
    .from(schema.practiceProgress)
    .where(and(eq(schema.practiceProgress.userId, s.userId), eq(schema.practiceProgress.problemId, s.problemId)));
  const patch: Partial<typeof schema.practiceProgress.$inferInsert> = { updatedAt: now, lastSubmissionId: s.id };
  if (s.kind === "run") patch.runs = progress!.runs + 1;
  let xp = 0;
  if (s.kind === "submit" && graded) {
    patch.submits = progress!.submits + 1;
    if (accepted) {
      if (s.maxMs !== null && (progress!.bestMs === null || s.maxMs < progress!.bestMs)) patch.bestMs = s.maxMs;
      if (!progress!.solvedAt) {
        patch.solvedAt = now;
        patch.solveMs = now.getTime() - progress!.firstAttemptAt.getTime();
      }
      if (s.independent && progress!.status !== "solved") {
        patch.status = "solved";
        patch.independentSolvedAt = now;
        xp = xpFor(o.difficulty, s.hintsUsed, o.dailyProblemId === s.problemId);
      } else if (!s.independent && progress!.status === "attempted") {
        patch.status = "solved_assisted";
      }
    }
  }
  await tx.update(schema.practiceProgress).set(patch).where(and(eq(schema.practiceProgress.userId, s.userId), eq(schema.practiceProgress.problemId, s.problemId)));

  if (s.kind === "submit" && graded) {
    for (const topic of o.topics) {
      await tx
        .insert(schema.practiceSkill)
        .values({ userId: s.userId, topic, attempts: 1, passes: accepted ? 1 : 0, independentPasses: accepted && s.independent ? 1 : 0, failures: accepted ? 0 : 1, lastAt: now })
        .onConflictDoUpdate({
          target: [schema.practiceSkill.userId, schema.practiceSkill.topic],
          set: {
            attempts: sql`${schema.practiceSkill.attempts} + 1`,
            passes: sql`${schema.practiceSkill.passes} + ${accepted ? 1 : 0}`,
            independentPasses: sql`${schema.practiceSkill.independentPasses} + ${accepted && s.independent ? 1 : 0}`,
            failures: sql`${schema.practiceSkill.failures} + ${accepted ? 0 : 1}`,
            lastAt: now,
          },
        });
    }
    await touchStreak(tx, s.userId, now);
    if (xp) await tx.update(schema.practiceProfile).set({ xp: sql`${schema.practiceProfile.xp} + ${xp}`, updatedAt: now }).where(eq(schema.practiceProfile.userId, s.userId));
  }

  if (s.sessionId && s.kind === "submit" && graded) await applyToSessionItem(tx, s);

  const eventId = await recordEvent(tx, {
    userId: s.userId,
    type: s.kind === "submit" ? "submission_graded" : "run_completed",
    problemId: s.problemId,
    sessionId: s.sessionId,
    submissionId: s.id,
    detail: { verdict: s.verdict, passed: s.passed, total: s.total, independent: s.independent, hintsUsed: s.hintsUsed, xp },
  });
  const badges = s.kind === "submit" && graded ? await awardBadges(tx, s.userId, eventId) : [];
  return { badges, xp };
}

async function applyToSessionItem(tx: Tx, s: typeof schema.practiceSubmission.$inferSelect) {
  const [item] = await tx
    .select()
    .from(schema.practiceSessionItem)
    .where(and(eq(schema.practiceSessionItem.sessionId, s.sessionId!), eq(schema.practiceSessionItem.problemId, s.problemId)));
  if (!item) return;
  const score = itemScore({ verdict: s.verdict as Verdict, passed: s.passed, total: s.total, hintsUsed: item.hintsUsed, solutionRevealed: item.solutionRevealed });
  if (score >= item.score || item.status !== "submitted") {
    await tx
      .update(schema.practiceSessionItem)
      .set({ status: "submitted", passed: s.passed, total: s.total, score: Math.max(score, item.score), bestSubmissionId: score >= item.score ? s.id : item.bestSubmissionId })
      .where(and(eq(schema.practiceSessionItem.sessionId, item.sessionId), eq(schema.practiceSessionItem.position, item.position)));
  }
  // A submission made before the deadline may finish grading after the session ended: refresh the total.
  const [session] = await tx.select().from(schema.practiceSession).where(eq(schema.practiceSession.id, s.sessionId!));
  if (session && session.status !== "active") {
    const { scoreSession } = await import("./sessions");
    await tx.update(schema.practiceSession).set({ score: await scoreSession(tx, session) }).where(eq(schema.practiceSession.id, session.id));
  }
}

// --- Per-user state on a problem page ----------------------------------------------------------------

export type UserProblemView = {
  status: "attempted" | "solved" | "solved_assisted" | null;
  hints: string[];
  hintCount: number;
  solution: PracticeSolution | null;
  draft: string | null;
  note: string;
  bookmarked: boolean;
  recent: { id: string; kind: string; verdict: string | null; passed: number; total: number; createdAt: string }[];
};

export async function userProblemView(userId: string, slug: string): Promise<UserProblemView> {
  const { problem, version } = await getProblemRecord(slug);
  const db = await getDb();
  const [progress] = await db
    .select()
    .from(schema.practiceProgress)
    .where(and(eq(schema.practiceProgress.userId, userId), eq(schema.practiceProgress.problemId, problem.id)));
  const [note] = await db.select().from(schema.practiceNote).where(and(eq(schema.practiceNote.userId, userId), eq(schema.practiceNote.problemId, problem.id)));
  const [bookmark] = await db
    .select()
    .from(schema.practiceBookmark)
    .where(and(eq(schema.practiceBookmark.userId, userId), eq(schema.practiceBookmark.problemId, problem.id)));
  const recent = await db
    .select({
      id: schema.practiceSubmission.id,
      kind: schema.practiceSubmission.kind,
      verdict: schema.practiceSubmission.verdict,
      passed: schema.practiceSubmission.passed,
      total: schema.practiceSubmission.total,
      createdAt: schema.practiceSubmission.createdAt,
    })
    .from(schema.practiceSubmission)
    .where(and(eq(schema.practiceSubmission.userId, userId), eq(schema.practiceSubmission.problemId, problem.id), eq(schema.practiceSubmission.kind, "submit")))
    .orderBy(desc(schema.practiceSubmission.createdAt))
    .limit(5);
  const hintsUsed = progress?.hintsUsed ?? 0;
  return {
    status: (progress?.status as UserProblemView["status"]) ?? null,
    hints: version.hints.slice(0, hintsUsed),
    hintCount: version.hints.length,
    solution: progress?.solutionRevealedAt ? version.solution : null,
    draft: progress?.draftCode ?? null,
    note: note?.body ?? "",
    bookmarked: Boolean(bookmark),
    recent: recent.map((r) => ({ ...r, createdAt: r.createdAt.toISOString() })),
  };
}

async function activeSessionItem(db: Db, userId: string, sessionId: string | null | undefined, problemId: string) {
  if (!sessionId) return null;
  const [session] = await db.select().from(schema.practiceSession).where(eq(schema.practiceSession.id, sessionId));
  if (!session || session.userId !== userId) throw new PracticeError("Session not found.", 404, "not_found");
  const [item] = await db
    .select()
    .from(schema.practiceSessionItem)
    .where(and(eq(schema.practiceSessionItem.sessionId, sessionId), eq(schema.practiceSessionItem.problemId, problemId)));
  if (!item) throw new PracticeError("That problem is not part of this session.", 400, "not_in_session");
  return { session, item };
}

/** Reveal hints progressively: level n requires hints 1..n-1 first. Returns every hint revealed so far. */
export async function revealHint(userId: string, slug: string, level: number, sessionId?: string | null): Promise<string[]> {
  if (!(await hit(`practice:hint:${userId}`, 60, 3600))) throw new PracticeError("Too many hint requests. Try again later.", 429, "rate_limited", 60);
  const { problem, version } = await getProblemRecord(slug);
  if (!Number.isInteger(level) || level < 1 || level > version.hints.length) throw new PracticeError("No such hint.", 400, "bad_hint");
  const db = await getDb();
  return db.transaction(async (tx) => {
    const inSession = await activeSessionItem(tx, userId, sessionId, problem.id);
    if (inSession && inSession.session.mode === "mock") throw new PracticeError("Hints are not available in a mock interview.", 403, "hints_disabled");
    await tx.insert(schema.practiceProgress).values({ userId, problemId: problem.id }).onConflictDoNothing();
    const [progress] = await tx
      .select()
      .from(schema.practiceProgress)
      .where(and(eq(schema.practiceProgress.userId, userId), eq(schema.practiceProgress.problemId, problem.id)));
    const used = progress!.hintsUsed;
    if (level > used + 1) throw new PracticeError(`Open hint ${used + 1} first.`, 400, "hint_order");
    if (level > used) {
      await tx
        .update(schema.practiceProgress)
        .set({ hintsUsed: level, updatedAt: new Date() })
        .where(and(eq(schema.practiceProgress.userId, userId), eq(schema.practiceProgress.problemId, problem.id)));
      if (inSession && inSession.item.hintsUsed < level) {
        await tx
          .update(schema.practiceSessionItem)
          .set({ hintsUsed: level })
          .where(and(eq(schema.practiceSessionItem.sessionId, inSession.item.sessionId), eq(schema.practiceSessionItem.position, inSession.item.position)));
      }
      await recordEvent(tx, { userId, type: "hint_requested", problemId: problem.id, sessionId: sessionId ?? null, detail: { level } });
    }
    return version.hints.slice(0, Math.max(level, used));
  });
}

/** Reveal the reference solution (after explicit confirmation). Not available during assessments. */
export async function revealSolution(userId: string, slug: string, sessionId?: string | null): Promise<PracticeSolution> {
  const { problem, version } = await getProblemRecord(slug);
  const db = await getDb();
  return db.transaction(async (tx) => {
    const inSession = await activeSessionItem(tx, userId, sessionId, problem.id);
    if (inSession && (inSession.session.mode === "timed" || inSession.session.mode === "mock") && inSession.session.status === "active") {
      throw new PracticeError("Solutions are hidden until the assessment ends.", 403, "solution_locked");
    }
    await tx.insert(schema.practiceProgress).values({ userId, problemId: problem.id }).onConflictDoNothing();
    const [progress] = await tx
      .select()
      .from(schema.practiceProgress)
      .where(and(eq(schema.practiceProgress.userId, userId), eq(schema.practiceProgress.problemId, problem.id)));
    if (!progress!.solutionRevealedAt) {
      const now = new Date();
      await tx
        .update(schema.practiceProgress)
        .set({ solutionRevealedAt: now, updatedAt: now })
        .where(and(eq(schema.practiceProgress.userId, userId), eq(schema.practiceProgress.problemId, problem.id)));
      if (inSession) {
        await tx
          .update(schema.practiceSessionItem)
          .set({ solutionRevealed: true })
          .where(and(eq(schema.practiceSessionItem.sessionId, inSession.item.sessionId), eq(schema.practiceSessionItem.position, inSession.item.position)));
      }
      await recordEvent(tx, {
        userId,
        type: "solution_revealed",
        problemId: problem.id,
        sessionId: sessionId ?? null,
        detail: { msSinceFirstAttempt: now.getTime() - progress!.firstAttemptAt.getTime(), submitsBefore: progress!.submits, alreadySolved: progress!.status === "solved" },
      });
    }
    return version.solution;
  });
}

const MAX_CODE = 64_000;

export async function saveDraft(userId: string, slug: string, code: string): Promise<void> {
  if (typeof code !== "string" || code.length > MAX_CODE) throw new PracticeError("The draft is too large.", 413, "too_large");
  if (!(await hit(`practice:draft:${userId}`, 240, 3600))) throw new PracticeError("Drafts are being saved too often.", 429, "rate_limited", 30);
  const { problem } = await getProblemRecord(slug);
  const db = await getDb();
  const now = new Date();
  await db
    .insert(schema.practiceProgress)
    .values({ userId, problemId: problem.id, draftCode: code, draftSavedAt: now })
    .onConflictDoUpdate({ target: [schema.practiceProgress.userId, schema.practiceProgress.problemId], set: { draftCode: code, draftSavedAt: now } });
}

export async function setBookmark(userId: string, slug: string, on: boolean): Promise<void> {
  const { problem } = await getProblemRecord(slug);
  const db = await getDb();
  if (on) {
    const added = await db.insert(schema.practiceBookmark).values({ userId, problemId: problem.id }).onConflictDoNothing().returning();
    if (added.length) await recordEvent(db, { userId, type: "question_bookmarked", problemId: problem.id });
  } else {
    await db.delete(schema.practiceBookmark).where(and(eq(schema.practiceBookmark.userId, userId), eq(schema.practiceBookmark.problemId, problem.id)));
  }
}

export async function saveNote(userId: string, slug: string, body: string): Promise<void> {
  if (typeof body !== "string" || body.length > 10_000) throw new PracticeError("Notes are limited to 10,000 characters.", 413, "too_large");
  const { problem } = await getProblemRecord(slug);
  const db = await getDb();
  if (!body.trim()) {
    await db.delete(schema.practiceNote).where(and(eq(schema.practiceNote.userId, userId), eq(schema.practiceNote.problemId, problem.id)));
    return;
  }
  await db
    .insert(schema.practiceNote)
    .values({ userId, problemId: problem.id, body })
    .onConflictDoUpdate({ target: [schema.practiceNote.userId, schema.practiceNote.problemId], set: { body, updatedAt: new Date() } });
}
