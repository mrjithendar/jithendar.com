import "server-only";
import { eq } from "drizzle-orm";
import { z } from "zod";
import { getDb, schema } from "@/db";
import { audit } from "../audit";
import { broadcastInvalidate, onInvalidate } from "../cache-bus";
import type { Actor } from "../posts";
import { seal, unseal, type Sealed } from "../secrets";
import { PracticeError } from "./errors";

/**
 * Admin → Python practice → Settings, stored in the `setting` table (key "practice").
 *
 * The executor's address and token are deployment secrets (PRACTICE_EXECUTOR_URL, PRACTICE_EXECUTOR_TOKEN) and
 * never stored here. Running code needs both those variables and `execution.enabled`: the switch stays off
 * until the sandbox (gVisor) is installed and verified (docs/PYTHON_PRACTICE_EXECUTOR.md).
 */
const KEY = "practice";

export const AI_PROVIDERS = ["openai", "gemini", "bedrock"] as const;
export type AiProvider = (typeof AI_PROVIDERS)[number];

export type Runtime = { id: string; label: string; enabled: boolean };

export type PracticeSettings = {
  execution: { enabled: boolean; runtimes: Runtime[]; defaultRuntime: string; perTestSeconds: number; totalSeconds: number; memoryMb: number };
  quotas: { runsPerHour: number; submitsPerHour: number; maxPending: number; aiRequestsPerDay: number; aiDailyBudgetUsd: number };
  ai: {
    enabled: boolean;
    provider: AiProvider;
    model: string;
    /** OpenAI-compatible base URL (OpenAI, Azure OpenAI, a gateway); empty = https://api.openai.com/v1. */
    baseUrl: string;
    /** Bedrock region. Bedrock uses the pod's AWS credentials (env or IRSA), never a key stored here. */
    region: string;
    apiKey: Sealed | null;
    timeoutMs: number;
    maxOutputTokens: number;
    inputUsdPerMTok: number;
    outputUsdPerMTok: number;
  };
  leaderboard: { enabled: boolean };
  retention: { activityDays: number; codeDays: number };
};

export const DEFAULT_SETTINGS: PracticeSettings = {
  execution: { enabled: false, runtimes: [{ id: "python-3.13", label: "Python 3.13", enabled: true }], defaultRuntime: "python-3.13", perTestSeconds: 2, totalSeconds: 10, memoryMb: 256 },
  quotas: { runsPerHour: 120, submitsPerHour: 60, maxPending: 2, aiRequestsPerDay: 40, aiDailyBudgetUsd: 5 },
  ai: { enabled: false, provider: "openai", model: "", baseUrl: "", region: "us-east-1", apiKey: null, timeoutMs: 30_000, maxOutputTokens: 900, inputUsdPerMTok: 0, outputUsdPerMTok: 0 },
  leaderboard: { enabled: true },
  retention: { activityDays: 730, codeDays: 365 },
};

let cached: Promise<PracticeSettings> | null = null;
onInvalidate("practice", () => {
  cached = null;
});

function merge(stored: Partial<PracticeSettings> | undefined): PracticeSettings {
  const s = stored ?? {};
  return {
    execution: { ...DEFAULT_SETTINGS.execution, ...s.execution },
    quotas: { ...DEFAULT_SETTINGS.quotas, ...s.quotas },
    ai: { ...DEFAULT_SETTINGS.ai, ...s.ai },
    leaderboard: { ...DEFAULT_SETTINGS.leaderboard, ...s.leaderboard },
    retention: { ...DEFAULT_SETTINGS.retention, ...s.retention },
  };
}

export async function getPracticeSettings(): Promise<PracticeSettings> {
  cached ??= (async () => {
    const db = await getDb();
    const [row] = await db.select().from(schema.setting).where(eq(schema.setting.key, KEY));
    return merge(row?.value as Partial<PracticeSettings> | undefined);
  })().catch((err) => {
    cached = null;
    throw err;
  });
  return cached;
}

export function executorEnv(env: Record<string, string | undefined> = process.env): { url: string; token: string } | null {
  const url = env.PRACTICE_EXECUTOR_URL?.trim().replace(/\/+$/, "");
  const token = env.PRACTICE_EXECUTOR_TOKEN?.trim();
  return url && token ? { url, token } : null;
}

/** Whether Run/Submit work right now (switch on and executor configured). */
export async function executionAvailable(): Promise<boolean> {
  return (await getPracticeSettings()).execution.enabled && executorEnv() !== null;
}

export function aiKey(settings: PracticeSettings): string | null {
  if (settings.ai.provider === "bedrock") return null;
  if (settings.ai.apiKey) return unseal(settings.ai.apiKey);
  const env = settings.ai.provider === "gemini" ? process.env.GEMINI_API_KEY : process.env.OPENAI_API_KEY;
  return env?.trim() || null;
}

export function aiConfigured(settings: PracticeSettings): boolean {
  return settings.ai.enabled && Boolean(settings.ai.model) && (settings.ai.provider === "bedrock" || Boolean(aiKey(settings)));
}

const num = (min: number, max: number) => z.coerce.number().min(min).max(max);
const settingsInput = z.object({
  execution: z.object({
    enabled: z.boolean(),
    runtimes: z.array(z.object({ id: z.string().regex(/^[a-z0-9.\-]{1,32}$/), label: z.string().trim().min(1).max(40), enabled: z.boolean() })).min(1).max(10),
    defaultRuntime: z.string(),
    perTestSeconds: num(0.5, 5),
    totalSeconds: num(2, 20),
    memoryMb: num(64, 256),
  }),
  quotas: z.object({ runsPerHour: num(1, 2000), submitsPerHour: num(1, 1000), maxPending: num(1, 10), aiRequestsPerDay: num(0, 1000), aiDailyBudgetUsd: num(0, 10_000) }),
  ai: z.object({
    enabled: z.boolean(),
    provider: z.enum(AI_PROVIDERS),
    model: z.string().trim().max(120).regex(/^[A-Za-z0-9._:\-/@]*$/, "Use the provider's model id."),
    baseUrl: z.union([z.literal(""), z.string().trim().url().startsWith("https://")]),
    region: z.string().trim().regex(/^[a-z]{2}(-[a-z]+)+-\d$/, "Use an AWS region such as us-east-1."),
    apiKey: z.string().trim().max(400).default(""),
    timeoutMs: num(2000, 120_000),
    maxOutputTokens: num(100, 4000),
    inputUsdPerMTok: num(0, 1000),
    outputUsdPerMTok: num(0, 1000),
  }),
  leaderboard: z.object({ enabled: z.boolean() }),
  retention: z.object({ activityDays: num(30, 3650), codeDays: num(30, 3650) }),
});

export async function savePracticeSettings(actor: Actor, raw: unknown): Promise<void> {
  if (actor.role !== "admin") throw new PracticeError("Only admins can change practice settings.", 403, "forbidden");
  const parsed = settingsInput.safeParse(raw);
  if (!parsed.success) throw new PracticeError(`Check the settings: ${parsed.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("; ")}`);
  const current = await getPracticeSettings();
  const v = parsed.data;
  if (!v.execution.runtimes.some((r) => r.id === v.execution.defaultRuntime && r.enabled)) throw new PracticeError("The default runtime must be one of the enabled runtimes.");
  const next: PracticeSettings = {
    ...v,
    ai: { ...v.ai, apiKey: v.ai.apiKey ? seal(v.ai.apiKey) : current.ai.apiKey },
  };
  const db = await getDb();
  await db
    .insert(schema.setting)
    .values({ key: KEY, value: next, updatedBy: actor.id })
    .onConflictDoUpdate({ target: schema.setting.key, set: { value: next, updatedBy: actor.id, updatedAt: new Date() } });
  cached = null;
  broadcastInvalidate("practice");
  await audit(actor, "practice.settings", undefined, {
    executionEnabled: v.execution.enabled,
    aiEnabled: v.ai.enabled,
    aiProvider: v.ai.provider,
    aiModel: v.ai.model,
    aiKeyChanged: Boolean(v.ai.apiKey),
    quotas: v.quotas,
  });
}

export async function clearAiKey(actor: Actor): Promise<void> {
  if (actor.role !== "admin") throw new PracticeError("Only admins can change practice settings.", 403, "forbidden");
  const current = await getPracticeSettings();
  const db = await getDb();
  const next = { ...current, ai: { ...current.ai, apiKey: null } };
  await db.update(schema.setting).set({ value: next, updatedBy: actor.id, updatedAt: new Date() }).where(eq(schema.setting.key, KEY));
  cached = null;
  broadcastInvalidate("practice");
  await audit(actor, "practice.settings.ai_key_removed");
}
