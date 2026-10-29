# Email (SMTP, Mailgun, Amazon SES)

Transactional email: sign-up verification, password-reset links and contact-form notifications to admins.
Configured in **Admin → Storage & email → Email** (admins only). Code: `src/lib/mail.ts`,
`src/app/admin/storage/EmailSettings.tsx`, `src/app/admin/storage/email-actions.ts`.

## How it works

- **One active provider**: Disabled, SMTP, Mailgun or Amazon SES. Only that one sends; there is **no automatic
  failover**. Settings of the other providers are kept, so switching back needs no re-entry.
- **Secrets** (SMTP password, Mailgun API key, SES secret key and session token) are encrypted in the database
  with `SETTINGS_ENCRYPTION_KEY` (AES-256-GCM) and never sent to the browser. The form only shows "Saved. Leave
  empty to keep it."; an empty field keeps the stored secret. Secrets are removed from error messages, logs and
  audit entries.
- **Configured vs tested**: saving validates and stores the settings and makes the provider active, but sends
  nothing. **Send test email** (with an explicit recipient) sends one real message through the saved settings
  and records "tested" or "test failed" with the provider's error. Changing the settings clears the test result.
  Test emails count toward provider usage/quotas.
- **Before an admin saves anything**, the deployment fallback `SMTP_URL` + `MAIL_FROM` (Secret
  `jithendar-com-env`) is used if `SMTP_URL` is a valid `smtp://` or `smtps://` URL. Once a choice is saved in the
  admin, it always wins (choose Disabled to turn email off).
- Audit log: `email.configure` (provider, sender, host/domain/region; never secrets) and `email.test` (result).
- Admin → System status shows the active provider and the last test result (no email is sent by the check).

## SMTP

| Field | Notes |
|---|---|
| Host, Port | e.g. `smtp.example.com`, 587 |
| Encryption | STARTTLS (587, required, no plaintext fallback) or TLS from the start (465). Unencrypted SMTP is not offered |
| Username, Password | Optional only if the server allows unauthenticated relay from the cluster |
| Sender email | An address the server may send as |

Configure SPF/DKIM for the sender domain as your SMTP provider documents.

## Mailgun

1. Mailgun → **Sending → Domains → Add new domain**, e.g. `mg.jithendar.com` (a subdomain keeps the root
   domain's mail reputation separate). Choose the **US or EU region**; the site must use the same region
   (`api.mailgun.net` or `api.eu.mailgun.net`).
2. Add the DNS records Mailgun shows at your DNS provider: the **SPF** `TXT` (`v=spf1 include:mailgun.org ~all`),
   the **DKIM** `TXT` (`…._domainkey`), and optionally `MX` and the tracking `CNAME`. Wait until Mailgun shows the
   domain as **Verified**.
3. Domain settings → **Sending API keys** → create a key for this domain (a domain sending key, not the account
   key). Paste it into **API key**.
4. Sender email: an address on that domain, e.g. `no-reply@mg.jithendar.com`.
5. Save, then **Send test email**. Errors: `401` = wrong key or region, `404` = wrong domain or region.

## Amazon SES

1. SES console (in the region you will use, e.g. `us-east-1`) → **Identities → Create identity**: the domain
   `jithendar.com` (recommended) or one address. For a domain, add the three **Easy DKIM** `CNAME` records; for a
   custom MAIL FROM domain also its `MX` and SPF `TXT`. Wait for **Verified**.
2. **Sandbox**: new SES accounts can only send to verified addresses and 200 emails a day. Until you request
   **production access** (SES → Account dashboard → Request production access), readers' verification and reset
   emails will be rejected. Verify your own address to test in the sandbox.
3. Authentication, one of:
   - **The server's AWS credentials** (preferred): an IAM role through pod identity / IRSA / instance profile, or
     `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` in the pod environment. Nothing secret is stored in the site.
     On the mk4 Minikube cluster there is no workload identity, so this needs the env variables in
     `jithendar-com-env`.
   - **Access keys stored here**: an IAM user (`AKIA…`) or temporary credentials (`ASIA…` + session token;
     these expire, so prefer a role for long-term use).
   Minimal IAM policy:
   ```json
   { "Version": "2012-10-17", "Statement": [{ "Effect": "Allow", "Action": ["ses:SendEmail", "ses:SendRawEmail"],
     "Resource": "*", "Condition": { "StringEquals": { "ses:FromAddress": "no-reply@jithendar.com" } } }] }
   ```
4. Sender email: the verified address or any address on the verified domain.
5. Save, then **Send test email**. `MessageRejected: Email address is not verified` in the sandbox means the
   recipient (or sender) is not verified yet.

## DMARC

Whatever the provider, publish a DMARC record once SPF and DKIM pass, starting with monitoring:
`_dmarc.jithendar.com TXT "v=DMARC1; p=none; rua=mailto:dmarc@jithendar.com"`.

## Network

The site's NetworkPolicy already allows egress to HTTPS (Mailgun and SES APIs) and to SMTP ports 465 and 587.
Another SMTP port would need adding to `deploy/base/networkpolicy.yaml` and `k8s/30-jithendar-com.yaml`.

## Tests

`tests/mail.test.ts`: per-provider validation, admin-only access, encrypted and never-returned secrets, empty
secret keeps the stored one, provider switching keeps settings, routing to the active provider only (SMTP, SES
with keys or default credentials, Mailgun), no failover, disabled sends nothing, `SMTP_URL` fallback only before a
choice, malformed `SMTP_URL` ignored, test email on request with redacted errors, legacy SES settings.
