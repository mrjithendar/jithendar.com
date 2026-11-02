import "server-only";
import { randomUUID } from "node:crypto";
import { and, eq, gte, sql } from "drizzle-orm";
import { z } from "zod";
import { getDb, schema } from "@/db";
import { rowsOf } from "@/db/rows";
import { log } from "../../log";
import { hit } from "../../rate-limit";
import { getProblemRecord } from "../catalog";
import { PracticeError } from "../errors";
import { recordEvent } from "../progress";
import { aiConfigured, aiKey, getPracticeSettings, type PracticeSettings } from "../settings";
import { callModel, ProviderError } from "./providers";

/**
 * Optional AI tutor. Rules:
 * - Progressive help: explanations and nudges, never a full solution unless the user already revealed it.
 * - Only public information goes to the provider: the statement, the user's own code, public test results.
 *   Never hidden tests, expected outputs of hidden tests, stdout of hidden tests, names, emails or user ids.
 * - The deterministic grader is the source of truth. Claims of correctness that contradict it are flagged.
 * - Failures (timeouts, quotas, provider outages) return a clear error; practice itself is unaffected.
 */
export const PROMPT_VERSION = "practice-tutor-v1-2026-11-02";

export const FEATURES = {
  explain_error: "Explain this error",
  explain_failure: "Why did this test fail?",
  review: "Review my code",
  complexity: "Time and space complexity",
  suggest_tests: "Suggest test cases",
  concept: "Ask about a concept",
  recommend: "What should I learn next?",
} as const;
export type Feature = keyof typeof FEATURES;

export const tutorInput = z.object({
  feature: z.enum(Object.keys(FEATURES) as [Feature, ...Feature[]]),
  slug: z.string().max(120).optional(),
  code: z.string().max(20_000).optional(),
  submissionId: z.uuid().optional(),
  question: z.string().max(500).optional(),
});

const ANSWER_SCHEMA = {
  type: "object",
  additionalProperties: false,
  required: ["summary", "points", "next_step", "code"],
  properties: {
    summary: { type: "string", description: "One or two sentences." },
    points: { type: "array", items: { type: "string" }, description: "At most five short explanations or suggestions." },
    next_step: { type: "string", description: "One concrete thing the learner should try next." },
    code: { type: "string", description: "Optional tiny illustration (at most 12 lines), or an empty string. Never a complete solution." },
  },
};
const answerShape = z.object({ summary: z.string(), points: z.array(z.string()).max(8), next_step: z.string(), code: z.string() });
export type TutorAnswer = z.infer<typeof answerShape> & { grounding: string | null; facts: { verdict: string | null; passed: number; total: number } | null; requestId: string };

const SYSTEM = `You are a patient Python tutor on a coding-practice site for engineers.
Help the learner understand and improve their own code. Be specific and concise.
Rules:
- Teach progressively: explain the concept or the bug, then suggest the next step. Do not write the complete solution to the problem, even if asked.
- Base statements about correctness only on the grader results provided. Never claim code passes tests the results say it fails.
- You cannot see hidden tests. Do not guess their contents.
- Use plain language. Code examples, if any, must be tiny and illustrate a concept, not solve the problem.`;

type Context = { user: string; facts: TutorAnswer["facts"]; problemId: string | null; entrypoint: string | null; solutionRevealed: boolean };

async function buildContext(userId: string, input: z.infer<typeof tutorInput>): Promise<Context> {
  const db = await getDb();
  const lines: string[] = [];
  let facts: Context["facts"] = null;
  let problemId: string | null = null;
  let entrypoint: string | null = null;
  let solutionRevealed = false;
  if (input.slug) {
    const { problem, version } = await getProblemRecord(input.slug);
    problemId = problem.id;
    entrypoint = version.entrypoint;
    const [progress] = await db
      .select()
      .from(schema.practiceProgress)
      .where(and(eq(schema.practiceProgress.userId, userId), eq(schema.practiceProgress.problemId, problem.id)));
    solutionRevealed = Boolean(progress?.solutionRevealedAt);
    lines.push(`Problem: ${version.title} (${problem.difficulty})`, version.description.slice(0, 4000));
    if (version.constraints.length) lines.push(`Constraints: ${version.constraints.join("; ")}`);
    if (version.prelude) lines.push("Provided helper code (read-only):", version.prelude.slice(0, 3000));
  }
  if (input.submissionId) {
    const [sub] = await db.select().from(schema.practiceSubmission).where(eq(schema.practiceSubmission.id, input.submissionId));
    if (!sub || sub.userId !== userId) throw new PracticeError("Submission not found.", 404, "not_found");
    facts = { verdict: sub.verdict, passed: sub.passed, total: sub.total };
    lines.push(`Grader verdict: ${sub.verdict ?? "pending"} — ${sub.passed} of ${sub.total} tests passed (hidden tests are counted but not shown).`);
    if (sub.loadError) lines.push(`Error while loading the code: ${sub.loadError.type}: ${sub.loadError.message}${sub.loadError.line ? ` (line ${sub.loadError.line})` : ""}`);
    const publicFailures = sub.results.filter((r) => r.visibility === "public" && r.status !== "passed" && !r.custom).slice(0, 3);
    for (const r of publicFailures) {
      lines.push(
        `Failed public test: args=${JSON.stringify(r.args).slice(0, 500)} kwargs=${JSON.stringify(r.kwargs ?? {}).slice(0, 200)} expected=${JSON.stringify(r.expected).slice(0, 500)} got=${(r.actualRepr ?? JSON.stringify(r.actual ?? null)).slice(0, 500)}${r.error ? ` error=${r.error.type}: ${r.error.message.slice(0, 300)}` : ""}`,
      );
    }
    if (!input.code) lines.push("Submitted code:", sub.code.slice(0, 12_000));
  }
  if (input.code) lines.push("Learner's code:", input.code.slice(0, 12_000));
  if (input.feature === "recommend") {
    const skills = await db.select().from(schema.practiceSkill).where(eq(schema.practiceSkill.userId, userId));
    lines.push("Graded submissions per topic (topic: passed/attempts):", skills.map((s) => `${s.topic}: ${s.passes}/${s.attempts}`).join(", ") || "none yet");
  }
  const task: Record<Feature, string> = {
    explain_error: "Explain the error in plain language, point to the line or construct that causes it, and suggest how to investigate.",
    explain_failure: "Explain why the failing public test produces a different result than expected. Point at the logic, not a full rewrite.",
    review: "Review the code: correctness risks, edge cases, readability, Pythonic style and error handling. Prioritise the most important issues.",
    complexity: "State the time and space complexity of the learner's code with a short justification, and whether a better complexity is possible (describe, don't implement).",
    suggest_tests: "Suggest edge-case inputs worth testing for this problem and what each checks. Do not provide expected outputs for them.",
    concept: `Answer the learner's question about Python or the concept involved: ${input.question ?? ""}`,
    recommend: "Recommend what to practise next and why, based on the per-topic results.",
  };
  lines.push(`Task: ${task[input.feature]}`);
  return { user: lines.join("\n\n"), facts, problemId, entrypoint, solutionRevealed };
}

/** Flag answers that contradict the grader, and withhold full solutions the learner hasn't unlocked. */
export function ground(answer: z.infer<typeof answerShape>, ctx: Pick<Context, "facts" | "entrypoint" | "solutionRevealed">): { answer: z.infer<typeof answerShape>; grounding: string | null } {
  let grounding: string | null = null;
  const text = `${answer.summary} ${answer.points.join(" ")} ${answer.next_step}`;
  if (ctx.facts && ctx.facts.verdict !== "accepted" && /\b(all (?:the )?tests (?:pass|passed|will pass)|(?:code|solution) is (?:correct|right)|works correctly|no bugs)\b/i.test(text)) {
    grounding = `The grader reports ${ctx.facts.passed} of ${ctx.facts.total} tests passing (${ctx.facts.verdict}). The assistant's claim that the code is correct was flagged — trust the test results.`;
  }
  let code = answer.code;
  const lines = code.split("\n");
  if (lines.length > 12) code = `${lines.slice(0, 12).join("\n")}\n# … (shortened)`;
  if (ctx.entrypoint && !ctx.solutionRevealed && new RegExp(`\\b(?:def|class)\\s+${ctx.entrypoint}\\b`).test(code)) {
    code = "";
    grounding = [grounding, "Example code that implemented the whole solution was withheld. Reveal the solution if you want to see a full implementation."].filter(Boolean).join(" ");
  }
  return { answer: { ...answer, code, points: answer.points.slice(0, 5) }, grounding };
}

async function record(row: Omit<typeof schema.practiceAiUsage.$inferInsert, "id" | "createdAt">) {
  const db = await getDb();
  await db.insert(schema.practiceAiUsage).values(row);
}

export function costMicroUsd(ai: PracticeSettings["ai"], input: number, output: number): number {
  return Math.round(input * ai.inputUsdPerMTok + output * ai.outputUsdPerMTok);
}

export async function askTutor(userId: string, raw: unknown, fetchImpl: typeof fetch = fetch): Promise<TutorAnswer> {
  const parsed = tutorInput.safeParse(raw);
  if (!parsed.success) throw new PracticeError(parsed.error.issues[0]?.message ?? "Invalid request.", 400, "invalid");
  const input = parsed.data;
  const settings = await getPracticeSettings();
  const ai = settings.ai;
  if (!aiConfigured(settings)) throw new PracticeError("The AI tutor is not enabled.", 503, "ai_disabled");
  const requestId = randomUUID();
  const base = { userId, feature: input.feature, provider: ai.provider, model: ai.model, promptVersion: PROMPT_VERSION, requestId };

  const db = await getDb();
  const dayStart = new Date(Date.now() - 86_400_000);
  const [usage] = rowsOf<{ mine: number; spend: number }>(
    await db.execute(sql`select count(*) filter (where user_id = ${userId} and status in ('ok', 'error'))::int as mine,
      coalesce(sum(cost_micro_usd), 0)::float as spend from practice_ai_usage where created_at > ${dayStart.toISOString()}`),
  );
  if ((usage?.mine ?? 0) >= settings.quotas.aiRequestsPerDay) {
    await record({ ...base, status: "quota", errorCode: "user_daily" });
    throw new PracticeError(`You've used today's ${settings.quotas.aiRequestsPerDay} AI requests. Practice continues without them.`, 429, "ai_quota");
  }
  if ((usage?.spend ?? 0) >= settings.quotas.aiDailyBudgetUsd * 1_000_000) {
    await record({ ...base, status: "quota", errorCode: "global_budget" });
    throw new PracticeError("The AI tutor has reached today's budget. Try again tomorrow.", 503, "ai_budget");
  }
  if (!(await hit(`practice:ai:${userId}`, 6, 60))) throw new PracticeError("Too many AI requests in a minute.", 429, "rate_limited", 30);

  const ctx = await buildContext(userId, input);
  const started = Date.now();
  let attempt = 0;
  for (;;) {
    attempt++;
    try {
      const result = await callModel(ai, aiKey(settings), { system: SYSTEM, user: ctx.user, schema: ANSWER_SCHEMA, maxTokens: ai.maxOutputTokens, signal: AbortSignal.timeout(ai.timeoutMs) }, fetchImpl);
      let answer: z.infer<typeof answerShape>;
      try {
        answer = answerShape.parse(JSON.parse(result.text.replace(/^```(?:json)?\s*|\s*```$/g, "")));
      } catch {
        answer = { summary: result.text.slice(0, 2000), points: [], next_step: "", code: "" };
      }
      const grounded = ground(answer, ctx);
      await record({ ...base, problemId: ctx.problemId, inputTokens: result.inputTokens, outputTokens: result.outputTokens, costMicroUsd: costMicroUsd(ai, result.inputTokens, result.outputTokens), latencyMs: Date.now() - started, status: "ok" });
      await recordEvent(db, { userId, type: "ai_assistance", problemId: ctx.problemId, detail: { feature: input.feature, requestId } });
      return { ...grounded.answer, grounding: grounded.grounding, facts: ctx.facts, requestId };
    } catch (error) {
      const pe = error instanceof ProviderError ? error : new ProviderError((error as Error).message, "unavailable", false);
      if (pe.retryable && attempt < 2 && Date.now() - started < ai.timeoutMs) {
        await new Promise((r) => setTimeout(r, 800));
        continue;
      }
      await record({ ...base, problemId: ctx.problemId, latencyMs: Date.now() - started, status: "error", errorCode: pe.code });
      log.warn("practice tutor failed", { requestId, code: pe.code, provider: ai.provider });
      throw new PracticeError(
        pe.code === "timeout" ? "The AI tutor took too long. Try again." : pe.code === "rate_limited" ? "The AI provider is busy. Try again in a minute." : "The AI tutor is unavailable right now.",
        503,
        `ai_${pe.code}`,
      );
    }
  }
}

/** Admin overview numbers. */
export async function aiUsageSummary(days = 1) {
  const db = await getDb();
  const since = new Date(Date.now() - days * 86_400_000);
  const rows = await db
    .select({ status: schema.practiceAiUsage.status, n: sql<number>`count(*)::int`, cost: sql<number>`coalesce(sum(${schema.practiceAiUsage.costMicroUsd}), 0)::float`, tokens: sql<number>`coalesce(sum(${schema.practiceAiUsage.inputTokens} + ${schema.practiceAiUsage.outputTokens}), 0)::int` })
    .from(schema.practiceAiUsage)
    .where(gte(schema.practiceAiUsage.createdAt, since))
    .groupBy(schema.practiceAiUsage.status);
  return { requests: rows.reduce((n, r) => n + r.n, 0), byStatus: Object.fromEntries(rows.map((r) => [r.status, r.n])), costUsd: rows.reduce((n, r) => n + r.cost, 0) / 1_000_000, tokens: rows.reduce((n, r) => n + r.tokens, 0) };
}
