"use client";

import { startTransition, useActionState, useState, type FormEvent } from "react";
import { StatusPill } from "@/components/admin/ui";
import { PasswordInput } from "@/components/ui/PasswordInput";
import { Alert, Button, Field, Input, Select } from "@/components/ui/form";
import type { EmailSummary, Provider, SendingProvider } from "@/lib/mail";
import { saveEmailAction, testEmailAction, type EmailFormState } from "./email-actions";

const LABELS: Record<Provider, string> = { disabled: "Disabled", smtp: "SMTP", mailgun: "Mailgun", ses: "Amazon SES" };

/**
 * Admin → Storage & email → Email. One provider selector; only the selected provider's fields are shown and
 * submitted. Stored secrets are never sent to the browser: the page only knows whether one is saved.
 */
export function EmailSettings({ initial, adminEmail }: { initial: EmailSummary; adminEmail: string }) {
  const [state, save, saving] = useActionState<EmailFormState, FormData>(saveEmailAction, {});
  const [testState, test, testing] = useActionState<EmailFormState, FormData>(testEmailAction, {});
  const summary = state.summary ?? initial;
  const [provider, setProvider] = useState<Provider>(initial.active);
  const [sesAuth, setSesAuth] = useState(String(initial.providers.ses.fields.auth));
  const errors = state.fieldErrors ?? {};
  const p = provider === "disabled" ? null : summary.providers[provider];
  const f = (name: string) => String(p?.fields[name] ?? "");
  const err = (name: string) => errors[name];
  const described = (name: string) => (errors[name] ? { "aria-invalid": true as const, "aria-describedby": `email-${name}-error` } : {});
  const keepHint = (has: boolean | undefined) => (has ? "Saved. Leave empty to keep it." : undefined);
  // Submit without React's automatic form reset: a validation error must keep what was typed, and the
  // controlled provider/auth selects must not snap back to their first option.
  const submitWith = (action: (data: FormData) => void) => (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    startTransition(() => action(data));
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2 text-sm text-fg-muted">
        <span>Active:</span>
        <strong className="text-fg">{summary.envFallback ? "SMTP from the deployment (SMTP_URL)" : LABELS[summary.active]}</strong>
        {summary.active !== "disabled" && <ProviderStatus s={summary.providers[summary.active as SendingProvider]} />}
      </div>

      <form onSubmit={submitWith(save)} className="space-y-5" noValidate key={summary.active + JSON.stringify(summary.providers[provider === "disabled" ? "smtp" : provider].fields)}>
        <Field label="Email provider" htmlFor="email-provider" hint="Only the selected provider sends email. Settings of the others are kept; there is no automatic failover.">
          <Select id="email-provider" name="provider" value={provider} onChange={(e) => setProvider(e.target.value as Provider)}>
            {(Object.keys(LABELS) as Provider[]).map((k) => (
              <option key={k} value={k}>
                {LABELS[k]}
                {k !== "disabled" && summary.providers[k as SendingProvider].configured ? " (configured)" : ""}
              </option>
            ))}
          </Select>
        </Field>

        {provider === "disabled" && <Alert tone="info">No email is sent: sign-up verification, password resets and contact notifications are skipped.</Alert>}

        {provider !== "disabled" && (
          <fieldset className="grid gap-4 sm:grid-cols-2">
            <legend className="mb-2 text-sm font-semibold text-fg sm:col-span-2">Sender</legend>
            <Field label="Sender name" htmlFor="email-fromName" optional error={err("fromName")}>
              <Input id="email-fromName" name="fromName" defaultValue={f("fromName")} placeholder="Jithendar.com" maxLength={80} {...described("fromName")} />
            </Field>
            <Field
              label="Sender email"
              htmlFor="email-fromEmail"
              error={err("fromEmail")}
              hint={provider === "ses" ? "A verified SES identity (the address or its domain)." : provider === "mailgun" ? "An address on the Mailgun sending domain." : "An address your SMTP server may send as."}
            >
              <Input id="email-fromEmail" name="fromEmail" type="email" defaultValue={f("fromEmail")} placeholder="no-reply@jithendar.com" required {...described("fromEmail")} />
            </Field>
            <Field label="Reply-to address" htmlFor="email-replyTo" optional error={err("replyTo")} hint="Where replies go, if not the sender.">
              <Input id="email-replyTo" name="replyTo" type="email" defaultValue={f("replyTo")} {...described("replyTo")} />
            </Field>
          </fieldset>
        )}

        {provider === "smtp" && (
          <fieldset className="grid gap-4 sm:grid-cols-2">
            <legend className="mb-2 text-sm font-semibold text-fg sm:col-span-2">SMTP server</legend>
            <Field label="Host" htmlFor="email-host" error={err("host")}>
              <Input id="email-host" name="host" defaultValue={f("host")} placeholder="smtp.example.com" required autoComplete="off" {...described("host")} />
            </Field>
            <Field label="Port" htmlFor="email-port" error={err("port")} hint="587 for STARTTLS, 465 for TLS.">
              <Input id="email-port" name="port" type="number" inputMode="numeric" min={1} max={65535} defaultValue={f("port") || "587"} required {...described("port")} />
            </Field>
            <Field label="Encryption" htmlFor="email-security" error={err("security")}>
              <Select id="email-security" name="security" defaultValue={f("security") || "starttls"}>
                <option value="starttls">STARTTLS (usually port 587)</option>
                <option value="tls">TLS from the start (usually port 465)</option>
              </Select>
            </Field>
            <Field label="Username" htmlFor="email-username" optional error={err("username")}>
              <Input id="email-username" name="username" defaultValue={f("username")} autoComplete="off" {...described("username")} />
            </Field>
            <Field label="Password" htmlFor="email-password" error={err("password")} hint={keepHint(p?.secrets.password)}>
              <PasswordInput id="email-password" name="password" autoComplete="new-password" {...described("password")} />
            </Field>
          </fieldset>
        )}

        {provider === "mailgun" && (
          <fieldset className="grid gap-4 sm:grid-cols-2">
            <legend className="mb-2 text-sm font-semibold text-fg sm:col-span-2">Mailgun</legend>
            <Field label="Sending domain" htmlFor="email-domain" error={err("domain")} hint="The verified domain in Mailgun, e.g. mg.jithendar.com.">
              <Input id="email-domain" name="domain" defaultValue={f("domain")} placeholder="mg.jithendar.com" required autoComplete="off" {...described("domain")} />
            </Field>
            <Field label="API region" htmlFor="email-region" error={err("region")} hint="The region the domain was created in.">
              <Select id="email-region" name="region" defaultValue={f("region") || "us"}>
                <option value="us">US (api.mailgun.net)</option>
                <option value="eu">EU (api.eu.mailgun.net)</option>
              </Select>
            </Field>
            <Field label="API key" htmlFor="email-apiKey" error={err("apiKey")} hint={keepHint(p?.secrets.apiKey) ?? "A sending key for this domain (Mailgun → Domain settings → Sending keys)."}>
              <PasswordInput id="email-apiKey" name="apiKey" autoComplete="off" {...described("apiKey")} />
            </Field>
          </fieldset>
        )}

        {provider === "ses" && (
          <fieldset className="grid gap-4 sm:grid-cols-2">
            <legend className="mb-2 text-sm font-semibold text-fg sm:col-span-2">Amazon SES</legend>
            <Field label="AWS region" htmlFor="email-region" error={err("region")} hint="Where the identity is verified, e.g. us-east-1.">
              <Input id="email-region" name="region" defaultValue={f("region") || "us-east-1"} required autoComplete="off" {...described("region")} />
            </Field>
            <Field label="Authentication" htmlFor="email-auth" error={err("auth")}>
              <Select id="email-auth" name="auth" value={sesAuth} onChange={(e) => setSesAuth(e.target.value)}>
                <option value="workload">The server&apos;s AWS credentials (role / environment)</option>
                <option value="keys">Access keys stored here (encrypted)</option>
              </Select>
            </Field>
            {sesAuth === "workload" ? (
              <p className="text-sm text-fg-subtle sm:col-span-2">
                Uses the AWS SDK default chain on the server: an IAM role (pod identity / IRSA / instance profile) or AWS_* environment variables. Nothing secret is stored here. Needs <code>ses:SendEmail</code>.
              </p>
            ) : (
              <>
                <Field label="Access key ID" htmlFor="email-accessKeyId" error={err("accessKeyId")} hint="An IAM user or role limited to ses:SendEmail.">
                  <Input id="email-accessKeyId" name="accessKeyId" defaultValue={f("accessKeyId")} autoComplete="off" {...described("accessKeyId")} />
                </Field>
                <Field label="Secret access key" htmlFor="email-secretAccessKey" error={err("secretAccessKey")} hint={keepHint(p?.secrets.secretAccessKey)}>
                  <PasswordInput id="email-secretAccessKey" name="secretAccessKey" autoComplete="off" {...described("secretAccessKey")} />
                </Field>
                <Field
                  label="Session token"
                  htmlFor="email-sessionToken"
                  optional
                  error={err("sessionToken")}
                  hint={keepHint(p?.secrets.sessionToken) ?? "Only for temporary keys (ASIA…). They expire; prefer the server's role for long-term use."}
                >
                  <PasswordInput id="email-sessionToken" name="sessionToken" autoComplete="off" {...described("sessionToken")} />
                </Field>
              </>
            )}
          </fieldset>
        )}

        {state.error && <Alert>{state.error}</Alert>}
        {state.ok && <Alert tone="success">{state.ok}</Alert>}
        <Button type="submit" loading={saving}>
          {saving ? "Saving…" : provider === "disabled" ? "Turn email off" : `Save and use ${LABELS[provider]}`}
        </Button>
      </form>

      {provider !== "disabled" && summary.providers[provider].configured && (
        <form onSubmit={submitWith(test)} className="space-y-4 border-t border-line pt-6">
          <input type="hidden" name="provider" value={provider} />
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-semibold text-fg">Test {LABELS[provider]}</h3>
            <ProviderStatus s={summary.providers[provider]} />
          </div>
          <p className="text-sm text-fg-muted">Sends one real email with the saved {LABELS[provider]} settings (counts toward provider usage). Nothing is sent until you click.</p>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="sm:w-96">
              <Field label="Send the test to" htmlFor="email-testTo" error={testState.fieldErrors?.testTo}>
                <Input id="email-testTo" name="testTo" type="email" defaultValue={adminEmail} required />
              </Field>
            </div>
            <Button type="submit" variant="secondary" loading={testing}>
              {testing ? "Sending…" : "Send test email"}
            </Button>
          </div>
          {testState.error && <Alert>{testState.error}</Alert>}
          {testState.ok && <Alert tone="success">{testState.ok}</Alert>}
        </form>
      )}
    </div>
  );
}

function ProviderStatus({ s }: { s: { configured: boolean; testedAt: string | null; lastError: string | null } }) {
  if (!s.configured) return <StatusPill status="not configured" />;
  if (s.lastError) return <span title={s.lastError}><StatusPill status="test failed" /></span>;
  return s.testedAt ? <StatusPill status="tested" /> : <StatusPill status="configured" />;
}
