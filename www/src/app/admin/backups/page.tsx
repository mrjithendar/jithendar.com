import { PasswordInput } from "@/components/ui/PasswordInput";
import { Flash, type FlashParams } from "@/components/admin/Flash";
import { AdminHeader, Card, StatusPill, Table, td, th } from "@/components/admin/ui";
import { Alert, Button, Field, Input, Select } from "@/components/ui/form";
import Link from "next/link";
import { adminActor } from "@/lib/admin";
import { BACKUP_ROOT, backupSummary, listStoredBackups, recentRuns, runBackup, saveDestination, saveGeneral, testDestination } from "@/lib/backups";
import { formatDateTime } from "@/lib/dates";
import { flash } from "@/lib/flash";
import { PostError } from "@/lib/posts";
import { requireRole } from "@/lib/session";

export const metadata = { title: "Backups" };

async function general(form: FormData) {
  "use server";
  const actor = await adminActor();
  await flash("/admin/backups", async () => {
    await saveGeneral(actor, Object.fromEntries(form));
    return "Backup settings saved.";
  });
}

async function destination(form: FormData) {
  "use server";
  const actor = await adminActor();
  await flash("/admin/backups", async () => {
    await saveDestination(actor, { enabled: form.has("enabled"), bucket: String(form.get("bucket") ?? "") });
    if (form.get("test") === "1") await testDestination(actor);
    return form.get("test") === "1" ? "Cloudflare R2 destination saved and tested successfully." : "Cloudflare R2 destination saved.";
  });
}

async function runNow() {
  "use server";
  const actor = await adminActor();
  await flash("/admin/backups", async () => {
    const r = await runBackup("manual", actor);
    if (r.status === "failed") throw new PostError(`Backup failed: ${r.results.map((x) => x.detail).join("; ")}`);
    return `Backup ${r.status}: ${r.results.map((x) => `${x.destination} ${x.ok ? "✓" : "✗ " + x.detail}`).join(", ")}`;
  });
}

export default async function BackupsPage({ searchParams }: { searchParams: FlashParams }) {
  await requireRole("admin");
  const [b, runs, stored, sp] = await Promise.all([backupSummary(), recentRuns(), listStoredBackups().catch(() => null), searchParams]);
  return (
    <>
      <AdminHeader
        title="Backups"
        description="Encrypted backups of content and configuration. Excludes password hashes, sessions, API-key hashes and stored credentials."
        actions={
          <>
            <form action={runNow}><Button type="submit">Back up now</Button></form>
            <a href="/api/admin/backup" download className="inline-flex items-center rounded-xl border border-line-strong px-4 py-2.5 text-sm font-semibold">Download backup</a>
          </>
        }
      />
      <Flash ok={sp.ok} error={sp.error} />
      <div className="space-y-6">
        <Card>
          <h2 className="mb-4 font-semibold text-fg">Schedule and encryption</h2>
          <form action={general} className="grid gap-4 sm:grid-cols-4">
            <Field label="Schedule" htmlFor="schedule">
              <Select id="schedule" name="schedule" defaultValue={b.schedule}><option value="off">Off (manual only)</option><option value="daily">Daily</option><option value="weekly">Weekly</option></Select>
            </Field>
            <Field label="Hour (UTC)" htmlFor="hourUtc" hint="21 UTC = 02:30 IST"><Input id="hourUtc" name="hourUtc" type="number" min={0} max={23} defaultValue={b.hourUtc} /></Field>
            <Field label="Keep last" htmlFor="retention" hint="Older backups are deleted."><Input id="retention" name="retention" type="number" min={1} max={365} defaultValue={b.retention} /></Field>
            <Field label="Backup passphrase" htmlFor="passphrase" hint={b.hasPassphrase ? "Set. Leave empty to keep it." : "Required, 12+ characters. Store it safely: without it backups cannot be restored."}>
              <PasswordInput id="passphrase" name="passphrase" autoComplete="new-password" />
            </Field>
            <div className="sm:col-span-4"><Button type="submit">Save</Button></div>
          </form>
        </Card>

        <Card>
          <div className="mb-4 flex items-center justify-between"><h2 className="font-semibold text-fg">Cloudflare R2</h2><StatusPill status={b.r2?.enabled ? "ok" : b.r2 ? "read" : "not configured"} /></div>
          <p className="mb-4 text-sm text-fg-muted">
            Backups use the R2 account and API token from <Link href="/admin/storage" className="link">Storage &amp; email</Link> and are written to{" "}
            <code className="text-xs">{BACKUP_ROOT}/</code> in the bucket below. A separate private bucket is recommended: anything in a bucket with a public custom domain can be
            fetched by URL (backups are encrypted, but keep them private anyway). The API token must have Object Read &amp; Write on that bucket.
          </p>
          {!b.storageReady && (
            <div className="mb-4"><Alert tone="info">Cloudflare R2 is not configured yet. <Link href="/admin/storage" className="font-semibold underline">Set it up</Link> first.</Alert></div>
          )}
          <form action={destination} className="grid gap-4 sm:grid-cols-2">
            <Field label="Bucket (optional)" htmlFor="r2-bucket" hint="Leave empty to use the media bucket.">
              <Input id="r2-bucket" name="bucket" defaultValue={b.r2?.bucket ?? ""} placeholder="jithendar-backups" autoComplete="off" spellCheck={false} />
            </Field>
            <label className="flex items-center gap-2 self-end pb-3 text-sm"><input type="checkbox" name="enabled" defaultChecked={b.r2?.enabled ?? true} /> Back up to Cloudflare R2</label>
            <div className="flex gap-2 sm:col-span-2">
              <Button type="submit" name="test" value="0" variant="secondary" disabled={!b.storageReady}>Save</Button>
              <Button type="submit" name="test" value="1" disabled={!b.storageReady}>Save and test</Button>
            </div>
          </form>
        </Card>

        {stored && stored.length > 0 && (
          <div>
            <h2 className="mb-3 font-semibold text-fg">Stored in R2</h2>
            <Table head={<tr><th className={th}>File</th><th className={th}>Size</th><th className={th}>Stored</th><th className={th}><span className="sr-only">Download</span></th></tr>}>
              {stored.map((f) => (
                <tr key={f.key}>
                  <td className={`${td} font-mono text-xs`}>{f.name}</td>
                  <td className={`${td} whitespace-nowrap`}>{Math.round(f.size / 1024)} KB</td>
                  <td className={`${td} whitespace-nowrap`}>{f.lastModified ? formatDateTime(f.lastModified) : "—"}</td>
                  <td className={td}><a className="link" href={`/api/admin/backup?file=${encodeURIComponent(f.name)}`} download>Download</a></td>
                </tr>
              ))}
            </Table>
          </div>
        )}

        <div>
          <h2 className="mb-3 font-semibold text-fg">Recent runs</h2>
          <Table head={<tr><th className={th}>Started</th><th className={th}>Trigger</th><th className={th}>Status</th><th className={th}>File</th><th className={th}>Destinations</th></tr>}>
            {runs.length === 0 && <tr><td className={td} colSpan={5}>No backups yet.</td></tr>}
            {runs.map((r) => (
              <tr key={r.id}>
                <td className={`${td} whitespace-nowrap`}>{formatDateTime(r.startedAt.toISOString())}</td>
                <td className={td}>{r.trigger}</td>
                <td className={td}><StatusPill status={r.status === "success" ? "ok" : r.status === "partial" ? "degraded" : r.status === "running" ? "pending" : "down"} /></td>
                <td className={`${td} font-mono text-xs`}>{r.filename ?? "—"}{r.sizeBytes ? ` (${Math.round(r.sizeBytes / 1024)} KB)` : ""}</td>
                <td className={`${td} text-xs`}>{r.results.map((x) => `${x.destination}: ${x.ok ? "ok" : x.detail}`).join(" · ")}</td>
              </tr>
            ))}
          </Table>
        </div>
      </div>
    </>
  );
}
