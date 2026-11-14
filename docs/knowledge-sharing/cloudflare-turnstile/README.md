# Cloudflare Turnstile tutorial: review notes

Draft: `content/blog/cloudflare-turnstile-nextjs-bot-protection.mdx` (`status: review`, not published).
Written 2026-11-03 against commit `dc249e8`. None of the Turnstile source files had uncommitted changes at that time, so the GitHub links pinned to `dc249e8` match the code shown.

## Publishing metadata

| Field | Value |
|---|---|
| Suggested slug | `cloudflare-turnstile-nextjs-bot-protection` |
| Title | How I Implemented Cloudflare Turnstile on jithendar.com |
| SEO title (73 chars) | Cloudflare Turnstile Tutorial: Bot Protection in Next.js with Better Auth |
| Meta description (151 chars) | A Cloudflare Turnstile tutorial for Next.js: how jithendar.com renders the widget, verifies tokens with Siteverify, and where its bot protection stops. |
| Excerpt | The schema has no `excerpt` field; listings use `description`. Suggested longer excerpt for social or newsletter use: "A step-by-step walk through Cloudflare Turnstile on a real Next.js site: loading the widget in React, verifying tokens on the server with Siteverify and Better Auth, handling failures, testing with Cloudflare's dummy keys, and the gaps found along the way." |
| Category | `cybersecurity` |
| Related | `projects/nextjs-site-on-kubernetes` |

Internal links in the article: `/contact`, `/projects/nextjs-site-on-kubernetes`. Both returned HTTP 200 on jithendar.com on 2026-11-03 (GET only). `/cookies` returned 404 and is not linked.

Live posts are stored in Postgres, so this MDX file only becomes a live post through the normal import and review flow.

## Source files used

- `src/components/Turnstile.tsx`: widget component
- `src/components/ContactForm.tsx`: contact form
- `src/app/login/LoginForm.tsx`, `src/app/login/page.tsx`: sign-in and sign-up
- `src/app/[page]/page.tsx`: renders the contact form on `/contact`
- `src/app/_actions/public.ts`: contact server action and `clientIp()`
- `src/lib/turnstile.ts`: key resolution and `verifyTurnstile()`
- `src/lib/contact.ts`: `submitContact()`
- `src/lib/auth.ts`: Better Auth `captcha` plugin, rate limits, origin check
- `src/app/api/auth/[...all]/route.ts`, `src/lib/auth-audit.ts`, `src/lib/security.ts`: auditing of captcha failures
- `src/lib/runtime-settings.ts`: admin-stored keys, sealing, `effectiveEnv()`
- `src/lib/health.ts`, `src/lib/dashboard.ts`, `src/app/admin/**`: status reporting
- `src/config/site.ts` (`isProductionEnv`), `Dockerfile`, `../k8s/30-jithendar-com.yaml` (`APP_ENV`)
- `../scripts/create-secrets.sh`, `docs/DEPLOYMENT.md`, `docs/AUTH.md`, `docs/COMMENTS.md`
- `content/pages/privacy-policy.mdx`, `content/pages/cookies.mdx`, `content/projects/nextjs-site-on-kubernetes.mdx`
- `tests/social-auth.test.ts`, `tests/security-admin.test.ts`, `tests/discussions.test.ts`
- `node_modules/better-auth/dist/plugins/captcha/**` and `dist/api/routes/email-verification.mjs` (better-auth 1.7.14)
- `node_modules/next/dist/docs/01-app/02-guides/server-actions.md` (Origin/Host check)

Versions confirmed from `node_modules`: Next.js 16.4.3, React 19.3.1, TypeScript 6.0.3, better-auth 1.7.14.

## Cloudflare documentation checked (2026-11-03)

- https://developers.cloudflare.com/turnstile/
- https://developers.cloudflare.com/turnstile/concepts/widget/
- https://developers.cloudflare.com/turnstile/get-started/client-side-rendering/
- https://developers.cloudflare.com/turnstile/get-started/client-side-rendering/widget-configurations/
- https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
- https://developers.cloudflare.com/turnstile/troubleshooting/testing/

## Validation

| Check | Result |
|---|---|
| All 10 "Actual project code" snippets compared line by line with their source files | Every line matches |
| Frontmatter and MDX compile (`loadContent` + `compileMdx`, in a temporary test) | Pass |
| Section 9 Vitest example, run as a temporary file in `tests/` and then deleted | 4/4 pass (3 from the article plus one success control) |
| `npx vitest run tests/content.test.ts tests/links.test.ts`, before another draft appeared | 13/13 pass |
| Full `npm test` | 7 failures in 6 files, all caused by `content/blog/mermaid-diagrams-on-jithendar-com.mdx` (description over 160 chars). That file belongs to another session and was not touched. A copy of `content/` without that file validates with this draft included. |
| `npm run lint`, `npm run typecheck`, `npm run build` | Not run: no application code changed, and ESLint/tsc do not check MDX |

## Limitations

- Not tested in a browser: Mermaid diagram rendering, widget behaviour on expiry (`refresh-expired: auto`), and the compact size switch.
- The `curl` example in section 9 was not run (no local dev server or database running). The Origin header may need adjusting to your local `SITE_URL`.
- The widget mode (Managed, Non-interactive or Invisible) is set in the Cloudflare dashboard and cannot be confirmed from the repository.
- No real forms were submitted and no production settings were read or changed.

## Security and UX gaps (also listed in the article, section 10)

1. No `hostname` check on Siteverify results in either path (`verifyTurnstile()`; the `captcha()` plugin has no `allowedHostnames`).
2. Signed-in users skip Turnstile on the contact form, including Google and GitHub accounts that never saw the widget. The code comment in `src/lib/contact.ts` ("sign-in already passed one") is true only for email sign-in.
3. The contact per-sender limit counts the *submitted* email, which the sender controls. The site-wide limit of 100 per hour can be filled by an attacker, which then blocks legitimate senders. Count-then-insert is not atomic.
4. `POST /api/auth/send-verification-email` sends email without a session and without Turnstile. Only the global rate limit (100 per 60 s) applies.
5. `clientIp()` trusts the first `X-Forwarded-For` value (only used as the optional `remoteip`).
6. Test-key fallback depends on `APP_ENV=production`. A public non-production deployment without keys accepts every request.
7. `verifyTurnstile()` logs nothing on failure, so contact-form outages and attacks look the same.
8. No unit test covers `verifyTurnstile()`.
9. UX: no specific message when the widget script fails to load; Cloudflare outages show as "complete the human verification again" on the contact form.
10. Stale text says comments use Turnstile: `content/pages/privacy-policy.mdx`, `content/pages/cookies.mdx`, the Turnstile group description in `src/lib/runtime-settings.ts`, and the health message in `src/lib/health.ts`.
11. Minor: in `loadScript()`, if an existing script tag has already fired `error`, a new caller waits forever (the event will not fire again).
