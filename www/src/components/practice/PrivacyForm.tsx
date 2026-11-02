"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Alert, Button, Field, Input } from "@/components/ui/form";
import { api } from "./api";

/** Preferred roles, leaderboard opt-in and public name; export and deletion of practice data. */
export function PrivacyForm({ roles, initial }: { roles: { slug: string; name: string }[]; initial: { roles: string[]; leaderboardOptIn: boolean; publicName: string } }) {
  const router = useRouter();
  const [prefs, setPrefs] = useState(initial);
  const [msg, setMsg] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api("/api/practice/me", { method: "PUT", body: prefs });
      setMsg({ tone: "success", text: "Saved." });
      router.refresh();
    } catch (err) {
      setMsg({ tone: "error", text: (err as Error).message });
    }
  }
  async function download() {
    const res = await fetch("/api/practice/me?export=1", { credentials: "same-origin" });
    if (!res.ok) return setMsg({ tone: "error", text: "Export failed." });
    const url = URL.createObjectURL(await res.blob());
    const a = Object.assign(document.createElement("a"), { href: url, download: `python-practice-${new Date().toISOString().slice(0, 10)}.json` });
    a.click();
    URL.revokeObjectURL(url);
  }
  async function wipe() {
    if (!confirm("Delete all your Python practice data (progress, submissions, notes, badges)? Your site account stays. This cannot be undone.")) return;
    await api("/api/practice/me", { method: "DELETE" });
    router.refresh();
  }
  return (
    <form onSubmit={save} className="space-y-4">
      {msg && <Alert tone={msg.tone}>{msg.text}</Alert>}
      <fieldset>
        <legend className="text-sm font-medium text-fg">Roles I&apos;m preparing for</legend>
        <div className="mt-2 flex flex-wrap gap-2">
          {roles.map((r) => {
            const on = prefs.roles.includes(r.slug);
            return (
              <button key={r.slug} type="button" aria-pressed={on} onClick={() => setPrefs({ ...prefs, roles: on ? prefs.roles.filter((x) => x !== r.slug) : [...prefs.roles, r.slug] })} className={`rounded-full border px-3 py-1.5 text-sm ${on ? "border-accent bg-accent-soft text-accent-text" : "border-line text-fg-muted"}`}>
                {r.name}
              </button>
            );
          })}
        </div>
      </fieldset>
      <label className="flex items-start gap-2 text-sm text-fg">
        <input type="checkbox" className="mt-1" checked={prefs.leaderboardOptIn} onChange={(e) => setPrefs({ ...prefs, leaderboardOptIn: e.target.checked })} />
        <span>Show me on the public leaderboard (XP, solved count and streak under the name below; never your email).</span>
      </label>
      <Field label="Public name" htmlFor="publicName" optional hint="Leave empty for an anonymous handle.">
        <Input id="publicName" value={prefs.publicName} maxLength={40} onChange={(e) => setPrefs({ ...prefs, publicName: e.target.value })} />
      </Field>
      <div className="flex flex-wrap gap-2">
        <Button type="submit">Save preferences</Button>
        <Button type="button" variant="secondary" onClick={() => void download()}>
          Export my data (JSON)
        </Button>
        <Button type="button" variant="danger" onClick={() => void wipe()}>
          Delete practice data
        </Button>
      </div>
    </form>
  );
}
