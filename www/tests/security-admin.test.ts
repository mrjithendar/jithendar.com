import { eq } from "drizzle-orm";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { schema, setDbForTests, type Db } from "@/db";
import type { Actor } from "@/lib/posts";
import { freshDb } from "./db-helpers";

vi.mock("server-only", () => ({}));
vi.mock("next/headers", () => ({ headers: async () => new Headers({ "x-forwarded-for": "198.51.100.7, 10.0.0.1", "user-agent": "vitest" }) }));

// Backups write to an in-memory "bucket" instead of R2.
const bucket = new Map<string, Buffer>();
vi.mock("@/lib/storage", async (orig) => ({
  ...(await orig<typeof import("@/lib/storage")>()),
  storageReady: async () => true,
  bucketOps: async (name = "") => ({
    bucket: name || "media",
    sameAsMedia: !name,
    mediaIsPublic: false,
    put: async (key: string, body: Buffer) => void bucket.set(`${name || "media"}/${key}`, body),
    list: async (prefix: string) =>
      [...bucket.keys()].filter((k) => k.startsWith(`${name || "media"}/${prefix}`)).map((k) => ({ key: k.slice((name || "media").length + 1), size: bucket.get(k)!.length, lastModified: null })),
    remove: async (key: string) => void bucket.delete(`${name || "media"}/${key}`),
    get: async (key: string) => bucket.get(`${name || "media"}/${key}`)!,
  }),
}));

const admin: Actor = { id: "admin", role: "admin", label: "admin@example.com" };
const author: Actor = { id: "author", role: "author", label: "a@example.com" };
let db: Db;

beforeEach(async () => {
  bucket.clear();
  // The integrations cache is per process; each test starts from an empty database.
  (await import("@/lib/cache-bus")).broadcastInvalidate("integrations");
  db = await freshDb();
  await db.insert(schema.user).values([
    { id: "admin", name: "Admin", email: "admin@example.com", role: "admin" },
    { id: "author", name: "A", email: "a@example.com", role: "author" },
  ]);
});
afterEach(() => {
  setDbForTests(undefined);
  vi.unstubAllEnvs();
});

const failedSignIn = (email: string, ip: string, body: Record<string, unknown> = { code: "INVALID_EMAIL_OR_PASSWORD" }, status = 401) => ({
  path: "/sign-in/email",
  method: "POST",
  request: new Request("https://jithendar.com/api/auth/sign-in/email", { method: "POST", headers: { "x-forwarded-for": ip, "user-agent": "curl/8" } }),
  response: Response.json(body, { status }),
  email,
});

describe("audit entries", () => {
  it("record the request IP and user agent and a severity", async () => {
    const { audit } = await import("@/lib/audit");
    await audit(admin, "user.role", "u1", { from: "user", to: "admin" });
    const [row] = await db.select().from(schema.auditLog);
    expect(row).toMatchObject({ action: "user.role", ip: "198.51.100.7", userAgent: "vitest", severity: "critical" });
  });
});

describe("sign-in auditing", () => {
  it("logs failed, rate-limited and Turnstile-blocked sign-ins without the password", async () => {
    const { auditAuthResponse } = await import("@/lib/auth-audit");
    await auditAuthResponse(failedSignIn("victim@example.com", "203.0.113.5"));
    await auditAuthResponse(failedSignIn("victim@example.com", "203.0.113.5", { code: "VERIFICATION_FAILED" }, 403));
    await auditAuthResponse({ ...failedSignIn("victim@example.com", "203.0.113.5"), response: new Response("", { status: 429 }) });
    const rows = await db.select().from(schema.auditLog);
    expect(rows.map((r) => r.action).sort()).toEqual(["auth.captcha_failed", "auth.login_failed", "auth.rate_limited"]);
    const failed = rows.find((r) => r.action === "auth.login_failed")!;
    expect(failed).toMatchObject({ target: "victim@example.com", ip: "203.0.113.5", userAgent: "curl/8", severity: "warning" });
    expect(JSON.stringify(rows)).not.toMatch(/password":/);
  });

  it("escalates repeated failures and reads the email from the request body", async () => {
    const { auditAuthResponse, emailFromRequest } = await import("@/lib/auth-audit");
    const req = new Request("https://jithendar.com/api/auth/sign-in/email", { method: "POST", body: JSON.stringify({ email: " Victim@Example.com ", password: "hunter2" }) });
    expect(await emailFromRequest(req, "/sign-in/email")).toBe("victim@example.com");
    expect(await req.json()).toMatchObject({ password: "hunter2" }); // the handler still gets the body
    for (let i = 0; i < 5; i++) await auditAuthResponse(failedSignIn("victim@example.com", "203.0.113.5"));
    const rows = await db.select().from(schema.auditLog).where(eq(schema.auditLog.action, "auth.login_failed"));
    expect(rows.filter((r) => r.severity === "critical")).toHaveLength(1);
  });

  it("flags a sign-in from a new IP after failures", async () => {
    const { auditAuthResponse, auditLogin } = await import("@/lib/auth-audit");
    await auditLogin({ userId: "admin", ipAddress: "192.0.2.1", userAgent: "ff" }, "/sign-in/email");
    for (let i = 0; i < 3; i++) await auditAuthResponse(failedSignIn("admin@example.com", "203.0.113.9"));
    await auditLogin({ userId: "admin", ipAddress: "203.0.113.9", userAgent: "curl" }, "/sign-in/email");
    const logins = await db.select().from(schema.auditLog).where(eq(schema.auditLog.action, "auth.login"));
    expect(logins.map((l) => l.severity)).toEqual(expect.arrayContaining(["info", "warning"]));
    expect(logins.find((l) => l.ip === "203.0.113.9")!.detail).toMatchObject({ method: "password", newIp: true, failuresBefore: 3 });
  });
});

describe("security overview", () => {
  it("detects credential stuffing, brute force and targeted accounts", async () => {
    const { auditAuthResponse } = await import("@/lib/auth-audit");
    const { securityOverview } = await import("@/lib/security");
    for (const who of ["a@x.io", "b@x.io", "c@x.io"]) await auditAuthResponse(failedSignIn(who, "203.0.113.66"));
    for (let i = 0; i < 10; i++) await auditAuthResponse(failedSignIn("a@x.io", "203.0.113.77"));
    for (const ip of ["198.51.100.1", "198.51.100.2", "198.51.100.3"]) await auditAuthResponse(failedSignIn("boss@x.io", ip));
    const s = await securityOverview(24);
    expect(s.failedLogins).toBe(16);
    const kinds = s.findings.map((f) => `${f.kind}:${f.title}`);
    expect(kinds).toEqual(expect.arrayContaining([expect.stringMatching(/^credential-stuffing:203\.0\.113\.66/), expect.stringMatching(/^brute-force:10 failed sign-ins from 203\.0\.113\.77/), expect.stringMatching(/^targeted-account:boss@x\.io/)]));
    expect(s.findings[0]!.severity).toBe("critical");
  });
});

describe("integrations", () => {
  it("social providers saved by an admin override the environment, secrets sealed", async () => {
    vi.stubEnv("GITHUB_CLIENT_ID", "env-id");
    vi.stubEnv("GITHUB_CLIENT_SECRET", "env-secret");
    const { activeProviders, saveSocialProvider, socialSummary, resetSocialProvider } = await import("@/lib/integrations");
    expect(await activeProviders()).toEqual(["github"]);
    await expect(saveSocialProvider(author, "google", { enabled: true, clientId: "x", clientSecret: "y" })).rejects.toThrow(/admins/);
    await expect(saveSocialProvider(admin, "google", { enabled: true, clientId: "abc.apps.googleusercontent.com", clientSecret: "" })).rejects.toThrow(/secret/);
    await saveSocialProvider(admin, "google", { enabled: true, clientId: "abc.apps.googleusercontent.com", clientSecret: "g-secret-value" });
    await saveSocialProvider(admin, "github", { enabled: false, clientId: "env-id", clientSecret: "" });
    expect(await activeProviders()).toEqual(["google"]);
    const [row] = await db.select().from(schema.setting).where(eq(schema.setting.key, "integrations"));
    expect(JSON.stringify(row!.value)).not.toContain("g-secret-value");
    expect((await socialSummary()).find((p) => p.provider === "google")).toMatchObject({ source: "admin", enabled: true, hasSecret: true });
    await resetSocialProvider(admin, "github");
    expect(await activeProviders()).toEqual(["google", "github"]);
  });

  it("checks the Gemini key with a free metadata request and prefers the admin key", async () => {
    vi.stubEnv("GEMINI_API_KEY", "env-key");
    vi.stubEnv("GEMINI_IMAGE_MODEL", "env-model");
    const { resolveGeminiImageConfig, saveGemini, geminiSummary } = await import("@/lib/integrations");
    expect(await resolveGeminiImageConfig()).toMatchObject({ apiKey: "env-key", model: "env-model" });
    const calls: string[] = [];
    const ok = vi.fn(async (url: string | URL | Request, init?: RequestInit) => {
      calls.push(`${String(url)} ${new Headers(init?.headers).get("x-goog-api-key")}`);
      return new Response("{}", { status: 200 });
    });
    expect(await saveGemini(admin, { enabled: true, apiKey: "AIza-admin-key", model: "gemini-3.1-flash-image", imageSize: "2K" }, ok as unknown as typeof fetch)).toEqual({ verified: true });
    expect(calls).toEqual(["https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image AIza-admin-key"]);
    expect(await resolveGeminiImageConfig()).toMatchObject({ apiKey: "AIza-admin-key", model: "gemini-3.1-flash-image", imageSize: "2K" });
    expect(await geminiSummary()).toMatchObject({ source: "admin", keyHint: "…-key", lastError: null });
    const denied = vi.fn(async () => new Response("{}", { status: 403 }));
    expect(await saveGemini(admin, { enabled: true, apiKey: "", model: "gemini-3.1-flash-image", imageSize: "1K" }, denied as unknown as typeof fetch)).toMatchObject({ verified: false, error: expect.stringMatching(/rejected/) });
    await saveGemini(admin, { enabled: false, apiKey: "", model: "gemini-3.1-flash-image", imageSize: "1K" });
    expect(await resolveGeminiImageConfig()).toBeNull();
  });
});

describe("R2 backups", () => {
  it("writes encrypted backups under jithendar/backups/, prunes old ones, and refuses odd names", async () => {
    const { listStoredBackups, readStoredBackup, runBackup, saveDestination, saveGeneral } = await import("@/lib/backups");
    await saveGeneral(admin, { schedule: "off", hourUtc: "3", retention: "1", passphrase: "correct horse battery staple" });
    await expect(saveDestination(admin, { enabled: true, bucket: "Bad_Bucket" })).rejects.toThrow(/Bucket names/);
    await saveDestination(admin, { enabled: true, bucket: "jithendar-backups" });
    bucket.set("jithendar-backups/jithendar/backups/jithendar-backup-20200101-000000.json.gz.enc", Buffer.from("old"));
    const r = await runBackup("manual", admin);
    expect(r).toMatchObject({ status: "success", results: [{ destination: "r2", ok: true }] });
    const stored = await listStoredBackups();
    expect(stored).toHaveLength(1);
    expect(stored[0]!.name).toMatch(/^jithendar-backup-\d{8}-\d{6}\.json\.gz\.enc$/);
    expect((await readStoredBackup(stored[0]!.name)).subarray(0, 5).toString()).toBe("JKBK1");
    await expect(readStoredBackup("../../etc/passwd")).rejects.toThrow(/Unknown/);
  });
});
