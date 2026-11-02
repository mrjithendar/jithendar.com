import Link from "next/link";
import { Flash, type FlashParams } from "@/components/admin/Flash";
import { AdminHeader, Card, Stat } from "@/components/admin/ui";
import { Button, Field, Input, Select } from "@/components/ui/form";
import { adminActor } from "@/lib/admin";
import { flash } from "@/lib/flash";
import { adminOverview } from "@/lib/practice/admin";
import { AI_PROVIDERS, executorEnv, getPracticeSettings, savePracticeSettings, clearAiKey } from "@/lib/practice/settings";
import { VERDICTS, type Verdict } from "@/lib/practice/types";
import { requireRole } from "@/lib/session";

export const metadata = { title: "Python practice" };

const num = (f: FormData, k: string) => Number(f.get(k));

async function save(form: FormData) {
  "use server";
  const actor = await adminActor();
  await flash("/admin/practice", async () => {
    const runtimes = String(form.get("runtimes") ?? "")
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean)
      .map((l) => {
        const [id, label, state] = l.split("|").map((s) => s.trim());
        return { id: id ?? "", label: label || id || "", enabled: state !== "off" };
      });
    await savePracticeSettings(actor, {
      execution: { enabled: form.get("executionEnabled") === "on", runtimes, defaultRuntime: String(form.get("defaultRuntime") ?? ""), perTestSeconds: num(form, "perTestSeconds"), totalSeconds: num(form, "totalSeconds"), memoryMb: num(form, "memoryMb") },
      quotas: { runsPerHour: num(form, "runsPerHour"), submitsPerHour: num(form, "submitsPerHour"), maxPending: num(form, "maxPending"), aiRequestsPerDay: num(form, "aiRequestsPerDay"), aiDailyBudgetUsd: num(form, "aiDailyBudgetUsd") },
      ai: {
        enabled: form.get("aiEnabled") === "on",
        provider: String(form.get("provider")),
        model: String(form.get("model") ?? ""),
        baseUrl: String(form.get("baseUrl") ?? ""),
        region: String(form.get("region") ?? "us-east-1"),
        apiKey: String(form.get("apiKey") ?? ""),
        timeoutMs: num(form, "timeoutMs"),
        maxOutputTokens: num(form, "maxOutputTokens"),
        inputUsdPerMTok: num(form, "inputUsdPerMTok"),
        outputUsdPerMTok: num(form, "outputUsdPerMTok"),
      },
      leaderboard: { enabled: form.get("leaderboardEnabled") === "on" },
      retention: { activityDays: num(form, "activityDays"), codeDays: num(form, "codeDays") },
    });
    return "Settings saved.";
  });
}

async function removeKey() {
  "use server";
  const actor = await adminActor();
  await flash("/admin/practice", async () => {
    await clearAiKey(actor);
    return "AI key removed.";
  });
}

export default async function PracticeAdmin({ searchParams }: { searchParams: FlashParams }) {
  const user = await requireRole("admin", "author");
  const [o, s] = await Promise.all([adminOverview(), getPracticeSettings()]);
  const env = executorEnv();
  const sp = await searchParams;
  const isAdmin = user.role === "admin";
  return (
    <>
      <AdminHeader
        title="Python practice"
        description="Problems, roles, the code runner, the AI tutor and abuse signals for /python-practice."
        actions={
          <>
            <Link href="/admin/practice/problems" className="text-sm font-medium text-accent-text underline">
              Problems
            </Link>
            <Link href="/admin/practice/catalog" className="text-sm font-medium text-accent-text underline">
              Roles, topics &amp; daily
            </Link>
          </>
        }
      />
      <Flash ok={sp.ok} error={sp.error} />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Published problems" value={o.problems.published ?? 0} hint={`${o.problems.draft ?? 0} drafts · ${o.problems.archived ?? 0} archived`} />
        <Stat label="Learners (7 days)" value={o.active.learners} hint={`${o.active.sessions} active sessions`} />
        <Stat label="Pending runs" value={o.queue.pending} hint={o.queue.avgMs ? `avg ${Math.round(o.queue.avgMs)} ms to result (24 h)` : "no runs in 24 h"} />
        <Stat label="AI today" value={o.ai.requests} hint={`$${o.ai.costUsd.toFixed(2)} est. · ${o.ai.tokens} tokens`} />
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="font-semibold text-fg">Code runner</h2>
          <dl className="mt-3 space-y-1 text-sm">
            <div>Execution switch: <strong>{s.execution.enabled ? "on" : "off"}</strong></div>
            <div>Executor URL and token: <strong>{env ? "configured" : "missing (PRACTICE_EXECUTOR_URL, PRACTICE_EXECUTOR_TOKEN)"}</strong></div>
            {o.executor.ok ? (
              <>
                <div>Executor: reachable · backend {o.executor.backend} · runtime class <code>{o.executor.runtime_class}</code></div>
                <div>Queue: {o.executor.queued} queued, {o.executor.running} running · dispatchers alive: {Object.keys(o.executor.dispatchers).length}</div>
                <div>Runtimes: {o.executor.runtimes.join(", ") || "none"}</div>
              </>
            ) : (
              <div>Executor: {o.executor.error}</div>
            )}
          </dl>
          <p className="mt-3 text-sm text-fg-muted">Turn execution on only after the gVisor sandbox is installed and verified (docs/PYTHON_PRACTICE_EXECUTOR.md).</p>
        </Card>
        <Card>
          <h2 className="font-semibold text-fg">Results in the last 24 hours</h2>
          {o.verdicts.length ? (
            <ul className="mt-3 space-y-1 text-sm">
              {o.verdicts.map((v) => (
                <li key={String(v.verdict)} className="flex justify-between">
                  <span>{VERDICTS[v.verdict as Verdict] ?? v.verdict}</span>
                  <span className="tabular-nums">{v.n}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-fg-muted">No runs.</p>
          )}
        </Card>
        <Card className="lg:col-span-2">
          <h2 className="font-semibold text-fg">Abuse signals (last hour)</h2>
          <p className="mt-1 text-sm text-fg-muted">Accounts with 10+ runs hitting time or memory limits, or 100+ runs. The executor also blocks repeat offenders for 15 minutes on its own.</p>
          {o.abuse.length ? (
            <table className="mt-3 w-full text-sm">
              <thead className="text-left text-fg-subtle">
                <tr>
                  <th className="py-1">Account</th>
                  <th>Limit hits</th>
                  <th>Rate-limited</th>
                  <th>Infra errors</th>
                </tr>
              </thead>
              <tbody>
                {o.abuse.map((a) => (
                  <tr key={a.email}>
                    <td className="py-1">{a.email}</td>
                    <td>{a.timeouts}</td>
                    <td>{a.limited}</td>
                    <td>{a.infra}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="mt-3 text-sm text-fg-muted">Nothing unusual.</p>
          )}
        </Card>
      </div>
      {isAdmin && (
        <Card className="mt-6">
          <h2 className="font-semibold text-fg">Settings</h2>
          <form action={save} className="mt-4 space-y-8">
            <fieldset className="grid gap-4 sm:grid-cols-3">
              <legend className="mb-2 text-sm font-semibold text-fg">Execution</legend>
              <label className="flex items-center gap-2 text-sm sm:col-span-3">
                <input type="checkbox" name="executionEnabled" defaultChecked={s.execution.enabled} /> Allow running and submitting code
              </label>
              <div className="sm:col-span-2">
                <Field label="Runtimes (id | label | on/off, one per line)" htmlFor="runtimes" hint="Ids must match EXECUTOR_RUNTIMES in the executor deployment.">
                  <textarea id="runtimes" name="runtimes" rows={3} className="w-full rounded-lg border border-line-strong bg-surface p-2 font-mono text-sm" defaultValue={s.execution.runtimes.map((r) => `${r.id} | ${r.label} | ${r.enabled ? "on" : "off"}`).join("\n")} />
                </Field>
              </div>
              <Field label="Default runtime" htmlFor="defaultRuntime"><Input id="defaultRuntime" name="defaultRuntime" defaultValue={s.execution.defaultRuntime} /></Field>
              <Field label="Max seconds per test" htmlFor="perTestSeconds"><Input id="perTestSeconds" name="perTestSeconds" type="number" step="0.5" defaultValue={s.execution.perTestSeconds} /></Field>
              <Field label="Max seconds per run" htmlFor="totalSeconds"><Input id="totalSeconds" name="totalSeconds" type="number" defaultValue={s.execution.totalSeconds} /></Field>
              <Field label="Max memory (MB)" htmlFor="memoryMb"><Input id="memoryMb" name="memoryMb" type="number" defaultValue={s.execution.memoryMb} /></Field>
            </fieldset>
            <fieldset className="grid gap-4 sm:grid-cols-3">
              <legend className="mb-2 text-sm font-semibold text-fg">Quotas</legend>
              <Field label="Runs per user per hour" htmlFor="runsPerHour"><Input id="runsPerHour" name="runsPerHour" type="number" defaultValue={s.quotas.runsPerHour} /></Field>
              <Field label="Submissions per user per hour" htmlFor="submitsPerHour"><Input id="submitsPerHour" name="submitsPerHour" type="number" defaultValue={s.quotas.submitsPerHour} /></Field>
              <Field label="Concurrent runs per user" htmlFor="maxPending"><Input id="maxPending" name="maxPending" type="number" defaultValue={s.quotas.maxPending} /></Field>
              <Field label="AI requests per user per day" htmlFor="aiRequestsPerDay"><Input id="aiRequestsPerDay" name="aiRequestsPerDay" type="number" defaultValue={s.quotas.aiRequestsPerDay} /></Field>
              <Field label="AI budget per day (USD)" htmlFor="aiDailyBudgetUsd"><Input id="aiDailyBudgetUsd" name="aiDailyBudgetUsd" type="number" step="0.01" defaultValue={s.quotas.aiDailyBudgetUsd} /></Field>
            </fieldset>
            <fieldset className="grid gap-4 sm:grid-cols-3">
              <legend className="mb-2 text-sm font-semibold text-fg">AI tutor</legend>
              <label className="flex items-center gap-2 text-sm sm:col-span-3">
                <input type="checkbox" name="aiEnabled" defaultChecked={s.ai.enabled} /> Enable the AI tutor
              </label>
              <Field label="Provider" htmlFor="provider">
                <Select id="provider" name="provider" defaultValue={s.ai.provider}>
                  {AI_PROVIDERS.map((p) => (
                    <option key={p} value={p}>{p === "openai" ? "OpenAI-compatible" : p === "gemini" ? "Google Gemini" : "Amazon Bedrock"}</option>
                  ))}
                </Select>
              </Field>
              <Field label="Model id" htmlFor="model" hint="Exactly as the provider names it."><Input id="model" name="model" defaultValue={s.ai.model} /></Field>
              <Field label="Base URL (OpenAI-compatible)" htmlFor="baseUrl" optional><Input id="baseUrl" name="baseUrl" defaultValue={s.ai.baseUrl} placeholder="https://api.openai.com/v1" /></Field>
              <Field label="Bedrock region" htmlFor="region"><Input id="region" name="region" defaultValue={s.ai.region} /></Field>
              <Field label="API key" htmlFor="apiKey" hint={s.ai.apiKey ? "A key is saved (encrypted). Leave empty to keep it." : "Falls back to OPENAI_API_KEY / GEMINI_API_KEY. Bedrock uses AWS credentials, not a key."}>
                <Input id="apiKey" name="apiKey" type="password" autoComplete="off" />
              </Field>
              <Field label="Timeout (ms)" htmlFor="timeoutMs"><Input id="timeoutMs" name="timeoutMs" type="number" defaultValue={s.ai.timeoutMs} /></Field>
              <Field label="Max output tokens" htmlFor="maxOutputTokens"><Input id="maxOutputTokens" name="maxOutputTokens" type="number" defaultValue={s.ai.maxOutputTokens} /></Field>
              <Field label="Input price (USD per million tokens)" htmlFor="inputUsdPerMTok"><Input id="inputUsdPerMTok" name="inputUsdPerMTok" type="number" step="0.001" defaultValue={s.ai.inputUsdPerMTok} /></Field>
              <Field label="Output price (USD per million tokens)" htmlFor="outputUsdPerMTok"><Input id="outputUsdPerMTok" name="outputUsdPerMTok" type="number" step="0.001" defaultValue={s.ai.outputUsdPerMTok} /></Field>
            </fieldset>
            <fieldset className="grid gap-4 sm:grid-cols-3">
              <legend className="mb-2 text-sm font-semibold text-fg">Community and retention</legend>
              <label className="flex items-center gap-2 text-sm sm:col-span-3">
                <input type="checkbox" name="leaderboardEnabled" defaultChecked={s.leaderboard.enabled} /> Public leaderboard (opt-in per user)
              </label>
              <Field label="Keep activity events (days)" htmlFor="activityDays"><Input id="activityDays" name="activityDays" type="number" defaultValue={s.retention.activityDays} /></Field>
              <Field label="Keep submitted code (days)" htmlFor="codeDays"><Input id="codeDays" name="codeDays" type="number" defaultValue={s.retention.codeDays} /></Field>
            </fieldset>
            <Button type="submit">Save settings</Button>
          </form>
          {s.ai.apiKey && (
            <form action={removeKey} className="mt-3">
              <Button type="submit" variant="ghost" size="sm">Remove saved AI key</Button>
            </form>
          )}
        </Card>
      )}
    </>
  );
}
