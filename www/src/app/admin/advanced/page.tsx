import Link from "next/link";
import { Flash, type FlashParams } from "@/components/admin/Flash";
import { AdminHeader, Card, StatusPill } from "@/components/admin/ui";
import { PasswordInput } from "@/components/ui/PasswordInput";
import { Button, Field, Input, Select, Textarea } from "@/components/ui/form";
import { adminActor } from "@/lib/admin";
import { flash } from "@/lib/flash";
import { GROUPS, runtimeSummary, saveRuntimeGroup, type Field as SettingField, type FieldState } from "@/lib/runtime-settings";
import { requireRole } from "@/lib/session";

export const metadata = { title: "Advanced settings" };

const BACK = "/admin/advanced";

async function save(form: FormData) {
  "use server";
  const actor = await adminActor();
  const group = String(form.get("group") ?? "");
  await flash(`${BACK}#${group}`, async () => {
    const input: Record<string, string> = {};
    for (const [k, v] of form.entries()) if (typeof v === "string" && /^[A-Z0-9_]+$/.test(k)) input[k] = v;
    const clear = form.getAll("clear").map(String);
    await saveRuntimeGroup(actor, group, input, clear);
    return `${GROUPS.find((g) => g.id === group)?.title ?? "Settings"} saved. Changes apply immediately.`;
  });
}

/** Where the value in effect comes from, shown under each field. */
function source(f: SettingField, s: FieldState): string {
  if (f.type === "secret") return s.hasSecret ? "Stored here (encrypted). Leave empty to keep it." : s.secretInDeployment ? "Set in the deployment. Enter a value here to override it." : "Not set.";
  if (s.value) return s.fromDeployment ? "Set here (overrides the deployment)." : "Set here.";
  return s.fromDeployment ? `From the deployment: ${s.fromDeployment.length > 60 ? `${s.fromDeployment.slice(0, 60)}…` : s.fromDeployment}` : "Not set.";
}

function Control({ f, s }: { f: SettingField; s: FieldState }) {
  const id = `f-${f.env}`;
  const hint = [f.hint, source(f, s)].filter(Boolean).join(" ");
  if (f.type === "boolean") {
    return (
      <label className="flex items-start gap-2 text-sm sm:col-span-2">
        <input type="hidden" name={f.env} value="" />
        <input type="checkbox" name={f.env} value="true" defaultChecked={(s.value || s.fromDeployment) === "true"} className="mt-0.5" />
        <span>
          {f.label}
          <span className="block text-xs text-fg-subtle">{hint}</span>
        </span>
      </label>
    );
  }
  return (
    <div className={f.type === "textarea" ? "sm:col-span-2" : ""}>
      <Field label={f.label} htmlFor={id} hint={hint}>
        {f.type === "secret" ? (
          <PasswordInput id={id} name={f.env} autoComplete="off" />
        ) : f.type === "select" ? (
          <Select id={id} name={f.env} defaultValue={s.value}>
            <option value="">Deployment default{s.fromDeployment ? ` (${s.fromDeployment})` : ""}</option>
            {f.options?.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </Select>
        ) : f.type === "textarea" ? (
          <Textarea id={id} name={f.env} rows={4} defaultValue={s.value} className="font-mono text-xs" spellCheck={false} />
        ) : (
          <Input id={id} name={f.env} type={f.type === "number" ? "number" : "text"} min={f.min} max={f.max} defaultValue={s.value} placeholder={s.fromDeployment ?? f.placeholder} autoComplete="off" spellCheck={false} />
        )}
      </Field>
      {f.type === "secret" && s.hasSecret && (
        <label className="mt-1.5 flex items-center gap-2 text-xs text-fg-muted">
          <input type="checkbox" name="clear" value={f.env} /> Remove the stored value
        </label>
      )}
    </div>
  );
}

export default async function AdvancedSettingsPage({ searchParams }: { searchParams: FlashParams }) {
  await requireRole("admin");
  const [state, sp] = await Promise.all([runtimeSummary(), searchParams]);
  const configured = (g: (typeof GROUPS)[number]) => g.fields.some((f) => state[f.env]!.value || state[f.env]!.hasSecret || state[f.env]!.fromDeployment || state[f.env]!.secretInDeployment);

  return (
    <>
      <AdminHeader
        title="Advanced settings"
        description={
          <>
            Options that used to need a change to the Kubernetes Secret and a restart. A value saved here overrides the deployment; an empty field uses the deployment&apos;s value.
            Content, look and features are in <Link href="/admin/appearance" className="link">Appearance &amp; settings</Link>; sign-in providers, Gemini and IndexNow in{" "}
            <Link href="/admin/integrations" className="link">Integrations</Link>; media storage and email in <Link href="/admin/storage" className="link">Storage &amp; email</Link>.
          </>
        }
      />
      <Flash ok={sp.ok} error={sp.error} />
      <nav aria-label="Sections" className="mb-6 flex flex-wrap gap-2 text-sm">
        {GROUPS.map((g) => (
          <a key={g.id} href={`#${g.id}`} className="rounded-full border border-line px-3 py-1.5 text-fg-muted hover:bg-surface-sunken hover:text-fg">{g.title}</a>
        ))}
      </nav>
      <div className="space-y-6">
        {GROUPS.map((g) => (
          <section key={g.id} id={g.id} aria-labelledby={`${g.id}-title`} className="scroll-mt-24">
            <Card>
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <h2 id={`${g.id}-title`} className="font-semibold text-fg">{g.title}</h2>
                <StatusPill status={configured(g) ? "configured" : "not configured"} />
              </div>
              <p className="mb-4 text-sm text-fg-muted">{g.description}</p>
              <form action={save} className="grid gap-4 sm:grid-cols-2">
                <input type="hidden" name="group" value={g.id} />
                {g.fields.map((f) => <Control key={f.env} f={f} s={state[f.env]!} />)}
                <div className="sm:col-span-2"><Button type="submit">Save</Button></div>
              </form>
            </Card>
          </section>
        ))}
        <Card>
          <h2 className="font-semibold text-fg">Only in the deployment</h2>
          <p className="mt-1 text-sm text-fg-muted">
            These stay in the Kubernetes Secret on purpose: the admin needs them to start, to read its own encrypted settings, or to know who is allowed in.
          </p>
          <ul className="mt-3 grid gap-x-6 gap-y-1 text-sm text-fg-muted sm:grid-cols-2">
            <li><code className="text-xs">DATABASE_URL</code>, <code className="text-xs">REDIS_URL</code>: where the admin&apos;s data lives</li>
            <li><code className="text-xs">BETTER_AUTH_SECRET</code>: signs every session</li>
            <li><code className="text-xs">SETTINGS_ENCRYPTION_KEY</code>: decrypts the secrets stored here</li>
            <li><code className="text-xs">SITE_URL</code>, <code className="text-xs">APP_ENV</code>: the site&apos;s identity and mode</li>
            <li><code className="text-xs">ADMIN_BOOTSTRAP_TOKEN</code>: first-run setup only</li>
            <li><code className="text-xs">LOG_LEVEL</code>, <code className="text-xs">OTEL_*</code>, <code className="text-xs">METRICS_PORT</code>: read once at start-up</li>
          </ul>
        </Card>
      </div>
    </>
  );
}
