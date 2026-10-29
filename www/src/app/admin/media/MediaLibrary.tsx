"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import { Dialog } from "@/components/admin/Dialog";
import { Alert, Button, buttonClass, Field, Input, Textarea } from "@/components/ui/form";
import type { MediaUse } from "@/lib/media";
import { bulkDeleteMediaAction, deleteMediaAction, mediaUsedInAction, saveMediaDetailsAction } from "./actions";

export type LibraryItem = {
  id: string;
  src: string;
  filename: string;
  kind: string;
  contentType: string;
  alt: string;
  title: string;
  caption: string;
  description: string;
  width: number | null;
  height: number | null;
  size: string;
  visibility: string;
  onLegacyStorage: boolean;
  uploadedAt: string;
  uploadedBy: string;
  uses: number;
  snippet: string;
};

type Limits = { alt: number; title: number; caption: number; description: number };

const ICON: Record<string, string> = { videos: "🎬", audio: "🎧", documents: "📄" };
const when = (iso: string) => new Date(iso).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });
const missingAlt = (m: LibraryItem) => m.kind === "images" && !m.alt.trim();

function Thumb({ item, className }: { item: LibraryItem; className: string }) {
  if (item.kind === "images" && item.visibility === "public") {
    // eslint-disable-next-line @next/next/no-img-element -- admin thumbnail
    return <img src={item.src} alt="" loading="lazy" width={item.width ?? undefined} height={item.height ?? undefined} className={`bg-surface-sunken object-cover ${className}`} />;
  }
  return (
    <span className={`flex items-center justify-center bg-surface-sunken text-3xl ${className}`} aria-hidden="true">
      {ICON[item.kind] ?? "🖼️"}
    </span>
  );
}

/**
 * The library grid/list. Click an item for its attachment details; "Bulk select" turns clicks into selection
 * for deleting several files at once (files still used by a post or page are always kept).
 */
export function MediaLibrary({
  items,
  view,
  viewHrefs,
  limits,
  total,
  filtered,
  clearHref,
}: {
  items: LibraryItem[];
  view: "grid" | "list";
  viewHrefs: { grid: string; list: string };
  limits: Limits;
  total: number;
  filtered: boolean;
  clearHref: string;
}) {
  const router = useRouter();
  const [bulk, setBulk] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [open, setOpen] = useState<LibraryItem | null>(null);
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const [pending, start] = useTransition();

  const toggle = (id: string) =>
    setSelected((s) => {
      const next = new Set(s);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  function activate(item: LibraryItem) {
    if (bulk) toggle(item.id);
    else setOpen(item);
  }

  function deleteSelected() {
    const ids = [...selected];
    const inUse = items.filter((i) => selected.has(i.id) && i.uses > 0).length;
    const note = inUse ? ` ${inUse} of them are in use and will be kept.` : "";
    if (!window.confirm(`Delete ${ids.length} file(s) permanently from storage? This cannot be undone.${note}`)) return;
    start(async () => {
      const r = await bulkDeleteMediaAction(ids);
      setMessage(r.ok ? { tone: "success", text: r.message } : { tone: "error", text: r.error });
      setSelected(new Set());
      router.refresh();
    });
  }

  const toolbar = (
    <div className="mb-4 flex flex-wrap items-center gap-2">
      <div className="inline-flex overflow-hidden rounded-lg border border-line" role="group" aria-label="View">
        <Link href={viewHrefs.grid} aria-current={view === "grid" ? "true" : undefined} className={`px-3 py-2 text-sm font-medium ${view === "grid" ? "bg-accent-soft text-accent-text" : "text-fg-muted hover:bg-surface-sunken"}`}>
          Grid
        </Link>
        <Link href={viewHrefs.list} aria-current={view === "list" ? "true" : undefined} className={`border-l border-line px-3 py-2 text-sm font-medium ${view === "list" ? "bg-accent-soft text-accent-text" : "text-fg-muted hover:bg-surface-sunken"}`}>
          List
        </Link>
      </div>
      <Button type="button" variant={bulk ? "primary" : "secondary"} size="sm" aria-pressed={bulk} onClick={() => { setBulk((b) => !b); setSelected(new Set()); }}>
        {bulk ? "Cancel selection" : "Bulk select"}
      </Button>
      {bulk && (
        <>
          <Button type="button" variant="ghost" size="sm" onClick={() => setSelected(new Set(items.map((i) => i.id)))}>Select all on page</Button>
          <Button type="button" variant="danger" size="sm" disabled={selected.size === 0} loading={pending} onClick={deleteSelected}>
            Delete permanently{selected.size ? ` (${selected.size})` : ""}
          </Button>
        </>
      )}
      <span className="ml-auto text-sm text-fg-subtle">{total} item(s)</span>
    </div>
  );

  return (
    <div>
      {toolbar}
      {message && <div className="mb-4"><Alert tone={message.tone}>{message.text}</Alert></div>}
      {items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-line-strong p-8 text-center text-sm text-fg-subtle">
          {filtered ? <>No media matches these filters. <Link href={clearHref} className="link">Clear filters</Link></> : "No files yet. Drop files above to upload."}
        </p>
      ) : view === "grid" ? (
        <ul className="grid grid-cols-2 gap-3 min-[520px]:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
          {items.map((m) => {
            const on = selected.has(m.id);
            return (
              <li key={m.id}>
                <button
                  type="button"
                  onClick={() => activate(m)}
                  aria-pressed={bulk ? on : undefined}
                  title={m.title || m.filename}
                  className={`group relative block w-full overflow-hidden rounded-lg border bg-surface text-left transition focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-accent/40 ${on ? "border-accent ring-2 ring-accent" : "border-line hover:border-line-strong"}`}
                >
                  <Thumb item={m} className="aspect-square w-full" />
                  <span className="sr-only">{m.title || m.alt || m.filename}</span>
                  {m.kind !== "images" && <span className="absolute inset-x-0 bottom-0 truncate bg-black/60 px-2 py-1 text-xs text-white">{m.filename}</span>}
                  <span className="absolute left-1.5 top-1.5 flex flex-wrap gap-1">
                    {missingAlt(m) && <span className="rounded bg-amber-500 px-1.5 py-0.5 text-[10px] font-semibold text-white">No alt</span>}
                    {m.visibility === "private" && <span className="rounded bg-slate-800/80 px-1.5 py-0.5 text-[10px] font-semibold text-white">Private</span>}
                  </span>
                  {bulk && (
                    <span className={`absolute right-1.5 top-1.5 flex h-6 w-6 items-center justify-center rounded border-2 text-xs font-bold ${on ? "border-accent bg-accent text-on-accent" : "border-white bg-black/30 text-transparent"}`} aria-hidden="true">✓</span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-line bg-surface">
          <table className="min-w-full divide-y divide-line text-sm">
            <thead className="bg-surface-muted text-left text-xs font-semibold text-fg-subtle">
              <tr>
                {bulk && <th className="w-10 px-3 py-2.5"><span className="sr-only">Select</span></th>}
                <th className="px-3 py-2.5">File</th>
                <th className="px-3 py-2.5">Alt text</th>
                <th className="px-3 py-2.5">Uploaded by</th>
                <th className="px-3 py-2.5">Used in</th>
                <th className="px-3 py-2.5">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {items.map((m) => (
                <tr key={m.id} className={selected.has(m.id) ? "bg-accent-soft" : "hover:bg-surface-muted"}>
                  {bulk && (
                    <td className="px-3 py-2">
                      <input type="checkbox" checked={selected.has(m.id)} onChange={() => toggle(m.id)} aria-label={`Select ${m.filename}`} />
                    </td>
                  )}
                  <td className="px-3 py-2">
                    <button type="button" onClick={() => setOpen(m)} className="flex items-center gap-3 text-left">
                      <Thumb item={m} className="h-12 w-12 shrink-0 rounded" />
                      <span className="min-w-0">
                        <span className="block max-w-xs truncate font-medium text-fg underline-offset-2 hover:underline">{m.title || m.filename}</span>
                        <span className="block text-xs text-fg-subtle">{m.filename} · {m.size}{m.width && m.height ? ` · ${m.width}×${m.height}` : ""}</span>
                      </span>
                    </button>
                  </td>
                  <td className="max-w-xs px-3 py-2 text-fg-muted">{missingAlt(m) ? <span className="font-semibold text-amber-700 dark:text-amber-300">Missing</span> : <span className="line-clamp-2">{m.alt || "—"}</span>}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-fg-muted">{m.uploadedBy}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-fg-muted">{m.uses > 0 ? `${m.uses} place(s)` : "Unattached"}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-fg-muted">{when(m.uploadedAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {open && (
        <AttachmentDetails
          key={open.id}
          item={open}
          limits={limits}
          onClose={() => setOpen(null)}
          onChanged={(text) => {
            setMessage({ tone: "success", text });
            router.refresh();
          }}
          onNavigate={(dir) => {
            const i = items.findIndex((x) => x.id === open.id);
            const next = items[i + dir];
            if (next) setOpen(next);
          }}
          hasPrev={items.findIndex((x) => x.id === open.id) > 0}
          hasNext={items.findIndex((x) => x.id === open.id) < items.length - 1}
        />
      )}
    </div>
  );
}

function CopyButton({ text, label }: { text: string; label: string }) {
  const [done, setDone] = useState(false);
  return (
    <Button
      type="button"
      variant="secondary"
      size="sm"
      onClick={async () => {
        await navigator.clipboard.writeText(text.startsWith("/") ? `${window.location.origin}${text}` : text);
        setDone(true);
        window.setTimeout(() => setDone(false), 1500);
      }}
    >
      {done ? "Copied" : label}
    </Button>
  );
}

/** WordPress-style "Attachment details": preview, file facts, editable text, usage, copy and delete. */
function AttachmentDetails({
  item,
  limits,
  onClose,
  onChanged,
  onNavigate,
  hasPrev,
  hasNext,
}: {
  item: LibraryItem;
  limits: Limits;
  onClose: () => void;
  onChanged: (message: string) => void;
  onNavigate: (dir: -1 | 1) => void;
  hasPrev: boolean;
  hasNext: boolean;
}) {
  const [values, setValues] = useState({ alt: item.alt, title: item.title, caption: item.caption, description: item.description });
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [uses, setUses] = useState<MediaUse[] | null>(null);
  const [pending, start] = useTransition();
  const dirty = values.alt !== item.alt || values.title !== item.title || values.caption !== item.caption || values.description !== item.description;

  useEffect(() => {
    let live = true;
    mediaUsedInAction(item.id).then((u) => live && setUses(u)).catch(() => live && setUses([]));
    return () => {
      live = false;
    };
  }, [item.id]);

  const set = (k: keyof typeof values) => (e: { target: { value: string } }) => {
    setSaved(false);
    setValues((v) => ({ ...v, [k]: e.target.value }));
  };

  function save() {
    setError(null);
    start(async () => {
      const r = await saveMediaDetailsAction(item.id, values);
      if (r.ok) {
        setSaved(true);
        onChanged("Attachment details saved.");
      } else setError(r.error);
    });
  }

  function remove() {
    if (item.uses > 0 || (uses && uses.length > 0)) return window.alert("This file is still used by a post or page. Remove it there first.");
    if (!window.confirm("Delete this file permanently from storage? This cannot be undone.")) return;
    start(async () => {
      const r = await deleteMediaAction(item.id);
      if (r.ok) {
        onClose();
        onChanged(r.message);
      } else setError(r.error);
    });
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title="Attachment details"
      footer={
        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" variant="ghost" size="sm" disabled={!hasPrev} onClick={() => onNavigate(-1)} aria-label="Previous item">←</Button>
          <Button type="button" variant="ghost" size="sm" disabled={!hasNext} onClick={() => onNavigate(1)} aria-label="Next item">→</Button>
          <button type="button" onClick={remove} className="ml-2 text-sm font-medium text-red-600 underline">Delete permanently</button>
          <div className="ml-auto flex gap-2">
            <Button type="button" variant="ghost" onClick={onClose}>Close</Button>
            <Button type="button" onClick={save} loading={pending} disabled={!dirty}>{saved && !dirty ? "Saved" : "Save"}</Button>
          </div>
        </div>
      }
    >
      <div className="grid gap-6 md:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <div className="space-y-3">
          <div className="flex min-h-48 items-center justify-center overflow-hidden rounded-lg border border-line bg-surface-sunken">
            {item.kind === "images" ? (
              // eslint-disable-next-line @next/next/no-img-element -- admin preview
              <img src={item.src} alt={values.alt} width={item.width ?? undefined} height={item.height ?? undefined} className="max-h-[50vh] w-auto max-w-full object-contain" />
            ) : item.kind === "videos" ? (
              <video src={item.src} controls preload="metadata" className="max-h-[50vh] w-full" />
            ) : item.kind === "audio" ? (
              <audio src={item.src} controls preload="metadata" className="w-full p-4" />
            ) : (
              <a href={item.src} target="_blank" rel="noopener" className="p-8 text-center text-5xl">
                📄<span className="mt-2 block text-sm text-fg-muted underline">Open {item.filename}</span>
              </a>
            )}
          </div>
          <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1 text-xs">
            <dt className="text-fg-subtle">Uploaded</dt><dd className="text-fg">{when(item.uploadedAt)}</dd>
            <dt className="text-fg-subtle">Uploaded by</dt><dd className="text-fg">{item.uploadedBy}</dd>
            <dt className="text-fg-subtle">File name</dt><dd className="break-all text-fg">{item.filename}</dd>
            <dt className="text-fg-subtle">File type</dt><dd className="text-fg">{item.contentType}</dd>
            <dt className="text-fg-subtle">File size</dt><dd className="text-fg">{item.size}</dd>
            {item.width && item.height ? <><dt className="text-fg-subtle">Dimensions</dt><dd className="text-fg">{item.width} × {item.height} px</dd></> : null}
            <dt className="text-fg-subtle">Visibility</dt><dd className="text-fg capitalize">{item.visibility}{item.onLegacyStorage ? " · legacy S3" : ""}</dd>
          </dl>
          <div className="flex flex-wrap gap-2">
            <CopyButton text={item.src} label="Copy URL" />
            <CopyButton text={item.snippet} label="Copy Markdown" />
            <a href={item.src} target="_blank" rel="noopener" className={buttonClass("ghost", "sm")}>Open file ↗</a>
          </div>
        </div>
        <div className="space-y-4">
          {error && <Alert>{error}</Alert>}
          <Field label="Alt text" htmlFor="d-alt" hint={item.kind === "images" ? "Required. Describe the purpose of the image for people who cannot see it; leave out “image of”." : "Optional description of the file."}>
            <Textarea id="d-alt" rows={2} maxLength={limits.alt} value={values.alt} onChange={set("alt")} aria-invalid={missingAlt({ ...item, alt: values.alt }) || undefined} />
          </Field>
          <Field label="Title" htmlFor="d-title" optional hint="Shown in the library instead of the file name.">
            <Input id="d-title" maxLength={limits.title} value={values.title} onChange={set("title")} />
          </Field>
          <Field label="Caption" htmlFor="d-caption" optional hint="Suggested caption when the image is inserted.">
            <Textarea id="d-caption" rows={2} maxLength={limits.caption} value={values.caption} onChange={set("caption")} />
          </Field>
          <Field label="Description" htmlFor="d-desc" optional hint="Internal notes: source, licence, credit.">
            <Textarea id="d-desc" rows={3} maxLength={limits.description} value={values.description} onChange={set("description")} />
          </Field>
          <div>
            <p className="text-sm font-medium text-fg">Used in</p>
            {uses === null ? (
              <p className="mt-1 text-sm text-fg-subtle">Checking…</p>
            ) : uses.length === 0 ? (
              <p className="mt-1 text-sm text-fg-subtle">{item.uses > 0 ? "Site settings (logo, banner or share image)." : "Not used anywhere."}</p>
            ) : (
              <ul className="mt-1 space-y-1 text-sm">
                {uses.map((u) => (
                  <li key={u.editHref} className="flex flex-wrap items-baseline gap-x-2">
                    <span className="text-xs uppercase text-fg-subtle">{u.kind}</span>
                    <Link href={u.editHref} className="link">{u.title}</Link>
                    {u.publicPath && <a href={u.publicPath} target="_blank" rel="noopener" className="text-xs text-fg-subtle underline">view</a>}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </Dialog>
  );
}
