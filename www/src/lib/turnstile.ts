import { isProductionEnv } from "@/config/site";

// Cloudflare's documented test keys: always pass. Used only outside production when keys are unset.
const TEST_SITE_KEY = "1x00000000000000000000AA";
const TEST_SECRET = "1x0000000000000000000000000000000AA";

type Env = Record<string, string | undefined>;

export function turnstileSiteKey(env: Env = process.env): string | undefined {
  return env.TURNSTILE_SITE_KEY || (isProductionEnv() ? undefined : TEST_SITE_KEY);
}

export function turnstileSecret(env: Env = process.env): string | undefined {
  return env.TURNSTILE_SECRET_KEY || (isProductionEnv() ? undefined : TEST_SECRET);
}

/** Keys from Admin → Advanced settings, falling back to the deployment (and to Cloudflare's test keys outside production). */
export async function turnstileKeys(): Promise<{ siteKey: string | undefined; secret: string | undefined; production: boolean }> {
  const { effectiveEnv } = await import("./runtime-settings");
  const env = await effectiveEnv();
  return { siteKey: turnstileSiteKey(env), secret: turnstileSecret(env), production: Boolean(env.TURNSTILE_SITE_KEY) };
}

/** Server-side Turnstile check for our own forms (contact, comments). Fails closed. */
export async function verifyTurnstile(token: string | null | undefined, ip?: string | null): Promise<boolean> {
  const { secret } = await turnstileKeys();
  if (!secret || !token) return false;
  try {
    const body = new URLSearchParams({ secret, response: token, ...(ip ? { remoteip: ip } : {}) });
    const res = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method: "POST",
      body,
      signal: AbortSignal.timeout(10_000),
    });
    const data = (await res.json()) as { success?: boolean };
    return data.success === true;
  } catch {
    return false;
  }
}
