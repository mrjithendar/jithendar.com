"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Alert, Button, Field, Input, Select } from "@/components/ui/form";
import { DIFFICULTIES, DIFFICULTY_INFO, MODE_INFO, MODES, TIMED_DURATIONS, type Mode } from "@/lib/practice/types";
import { api, ApiError } from "./api";
import { usePracticeAuth } from "./AuthGate";

/** Configure and start a session (any mode). Guests get the sign-in dialog; the server checks again. */
export function StartPracticeForm({
  roles,
  topics,
  initialRoles = [],
  initialMode = "guided",
  compact = false,
}: {
  roles: { slug: string; name: string }[];
  topics: { slug: string; name: string }[];
  initialRoles?: string[];
  initialMode?: Mode;
  compact?: boolean;
}) {
  const router = useRouter();
  const { requireAuth } = usePracticeAuth();
  const [mode, setMode] = useState<Mode>(initialMode);
  const [selRoles, setSelRoles] = useState<string[]>(initialRoles);
  const [diffs, setDiffs] = useState<string[]>([]);
  const [selTopics, setSelTopics] = useState<string[]>([]);
  const [count, setCount] = useState(3);
  const [duration, setDuration] = useState<string>("30");
  const [customDuration, setCustomDuration] = useState(20);
  const [includeFailed, setIncludeFailed] = useState(false);
  const [excludeSolved, setExcludeSolved] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toggle = (list: string[], v: string) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);
  const fixed = mode === "daily";

  async function start(e: React.FormEvent) {
    e.preventDefault();
    if (!requireAuth("Practice sessions are saved to your account so you can resume them and track progress.")) return;
    setBusy(true);
    setError(null);
    try {
      const minutes = mode === "timed" || mode === "mock" ? (duration === "custom" ? customDuration : Number(duration)) : null;
      const { id } = await api<{ id: string }>("/api/practice/sessions", { body: { mode, roles: selRoles, difficulties: diffs, topics: selTopics, count, durationMinutes: minutes, includeFailed, excludeSolved } });
      router.push(`/python-practice/session/${id}`);
    } catch (err) {
      if (err instanceof ApiError && err.code === "auth_required") requireAuth("Sign in again to start a session.");
      else setError(err instanceof Error ? err.message : "Could not start the session.");
      setBusy(false);
    }
  }

  const chip = (active: boolean) => `rounded-full border px-3 py-1.5 text-sm ${active ? "border-accent bg-accent-soft text-accent-text" : "border-line bg-surface text-fg-muted hover:text-fg"}`;

  return (
    <form onSubmit={start} className="space-y-5">
      {error && <Alert>{error}</Alert>}
      <fieldset>
        <legend className="text-sm font-medium text-fg">Mode</legend>
        <div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {MODES.map((m) => (
            <label key={m} className={`cursor-pointer rounded-lg border p-3 text-sm ${mode === m ? "border-accent bg-accent-soft" : "border-line bg-surface"}`}>
              <input type="radio" name="mode" value={m} checked={mode === m} onChange={() => setMode(m)} className="sr-only" />
              <span className="font-semibold text-fg">{MODE_INFO[m].label}</span>
              {!compact && <span className="mt-1 block text-fg-muted">{MODE_INFO[m].description}</span>}
            </label>
          ))}
        </div>
      </fieldset>
      {!fixed && (
        <>
          <fieldset>
            <legend className="text-sm font-medium text-fg">Roles {selRoles.length === 0 && <span className="font-normal text-fg-subtle">(all)</span>}</legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {roles.map((r) => (
                <button key={r.slug} type="button" aria-pressed={selRoles.includes(r.slug)} className={chip(selRoles.includes(r.slug))} onClick={() => setSelRoles(toggle(selRoles, r.slug))}>
                  {r.name}
                </button>
              ))}
            </div>
          </fieldset>
          {mode !== "adaptive" && (
            <fieldset>
              <legend className="text-sm font-medium text-fg">Difficulty {diffs.length === 0 && <span className="font-normal text-fg-subtle">(any)</span>}</legend>
              <div className="mt-2 flex flex-wrap gap-2">
                {DIFFICULTIES.map((d) => (
                  <button key={d} type="button" aria-pressed={diffs.includes(d)} className={chip(diffs.includes(d))} onClick={() => setDiffs(toggle(diffs, d))} title={DIFFICULTY_INFO[d].criteria}>
                    {DIFFICULTY_INFO[d].label}
                  </button>
                ))}
              </div>
            </fieldset>
          )}
          {mode !== "adaptive" && !compact && (
            <details>
              <summary className="cursor-pointer text-sm font-medium text-fg">Topics {selTopics.length ? `(${selTopics.length})` : "(any)"}</summary>
              <div className="mt-2 flex flex-wrap gap-2">
                {topics.map((t) => (
                  <button key={t.slug} type="button" aria-pressed={selTopics.includes(t.slug)} className={chip(selTopics.includes(t.slug))} onClick={() => setSelTopics(toggle(selTopics, t.slug))}>
                    {t.name}
                  </button>
                ))}
              </div>
            </details>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Number of questions" htmlFor="count">
              <Input id="count" type="number" min={1} max={10} value={count} onChange={(e) => setCount(Number(e.target.value))} />
            </Field>
            {(mode === "timed" || mode === "mock") && (
              <Field label="Duration" htmlFor="duration" hint="The countdown runs on the server; refreshing doesn't reset it.">
                <div className="flex gap-2">
                  <Select id="duration" value={duration} onChange={(e) => setDuration(e.target.value)}>
                    {TIMED_DURATIONS.map((d) => (
                      <option key={d} value={d}>
                        {d} minutes
                      </option>
                    ))}
                    <option value="custom">Custom</option>
                  </Select>
                  {duration === "custom" && <Input type="number" min={5} max={180} value={customDuration} onChange={(e) => setCustomDuration(Number(e.target.value))} aria-label="Custom minutes" className="!w-28" />}
                </div>
              </Field>
            )}
          </div>
          {mode !== "adaptive" && (
            <div className="flex flex-col gap-2 text-sm text-fg">
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={includeFailed} onChange={(e) => setIncludeFailed(e.target.checked)} /> Include questions I attempted but haven&apos;t solved
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={excludeSolved} onChange={(e) => setExcludeSolved(e.target.checked)} /> Exclude questions I&apos;ve already solved
              </label>
            </div>
          )}
        </>
      )}
      <Button type="submit" loading={busy}>
        Start {MODE_INFO[mode].label.toLowerCase()}
      </Button>
    </form>
  );
}
