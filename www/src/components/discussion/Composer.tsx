"use client";

import { useId, useRef, useState, useTransition } from "react";
import { LinkIcon } from "@/components/icons";
import { previewCommentAction } from "@/app/_actions/comments";
import { Alert, Button, Spinner, Textarea } from "@/components/ui/form";
import { copyCodeOnClick } from "./copy-code";
import { applyFormat, CODE_LANGUAGES, type Format } from "./markdown-format";

const MAX = 5000;

export type ComposerSubmit = (body: string, clientKey: string) => Promise<{ ok: true } | { ok: false; error: string }>;

const newKey = () => (typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`);

/**
 * Write / Preview composer for new comments, replies and edits. Preview is rendered on the server by the same
 * sanitiser that renders published comments. New comments and replies carry a client key (one per draft: a
 * double click or a retried request cannot post the same comment twice).
 */
export function Composer({
  label,
  submitLabel,
  pendingLabel = "Posting…",
  initial = "",
  autoFocus = false,
  onSubmit,
  onCancel,
}: {
  label: string;
  submitLabel: string;
  pendingLabel?: string;
  initial?: string;
  autoFocus?: boolean;
  onSubmit: ComposerSubmit;
  onCancel?: () => void;
}) {
  const id = useId();
  const [body, setBody] = useState(initial);
  const [tab, setTab] = useState<"write" | "preview">("write");
  const [preview, setPreview] = useState<{ html?: string; error?: string; loading?: boolean }>({});
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const clientKey = useRef(newKey());
  const textarea = useRef<HTMLTextAreaElement>(null);
  const [language, setLanguage] = useState<string>("bash");
  const length = body.trim().length;
  const tooLong = body.length > MAX;

  async function showPreview() {
    setTab("preview");
    if (length < 2) {
      setPreview({ error: "Nothing to preview yet." });
      return;
    }
    setPreview({ loading: true });
    const r = await previewCommentAction(body);
    setPreview(r.ok ? { html: r.html } : { error: r.error });
  }

  /** Toolbar and shortcuts: apply Markdown to the selection, then put the cursor/selection where it belongs. */
  function format(kind: Format) {
    const t = textarea.current;
    if (!t) return;
    const edit = applyFormat(kind, body, t.selectionStart, t.selectionEnd, { language });
    setBody(edit.value);
    requestAnimationFrame(() => {
      t.focus();
      t.setSelectionRange(edit.start, edit.end);
    });
  }

  function submit(e?: React.FormEvent) {
    e?.preventDefault();
    if (pending) return;
    setError(null);
    if (length < 2) return setError("Write a comment first.");
    if (tooLong) return setError(`Comments can be up to ${MAX} characters.`);
    start(async () => {
      const r = await onSubmit(body, clientKey.current);
      if (!r.ok) {
        setError(r.error);
        return;
      }
      setBody("");
      setTab("write");
      clientKey.current = newKey();
    });
  }

  const tabClass = (on: boolean) =>
    `min-h-9 rounded-md px-3 text-sm font-semibold transition-colors ${on ? "bg-surface text-fg shadow-sm" : "text-fg-muted hover:text-fg"}`;

  return (
    <form onSubmit={submit} className="space-y-3" aria-label={label}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label htmlFor={`${id}-body`} className="text-sm font-medium text-fg">
          {label}
        </label>
        <div role="group" aria-label="Editor mode" className="inline-flex rounded-lg bg-surface-sunken p-1">
          <button type="button" aria-pressed={tab === "write"} className={tabClass(tab === "write")} onClick={() => { setTab("write"); requestAnimationFrame(() => textarea.current?.focus()); }}>
            Write
          </button>
          <button type="button" aria-pressed={tab === "preview"} className={tabClass(tab === "preview")} onClick={showPreview}>
            Preview
          </button>
        </div>
      </div>
      <div hidden={tab !== "write"} className="overflow-hidden rounded-[var(--radius-control)] border border-line-strong focus-within:border-brand-500">
        <div role="toolbar" aria-label="Formatting" aria-controls={`${id}-body`} className="flex flex-wrap items-center gap-0.5 border-b border-line bg-surface-muted px-1.5 py-1">
          <Tool label="Bold (Ctrl/⌘ B)" onClick={() => format("bold")}>
            <b>B</b>
          </Tool>
          <Tool label="Italic (Ctrl/⌘ I)" onClick={() => format("italic")}>
            <i>I</i>
          </Tool>
          <Tool label="Link (Ctrl/⌘ K)" onClick={() => format("link")}>
            <LinkIcon className="h-4 w-4" />
          </Tool>
          <Tool label="Inline code (Ctrl/⌘ E)" onClick={() => format("code")}>
            <span className="font-mono text-xs">{"</>"}</span>
          </Tool>
          <span className="mx-1 h-5 w-px bg-line" aria-hidden="true" />
          <Tool label="Quote" onClick={() => format("quote")}>
            ❝
          </Tool>
          <Tool label="Bulleted list" onClick={() => format("list")}>
            •
          </Tool>
          <span className="mx-1 h-5 w-px bg-line" aria-hidden="true" />
          <Tool label={`Code block (${language})`} onClick={() => format("codeBlock")}>
            <span className="font-mono text-xs">{"{ }"}</span>
          </Tool>
          <select
            aria-label="Code block language"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="h-8 rounded-md border border-line bg-surface px-1.5 font-mono text-xs text-fg-muted"
          >
            {CODE_LANGUAGES.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </div>
        <Textarea
          ref={textarea}
          id={`${id}-body`}
          rows={4}
          value={body}
          autoFocus={autoFocus}
          onChange={(e) => setBody(e.target.value)}
          className="rounded-none! border-0! shadow-none! focus:ring-0!"
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
            const shortcut = e.metaKey || e.ctrlKey ? ({ b: "bold", i: "italic", k: "link", e: "code" } as const)[e.key.toLowerCase() as "b"] : undefined;
            if (shortcut && !e.shiftKey && !e.altKey) {
              e.preventDefault();
              format(shortcut);
            }
            if (e.key === "Escape" && onCancel && !body.trim()) onCancel();
          }}
          maxLength={MAX + 500}
          aria-invalid={tooLong || undefined}
          aria-describedby={`${id}-help`}
          placeholder="Add to the discussion…"
        />
      </div>
      {tab === "preview" && (
        <div className="min-h-[7.5rem] rounded-[var(--radius-control)] border border-line bg-surface-muted px-3.5 py-2.5" aria-live="polite" aria-busy={preview.loading || undefined}>
          {preview.loading && (
            <p className="flex items-center gap-2 text-sm text-fg-subtle">
              <Spinner /> Rendering preview…
            </p>
          )}
          {preview.error && <p className="text-sm text-fg-subtle">{preview.error}</p>}
          {preview.html && <div className="comment-body" onClick={copyCodeOnClick} dangerouslySetInnerHTML={{ __html: preview.html }} />}
        </div>
      )}
      <p id={`${id}-help`} className="flex flex-wrap justify-between gap-x-4 gap-y-1 text-xs text-fg-subtle">
        <span>
          Markdown works too: **bold**, _italic_, `code`, links (pasted URLs become links), and ```bash code blocks (highlighted). Your name and avatar are shown with your comment.
        </span>
        <span className={tooLong ? "font-semibold text-red-700 dark:text-red-300" : ""}>
          {body.length}/{MAX}
        </span>
      </p>
      {error && <Alert>{error}</Alert>}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" loading={pending} disabled={pending}>
          {pending ? pendingLabel : submitLabel}
        </Button>
        {onCancel && (
          <Button type="button" variant="ghost" onClick={onCancel} disabled={pending}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}

function Tool({ label, onClick, children }: { label: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      onClick={onClick}
      className="inline-flex h-8 min-w-8 items-center justify-center rounded-md px-1.5 text-sm text-fg-muted transition-colors hover:bg-surface-sunken hover:text-fg"
    >
      {children}
    </button>
  );
}
