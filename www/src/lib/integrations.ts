import "server-only";
import { eq } from "drizzle-orm";
import { z } from "zod";
import { getDb, schema } from "@/db";
import { audit } from "./audit";
import { SOCIAL_PROVIDERS, socialProviderConfig, type SocialProvider } from "./auth-providers";
import { broadcastInvalidate, onInvalidate } from "./cache-bus";
import { geminiImageConfig, IMAGE_SIZES, type GeminiImageConfig } from "./gemini";
import { INDEXNOW_KEY_PATTERN, resetIndexNowKeyCache, type StoredIndexNow } from "./indexnow-key";
import type { Actor } from "./posts";
import { PostError } from "./posts";
import { seal, unseal, type Sealed } from "./secrets";

/**
 * Integrations an admin manages in Admin → Integrations: social sign-in (Google, GitHub) and image generation
 * (Gemini). Secrets are sealed with SETTINGS_ENCRYPTION_KEY and never sent back to the browser.
 *
 * Precedence: once a provider or Gemini has been saved in the admin, that entry wins (including "disabled");
 * until then the deployment's environment variables (GOOGLE_CLIENT_ID…, GEMINI_API_KEY…) are used.
 */
const KEY = "integrations";

type StoredProvider = { enabled: boolean; clientId: string; clientSecret: Sealed | null };
type StoredGemini = { enabled: boolean; apiKey: Sealed | null; model: string; imageSize: (typeof IMAGE_SIZES)[number]; verifiedAt: string | null; lastError: string | null };
type Stored = { social: Partial<Record<SocialProvider, StoredProvider>>; gemini: StoredGemini | null; indexNow: StoredIndexNow | null };

const EMPTY: Stored = { social: {}, gemini: null, indexNow: null };
let cached: Promise<Stored> | null = null;
onInvalidate("integrations", () => {
  cached = null;
  resetIndexNowKeyCache();
});

async function readStored(): Promise<Stored> {
  cached ??= (async () => {
    const db = await getDb();
    const [row] = await db.select().from(schema.setting).where(eq(schema.setting.key, KEY));
    const v = (row?.value as Partial<Stored> | undefined) ?? {};
    return { social: v.social ?? {}, gemini: v.gemini ?? null, indexNow: v.indexNow ?? null };
  })().catch((err) => {
    cached = null;
    throw err;
  });
  return cached;
}

async function write(next: Stored, actorId: string) {
  const db = await getDb();
  await db
    .insert(schema.setting)
    .values({ key: KEY, value: next, updatedBy: actorId })
    .onConflictDoUpdate({ target: schema.setting.key, set: { value: next, updatedBy: actorId, updatedAt: new Date() } });
  broadcastInvalidate("integrations");
}

function adminOnly(actor: Actor) {
  if (actor.role !== "admin") throw new PostError("Only admins can manage integrations.", 403);
}

// --- Social sign-in ----------------------------------------------------------------------------

/** The environment as Better Auth's provider helpers read it, with admin-saved providers overriding it. */
async function effectiveEnv(): Promise<Record<string, string | undefined>> {
  const stored = await readStored().catch(() => EMPTY);
  const env: Record<string, string | undefined> = { ...process.env };
  for (const p of SOCIAL_PROVIDERS) {
    const s = stored.social[p];
    if (!s) continue;
    const prefix = p.toUpperCase();
    env[`${prefix}_CLIENT_ID`] = s.enabled ? s.clientId : undefined;
    env[`${prefix}_CLIENT_SECRET`] = s.enabled && s.clientSecret ? unseal(s.clientSecret) : undefined;
  }
  return env;
}

/** Providers shown on the sign-in page and in Account → Connected accounts. */
export async function activeProviders(): Promise<SocialProvider[]> {
  const env = await effectiveEnv();
  return SOCIAL_PROVIDERS.filter((p) => env[`${p.toUpperCase()}_CLIENT_ID`]?.trim() && env[`${p.toUpperCase()}_CLIENT_SECRET`]?.trim());
}

/** Better Auth `socialProviders` built from the effective configuration. */
export async function activeSocialProviderConfig() {
  return socialProviderConfig(await effectiveEnv());
}

export type ProviderSummary = { provider: SocialProvider; source: "admin" | "env" | "none"; enabled: boolean; clientId: string; hasSecret: boolean };

export async function socialSummary(): Promise<ProviderSummary[]> {
  const stored = await readStored();
  return SOCIAL_PROVIDERS.map((provider) => {
    const s = stored.social[provider];
    if (s) return { provider, source: "admin", enabled: s.enabled, clientId: s.clientId, hasSecret: Boolean(s.clientSecret) };
    const prefix = provider.toUpperCase();
    const id = process.env[`${prefix}_CLIENT_ID`]?.trim() ?? "";
    const env = Boolean(id && process.env[`${prefix}_CLIENT_SECRET`]?.trim());
    return { provider, source: env ? "env" : "none", enabled: env, clientId: env ? id : "", hasSecret: env };
  });
}

const providerInput = z.object({
  enabled: z.boolean(),
  clientId: z.string().trim().max(300).regex(/^[\w.\-]*$/, "The client ID has characters a client ID never contains."),
  clientSecret: z.string().trim().max(500).default(""),
});

export async function saveSocialProvider(actor: Actor, provider: SocialProvider, raw: unknown) {
  adminOnly(actor);
  if (!SOCIAL_PROVIDERS.includes(provider)) throw new PostError("Unknown provider.");
  const parsed = providerInput.safeParse(raw);
  if (!parsed.success) throw new PostError("Check the client ID and secret.", 400, parsed.error.issues.map((i) => i.message));
  const stored = await readStored();
  const before = stored.social[provider];
  const clientSecret = parsed.data.clientSecret ? seal(parsed.data.clientSecret) : (before?.clientSecret ?? null);
  if (parsed.data.enabled && (!parsed.data.clientId || !clientSecret)) throw new PostError("A client ID and a client secret are required to turn this provider on.");
  await write({ ...stored, social: { ...stored.social, [provider]: { enabled: parsed.data.enabled, clientId: parsed.data.clientId, clientSecret } } }, actor.id);
  await audit(actor, "integrations.social", provider, { enabled: parsed.data.enabled, secretChanged: Boolean(parsed.data.clientSecret) });
}

/** Forget the admin entry so the environment variables (if any) apply again. */
export async function resetSocialProvider(actor: Actor, provider: SocialProvider) {
  adminOnly(actor);
  const stored = await readStored();
  const social = { ...stored.social };
  delete social[provider];
  await write({ ...stored, social }, actor.id);
  await audit(actor, "integrations.social.reset", provider);
}

// --- Gemini image generation ------------------------------------------------------------------

/** Effective Gemini configuration: the admin entry when saved, otherwise GEMINI_* environment variables. */
export async function resolveGeminiImageConfig(): Promise<GeminiImageConfig | null> {
  // Timeout and the other GEMINI_* tuning values can come from Admin → Advanced settings.
  const { effectiveEnv } = await import("./runtime-settings");
  const env = await effectiveEnv();
  const stored = (await readStored().catch(() => EMPTY)).gemini;
  if (!stored) return geminiImageConfig(env);
  if (!stored.enabled || !stored.apiKey || !stored.model) return null;
  return geminiImageConfig({ ...env, GEMINI_API_KEY: unseal(stored.apiKey), GEMINI_IMAGE_MODEL: stored.model, GEMINI_IMAGE_SIZE: stored.imageSize });
}

export type GeminiSummary = { source: "admin" | "env" | "none"; enabled: boolean; model: string; imageSize: string; hasKey: boolean; keyHint: string; verifiedAt: string | null; lastError: string | null };

export async function geminiSummary(): Promise<GeminiSummary> {
  const s = (await readStored()).gemini;
  if (s) {
    const key = s.apiKey ? unseal(s.apiKey) : "";
    return { source: "admin", enabled: s.enabled, model: s.model, imageSize: s.imageSize, hasKey: Boolean(key), keyHint: key ? `…${key.slice(-4)}` : "", verifiedAt: s.verifiedAt, lastError: s.lastError };
  }
  const env = geminiImageConfig();
  return env
    ? { source: "env", enabled: true, model: env.model, imageSize: env.imageSize, hasKey: true, keyHint: `…${env.apiKey.slice(-4)}`, verifiedAt: null, lastError: null }
    : { source: "none", enabled: false, model: "", imageSize: "1K", hasKey: false, keyHint: "", verifiedAt: null, lastError: null };
}

const geminiInput = z.object({
  enabled: z.boolean(),
  apiKey: z.string().trim().max(200).default(""),
  model: z.string().trim().max(100).regex(/^[a-z0-9][a-z0-9.\-]*$/i, "Use the model code from ai.google.dev, e.g. gemini-3.1-flash-image."),
  imageSize: z.enum(IMAGE_SIZES),
});

/**
 * Save the Gemini settings and, when it is on, check the key and model with a free metadata request
 * (GET models/{model}): no image is generated and nothing is billed.
 */
export async function saveGemini(actor: Actor, raw: unknown, fetchImpl: typeof fetch = fetch): Promise<{ verified: boolean; error?: string }> {
  adminOnly(actor);
  const parsed = geminiInput.safeParse(raw);
  if (!parsed.success) throw new PostError("Check the Gemini settings.", 400, parsed.error.issues.map((i) => i.message));
  const stored = await readStored();
  const apiKey = parsed.data.apiKey ? seal(parsed.data.apiKey) : (stored.gemini?.apiKey ?? null);
  if (parsed.data.enabled && !apiKey) throw new PostError("Enter an API key to turn image generation on.");
  let verifiedAt: string | null = null;
  let lastError: string | null = null;
  if (parsed.data.enabled && apiKey) {
    const check = await checkGeminiKey(unseal(apiKey), parsed.data.model, fetchImpl);
    if (check.ok) verifiedAt = new Date().toISOString();
    else lastError = check.error;
  }
  await write({ ...stored, gemini: { enabled: parsed.data.enabled, apiKey, model: parsed.data.model, imageSize: parsed.data.imageSize, verifiedAt, lastError } }, actor.id);
  await audit(actor, "integrations.gemini", parsed.data.model, { enabled: parsed.data.enabled, keyChanged: Boolean(parsed.data.apiKey), verified: Boolean(verifiedAt) });
  return verifiedAt || !parsed.data.enabled ? { verified: Boolean(verifiedAt) } : { verified: false, error: lastError ?? "unknown error" };
}

export async function removeGeminiKey(actor: Actor) {
  adminOnly(actor);
  const stored = await readStored();
  await write({ ...stored, gemini: null }, actor.id);
  await audit(actor, "integrations.gemini.reset", undefined);
}

export async function checkGeminiKey(apiKey: string, model: string, fetchImpl: typeof fetch = fetch): Promise<{ ok: true } | { ok: false; error: string }> {
  try {
    const res = await fetchImpl(`https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}`, {
      headers: { "x-goog-api-key": apiKey },
      signal: AbortSignal.timeout(10_000),
    });
    if (res.ok) return { ok: true };
    if (res.status === 400 || res.status === 401 || res.status === 403) return { ok: false, error: "Google rejected the API key." };
    if (res.status === 404) return { ok: false, error: `The model "${model}" was not found for this key.` };
    return { ok: false, error: `Google answered HTTP ${res.status}.` };
  } catch (e) {
    return { ok: false, error: `Could not reach Google: ${(e as Error).message}` };
  }
}

// --- IndexNow ---------------------------------------------------------------------------------

export type IndexNowSummary = { source: "admin" | "env" | "none"; enabled: boolean; key: string | null };

export async function indexNowSummary(): Promise<IndexNowSummary> {
  const env = process.env.INDEXNOW_KEY?.trim();
  if (env && INDEXNOW_KEY_PATTERN.test(env)) return { source: "env", enabled: true, key: env };
  const s = (await readStored()).indexNow;
  return s ? { source: "admin", enabled: s.enabled, key: s.key } : { source: "none", enabled: false, key: null };
}

/** Turn IndexNow on or off. The first time it is turned on, a random 32-character key is generated (kept when turned off). */
export async function setIndexNow(actor: Actor, enabled: boolean, opts: { regenerate?: boolean } = {}) {
  adminOnly(actor);
  const stored = await readStored();
  const { randomBytes } = await import("node:crypto");
  const key = !stored.indexNow?.key || opts.regenerate ? randomBytes(16).toString("hex") : stored.indexNow.key;
  await write({ ...stored, indexNow: { enabled, key } }, actor.id);
  resetIndexNowKeyCache();
  await audit(actor, opts.regenerate ? "integrations.indexnow.key" : "integrations.indexnow", undefined, { enabled });
}
