import { desc, eq, sql } from "drizzle-orm";
import { gzipSync } from "node:zlib";
import { z } from "zod";
import { getDb, schema } from "@/db";
import { rowsOf } from "@/db/rows";
import { audit } from "./audit";
import { log } from "./log";
import type { Actor } from "./posts";
import { PostError } from "./posts";
import { encryptWithPassphrase, seal, unseal, type Sealed } from "./secrets";
import { bucketOps, storageReady } from "./storage";

/**
 * Encrypted site backups to Cloudflare R2 (the media storage account; optionally a separate private bucket).
 * Contents: content, configuration and accounts WITHOUT password hashes, sessions, API-key hashes or stored
 * credentials. Each file is gzip + AES-256-GCM with a passphrase only the owner knows.
 *
 * Objects: {bucket}/jithendar/backups/jithendar-backup-{yyyymmdd-hhmmss}.json.gz.enc
 */
const KEY = "backups";
const PREFIX = "jithendar-backup-";
export const BACKUP_ROOT = "jithendar/backups";
const LOCK_ID = 7_250_032;

type R2Dest = { enabled: boolean; bucket: string };
export type BackupConfig = {
  passphrase: Sealed | null;
  schedule: "off" | "daily" | "weekly";
  hourUtc: number;
  retention: number;
  r2: R2Dest | null;
};

const empty: BackupConfig = { passphrase: null, schedule: "off", hourUtc: 21, retention: 14, r2: null };

export async function readBackupConfig(): Promise<BackupConfig> {
  const db = await getDb();
  const [row] = await db.select().from(schema.setting).where(eq(schema.setting.key, KEY));
  const v = (row?.value as Partial<BackupConfig> | undefined) ?? {};
  // Older rows may still hold s3/sftp/gdrive destinations (removed): only the known fields are kept.
  return { passphrase: v.passphrase ?? empty.passphrase, schedule: v.schedule ?? empty.schedule, hourUtc: v.hourUtc ?? empty.hourUtc, retention: v.retention ?? empty.retention, r2: v.r2 ?? null };
}

async function writeConfig(c: BackupConfig, userId: string) {
  const db = await getDb();
  await db
    .insert(schema.setting)
    .values({ key: KEY, value: c, updatedBy: userId })
    .onConflictDoUpdate({ target: schema.setting.key, set: { value: c, updatedBy: userId, updatedAt: new Date() } });
}

/** What the admin form may show: never secrets, only whether they are set. */
export async function backupSummary() {
  const c = await readBackupConfig();
  return {
    hasPassphrase: Boolean(c.passphrase),
    schedule: c.schedule,
    hourUtc: c.hourUtc,
    retention: c.retention,
    storageReady: await storageReady(),
    r2: c.r2 && { enabled: c.r2.enabled, bucket: c.r2.bucket },
  };
}

function admin(actor: Actor) {
  if (actor.role !== "admin") throw new PostError("Only admins can manage backups.", 403);
}

const generalInput = z.object({
  schedule: z.enum(["off", "daily", "weekly"]),
  hourUtc: z.coerce.number().int().min(0).max(23),
  retention: z.coerce.number().int().min(1).max(365),
  passphrase: z.string().max(200).default(""),
});

export async function saveGeneral(actor: Actor, raw: unknown) {
  admin(actor);
  const parsed = generalInput.safeParse(raw);
  if (!parsed.success) throw new PostError("Backup settings are not valid.", 400, parsed.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`));
  const c = await readBackupConfig();
  if (parsed.data.passphrase && parsed.data.passphrase.length < 12) throw new PostError("Use a backup passphrase of at least 12 characters.");
  if (!parsed.data.passphrase && !c.passphrase) throw new PostError("Set a backup passphrase. You will need it to restore.");
  await writeConfig(
    { ...c, schedule: parsed.data.schedule, hourUtc: parsed.data.hourUtc, retention: parsed.data.retention, passphrase: parsed.data.passphrase ? seal(parsed.data.passphrase) : c.passphrase },
    actor.id,
  );
  await audit(actor, "backup.configure", "general", { schedule: parsed.data.schedule, retention: parsed.data.retention });
}

const BUCKET = /^$|^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$/;

/** Turn the R2 destination on or off and choose its bucket ("" = the media bucket). */
export async function saveDestination(actor: Actor, f: { enabled: boolean; bucket: string }) {
  admin(actor);
  const bucket = f.bucket.trim().toLowerCase();
  if (!BUCKET.test(bucket)) throw new PostError("Bucket names are 3–63 lowercase letters, digits and hyphens.");
  if (f.enabled && !(await storageReady())) throw new PostError("Configure Cloudflare R2 in Storage & email first.");
  const c = await readBackupConfig();
  await writeConfig({ ...c, r2: { enabled: f.enabled, bucket } }, actor.id);
  await audit(actor, "backup.destination", "r2", { enabled: f.enabled, bucket: bucket || "(media bucket)" });
}

// --- Destination ---------------------------------------------------------------------------

type Target = { name: string; put: (file: string, data: Buffer) => Promise<void>; prune: (retention: number) => Promise<number> };

async function r2Target(d: R2Dest): Promise<Target> {
  const ops = await bucketOps(d.bucket);
  const key = (f: string) => `${BACKUP_ROOT}/${f}`;
  return {
    name: "r2",
    put: (file, data) => ops.put(key(file), data),
    prune: async (retention) => {
      const old = (await ops.list(key(PREFIX))).map((o) => o.key).sort().reverse().slice(retention);
      for (const k of old) await ops.remove(k);
      return old.length;
    },
  };
}

async function targets(c: BackupConfig, onlyEnabled = true): Promise<Target[]> {
  if (!c.r2 || (onlyEnabled && !c.r2.enabled)) return [];
  return [await r2Target(c.r2)];
}

/** Write and remove a small probe object to prove the bucket is writable. */
export async function testDestination(actor: Actor) {
  admin(actor);
  const c = await readBackupConfig();
  if (!c.r2) throw new PostError("Save the destination first.");
  try {
    const ops = await bucketOps(c.r2.bucket);
    const probe = `${BACKUP_ROOT}/connection-test-${Date.now()}.txt`;
    await ops.put(probe, Buffer.from("ok"), "text/plain");
    await ops.remove(probe);
  } catch (e) {
    throw new PostError(`Connection test failed: ${(e as Error).message}`);
  }
}

/** Backups stored in R2, newest first (for the admin list). */
export async function listStoredBackups(): Promise<{ key: string; name: string; size: number; lastModified: string | null }[]> {
  const c = await readBackupConfig();
  if (!c.r2 || !(await storageReady())) return [];
  const ops = await bucketOps(c.r2.bucket);
  return (await ops.list(`${BACKUP_ROOT}/${PREFIX}`))
    .map((o) => ({ ...o, name: o.key.slice(BACKUP_ROOT.length + 1) }))
    .sort((a, b) => b.name.localeCompare(a.name));
}

/** Bytes of one stored backup (admin download). Only names this site writes are accepted. */
export async function readStoredBackup(name: string): Promise<Buffer> {
  if (!/^jithendar-backup-\d{8}-\d{6}\.json\.gz\.enc$/.test(name)) throw new PostError("Unknown backup.", 404);
  const c = await readBackupConfig();
  if (!c.r2) throw new PostError("Backups are not configured.", 404);
  return (await bucketOps(c.r2.bucket)).get(`${BACKUP_ROOT}/${name}`);
}

// --- Building and running -----------------------------------------------------------

/** Tables in the backup, and columns that must never leave the server. */
const TABLES: { name: string; omit?: string[] }[] = [
  { name: "post" },
  { name: "page" },
  { name: "category" },
  { name: "author_profile" },
  { name: "comment" },
  { name: "contact_message" },
  { name: "media" },
  { name: "redirect" },
  { name: "user", omit: [] },
];

export async function buildBackup(): Promise<{ filename: string; data: Buffer }> {
  const c = await readBackupConfig();
  if (!c.passphrase) throw new PostError("Set a backup passphrase first.");
  const db = await getDb();
  const tables: Record<string, unknown[]> = {};
  for (const t of TABLES) tables[t.name] = rowsOf(await db.execute(sql.raw(`select * from "${t.name}"`)));
  // Only the public site settings: storage/email/backup credentials are excluded on purpose.
  const [site] = await db.select().from(schema.setting).where(eq(schema.setting.key, "site"));
  const payload = {
    format: "jithendar-backup",
    version: 1,
    createdAt: new Date().toISOString(),
    appVersion: process.env.GIT_SHA ?? "dev",
    note: "Excludes password hashes, sessions, API-key hashes and stored credentials. Media bytes live in R2; this holds their metadata.",
    settings: site?.value ?? null,
    tables,
  };
  const data = await encryptWithPassphrase(gzipSync(Buffer.from(JSON.stringify(payload))), unseal(c.passphrase));
  const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\..+/, "").replace("T", "-");
  return { filename: `${PREFIX}${stamp}.json.gz.enc`, data };
}

export async function runBackup(trigger: "manual" | "scheduled", actor?: Actor) {
  const db = await getDb();
  const [run] = await db.insert(schema.backupRun).values({ trigger, status: "running", triggeredBy: actor?.label ?? "scheduler" }).returning();
  const results: { destination: string; ok: boolean; detail: string }[] = [];
  try {
    const c = await readBackupConfig();
    const dests = await targets(c);
    if (dests.length === 0) throw new PostError("Turn on the Cloudflare R2 destination first.");
    const { filename, data } = await buildBackup();
    for (const d of dests) {
      try {
        await d.put(filename, data);
        const pruned = await d.prune(c.retention).catch(() => 0);
        results.push({ destination: d.name, ok: true, detail: pruned ? `uploaded; removed ${pruned} old backup(s)` : "uploaded" });
      } catch (e) {
        results.push({ destination: d.name, ok: false, detail: (e as Error).message.slice(0, 300) });
      }
    }
    const status = results.every((r) => r.ok) ? "success" : results.some((r) => r.ok) ? "partial" : "failed";
    await db.update(schema.backupRun).set({ status, filename, sizeBytes: data.length, results, finishedAt: new Date() }).where(eq(schema.backupRun.id, run!.id));
    log.info("backup finished", { trigger, status, sizeBytes: data.length, results });
    if (actor) await audit(actor, "backup.run", filename, { status });
    return { status, results };
  } catch (error) {
    const detail = error instanceof PostError ? error.message : "Unexpected error (see logs).";
    if (!(error instanceof PostError)) log.error("backup failed", { err: error, trigger });
    await db.update(schema.backupRun).set({ status: "failed", results: [{ destination: "-", ok: false, detail }], finishedAt: new Date() }).where(eq(schema.backupRun.id, run!.id));
    return { status: "failed", results: [{ destination: "-", ok: false, detail }] };
  }
}

export async function recentRuns(limit = 20) {
  const db = await getDb();
  return db.select().from(schema.backupRun).orderBy(desc(schema.backupRun.startedAt)).limit(limit);
}

/** In-app scheduler: one replica (Postgres advisory lock) runs due backups. Checked every 15 minutes. */
export function startBackupScheduler() {
  const g = globalThis as unknown as { __backupTimer?: NodeJS.Timeout };
  if (g.__backupTimer) return;
  const tick = async () => {
    try {
      const c = await readBackupConfig();
      if (c.schedule === "off" || !c.passphrase) return;
      const now = new Date();
      if (now.getUTCHours() < c.hourUtc) return;
      const [last] = await recentRuns(1);
      const interval = c.schedule === "daily" ? 20 * 3600_000 : 6.5 * 86_400_000;
      if (last && now.getTime() - last.startedAt.getTime() < interval) return;
      const db = await getDb();
      const [{ locked } = { locked: false }] = rowsOf<{ locked: boolean }>(await db.execute(sql`select pg_try_advisory_lock(${LOCK_ID}) as locked`));
      if (!locked) return;
      try {
        await runBackup("scheduled");
      } finally {
        await db.execute(sql`select pg_advisory_unlock(${LOCK_ID})`);
      }
    } catch (error) {
      log.warn("backup scheduler tick failed", { err: error });
    }
  };
  g.__backupTimer = setInterval(() => void tick(), 15 * 60_000);
  g.__backupTimer.unref?.();
}
