import { eq } from "drizzle-orm";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { schema, setDbForTests, type Db } from "@/db";
import { freshDb } from "./db-helpers";

vi.mock("server-only", () => ({}));

// SMTP: capture what nodemailer would send.
const smtpSent: { options: Record<string, unknown>; message: Record<string, unknown> }[] = [];
let smtpFails: Error | null = null;
vi.mock("nodemailer", () => ({
  default: {
    createTransport: (options: Record<string, unknown>) => ({
      sendMail: async (message: Record<string, unknown>) => {
        if (smtpFails) throw smtpFails;
        smtpSent.push({ options, message });
      },
    }),
  },
}));

// SES: capture SendEmail input and the client configuration.
const sesSent: { config: Record<string, unknown>; input: Record<string, unknown> }[] = [];
vi.mock("@aws-sdk/client-sesv2", () => ({
  SESv2Client: class {
    constructor(readonly config: Record<string, unknown>) {}
    async send(cmd: { input: Record<string, unknown> }) {
      sesSent.push({ config: this.config, input: cmd.input });
    }
  },
  SendEmailCommand: class {
    constructor(readonly input: Record<string, unknown>) {}
  },
}));

// Mailgun: the HTTP API.
const mailgun = vi.fn(async () => new Response("{}", { status: 200 }));

const admin = { id: "admin", role: "admin" as const, label: "admin@example.com" };
const author = { id: "author", role: "author" as const, label: "author@example.com" };
const sender = { fromName: "Jithendar.com", fromEmail: "no-reply@jithendar.com", replyTo: "" };
const SMTP_PASSWORD = "smtp-pass-0123456789";
const MAILGUN_KEY = "key-mailgun-abcdef0123456789";
const SES_SECRET = "ses/secret+0123456789abcdefABCDEF";

let db: Db;
beforeEach(async () => {
  db = await freshDb();
  smtpSent.length = 0;
  sesSent.length = 0;
  smtpFails = null;
  mailgun.mockReset().mockImplementation(async () => new Response("{}", { status: 200 }));
  vi.stubGlobal("fetch", mailgun);
  vi.stubEnv("SMTP_URL", "");
  vi.stubEnv("MAIL_FROM", "");
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  setDbForTests(undefined);
});

const lib = () => import("@/lib/mail");
async function storedJson() {
  const [row] = await db.select().from(schema.setting).where(eq(schema.setting.key, "email"));
  return JSON.stringify(row?.value ?? null);
}

describe("provider selection and validation", () => {
  it("validates only the selected provider's fields, with per-field messages", async () => {
    const { saveEmailSettings } = await lib();
    await expect(saveEmailSettings(admin, "smtp", { ...sender, host: "not a host", port: "99999", security: "starttls" })).rejects.toMatchObject({
      fieldErrors: { host: expect.any(String), port: expect.any(String) },
    });
    await expect(saveEmailSettings(admin, "mailgun", { ...sender, fromEmail: "nope", domain: "mg.jithendar.com", region: "us" })).rejects.toMatchObject({
      fieldErrors: { fromEmail: "Enter a valid email address.", apiKey: "Enter the Mailgun API key." },
    });
    await expect(saveEmailSettings(admin, "mailgun", { ...sender, domain: "mg.jithendar.com", region: "us", apiKey: "" })).rejects.toMatchObject({
      fieldErrors: { apiKey: "Enter the Mailgun API key." },
    });
    await expect(saveEmailSettings(admin, "ses", { ...sender, region: "useast", auth: "workload" })).rejects.toMatchObject({ fieldErrors: { region: expect.stringMatching(/region/) } });
    await expect(saveEmailSettings(admin, "ses", { ...sender, region: "us-east-1", auth: "keys", accessKeyId: "ASIAEXAMPLE123456789", secretAccessKey: "x".repeat(40) })).rejects.toMatchObject({
      fieldErrors: { sessionToken: expect.stringMatching(/session token/) },
    });
    await expect(saveEmailSettings(admin, "pigeon", {})).rejects.toMatchObject({ fieldErrors: { provider: expect.any(String) } });
    // Nothing invalid was stored.
    expect(await storedJson()).toBe("null");
  });

  it("is admin-only", async () => {
    const { saveEmailSettings, sendTestEmail } = await lib();
    await expect(saveEmailSettings(author, "disabled", {})).rejects.toMatchObject({ status: 403 });
    await expect(sendTestEmail(author, "smtp", "a@example.com")).rejects.toMatchObject({ status: 403 });
  });
});

describe("secrets", () => {
  it("encrypts secrets, never returns them, keeps them when the field is empty, and keeps other providers on switch", async () => {
    const { saveEmailSettings, emailSummary } = await lib();
    await saveEmailSettings(admin, "smtp", { ...sender, host: "smtp.example.com", port: "587", security: "starttls", username: "mailer", password: SMTP_PASSWORD });
    await saveEmailSettings(admin, "mailgun", { ...sender, domain: "mg.jithendar.com", region: "eu", apiKey: MAILGUN_KEY });
    const raw = await storedJson();
    expect(raw).not.toContain(SMTP_PASSWORD);
    expect(raw).not.toContain(MAILGUN_KEY);

    const summary = await emailSummary();
    expect(summary.active).toBe("mailgun");
    expect(summary.providers.smtp).toMatchObject({ configured: true, secrets: { password: true }, fields: { host: "smtp.example.com" } });
    expect(summary.providers.mailgun).toMatchObject({ configured: true, secrets: { apiKey: true } });
    const json = JSON.stringify(summary);
    expect(json).not.toContain(SMTP_PASSWORD);
    expect(json).not.toContain(MAILGUN_KEY);
    expect(json).not.toMatch(/"(iv|tag|data)"/);

    // Re-saving with an empty key keeps the stored one (and still sends with it).
    await saveEmailSettings(admin, "mailgun", { ...sender, domain: "mg.jithendar.com", region: "eu", apiKey: "" });
    const { sendMail } = await lib();
    expect(await sendMail("reader@example.com", "Hi", "Body")).toBe(true);
    const [, init] = mailgun.mock.calls[0] as unknown as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe(`Basic ${Buffer.from(`api:${MAILGUN_KEY}`).toString("base64")}`);
  });

  it("forgets SES keys when switching to the server's AWS credentials", async () => {
    const { saveEmailSettings } = await lib();
    await saveEmailSettings(admin, "ses", { ...sender, region: "us-east-1", auth: "keys", accessKeyId: "AKIAEXAMPLE123456789", secretAccessKey: SES_SECRET });
    await saveEmailSettings(admin, "ses", { ...sender, region: "us-east-1", auth: "workload" });
    const raw = JSON.parse(await storedJson());
    expect(raw.ses).toMatchObject({ auth: "workload", accessKeyId: "", secretAccessKey: null, sessionToken: null });
  });
});

describe("routing transactional email", () => {
  it("sends only through the active provider, with sender and reply-to; never fails over", async () => {
    const { saveEmailSettings, sendMail } = await lib();
    await saveEmailSettings(admin, "smtp", { ...sender, replyTo: "hello@jithendar.com", host: "smtp.example.com", port: "465", security: "tls", username: "mailer", password: SMTP_PASSWORD });
    expect(await sendMail("reader@example.com", "Verify", "Click")).toBe(true);
    expect(smtpSent[0]!.options).toMatchObject({ host: "smtp.example.com", port: 465, secure: true, auth: { user: "mailer", pass: SMTP_PASSWORD } });
    expect(smtpSent[0]!.message).toMatchObject({ from: '"Jithendar.com" <no-reply@jithendar.com>', to: "reader@example.com", replyTo: "hello@jithendar.com" });

    await saveEmailSettings(admin, "ses", { ...sender, region: "eu-west-1", auth: "keys", accessKeyId: "AKIAEXAMPLE123456789", secretAccessKey: SES_SECRET });
    expect(await sendMail("reader@example.com", "Reset", "Link")).toBe(true);
    expect(sesSent).toHaveLength(1);
    expect(sesSent[0]!.config).toMatchObject({ region: "eu-west-1", credentials: { accessKeyId: "AKIAEXAMPLE123456789", secretAccessKey: SES_SECRET } });
    expect(smtpSent).toHaveLength(1);

    // SES with the server's credentials: no credentials passed (AWS SDK default chain).
    await saveEmailSettings(admin, "ses", { ...sender, region: "eu-west-1", auth: "workload" });
    await sendMail("reader@example.com", "Reset", "Link");
    expect(sesSent[1]!.config).not.toHaveProperty("credentials");

    // A failing provider does not hand over to another one.
    await saveEmailSettings(admin, "smtp", { ...sender, host: "smtp.example.com", port: "587", security: "starttls", username: "mailer", password: "" });
    smtpFails = new Error("connection refused");
    expect(await sendMail("reader@example.com", "Verify", "Click")).toBe(false);
    expect(sesSent).toHaveLength(2);
    expect(mailgun).not.toHaveBeenCalled();
  });

  it("sends nothing when disabled, and uses SMTP_URL only until an admin has chosen", async () => {
    const { saveEmailSettings, sendMail, mailConfigured } = await lib();
    vi.stubEnv("SMTP_URL", "smtps://user:pw@smtp.example.com:465");
    vi.stubEnv("MAIL_FROM", "Jithendar.com <no-reply@jithendar.com>");
    expect(await mailConfigured()).toBe(true);
    expect(await sendMail("a@example.com", "S", "T")).toBe(true);
    expect(smtpSent).toHaveLength(1);
    await saveEmailSettings(admin, "disabled", {});
    expect(await mailConfigured()).toBe(false);
    expect(await sendMail("a@example.com", "S", "T")).toBe(false);
    expect(smtpSent).toHaveLength(1);
  });

  it("ignores a malformed SMTP_URL instead of trying to send with it", async () => {
    const { sendMail, mailConfigured } = await lib();
    vi.stubEnv("SMTP_URL", "jithendar.com:587");
    vi.stubEnv("MAIL_FROM", "no-reply@jithendar.com");
    expect(await mailConfigured()).toBe(false);
    expect(await sendMail("a@example.com", "S", "T")).toBe(false);
  });
});

describe("test email", () => {
  it("sends only on request, to the given address, and records tested vs failed with secrets redacted", async () => {
    const { saveEmailSettings, sendTestEmail, emailSummary } = await lib();
    await saveEmailSettings(admin, "mailgun", { ...sender, domain: "mg.jithendar.com", region: "us", apiKey: MAILGUN_KEY });
    expect(mailgun).not.toHaveBeenCalled();
    expect((await emailSummary()).providers.mailgun).toMatchObject({ configured: true, testedAt: null });

    await expect(sendTestEmail(admin, "mailgun", "not-an-email")).rejects.toMatchObject({ fieldErrors: { testTo: expect.any(String) } });
    expect(await sendTestEmail(admin, "mailgun", "me@example.com")).toEqual({ ok: true });
    const [url, init] = mailgun.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("https://api.mailgun.net/v3/mg.jithendar.com/messages");
    expect(String(init.body)).toContain("to=me%40example.com");
    expect((await emailSummary()).providers.mailgun.testedAt).not.toBeNull();

    mailgun.mockImplementation(async () => new Response(`Forbidden for ${MAILGUN_KEY}`, { status: 401 }));
    const failed = await sendTestEmail(admin, "mailgun", "me@example.com");
    expect(failed.ok).toBe(false);
    expect(!failed.ok && failed.error).toMatch(/401.*check the API key/);
    expect(!failed.ok && failed.error).not.toContain(MAILGUN_KEY);
    const s = (await emailSummary()).providers.mailgun;
    expect(s.lastError).toContain("[redacted]");
    expect(await storedJson()).not.toContain(MAILGUN_KEY);

    // Testing a provider never changes which one is active; audit entries carry no secrets.
    expect((await emailSummary()).active).toBe("mailgun");
    const auditRows = await db.select().from(schema.auditLog);
    expect(auditRows.map((a) => a.action)).toEqual(expect.arrayContaining(["email.configure", "email.test"]));
    expect(JSON.stringify(auditRows)).not.toContain(MAILGUN_KEY);
  });

  it("refuses to test a provider that has no saved settings", async () => {
    const { sendTestEmail } = await lib();
    await expect(sendTestEmail(admin, "ses", "me@example.com")).rejects.toThrow(/Save the Amazon SES settings first/);
  });
});

describe("existing configuration", () => {
  it("reads the earlier SES-only settings as Amazon SES", async () => {
    const { seal } = await import("@/lib/secrets");
    await db.insert(schema.setting).values({
      key: "email",
      value: { provider: "ses", region: "us-east-1", from: "Jithendar.com <no-reply@jithendar.com>", accessKeyId: "AKIAEXAMPLE123456789", secretAccessKey: seal(SES_SECRET), verifiedAt: "2026-10-28T10:00:00.000Z" },
    });
    const { emailSummary, sendMail } = await lib();
    const s = await emailSummary();
    expect(s.active).toBe("ses");
    expect(s.providers.ses).toMatchObject({ testedAt: "2026-10-28T10:00:00.000Z", fields: { fromName: "Jithendar.com", fromEmail: "no-reply@jithendar.com", auth: "keys" } });
    expect(await sendMail("a@example.com", "S", "T")).toBe(true);
    expect(sesSent[0]!.config).toMatchObject({ credentials: { secretAccessKey: SES_SECRET } });
  });
});
