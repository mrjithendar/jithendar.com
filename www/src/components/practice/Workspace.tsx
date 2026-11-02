"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore, type ReactNode } from "react";
import { Dialog } from "@/components/admin/Dialog";
import { Alert, Button, buttonClass, Select, Spinner, Textarea } from "@/components/ui/form";
import type { PracticeSolution, PracticeTestResult } from "@/db/schema";
import { callRepr, pyRepr } from "@/lib/practice/compare";
import { DIFFICULTY_INFO, VERDICTS, type PublicProblem, type Verdict } from "@/lib/practice/types";
import { api, ApiError, newKey } from "./api";
import { usePracticeAuth } from "./AuthGate";
import { CodeEditor, type EditorHandle } from "./CodeEditor";
import { DifficultyBadge } from "./Badges";

type UserState = {
  status: "attempted" | "solved" | "solved_assisted" | null;
  hints: string[];
  hintCount: number;
  solution: PracticeSolution | null;
  draft: string | null;
  note: string;
  bookmarked: boolean;
  recent: { id: string; kind: string; verdict: string | null; passed: number; total: number; createdAt: string }[];
};
type Submission = {
  id: string;
  kind: "run" | "submit";
  status: "queued" | "running" | "completed" | "error";
  verdict: Verdict | null;
  passed: number;
  total: number;
  results: PracticeTestResult[];
  custom: PracticeTestResult[];
  loadError: { type: string; message: string; line?: number; offset?: number } | null;
  maxMs: number | null;
  maxMemoryKb: number | null;
  pythonVersion: string | null;
  independent: boolean;
  queuePosition?: number | null;
  badges?: string[];
  xp?: number;
};
type TutorAnswer = { summary: string; points: string[]; next_step: string; code: string; grounding: string | null; facts: { verdict: string | null; passed: number; total: number } | null };

export type WorkspaceProps = {
  problem: PublicProblem;
  descriptionHtml: string;
  roleNames: Record<string, string>;
  topicNames: Record<string, string>;
  execution: { enabled: boolean; runtimes: { id: string; label: string }[]; defaultRuntime: string };
  aiEnabled: boolean;
  initialState: UserState | null;
  session?: { id: string; mode: string; active: boolean } | null;
  /** Rendered above the panels (session navigation and timer). */
  header?: ReactNode;
};

const LEFT_TABS = ["Problem", "Hints", "Solution", "Notes", "Submissions", "AI tutor"] as const;
type LeftTab = (typeof LEFT_TABS)[number];

function subscribeTheme(onChange: () => void) {
  const obs = new MutationObserver(onChange);
  obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  mq.addEventListener("change", onChange);
  return () => {
    obs.disconnect();
    mq.removeEventListener("change", onChange);
  };
}

function siteIsDark() {
  const t = document.documentElement.dataset.theme;
  return t ? t === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
}

/** The editor follows the site's light/dark theme unless the user picked one for the editor. */
function usePrefersDark(mode: "system" | "light" | "dark") {
  const site = useSyncExternalStore(subscribeTheme, siteIsDark, () => false);
  return mode === "system" ? site : mode === "dark";
}

export function Workspace({ problem, descriptionHtml, roleNames, topicNames, execution, aiEnabled, initialState, session, header }: WorkspaceProps) {
  const { signedIn, requireAuth } = usePracticeAuth();
  const draftKey = `practice:draft:${problem.slug}:v${problem.version}`;
  const [state, setState] = useState<UserState | null>(initialState);
  const [code, setCode] = useState(initialState?.draft ?? problem.starterCode);
  const [tab, setTab] = useState<LeftTab>("Problem");
  const [mobilePane, setMobilePane] = useState<"problem" | "code" | "results">("problem");
  const [split, setSplit] = useState(44);
  const [fullscreen, setFullscreen] = useState(false);
  const [fontSize, setFontSize] = useState(14);
  const [themeMode, setThemeMode] = useState<"system" | "light" | "dark">("system");
  const dark = usePrefersDark(themeMode);
  const [runtime, setRuntime] = useState(execution.defaultRuntime);
  const [busy, setBusy] = useState<null | "run" | "submit">(null);
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [saved, setSaved] = useState<"idle" | "saving" | "saved">("idle");
  const [custom, setCustom] = useState("");
  const editor = useRef<EditorHandle | null>(null);
  const poll = useRef<AbortController | null>(null);
  const hintsLocked = session?.mode === "mock" && session.active;
  const solutionLocked = (session?.mode === "timed" || session?.mode === "mock") && session.active;

  // Editor preferences and a local draft copy (survives a lost connection). They live in localStorage, which the
  // server render cannot read, so they are applied once after hydration.
  useEffect(() => {
    /* eslint-disable react-hooks/set-state-in-effect -- restoring client-only preferences after hydration */
    try {
      const prefs = JSON.parse(localStorage.getItem("practice:editor") ?? "{}") as { fontSize?: number; theme?: "system" | "light" | "dark"; split?: number };
      if (prefs.fontSize) setFontSize(prefs.fontSize);
      if (prefs.theme) setThemeMode(prefs.theme);
      if (prefs.split) setSplit(prefs.split);
      const local = localStorage.getItem(draftKey);
      if (signedIn && local && !initialState?.draft) {
        setCode(local);
        editor.current?.setValue(local);
      }
    } catch {
      /* private mode */
    }
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [draftKey, signedIn, initialState?.draft]);
  useEffect(() => {
    try {
      localStorage.setItem("practice:editor", JSON.stringify({ fontSize, theme: themeMode, split }));
    } catch {
      /* ignore */
    }
  }, [fontSize, themeMode, split]);

  // Autosave: locally at once, to the server two seconds after typing stops.
  const saveDraft = useCallback(
    async (text: string) => {
      if (!signedIn) return;
      setSaved("saving");
      try {
        await api(`/api/practice/problems/${problem.slug}/state`, { method: "PUT", body: { draft: text } });
        setSaved("saved");
      } catch {
        setSaved("idle");
      }
    },
    [problem.slug, signedIn],
  );
  useEffect(() => {
    if (!signedIn || code === (initialState?.draft ?? problem.starterCode)) return;
    try {
      localStorage.setItem(draftKey, code);
    } catch {
      /* ignore */
    }
    const t = setTimeout(() => void saveDraft(code), 2000);
    return () => clearTimeout(t);
  }, [code, draftKey, saveDraft, signedIn, initialState?.draft, problem.starterCode]);

  useEffect(() => () => poll.current?.abort(), []);
  useEffect(() => {
    if (!busy) return;
    const started = Date.now();
    const t = setInterval(() => setElapsed(Date.now() - started), 200);
    return () => clearInterval(t);
  }, [busy]);
  useEffect(() => {
    if (!fullscreen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setFullscreen(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [fullscreen]);

  const handleError = useCallback(
    (e: unknown) => {
      if (e instanceof ApiError && e.code === "auth_required") requireAuth("Your session has ended. Sign in again to continue.");
      setError(e instanceof Error ? e.message : "Something went wrong.");
    },
    [requireAuth],
  );

  const refreshState = useCallback(async () => {
    if (!signedIn) return;
    try {
      setState(await api<UserState>(`/api/practice/problems/${problem.slug}/state`));
    } catch {
      /* non-critical */
    }
  }, [problem.slug, signedIn]);

  async function execute(kind: "run" | "submit") {
    if (!requireAuth(kind === "run" ? "Running code needs an account." : "Submitting answers for grading needs an account.")) return;
    if (busy) return;
    if (!execution.enabled) {
      setError("Running code is not enabled on this site yet. You can still read the problem, hints and the reference solution.");
      return;
    }
    let customTests: { args: unknown[] }[] | undefined;
    if (kind === "run" && custom.trim()) {
      try {
        const parsed = JSON.parse(`[${custom.trim().split("\n").filter(Boolean).join(",")}]`) as unknown[];
        customTests = parsed.slice(0, 5).map((a) => ({ args: Array.isArray(a) ? a : [a] }));
      } catch {
        setError("Custom inputs must be JSON arrays of arguments, one per line, e.g. [[1, 2], 3].");
        return;
      }
    }
    setBusy(kind);
    setError(null);
    setSubmission(null);
    setMobilePane("results");
    poll.current?.abort();
    const ctl = new AbortController();
    poll.current = ctl;
    try {
      let sub = await api<Submission>("/api/practice/run", { body: { slug: problem.slug, code, kind, runtime, sessionId: session?.id ?? null, idempotencyKey: newKey(), custom: customTests } });
      setSubmission(sub);
      let delay = 600;
      while ((sub.status === "queued" || sub.status === "running") && !ctl.signal.aborted) {
        await new Promise((r) => setTimeout(r, delay));
        delay = Math.min(delay * 1.3, 2000);
        sub = await api<Submission>(`/api/practice/submissions/${sub.id}`, { signal: ctl.signal });
        setSubmission(sub);
      }
      if (kind === "submit") await refreshState();
    } catch (e) {
      if (!ctl.signal.aborted) handleError(e);
    } finally {
      setBusy(null);
    }
  }

  async function cancel() {
    const id = submission?.id;
    poll.current?.abort();
    setBusy(null);
    if (id) await api(`/api/practice/submissions/${id}`, { method: "DELETE" }).catch(() => null);
  }

  function reset() {
    if (!requireAuth("Editing code needs an account.")) return;
    if (!confirm("Replace your code with the starter code?")) return;
    setCode(problem.starterCode);
    editor.current?.setValue(problem.starterCode);
  }

  async function toggleBookmark() {
    if (!requireAuth("Bookmarks are saved to your account.")) return;
    const next = !state?.bookmarked;
    setState((s) => (s ? { ...s, bookmarked: next } : s));
    await api(`/api/practice/problems/${problem.slug}/state`, { method: "PUT", body: { bookmarked: next } }).catch(handleError);
  }

  const startDrag = (e: React.PointerEvent) => {
    const container = (e.currentTarget as HTMLElement).parentElement!;
    const rect = container.getBoundingClientRect();
    const move = (ev: PointerEvent) => setSplit(Math.min(70, Math.max(25, ((ev.clientX - rect.left) / rect.width) * 100)));
    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  };

  const statusChip =
    state?.status === "solved" ? (
      <span className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-800 ring-1 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-300">Solved</span>
    ) : state?.status === "solved_assisted" ? (
      <span className="rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-800 ring-1 ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-300">Solved with solution</span>
    ) : state?.status === "attempted" ? (
      <span className="rounded-full bg-surface-sunken px-2.5 py-0.5 text-xs font-semibold text-fg-muted">Attempted</span>
    ) : null;

  const left = (
    <div className="flex h-full min-h-0 flex-col">
      <div role="tablist" aria-label="Problem panels" className="flex shrink-0 gap-1 overflow-x-auto border-b border-line px-3">
        {LEFT_TABS.map((t) => (
          <button
            key={t}
            role="tab"
            type="button"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
            className={`whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-medium ${tab === t ? "border-accent text-fg" : "border-transparent text-fg-muted hover:text-fg"}`}
          >
            {t}
          </button>
        ))}
      </div>
      <div role="tabpanel" className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-5">
        {tab === "Problem" && <ProblemPanel problem={problem} html={descriptionHtml} roleNames={roleNames} topicNames={topicNames} />}
        {tab === "Hints" && <HintsPanel problem={problem} state={state} setState={setState} locked={hintsLocked} sessionId={session?.id ?? null} onError={handleError} />}
        {tab === "Solution" && <SolutionPanel slug={problem.slug} state={state} setState={setState} locked={solutionLocked} sessionId={session?.id ?? null} onError={handleError} />}
        {tab === "Notes" && <NotesPanel slug={problem.slug} initial={state?.note ?? ""} onError={handleError} />}
        {tab === "Submissions" && <SubmissionsPanel state={state} />}
        {tab === "AI tutor" && <TutorPanel slug={problem.slug} code={code} enabled={aiEnabled} submissionId={submission?.id ?? state?.recent[0]?.id ?? null} onError={handleError} />}
      </div>
    </div>
  );

  const toolbar = (
    <div className="flex flex-wrap items-center gap-2 border-b border-line px-3 py-2">
      {execution.runtimes.length > 1 ? (
        <label className="flex items-center gap-1.5 text-sm text-fg-muted">
          <span className="sr-only">Python version</span>
          <Select value={runtime} onChange={(e) => setRuntime(e.target.value)} className="!min-h-9 !w-auto !py-1 !text-sm">
            {execution.runtimes.map((r) => (
              <option key={r.id} value={r.id}>
                {r.label}
              </option>
            ))}
          </Select>
        </label>
      ) : (
        <span className="text-sm text-fg-subtle">{execution.runtimes[0]?.label ?? "Python"}</span>
      )}
      <div className="flex items-center rounded-lg border border-line" role="group" aria-label="Font size">
        <button type="button" className="px-2 py-1 text-sm text-fg-muted hover:text-fg" onClick={() => setFontSize((f) => Math.max(11, f - 1))} aria-label="Smaller font">
          A−
        </button>
        <button type="button" className="px-2 py-1 text-sm text-fg-muted hover:text-fg" onClick={() => setFontSize((f) => Math.min(24, f + 1))} aria-label="Larger font">
          A+
        </button>
      </div>
      <Select value={themeMode} onChange={(e) => setThemeMode(e.target.value as typeof themeMode)} className="!min-h-9 !w-auto !py-1 !text-sm" aria-label="Editor theme">
        <option value="system">Site theme</option>
        <option value="light">Light editor</option>
        <option value="dark">Dark editor</option>
      </Select>
      <button type="button" onClick={() => setFullscreen((f) => !f)} className={buttonClass("ghost", "sm")} aria-pressed={fullscreen}>
        {fullscreen ? "Exit full screen" : "Full screen"}
      </button>
      <button type="button" onClick={reset} className={buttonClass("ghost", "sm")}>
        Reset
      </button>
      <span className="ml-auto text-xs text-fg-subtle" aria-live="polite">
        {signedIn ? (saved === "saving" ? "Saving…" : saved === "saved" ? "Draft saved" : "") : ""}
      </span>
    </div>
  );

  const actions = (
    <div className="flex flex-wrap items-center gap-2 border-t border-line px-3 py-2">
      {busy ? (
        <>
          <Spinner />
          <span className="text-sm text-fg-muted" aria-live="polite">
            {submission?.status === "queued" ? `Queued${submission.queuePosition ? ` (position ${submission.queuePosition})` : ""}…` : busy === "run" ? "Running…" : "Grading…"} {(elapsed / 1000).toFixed(1)} s
          </span>
          <Button variant="ghost" size="sm" onClick={() => void cancel()}>
            Cancel
          </Button>
        </>
      ) : (
        <span className="hidden text-xs text-fg-subtle sm:inline">Ctrl/⌘ + Enter runs · Ctrl/⌘ + Shift + Enter submits</span>
      )}
      <div className="ml-auto flex gap-2">
        <Button variant="secondary" size="sm" onClick={() => void execute("run")} disabled={Boolean(busy)}>
          Run
        </Button>
        <Button size="sm" onClick={() => void execute("submit")} disabled={Boolean(busy)}>
          Submit
        </Button>
      </div>
    </div>
  );

  const editorPane = (
    <div className="flex h-full min-h-0 flex-col">
      {toolbar}
      <div className="relative min-h-0 flex-1">
        {signedIn ? (
          <CodeEditor
            value={code}
            onChange={setCode}
            dark={dark}
            fontSize={fontSize}
            onRun={() => void execute("run")}
            onSubmit={() => void execute("submit")}
            onSave={() => void saveDraft(code)}
            handleRef={(h) => {
              editor.current = h;
            }}
          />
        ) : (
          <GuestEditor code={problem.starterCode} />
        )}
      </div>
      {signedIn && (
        <details className="border-t border-line px-3 py-2 text-sm">
          <summary className="cursor-pointer text-fg-muted">Custom inputs (Run only)</summary>
          <p className="mt-2 text-fg-subtle">One JSON array of arguments per line, up to five. Example for {problem.entrypoint}: {JSON.stringify(problem.examples[0]?.args ?? [])}</p>
          <Textarea value={custom} onChange={(e) => setCustom(e.target.value)} rows={3} className="mt-2 font-mono !text-sm" aria-label="Custom inputs" />
        </details>
      )}
      {actions}
    </div>
  );

  const results = <ResultsPanel submission={submission} error={error} entrypoint={problem.entrypoint} executionEnabled={execution.enabled} busy={busy} />;

  return (
    <div className={fullscreen ? "fixed inset-0 z-40 flex flex-col bg-canvas" : "flex flex-col"}>
      <div className="flex flex-wrap items-center gap-3 border-b border-line bg-surface px-4 py-3">
        <h1 className="min-w-0 text-lg font-semibold text-fg [overflow-wrap:anywhere] sm:text-xl">{problem.title}</h1>
        <DifficultyBadge difficulty={problem.difficulty} />
        {statusChip}
        <span className="text-sm text-fg-subtle">~{problem.minutes} min</span>
        <button type="button" onClick={() => void toggleBookmark()} aria-pressed={Boolean(state?.bookmarked)} className={`${buttonClass("ghost", "sm")} ml-auto`}>
          {state?.bookmarked ? "★ Bookmarked" : "☆ Bookmark"}
        </button>
      </div>
      {header}
      {/* Phones and tablets: one pane at a time. */}
      <div className="flex border-b border-line lg:hidden" role="tablist" aria-label="Workspace">
        {(["problem", "code", "results"] as const).map((p) => (
          <button key={p} role="tab" type="button" aria-selected={mobilePane === p} onClick={() => setMobilePane(p)} className={`flex-1 border-b-2 py-2.5 text-sm font-medium capitalize ${mobilePane === p ? "border-accent text-fg" : "border-transparent text-fg-muted"}`}>
            {p}
          </button>
        ))}
      </div>
      <div className="lg:hidden">
        <div className={mobilePane === "problem" ? "h-[70dvh]" : "hidden"}>{left}</div>
        <div className={mobilePane === "code" ? "flex h-[75dvh] flex-col" : "hidden"}>{editorPane}</div>
        <div className={mobilePane === "results" ? "min-h-[50dvh] p-4" : "hidden"}>{results}</div>
      </div>
      {/* Desktop: resizable split. */}
      <div className={`hidden min-h-0 lg:flex ${fullscreen ? "flex-1" : "h-[calc(100dvh-var(--spacing-header)-4rem)] min-h-[36rem]"}`}>
        <div style={{ width: `${split}%` }} className="min-w-0 border-r border-line bg-surface">
          {left}
        </div>
        <div
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize panels"
          aria-valuenow={Math.round(split)}
          aria-valuemin={25}
          aria-valuemax={70}
          tabIndex={0}
          onPointerDown={startDrag}
          onKeyDown={(e) => {
            if (e.key === "ArrowLeft") setSplit((s) => Math.max(25, s - 2));
            if (e.key === "ArrowRight") setSplit((s) => Math.min(70, s + 2));
          }}
          className="w-1.5 shrink-0 cursor-col-resize bg-line hover:bg-accent focus-visible:bg-accent"
        />
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="min-h-0 flex-[3]">{editorPane}</div>
          <div className="min-h-0 flex-[2] overflow-y-auto border-t border-line bg-surface-muted p-4">{results}</div>
        </div>
      </div>
    </div>
  );
}

function GuestEditor({ code }: { code: string }) {
  const { requireAuth } = usePracticeAuth();
  return (
    <div className="relative h-full min-h-[18rem]">
      <pre className="h-full overflow-auto bg-surface-muted p-4 font-mono text-sm leading-6 text-fg-muted" aria-label="Starter code (read only)">
        {code}
      </pre>
      <div className="absolute inset-x-0 bottom-0 flex justify-center border-t border-line bg-surface/95 p-4">
        <button type="button" onClick={() => requireAuth("The interactive editor is available to signed-in users.")} className={buttonClass("primary")}>
          Sign in to write and run code
        </button>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-6 first:mt-0">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-fg-subtle">{title}</h2>
      <div className="mt-2">{children}</div>
    </section>
  );
}

function ProblemPanel({ problem, html, roleNames, topicNames }: { problem: PublicProblem; html: string; roleNames: Record<string, string>; topicNames: Record<string, string> }) {
  return (
    <div className="text-[0.9375rem] leading-7 text-fg">
      <div className="prose-practice space-y-3 [&_code]:rounded [&_code]:bg-surface-sunken [&_code]:px-1 [&_code]:font-mono [&_code]:text-[0.875em] [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:bg-surface-sunken [&_pre]:p-3 [&_ul]:list-disc [&_ul]:pl-5" dangerouslySetInnerHTML={{ __html: html }} />
      <Section title="Function">
        <p>
          Implement <code className="rounded bg-surface-sunken px-1 font-mono text-sm">{problem.entrypoint}</code>. {problem.io.input && <>Input: {problem.io.input}. </>}
          {problem.io.output && <>Returns: {problem.io.output}.</>}
        </p>
      </Section>
      {problem.constraints.length > 0 && (
        <Section title="Constraints">
          <ul className="list-disc space-y-1 pl-5">
            {problem.constraints.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </Section>
      )}
      <Section title="Examples">
        <div className="space-y-3">
          {problem.examples.map((e, i) => (
            <div key={i} className="rounded-lg border border-line bg-surface-muted p-3 font-mono text-sm">
              <div className="text-fg">
                <span className="text-fg-subtle">&gt;&gt;&gt; </span>
                {callRepr(problem.entrypoint, e.args, e.kwargs)}
              </div>
              <div className="mt-1 text-fg-muted [overflow-wrap:anywhere]">{pyRepr(e.expected)}</div>
              {e.explanation && <p className="mt-2 font-sans text-[0.875rem] text-fg-muted">{e.explanation}</p>}
            </div>
          ))}
        </div>
      </Section>
      {problem.prelude && (
        <Section title="Provided environment">
          <p className="mb-2 text-sm text-fg-muted">This code runs before yours (fake clients, clocks and the test harness). You can use its names; don&apos;t edit them.</p>
          <pre className="max-h-80 overflow-auto rounded-lg bg-surface-sunken p-3 font-mono text-[0.8125rem] leading-5">{problem.prelude}</pre>
        </Section>
      )}
      <Section title="Details">
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
          <dt className="text-fg-subtle">Level</dt>
          <dd>{DIFFICULTY_INFO[problem.difficulty].criteria}</dd>
          <dt className="text-fg-subtle">Roles</dt>
          <dd>{problem.roles.map((r) => roleNames[r] ?? r).join(", ")}</dd>
          <dt className="text-fg-subtle">Topics</dt>
          <dd>{problem.topics.map((t) => topicNames[t] ?? t).join(", ")}</dd>
          <dt className="text-fg-subtle">Tests</dt>
          <dd>
            {problem.publicTestCount} public (run with Run), {problem.hiddenTestCount} hidden (graded on Submit)
          </dd>
          <dt className="text-fg-subtle">Grading</dt>
          <dd>{problem.comparator === "float" ? "Numbers compared with a small tolerance" : problem.comparator === "unordered" ? "Order of the returned list doesn't matter" : "Exact match of the return value"}</dd>
        </dl>
      </Section>
    </div>
  );
}

function HintsPanel({ problem, state, setState, locked, sessionId, onError }: { problem: PublicProblem; state: UserState | null; setState: (fn: (s: UserState | null) => UserState | null) => void; locked: boolean; sessionId: string | null; onError: (e: unknown) => void }) {
  const { requireAuth } = usePracticeAuth();
  const [busy, setBusy] = useState(false);
  const shown = state?.hints ?? [];
  const labels = ["Concept", "Approach", "Pseudocode"];
  async function open(level: number) {
    if (!requireAuth("Hints are recorded on your account so your progress stays honest.")) return;
    setBusy(true);
    try {
      const { hints } = await api<{ hints: string[] }>(`/api/practice/problems/${problem.slug}/assist`, { body: { action: "hint", level, sessionId } });
      setState((s) => (s ? { ...s, hints } : s));
    } catch (e) {
      onError(e);
    } finally {
      setBusy(false);
    }
  }
  if (locked) return <Alert tone="info">Hints are not available during a mock interview.</Alert>;
  return (
    <div className="space-y-4">
      <p className="text-sm text-fg-muted">Hints open one at a time, from a nudge to pseudocode. They&apos;re recorded, and each one lowers the XP for this problem by 10% (an independent solve still counts).</p>
      {shown.map((h, i) => (
        <div key={i} className="rounded-lg border border-line bg-surface-muted p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">
            Hint {i + 1} · {labels[i] ?? ""}
          </p>
          <pre className="mt-1 whitespace-pre-wrap font-sans text-[0.9375rem] leading-7 text-fg">{h}</pre>
        </div>
      ))}
      {shown.length < problem.hintCount && (
        <Button variant="secondary" loading={busy} onClick={() => void open(shown.length + 1)}>
          Show hint {shown.length + 1} ({labels[shown.length] ?? "more"})
        </Button>
      )}
    </div>
  );
}

function SolutionPanel({ slug, state, setState, locked, sessionId, onError }: { slug: string; state: UserState | null; setState: (fn: (s: UserState | null) => UserState | null) => void; locked: boolean; sessionId: string | null; onError: (e: unknown) => void }) {
  const { requireAuth } = usePracticeAuth();
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const solution = state?.solution;
  async function reveal() {
    setBusy(true);
    try {
      const { solution } = await api<{ solution: PracticeSolution }>(`/api/practice/problems/${slug}/assist`, { body: { action: "solution", confirm: true, sessionId } });
      setState((s) => (s ? { ...s, solution } : s));
      setConfirming(false);
    } catch (e) {
      onError(e);
    } finally {
      setBusy(false);
    }
  }
  if (locked) return <Alert tone="info">The reference solution is hidden until the assessment ends.</Alert>;
  if (!solution)
    return (
      <div className="space-y-3 text-[0.9375rem] text-fg-muted">
        <p>The reference solution includes a working implementation, a step-by-step explanation, complexity, alternatives, edge cases and production notes.</p>
        <Button variant="secondary" onClick={() => requireAuth("Revealing solutions is recorded on your account.") && setConfirming(true)}>
          Reveal solution
        </Button>
        <Dialog open={confirming} onClose={() => setConfirming(false)} title="Reveal the solution?" size="md">
          <div className="space-y-3 text-[0.9375rem] leading-7 text-fg-muted">
            <p>
              If you haven&apos;t solved this problem yet, a later accepted submission will count as <strong className="text-fg">solved with the solution</strong>, not as an independent solve,
              and it won&apos;t earn XP. Your time and attempts so far are recorded.
            </p>
            <p>You can keep experimenting with the code afterwards.</p>
            <div className="flex gap-2 pt-2">
              <Button loading={busy} onClick={() => void reveal()}>
                Reveal solution
              </Button>
              <Button variant="ghost" onClick={() => setConfirming(false)}>
                Keep trying
              </Button>
            </div>
          </div>
        </Dialog>
      </div>
    );
  return (
    <div className="space-y-5 text-[0.9375rem] leading-7">
      <pre className="overflow-x-auto rounded-lg bg-surface-sunken p-3 font-mono text-[0.8125rem] leading-5">{solution.code}</pre>
      <Section title="How it works">
        <p className="whitespace-pre-line">{solution.explanation}</p>
      </Section>
      <Section title="Complexity">
        <p>
          Time: {solution.time}. Space: {solution.space}.
        </p>
      </Section>
      {[
        ["Alternative approaches", solution.alternatives],
        ["Edge cases", solution.edgeCases],
        ["In production", solution.production],
      ].map(([title, items]) =>
        (items as string[]).length ? (
          <Section key={title as string} title={title as string}>
            <ul className="list-disc space-y-1 pl-5">
              {(items as string[]).map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
          </Section>
        ) : null,
      )}
    </div>
  );
}

function NotesPanel({ slug, initial, onError }: { slug: string; initial: string; onError: (e: unknown) => void }) {
  const { signedIn, requireAuth } = usePracticeAuth();
  const [note, setNote] = useState(initial);
  const [status, setStatus] = useState("");
  async function save() {
    if (!requireAuth("Notes are saved to your account.")) return;
    setStatus("Saving…");
    try {
      await api(`/api/practice/problems/${slug}/state`, { method: "PUT", body: { note } });
      setStatus("Saved");
    } catch (e) {
      setStatus("");
      onError(e);
    }
  }
  return (
    <div className="space-y-3">
      <p className="text-sm text-fg-muted">Private notes for this problem: what tripped you up, patterns to remember.</p>
      <Textarea value={note} onChange={(e) => setNote(e.target.value)} rows={10} maxLength={10_000} disabled={!signedIn} aria-label="Notes" />
      <div className="flex items-center gap-3">
        <Button variant="secondary" size="sm" onClick={() => void save()}>
          Save note
        </Button>
        <span className="text-sm text-fg-subtle" aria-live="polite">
          {status}
        </span>
      </div>
    </div>
  );
}

function SubmissionsPanel({ state }: { state: UserState | null }) {
  if (!state) return <p className="text-sm text-fg-muted">Sign in to see your submissions.</p>;
  if (!state.recent.length) return <p className="text-sm text-fg-muted">No submissions yet.</p>;
  return (
    <div className="space-y-2">
      <ul className="divide-y divide-line text-sm">
        {state.recent.map((r) => (
          <li key={r.id} className="flex items-center justify-between py-2">
            <span className={r.verdict === "accepted" ? "font-medium text-emerald-700 dark:text-emerald-300" : "text-fg"}>{VERDICTS[r.verdict as Verdict] ?? "Pending"}</span>
            <span className="text-fg-subtle">
              {r.passed}/{r.total} · {new Date(r.createdAt).toLocaleString()}
            </span>
          </li>
        ))}
      </ul>
      <Link href="/python-practice/history" className="text-sm text-accent-text underline">
        Full history
      </Link>
    </div>
  );
}

function TutorPanel({ slug, code, enabled, submissionId, onError }: { slug: string; code: string; enabled: boolean; submissionId: string | null; onError: (e: unknown) => void }) {
  const { requireAuth } = usePracticeAuth();
  const [answer, setAnswer] = useState<TutorAnswer | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const features: [string, string, boolean][] = [
    ["explain_error", "Explain my error", Boolean(submissionId)],
    ["explain_failure", "Why did a test fail?", Boolean(submissionId)],
    ["review", "Review my code", true],
    ["complexity", "Complexity", true],
    ["suggest_tests", "Suggest test cases", true],
  ];
  async function ask(feature: string) {
    if (!requireAuth("The AI tutor is available to signed-in users.")) return;
    setBusy(feature);
    try {
      setAnswer(await api<TutorAnswer>("/api/practice/ai", { body: { feature, slug, code, submissionId: submissionId ?? undefined, question: feature === "concept" ? question : undefined } }));
    } catch (e) {
      onError(e);
    } finally {
      setBusy(null);
    }
  }
  if (!enabled) return <Alert tone="info">The AI tutor isn&apos;t enabled on this site. Hints and the reference solution are always available.</Alert>;
  return (
    <div className="space-y-4">
      <p className="text-sm text-fg-muted">
        The tutor explains and nudges; it won&apos;t write the solution for you. It sees the problem, your code and public test results — never hidden tests. The grader&apos;s verdict always wins.
      </p>
      <div className="flex flex-wrap gap-2">
        {features.map(([id, label, ok]) => (
          <Button key={id} variant="secondary" size="sm" disabled={!ok || Boolean(busy)} loading={busy === id} onClick={() => void ask(id)}>
            {label}
          </Button>
        ))}
      </div>
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (question.trim()) void ask("concept");
        }}
      >
        <input value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={500} placeholder="Ask about a Python concept…" className="min-h-9 flex-1 rounded-lg border border-line-strong bg-surface px-3 text-sm" aria-label="Question for the tutor" />
        <Button size="sm" type="submit" disabled={Boolean(busy) || !question.trim()} loading={busy === "concept"}>
          Ask
        </Button>
      </form>
      {answer && (
        <div className="space-y-3 rounded-lg border border-line bg-surface-muted p-4 text-[0.9375rem] leading-7" aria-live="polite">
          {answer.facts && (
            <p className="text-sm text-fg-subtle">
              Grader: {VERDICTS[answer.facts.verdict as Verdict] ?? "pending"}, {answer.facts.passed}/{answer.facts.total} tests.
            </p>
          )}
          {answer.grounding && <Alert tone="info">{answer.grounding}</Alert>}
          <p className="font-medium text-fg">{answer.summary}</p>
          {answer.points.length > 0 && (
            <ul className="list-disc space-y-1 pl-5">
              {answer.points.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          )}
          {answer.code && <pre className="overflow-x-auto rounded bg-surface-sunken p-3 font-mono text-[0.8125rem]">{answer.code}</pre>}
          {answer.next_step && (
            <p>
              <strong>Next:</strong> {answer.next_step}
            </p>
          )}
          <p className="text-xs text-fg-subtle">AI-generated. It can be wrong; the test results are authoritative.</p>
        </div>
      )}
    </div>
  );
}

const STATUS_STYLE: Record<string, string> = {
  passed: "text-emerald-700 dark:text-emerald-300",
  failed: "text-red-700 dark:text-red-300",
  error: "text-red-700 dark:text-red-300",
  timeout: "text-amber-800 dark:text-amber-300",
  memory: "text-amber-800 dark:text-amber-300",
  skipped: "text-fg-subtle",
};

function ResultsPanel({ submission, error, entrypoint, executionEnabled, busy }: { submission: Submission | null; error: string | null; entrypoint: string; executionEnabled: boolean; busy: string | null }) {
  const verdict = submission?.verdict;
  const done = submission && (submission.status === "completed" || submission.status === "error");
  const hidden = useMemo(() => submission?.results.filter((r) => r.visibility === "hidden") ?? [], [submission]);
  if (error) return <Alert>{error}</Alert>;
  if (!submission)
    return (
      <p className="text-sm text-fg-muted">
        {busy ? "Starting…" : executionEnabled ? "Run executes the public tests. Submit grades against public and hidden tests." : "Running code is not enabled on this site yet."}
      </p>
    );
  if (!done) return <p className="text-sm text-fg-muted">Waiting for the sandbox…</p>;
  return (
    <div className="space-y-4">
      <div className={`rounded-lg border p-3 ${verdict === "accepted" ? "border-emerald-200 bg-emerald-50 dark:border-emerald-500/30 dark:bg-emerald-500/10" : "border-line bg-surface"}`} role="status">
        <p className="font-semibold text-fg">
          {submission.kind === "run" ? "Run" : "Submission"}: {verdict ? VERDICTS[verdict] : "—"}
          {submission.total > 0 && (
            <span className="font-normal text-fg-muted">
              {" "}
              · {submission.passed}/{submission.total} tests passed
            </span>
          )}
        </p>
        <p className="mt-1 text-sm text-fg-muted">
          {[submission.pythonVersion && `Python ${submission.pythonVersion}`, submission.maxMs !== null && `slowest test ${submission.maxMs.toFixed(1)} ms`, submission.maxMemoryKb && `peak memory ${(submission.maxMemoryKb / 1024).toFixed(1)} MiB`]
            .filter(Boolean)
            .join(" · ")}
        </p>
        {submission.kind === "submit" && verdict === "accepted" && <p className="mt-1 text-sm text-fg">{submission.independent ? `Solved independently.${submission.xp ? ` +${submission.xp} XP.` : ""}` : "Accepted — counted as solved with the solution."}</p>}
        {submission.badges?.length ? <p className="mt-1 text-sm font-medium text-fg">New achievement: {submission.badges.join(", ")}</p> : null}
      </div>
      {submission.loadError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-200">
          <p className="font-semibold">
            {submission.loadError.type}
            {submission.loadError.line ? ` on line ${submission.loadError.line}` : ""}
          </p>
          <pre className="mt-1 whitespace-pre-wrap font-mono">{submission.loadError.message}</pre>
        </div>
      )}
      {submission.results
        .filter((r) => r.visibility === "public")
        .map((r) => (
          <details key={r.index} className="rounded-lg border border-line bg-surface p-3 text-sm" open={r.status !== "passed"}>
            <summary className="cursor-pointer">
              <span className={`font-semibold ${STATUS_STYLE[r.status]}`}>{r.status === "passed" ? "✓ Passed" : r.status === "failed" ? "✗ Wrong answer" : r.status === "error" ? "✗ Error" : r.status === "timeout" ? "⏱ Time limit" : r.status === "memory" ? "Memory limit" : "Skipped"}</span>{" "}
              <code className="font-mono text-fg-muted">{callRepr(entrypoint, r.args, r.kwargs).slice(0, 120)}</code>
              {r.ms !== undefined && <span className="ml-2 text-fg-subtle">{r.ms} ms</span>}
            </summary>
            <dl className="mt-2 grid grid-cols-[6rem_1fr] gap-x-3 gap-y-1 font-mono text-[0.8125rem]">
              <dt className="font-sans text-fg-subtle">Expected</dt>
              <dd className="[overflow-wrap:anywhere]">{pyRepr(r.expected)}</dd>
              <dt className="font-sans text-fg-subtle">Got</dt>
              <dd className="[overflow-wrap:anywhere]">{r.actual !== undefined ? pyRepr(r.actual) : (r.actualRepr ?? "—")}</dd>
              {r.stdout && (
                <>
                  <dt className="font-sans text-fg-subtle">Printed</dt>
                  <dd>
                    <pre className="whitespace-pre-wrap">{r.stdout}</pre>
                  </dd>
                </>
              )}
              {r.error && (
                <>
                  <dt className="font-sans text-fg-subtle">Error</dt>
                  <dd>
                    <pre className="whitespace-pre-wrap text-red-700 dark:text-red-300">{r.error.traceback || `${r.error.type}: ${r.error.message}`}</pre>
                  </dd>
                </>
              )}
            </dl>
          </details>
        ))}
      {hidden.length > 0 && (
        <div className="rounded-lg border border-line bg-surface p-3 text-sm">
          <p className="font-medium text-fg">
            Hidden tests: {hidden.filter((h) => h.status === "passed").length}/{hidden.length} passed
          </p>
          <p className="mt-1 flex flex-wrap gap-1.5" aria-label="Hidden test results">
            {hidden.map((h, i) => (
              <span key={h.index} title={`Hidden test ${i + 1}: ${h.status}`} className={`inline-flex h-6 min-w-6 items-center justify-center rounded px-1 text-xs font-semibold ${h.status === "passed" ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300" : "bg-red-100 text-red-800 dark:bg-red-500/15 dark:text-red-300"}`}>
                {h.status === "passed" ? "✓" : h.status === "timeout" ? "⏱" : "✗"}
              </span>
            ))}
          </p>
          <p className="mt-2 text-fg-subtle">Inputs and outputs of hidden tests are not shown. Think about edge cases: empty input, duplicates, boundaries, large values.</p>
        </div>
      )}
      {submission.custom.map((r) => (
        <div key={`c${r.index}`} className="rounded-lg border border-line bg-surface p-3 text-sm">
          <p className="font-semibold text-fg">Custom input {r.index + 1}</p>
          <p className="mt-1 font-mono text-[0.8125rem] [overflow-wrap:anywhere]">→ {r.actual !== undefined ? pyRepr(r.actual) : (r.actualRepr ?? r.status)}</p>
          {r.stdout && <pre className="mt-1 whitespace-pre-wrap font-mono text-[0.8125rem] text-fg-muted">{r.stdout}</pre>}
          {r.error && <pre className="mt-1 whitespace-pre-wrap font-mono text-[0.8125rem] text-red-700 dark:text-red-300">{r.error.traceback || `${r.error.type}: ${r.error.message}`}</pre>}
        </div>
      ))}
    </div>
  );
}
