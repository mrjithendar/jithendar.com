import { SESv2Client, SendEmailCommand } from "@aws-sdk/client-sesv2";
import { eq } from "drizzle-orm";
import nodemailer from "nodemailer";
import { z } from "zod";
import { getDb, schema } from "@/db";
import { audit } from "./audit";
import { log } from "./log";
import type { Actor } from "./posts";
import { PostError } from "./posts";
import { seal, unseal, type Sealed } from "./secrets";

/**
 * Outgoing email (verification, password reset, contact-form notifications).
 *
 * An admin picks one provider in Admin → Storage & email: Disabled, SMTP, Mailgun or Amazon SES. Settings
 * of every provider are kept (secrets encrypted with SETTINGS_ENCRYPTION_KEY), but only the selected one
 * sends; there is no automatic failover. "Configured" (valid settings saved) and "tested" (a test email the
 * admin sent succeeded) are tracked separately; a test is only ever sent when the admin asks for it.
 *
 * Until an admin has saved a choice, the deployment fallback SMTP_URL + MAIL_FROM is used if set.
 */
const EMAIL_KEY = "email";

export const PROVIDERS = ["disabled", "smtp", "mailgun", "ses"] as const;
export type Provider = (typeof PROVIDERS)[number];
export type SendingProvider = Exclude<Provider, "disabled">;
export const providerLabels: Record<Provider, string> = { disabled: "Disabled", smtp: "SMTP", mailgun: "Mailgun", ses: "Amazon SES" };

type Sender = { fromName: string; fromEmail: string; replyTo: string };
type Status = { testedAt: string | null; lastError: string | null };
type SmtpConfig = Sender & Status & { host: string; port: number; security: "tls" | "starttls"; username: string; password: Sealed | null };
type MailgunConfig = Sender & Status & { domain: string; region: "us" | "eu"; apiKey: Sealed };
type SesConfig = Sender & Status & { region: string; auth: "workload" | "keys"; accessKeyId: string; secretAccessKey: Sealed | null; sessionToken: Sealed | null };

export type EmailConfig = { version: 2; active: Provider; smtp: SmtpConfig | null; mailgun: MailgunConfig | null; ses: SesConfig | null };

/** The first format: SES only, active once a test email succeeded. */
type LegacyConfig = { provider: "ses"; region: string; from: string; accessKeyId: string; secretAccessKey: Sealed; verifiedAt: string | null };

// --- Validation ---------------------------------------------------------------------------------------

const email = z.string().trim().toLowerCase().max(254).email("Enter a valid email address.");
const optionalEmail = z.union([z.literal(""), email]);
const displayName = z
  .string()
  .trim()
  .max(80, "Keep the sender name under 80 characters.")
  .refine((v) => !/[<>"\r\n]/.test(v), "The sender name cannot contain < > \" or line breaks.");
const hostname = z
  .string()
  .trim()
  .toLowerCase()
  .min(1, "Enter the host name.")
  .max(253)
  .regex(/^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/, "Enter a host name such as smtp.example.com.");
const sender = { fromName: displayName, fromEmail: email, replyTo: optionalEmail };

export const smtpInput = z.object({
  ...sender,
  host: hostname,
  port: z.coerce.number().int("Enter a port number.").min(1).max(65535),
  security: z.enum(["tls", "starttls"], { message: "Choose TLS or STARTTLS." }),
  username: z.string().trim().max(254).default(""),
  password: z.string().max(1000).default(""),
});
export const mailgunInput = z.object({
  ...sender,
  domain: hostname,
  region: z.enum(["us", "eu"], { message: "Choose the US or EU region." }),
  apiKey: z.string().trim().max(200).default(""),
});
export const sesInput = z.object({
  ...sender,
  region: z.string().trim().regex(/^[a-z]{2}(-[a-z]+)+-\d$/, "Enter an AWS region such as us-east-1."),
  auth: z.enum(["workload", "keys"], { message: "Choose how the site authenticates to AWS." }),
  accessKeyId: z.string().trim().max(128).default(""),
  secretAccessKey: z.string().max(400).default(""),
  sessionToken: z.string().max(4000).default(""),
});

// --- Storage ------------------------------------------------------------------------------------------

function fromLegacy(c: LegacyConfig): EmailConfig {
  const m = /^\s*(?:"?([^"<]*?)"?\s*)?<([^>]+)>\s*$/.exec(c.from);
  return {
    version: 2,
    active: c.verifiedAt ? "ses" : "disabled",
    smtp: null,
    mailgun: null,
    ses: {
      fromName: m?.[1]?.trim() ?? "",
      fromEmail: (m?.[2] ?? c.from).trim(),
      replyTo: "",
      region: c.region,
      auth: "keys",
      accessKeyId: c.accessKeyId,
      secretAccessKey: c.secretAccessKey,
      sessionToken: null,
      testedAt: c.verifiedAt,
      lastError: null,
    },
  };
}

/** The saved configuration, or null when no admin has saved one (then the SMTP_URL fallback applies). */
export async function readEmailConfig(): Promise<EmailConfig | null> {
  try {
    const db = await getDb();
    const [row] = await db.select().from(schema.setting).where(eq(schema.setting.key, EMAIL_KEY));
    const value = row?.value as EmailConfig | LegacyConfig | undefined;
    if (!value) return null;
    return "version" in value && value.version === 2 ? value : fromLegacy(value as LegacyConfig);
  } catch {
    return null;
  }
}

async function writeConfig(actor: Actor, config: EmailConfig) {
  const db = await getDb();
  await db
    .insert(schema.setting)
    .values({ key: EMAIL_KEY, value: config, updatedBy: actor.id })
    .onConflictDoUpdate({ target: schema.setting.key, set: { value: config, updatedBy: actor.id, updatedAt: new Date() } });
}

// --- Status for the admin (never secrets) ---------------------------------------------------------------

export type ProviderSummary = { configured: boolean; testedAt: string | null; lastError: string | null; fields: Record<string, string | number>; secrets: Record<string, boolean> };
export type EmailSummary = {
  active: Provider;
  /** Using the SMTP_URL/MAIL_FROM deployment fallback (no admin choice saved yet). */
  envFallback: boolean;
  providers: Record<SendingProvider, ProviderSummary>;
};

const senderFields = (c: Sender | null) => ({ fromName: c?.fromName ?? "", fromEmail: c?.fromEmail ?? "", replyTo: c?.replyTo ?? "" });

export async function emailSummary(): Promise<EmailSummary> {
  const c = await readEmailConfig();
  const status = (p: Status | null) => ({ configured: !!p, testedAt: p?.testedAt ?? null, lastError: p?.lastError ?? null });
  return {
    active: c?.active ?? "disabled",
    envFallback: !c && envSmtp() !== null,
    providers: {
      smtp: {
        ...status(c?.smtp ?? null),
        fields: { ...senderFields(c?.smtp ?? null), host: c?.smtp?.host ?? "", port: c?.smtp?.port ?? 587, security: c?.smtp?.security ?? "starttls", username: c?.smtp?.username ?? "" },
        secrets: { password: !!c?.smtp?.password },
      },
      mailgun: {
        ...status(c?.mailgun ?? null),
        fields: { ...senderFields(c?.mailgun ?? null), domain: c?.mailgun?.domain ?? "", region: c?.mailgun?.region ?? "us" },
        secrets: { apiKey: !!c?.mailgun?.apiKey },
      },
      ses: {
        ...status(c?.ses ?? null),
        fields: { ...senderFields(c?.ses ?? null), region: c?.ses?.region ?? "us-east-1", auth: c?.ses?.auth ?? "workload", accessKeyId: c?.ses?.accessKeyId ?? "" },
        secrets: { secretAccessKey: !!c?.ses?.secretAccessKey, sessionToken: !!c?.ses?.sessionToken },
      },
    },
  };
}

/** Whether transactional email can be sent right now (the active provider is configured, or the env fallback). */
export async function mailConfigured(): Promise<boolean> {
  const c = await readEmailConfig();
  if (!c) return envSmtp() !== null;
  return c.active !== "disabled" && !!c[c.active];
}

// --- Sending -----------------------------------------------------------------------------------------

export type Message = { to: string; subject: string; text: string };

function envSmtp(): { url: string; from: string } | null {
  const url = process.env.SMTP_URL?.trim();
  const from = process.env.MAIL_FROM?.trim();
  return url && from && /^smtps?:\/\//i.test(url) ? { url, from } : null;
}

const fromHeader = (s: Sender) => (s.fromName ? `"${s.fromName}" <${s.fromEmail}>` : s.fromEmail);

async function sendSmtp(c: SmtpConfig, m: Message) {
  const transport = nodemailer.createTransport({
    host: c.host,
    port: c.port,
    secure: c.security === "tls",
    requireTLS: c.security === "starttls",
    auth: c.username ? { user: c.username, pass: c.password ? unseal(c.password) : "" } : undefined,
    connectionTimeout: 15_000,
    greetingTimeout: 15_000,
    socketTimeout: 30_000,
  });
  await transport.sendMail({ from: fromHeader(c), to: m.to, subject: m.subject, text: m.text, ...(c.replyTo ? { replyTo: c.replyTo } : {}) });
}

/** Mailgun Messages API: POST /v3/{domain}/messages with HTTP basic auth api:{key}; EU domains use api.eu.mailgun.net. */
async function sendMailgun(c: MailgunConfig, m: Message) {
  const base = c.region === "eu" ? "https://api.eu.mailgun.net" : "https://api.mailgun.net";
  const body = new URLSearchParams({ from: fromHeader(c), to: m.to, subject: m.subject, text: m.text });
  if (c.replyTo) body.set("h:Reply-To", c.replyTo);
  const res = await fetch(`${base}/v3/${encodeURIComponent(c.domain)}/messages`, {
    method: "POST",
    headers: { Authorization: `Basic ${Buffer.from(`api:${unseal(c.apiKey)}`).toString("base64")}` },
    body,
    signal: AbortSignal.timeout(20_000),
  });
  if (!res.ok) {
    const detail = (await res.text().catch(() => "")).slice(0, 300);
    const hint = res.status === 401 ? " (check the API key and region)" : res.status === 404 ? " (check the sending domain and region)" : "";
    throw new Error(`Mailgun answered ${res.status}${hint}: ${detail}`);
  }
}

/** SESv2 SendEmail. "workload" uses the AWS SDK default chain (env, web identity / pod identity, instance role). */
async function sendSes(c: SesConfig, m: Message) {
  const credentials =
    c.auth === "keys" && c.secretAccessKey
      ? { accessKeyId: c.accessKeyId, secretAccessKey: unseal(c.secretAccessKey), ...(c.sessionToken ? { sessionToken: unseal(c.sessionToken) } : {}) }
      : undefined;
  const ses = new SESv2Client({ region: c.region, ...(credentials ? { credentials } : {}) });
  await ses.send(
    new SendEmailCommand({
      FromEmailAddress: fromHeader(c),
      Destination: { ToAddresses: [m.to] },
      ...(c.replyTo ? { ReplyToAddresses: [c.replyTo] } : {}),
      Content: { Simple: { Subject: { Data: m.subject, Charset: "UTF-8" }, Body: { Text: { Data: m.text, Charset: "UTF-8" } } } },
    }),
  );
}

async function sendVia(config: EmailConfig, provider: SendingProvider, m: Message) {
  if (provider === "smtp" && config.smtp) return sendSmtp(config.smtp, m);
  if (provider === "mailgun" && config.mailgun) return sendMailgun(config.mailgun, m);
  if (provider === "ses" && config.ses) return sendSes(config.ses, m);
  throw new Error(`${providerLabels[provider]} is not configured.`);
}

/** Remove every stored secret (and its encodings) from an error message before it is shown or logged. */
function redact(message: string, config: EmailConfig | null): string {
  const secrets: string[] = [];
  const add = (s: Sealed | null | undefined) => {
    if (!s) return;
    try {
      const v = unseal(s);
      if (v.length >= 4) secrets.push(v, Buffer.from(`api:${v}`).toString("base64"), encodeURIComponent(v));
    } catch {
      /* unreadable secret: nothing to redact */
    }
  };
  add(config?.smtp?.password);
  add(config?.mailgun?.apiKey);
  add(config?.ses?.secretAccessKey);
  add(config?.ses?.sessionToken);
  let out = message;
  for (const s of secrets) out = out.split(s).join("[redacted]");
  return out.replace(/smtps?:\/\/[^@\s]*@/gi, "smtp://[redacted]@").slice(0, 500);
}

/**
 * Send a transactional email with the active provider. Returns false (and logs) when email is disabled,
 * not configured or the provider fails; callers never break because mail is down. No failover.
 */
export async function sendMail(to: string, subject: string, text: string): Promise<boolean> {
  const config = await readEmailConfig();
  try {
    if (!config) {
      const env = envSmtp();
      if (!env) {
        log.warn("email not configured; message not sent", { subject });
        return false;
      }
      await nodemailer.createTransport(env.url).sendMail({ from: env.from, to, subject, text });
      return true;
    }
    if (config.active === "disabled") {
      log.warn("email disabled; message not sent", { subject });
      return false;
    }
    await sendVia(config, config.active, { to, subject, text });
    return true;
  } catch (error) {
    log.error("mail send failed", { provider: config?.active ?? "env-smtp", subject, error: redact(error instanceof Error ? error.message : String(error), config) });
    return false;
  }
}

// --- Admin actions -----------------------------------------------------------------------------------

export class EmailSettingsError extends PostError {
  constructor(
    message: string,
    readonly fieldErrors: Record<string, string> = {},
  ) {
    super(message, 400, Object.values(fieldErrors));
  }
}

function fieldErrorsOf(error: z.ZodError): Record<string, string> {
  const out: Record<string, string> = {};
  for (const issue of error.issues) out[String(issue.path[0] ?? "form")] ??= issue.message;
  return out;
}

/** Keep the stored secret when the field was left empty; an unchanged config keeps its test result. */
const keep = (input: string, stored: Sealed | null | undefined): Sealed | null => (input ? seal(input) : (stored ?? null));

function sameSettings(a: object | null, b: object): boolean {
  if (!a) return false;
  const strip = (o: object) => JSON.stringify(Object.entries(o).filter(([k]) => !["testedAt", "lastError"].includes(k) && !/password|apiKey|secretAccessKey|sessionToken/.test(k)));
  return strip(a) === strip(b);
}

/**
 * Save the selected provider and its settings (other providers' saved settings are kept). Selecting
 * "disabled" turns email off without forgetting anything. No email is sent here.
 */
export async function saveEmailSettings(actor: Actor, active: unknown, raw: Record<string, unknown>): Promise<EmailSummary> {
  if (actor.role !== "admin") throw new PostError("Only admins can configure email.", 403);
  if (!PROVIDERS.includes(active as Provider)) throw new EmailSettingsError("Choose an email provider.", { provider: "Choose an email provider." });
  const provider = active as Provider;
  const current = (await readEmailConfig()) ?? { version: 2, active: "disabled", smtp: null, mailgun: null, ses: null };
  const next: EmailConfig = { ...current, version: 2, active: provider };
  const changedSecret = (v: unknown) => typeof v === "string" && v.length > 0;

  if (provider === "smtp") {
    const p = smtpInput.safeParse(raw);
    const missing: Record<string, string> = raw.username && !raw.password && !current.smtp?.password ? { password: "Enter the SMTP password." } : {};
    if (!p.success) throw new EmailSettingsError("Check the SMTP settings.", { ...missing, ...fieldErrorsOf(p.error) });
    const password = keep(p.data.password, current.smtp?.password);
    if (p.data.username && !password) throw new EmailSettingsError("Check the SMTP settings.", { password: "Enter the SMTP password." });
    const { password: _pw, ...rest } = p.data;
    void _pw;
    const value: SmtpConfig = { ...rest, password: p.data.username ? password : null, testedAt: null, lastError: null };
    const unchanged = sameSettings(current.smtp, value) && !changedSecret(raw.password);
    next.smtp = unchanged ? { ...value, testedAt: current.smtp!.testedAt, lastError: current.smtp!.lastError } : value;
  } else if (provider === "mailgun") {
    const p = mailgunInput.safeParse(raw);
    const missing: Record<string, string> = !raw.apiKey && !current.mailgun?.apiKey ? { apiKey: "Enter the Mailgun API key." } : {};
    if (!p.success) throw new EmailSettingsError("Check the Mailgun settings.", { ...missing, ...fieldErrorsOf(p.error) });
    const apiKey = keep(p.data.apiKey, current.mailgun?.apiKey);
    if (!apiKey) throw new EmailSettingsError("Check the Mailgun settings.", { apiKey: "Enter the Mailgun API key." });
    const { apiKey: _k, ...rest } = p.data;
    void _k;
    const value: MailgunConfig = { ...rest, apiKey, testedAt: null, lastError: null };
    const unchanged = sameSettings(current.mailgun, value) && !changedSecret(raw.apiKey);
    next.mailgun = unchanged ? { ...value, testedAt: current.mailgun!.testedAt, lastError: current.mailgun!.lastError } : value;
  } else if (provider === "ses") {
    const p = sesInput.safeParse(raw);
    if (!p.success) throw new EmailSettingsError("Check the Amazon SES settings.", fieldErrorsOf(p.error));
    let value: SesConfig;
    if (p.data.auth === "keys") {
      if (!/^(AKIA|ASIA)[A-Z0-9]{12,124}$/.test(p.data.accessKeyId)) throw new EmailSettingsError("Check the Amazon SES settings.", { accessKeyId: "Enter an access key ID (starts with AKIA or ASIA)." });
      const sameKey = current.ses?.accessKeyId === p.data.accessKeyId;
      const secretAccessKey = keep(p.data.secretAccessKey, sameKey ? current.ses?.secretAccessKey : null);
      if (!secretAccessKey) throw new EmailSettingsError("Check the Amazon SES settings.", { secretAccessKey: "Enter the secret access key." });
      // Temporary (ASIA…) keys need their session token; a new token always replaces the old one.
      const sessionToken = p.data.accessKeyId.startsWith("ASIA") ? keep(p.data.sessionToken, sameKey ? current.ses?.sessionToken : null) : null;
      if (p.data.accessKeyId.startsWith("ASIA") && !sessionToken) throw new EmailSettingsError("Check the Amazon SES settings.", { sessionToken: "Temporary keys (ASIA…) need their session token." });
      value = { ...senderOf(p.data), region: p.data.region, auth: "keys", accessKeyId: p.data.accessKeyId, secretAccessKey, sessionToken, testedAt: null, lastError: null };
    } else {
      value = { ...senderOf(p.data), region: p.data.region, auth: "workload", accessKeyId: "", secretAccessKey: null, sessionToken: null, testedAt: null, lastError: null };
    }
    const unchanged = sameSettings(current.ses, value) && !changedSecret(raw.secretAccessKey) && !changedSecret(raw.sessionToken);
    next.ses = unchanged ? { ...value, testedAt: current.ses!.testedAt, lastError: current.ses!.lastError } : value;
  }

  await writeConfig(actor, next);
  await audit(actor, "email.configure", provider, {
    active: provider,
    ...(provider !== "disabled" ? { fromEmail: next[provider]!.fromEmail } : {}),
    ...(provider === "ses" ? { region: next.ses!.region, auth: next.ses!.auth } : {}),
    ...(provider === "mailgun" ? { domain: next.mailgun!.domain, region: next.mailgun!.region } : {}),
    ...(provider === "smtp" ? { host: next.smtp!.host, port: next.smtp!.port } : {}),
  });
  log.info("email settings saved", { provider });
  return emailSummary();
}

const senderOf = (d: Sender): Sender => ({ fromName: d.fromName, fromEmail: d.fromEmail, replyTo: d.replyTo });

/**
 * Send one test email with a provider's saved settings to an address the admin typed. Records the result
 * (tested / last error, secrets redacted) without changing which provider is active.
 */
export async function sendTestEmail(actor: Actor, provider: unknown, to: unknown): Promise<{ ok: true } | { ok: false; error: string }> {
  if (actor.role !== "admin") throw new PostError("Only admins can test email.", 403);
  if (!["smtp", "mailgun", "ses"].includes(provider as string)) throw new EmailSettingsError("Choose a provider to test.", { provider: "Choose a provider to test." });
  const recipient = email.safeParse(to);
  if (!recipient.success) throw new EmailSettingsError("Enter the address to send the test to.", { testTo: recipient.error.issues[0]!.message });
  const p = provider as SendingProvider;
  const config = await readEmailConfig();
  if (!config?.[p]) throw new EmailSettingsError(`Save the ${providerLabels[p]} settings first.`);
  let error: string | null = null;
  try {
    await sendVia(config, p, {
      to: recipient.data,
      subject: "Jithendar.com test email",
      text: `This is a test email from Jithendar.com, sent through ${providerLabels[p]} by an admin from Admin → Storage & email.\n\nIf it reached you, the settings work.`,
    });
  } catch (e) {
    error = redact(e instanceof Error ? e.message : String(e), config);
  }
  const fresh = (await readEmailConfig()) ?? config;
  const entry = fresh[p];
  if (entry) {
    (fresh as Record<SendingProvider, Status | null>)[p] = { ...entry, testedAt: error ? entry.testedAt : new Date().toISOString(), lastError: error };
    await writeConfig(actor, fresh);
  }
  await audit(actor, "email.test", p, { ok: !error });
  return error ? { ok: false, error } : { ok: true };
}
