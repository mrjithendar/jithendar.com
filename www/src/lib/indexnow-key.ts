import { eq } from "drizzle-orm";
import { getDb, schema } from "@/db";

/**
 * The active IndexNow key: INDEXNOW_KEY from the deployment when set, otherwise the key generated in
 * Admin → Integrations (stored, not secret: it is published at /{key}.txt). Small and dependency-light because
 * the proxy calls it (only for *.txt requests); cached 30 s per process, so a change applies everywhere
 * within half a minute.
 */
export const INDEXNOW_KEY_PATTERN = /^[A-Za-z0-9-]{8,128}$/;
const TTL_MS = 30_000;
let cached: { key: string | null; at: number } | undefined;

export type StoredIndexNow = { enabled: boolean; key: string };

export async function indexNowKey(now = Date.now()): Promise<string | null> {
  const env = process.env.INDEXNOW_KEY?.trim();
  if (env && INDEXNOW_KEY_PATTERN.test(env)) return env;
  if (cached && now - cached.at < TTL_MS) return cached.key;
  let key: string | null = null;
  try {
    const db = await getDb();
    const [row] = await db.select({ value: schema.setting.value }).from(schema.setting).where(eq(schema.setting.key, "integrations"));
    const s = (row?.value as { indexNow?: Partial<StoredIndexNow> } | undefined)?.indexNow;
    key = s?.enabled === true && typeof s.key === "string" && INDEXNOW_KEY_PATTERN.test(s.key) ? s.key : null;
  } catch {
    key = cached?.key ?? null; // database unavailable: keep the last known key
  }
  cached = { key, at: now };
  return key;
}

export function resetIndexNowKeyCache() {
  cached = undefined;
}
