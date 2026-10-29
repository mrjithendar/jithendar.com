import { PasswordInput } from "@/components/ui/PasswordInput";
import { Flash, type FlashParams } from "@/components/admin/Flash";
import { AdminHeader, Card, StatusPill } from "@/components/admin/ui";
import { Alert, Button, Field, Input, Select } from "@/components/ui/form";
import { isProductionEnv, siteUrl } from "@/config/site";
import { adminActor } from "@/lib/admin";
import { callbackUrl, providerLabels, SOCIAL_PROVIDERS, type SocialProvider } from "@/lib/auth-providers";
import { formatDateTime } from "@/lib/dates";
import { flash } from "@/lib/flash";
import { IMAGE_SIZES } from "@/lib/gemini";
import { audit } from "@/lib/audit";
import { queueSitemapForIndexNow } from "@/lib/indexnow";
import { geminiSummary, indexNowSummary, removeGeminiKey, resetSocialProvider, saveGemini, saveSocialProvider, setIndexNow, socialSummary } from "@/lib/integrations";
import { PostError } from "@/lib/posts";
import { requireRole } from "@/lib/session";
import { storageReady } from "@/lib/storage";

export const metadata = { title: "Integrations" };

const BACK = "/admin/integrations";

const CONSOLE: Record<SocialProvider, { href: string; label: string; steps: string }> = {
  google: {
    href: "https://console.cloud.google.com/apis/credentials",
    label: "Google Cloud console → APIs & Services → Credentials",
    steps: "Create an OAuth client ID of type “Web application”, add the redirect URI below, and keep the consent screen to the email and profile scopes.",
  },
  github: {
    href: "https://github.com/settings/developers",
    label: "GitHub → Settings → Developer settings → OAuth Apps",
    steps: "Register a new OAuth App with this site as the homepage and the callback URL below, then generate a client secret.",
  },
};

async function saveProvider(form: FormData) {
  "use server";
  const actor = await adminActor();
  const provider = String(form.get("provider")) as SocialProvider;
  await flash(BACK, async () => {
    if (form.get("intent") === "reset") {
      await resetSocialProvider(actor, provider);
      return `${providerLabels[provider]} now follows the deployment's environment variables.`;
    }
    await saveSocialProvider(actor, provider, { enabled: form.has("enabled"), clientId: String(form.get("clientId") ?? ""), clientSecret: String(form.get("clientSecret") ?? "") });
    return form.has("enabled") ? `${providerLabels[provider]} sign-in is on.` : `${providerLabels[provider]} sign-in is off.`;
  });
}

async function saveImageGeneration(form: FormData) {
  "use server";
  const actor = await adminActor();
  await flash(BACK, async () => {
    if (form.get("intent") === "reset") {
      await removeGeminiKey(actor);
      return "Gemini settings removed. Environment variables apply again, if set.";
    }
    const r = await saveGemini(actor, { enabled: form.has("enabled"), apiKey: String(form.get("apiKey") ?? ""), model: String(form.get("model") ?? ""), imageSize: String(form.get("imageSize") ?? "1K") });
    if (r.error) throw new PostError(`Saved, but the key check failed: ${r.error} “Generate image” stays available; requests will fail until this is fixed.`);
    return r.verified ? "Gemini key verified and saved. “Generate image” is available in the editor." : "Image generation is off.";
  });
}

async function indexNowAction(form: FormData) {
  "use server";
  const actor = await adminActor();
  const intent = String(form.get("intent"));
  await flash(BACK, async () => {
    if (intent === "submit-all") {
      const { queued, total } = await queueSitemapForIndexNow();
      await audit(actor, "integrations.indexnow.submit", undefined, { queued, total });
      return queued > 0 ? `${queued} of ${total} sitemap URLs queued for IndexNow; they are sent within a minute.` : "Nothing queued: IndexNow is off, or this is not the production site.";
    }
    await setIndexNow(actor, intent !== "off", { regenerate: intent === "regenerate" });
    return intent === "off" ? "IndexNow is off." : intent === "regenerate" ? "New IndexNow key generated." : "IndexNow is on. Publishing and updating posts now notifies Bing and other IndexNow engines.";
  });
}

const SOURCE: Record<string, string> = { admin: "Set here", env: "From environment", none: "Not configured" };

export default async function IntegrationsPage({ searchParams }: { searchParams: FlashParams }) {
  await requireRole("admin");
  const [social, gemini, indexNow, storage, sp] = await Promise.all([socialSummary(), geminiSummary(), indexNowSummary(), storageReady(), searchParams]);
  const origin = siteUrl();

  return (
    <>
      <AdminHeader
        title="Integrations"
        description="Social sign-in and AI image generation. Secrets are encrypted at rest (SETTINGS_ENCRYPTION_KEY) and never shown again; leave a secret field empty to keep the stored value."
      />
      <Flash ok={sp.ok} error={sp.error} />
      <div className="space-y-6">
        <section aria-labelledby="social-title" className="space-y-4">
          <div>
            <h2 id="social-title" className="text-lg font-semibold text-fg">Social sign-in</h2>
            <p className="mt-1 text-sm text-fg-muted">
              Readers can sign in or register with these providers (registration follows the “Registration” switch in Appearance). Accounts are never linked by matching email;
              people connect providers themselves in Account → Settings. Changes apply to new sign-ins immediately.
            </p>
          </div>
          {SOCIAL_PROVIDERS.map((p) => {
            const s = social.find((x) => x.provider === p)!;
            const help = CONSOLE[p];
            return (
              <Card key={p}>
                <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-semibold text-fg">{providerLabels[p]}</h3>
                  <div className="flex items-center gap-2 text-xs text-fg-subtle">
                    {SOURCE[s.source]}
                    <StatusPill status={s.enabled ? "ok" : s.source === "none" ? "not configured" : "closed"} />
                  </div>
                </div>
                <p className="mb-4 text-sm text-fg-muted">
                  <a href={help.href} target="_blank" rel="noopener noreferrer" className="link">{help.label}</a>. {help.steps}
                </p>
                <div className="mb-4">
                  <Field label="Authorized redirect / callback URL" htmlFor={`cb-${p}`} hint="Register exactly this URL with the provider.">
                    <Input id={`cb-${p}`} readOnly value={callbackUrl(origin, p)} className="font-mono text-xs" />
                  </Field>
                </div>
                <form action={saveProvider} className="grid gap-4 sm:grid-cols-2">
                  <input type="hidden" name="provider" value={p} />
                  <Field label="Client ID" htmlFor={`id-${p}`}>
                    <Input id={`id-${p}`} name="clientId" defaultValue={s.clientId} autoComplete="off" spellCheck={false} />
                  </Field>
                  <Field label="Client secret" htmlFor={`secret-${p}`} hint={s.hasSecret ? "Stored. Leave empty to keep it." : undefined}>
                    <PasswordInput id={`secret-${p}`} name="clientSecret" autoComplete="off" />
                  </Field>
                  <label className="flex items-center gap-2 text-sm sm:col-span-2">
                    <input type="checkbox" name="enabled" defaultChecked={s.enabled} /> Allow sign-in with {providerLabels[p]}
                  </label>
                  <div className="flex flex-wrap gap-2 sm:col-span-2">
                    <Button type="submit" name="intent" value="save">Save</Button>
                    {s.source === "admin" && (
                      <Button type="submit" name="intent" value="reset" variant="ghost">Use environment instead</Button>
                    )}
                  </div>
                </form>
              </Card>
            );
          })}
        </section>

        <section aria-labelledby="indexnow-title" className="space-y-4">
          <div>
            <h2 id="indexnow-title" className="text-lg font-semibold text-fg">IndexNow</h2>
            <p className="mt-1 text-sm text-fg-muted">
              Tells Bing, Yandex, Seznam, Naver and other IndexNow search engines as soon as a post is published, updated or removed, so they recrawl it quickly.
              Google does not use IndexNow (it reads the sitemap). Submissions run in the background with retries and only from the production site.
            </p>
          </div>
          <Card>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <h3 className="font-semibold text-fg">Instant indexing</h3>
              <div className="flex items-center gap-2 text-xs text-fg-subtle">
                {SOURCE[indexNow.source]}
                <StatusPill status={indexNow.enabled ? "ok" : "closed"} />
              </div>
            </div>
            {indexNow.key && (
              <div className="mb-4">
                <Field label="Key file" htmlFor="in-key" hint="Search engines fetch this file to confirm the key belongs to this site.">
                  <Input id="in-key" readOnly value={`${origin}/${indexNow.key}.txt`} className="font-mono text-xs" />
                </Field>
                {indexNow.enabled && <a href={`/${indexNow.key}.txt`} target="_blank" rel="noopener" className="link mt-1 inline-block text-sm">Open key file ↗</a>}
              </div>
            )}
            {!isProductionEnv() && <div className="mb-4"><Alert tone="info">This is not the production site, so nothing is sent.</Alert></div>}
            {indexNow.source === "env" ? (
              <p className="text-sm text-fg-muted">Set by INDEXNOW_KEY in the deployment. Remove that variable to manage IndexNow here.</p>
            ) : (
              <form action={indexNowAction} className="flex flex-wrap gap-2">
                {indexNow.enabled ? (
                  <>
                    <Button type="submit" name="intent" value="submit-all" variant="secondary">Submit all pages now</Button>
                    <Button type="submit" name="intent" value="regenerate" variant="ghost">New key</Button>
                    <Button type="submit" name="intent" value="off" variant="ghost">Turn off</Button>
                  </>
                ) : (
                  <Button type="submit" name="intent" value="on">Turn on IndexNow</Button>
                )}
              </form>
            )}
            {indexNow.source === "env" && indexNow.enabled && (
              <form action={indexNowAction} className="mt-3"><Button type="submit" name="intent" value="submit-all" variant="secondary">Submit all pages now</Button></form>
            )}
          </Card>
        </section>

        <section aria-labelledby="gemini-title" className="space-y-4">
          <div>
            <h2 id="gemini-title" className="text-lg font-semibold text-fg">Image generation (Gemini)</h2>
            <p className="mt-1 text-sm text-fg-muted">
              Powers “✨ Generate image” for cover images in the post and page editors. Results are saved to the media library only when an author accepts them. Per-user and daily
              limits come from GEMINI_IMAGE_*_LIMIT in the deployment.
            </p>
          </div>
          <Card>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <h3 className="font-semibold text-fg">Google Gemini API</h3>
              <div className="flex items-center gap-2 text-xs text-fg-subtle">
                {SOURCE[gemini.source]}
                <StatusPill status={!gemini.enabled ? (gemini.source === "none" ? "not configured" : "closed") : gemini.lastError ? "test failed" : gemini.verifiedAt ? "tested" : "configured"} />
              </div>
            </div>
            {!storage && (
              <div className="mb-4">
                <Alert tone="info">Media storage (Cloudflare R2) must be configured in Storage & email before generated images can be saved.</Alert>
              </div>
            )}
            {gemini.lastError && (
              <div className="mb-4">
                <Alert>Last key check failed: {gemini.lastError}</Alert>
              </div>
            )}
            <p className="mb-4 text-sm text-fg-muted">
              Create a key in <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer" className="link">Google AI Studio → API keys</a>. Saving checks the key and model
              with a free metadata request; no image is generated.
              {gemini.verifiedAt && <> Last verified {formatDateTime(gemini.verifiedAt)}.</>}
            </p>
            <form action={saveImageGeneration} className="grid gap-4 sm:grid-cols-2">
              <Field label="API key" htmlFor="g-key" hint={gemini.hasKey ? `Stored (${gemini.keyHint}). Leave empty to keep it.` : "Starts with AIza…"}>
                <PasswordInput id="g-key" name="apiKey" autoComplete="off" />
              </Field>
              <Field label="Image model" htmlFor="g-model" hint="Model code from ai.google.dev/gemini-api/docs/models.">
                <Input id="g-model" name="model" defaultValue={gemini.model || "gemini-3.1-flash-image"} required spellCheck={false} />
              </Field>
              <Field label="Image size" htmlFor="g-size" hint="Larger sizes cost more and take longer (model-dependent).">
                <Select id="g-size" name="imageSize" defaultValue={gemini.imageSize}>
                  {IMAGE_SIZES.map((s) => <option key={s} value={s}>{s}</option>)}
                </Select>
              </Field>
              <label className="flex items-center gap-2 self-end pb-3 text-sm">
                <input type="checkbox" name="enabled" defaultChecked={gemini.source === "none" ? true : gemini.enabled} /> Enable “Generate image”
              </label>
              <div className="flex flex-wrap gap-2 sm:col-span-2">
                <Button type="submit" name="intent" value="save">Save and verify</Button>
                {gemini.source === "admin" && <Button type="submit" name="intent" value="reset" variant="ghost">Remove stored key</Button>}
              </div>
            </form>
          </Card>
        </section>
      </div>
    </>
  );
}
