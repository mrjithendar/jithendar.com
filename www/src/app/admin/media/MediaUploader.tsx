"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { finishUpload, requestUpload, uploadMedia } from "@/app/admin/_actions/shared";
import { Alert, Button, Input, Select } from "@/components/ui/form";

const ACCEPT = "image/jpeg,image/png,image/webp,image/avif,image/gif,video/mp4,video/webm,audio/mpeg,audio/mp4,audio/x-m4a,audio/ogg,audio/wav,audio/x-wav,application/pdf";
/** Browsers report a few types under legacy names; send the canonical one (the server checks the bytes anyway). */
const CANONICAL: Record<string, string> = { "audio/x-m4a": "audio/mp4", "audio/m4a": "audio/mp4", "audio/x-wav": "audio/wav", "audio/wave": "audio/wav", "audio/mp3": "audio/mpeg" };
const MAX_FILES = 20;
/** Images up to this size can go through the site when the browser cannot reach R2 directly (server action limit 11 MB). */
const RELAY_MAX_BYTES = 10 * 1024 * 1024;

/** The browser could not talk to R2 at all: almost always a missing or wrong CORS policy on the bucket. */
class DirectUploadBlocked extends Error {}

async function sha256Hex(file: File): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** "team-photo_2026.jpg" → "Team photo 2026": a starting point the author should improve, never a final alt text. */
function altFromName(name: string): string {
  const base = name.replace(/\.[a-z0-9]+$/i, "").replace(/[-_]+/g, " ").replace(/\s+/g, " ").trim();
  return base ? base[0]!.toUpperCase() + base.slice(1) : "";
}

type Queued = { key: string; file: File; alt: string; visibility: "public" | "private"; state: "ready" | "uploading" | "done" | "error"; progress: number; error?: string };

/**
 * Drop or choose up to 20 files; each gets alt text (pre-filled from its name, editable, required for images)
 * and visibility, then uploads straight from the browser to R2 with a short-lived presigned URL (large videos
 * never pass through the site's pods). The server verifies size, checksum and real type of every file.
 */
export function MediaUploader() {
  const router = useRouter();
  const [queue, setQueue] = useState<Queued[]>([]);
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const current = useRef<XMLHttpRequest | null>(null);
  const cancelled = useRef(false);

  const update = (key: string, patch: Partial<Queued>) => setQueue((q) => q.map((x) => (x.key === key ? { ...x, ...patch } : x)));

  function add(files: FileList | File[]) {
    setNotice(null);
    const list = [...files].slice(0, MAX_FILES);
    if (files.length > MAX_FILES) setNotice(`Only the first ${MAX_FILES} files were added.`);
    setQueue((q) => [
      ...q.filter((x) => x.state !== "done"),
      ...list.map((file) => ({ key: `${file.name}-${file.size}-${crypto.randomUUID()}`, file, alt: file.type.startsWith("image/") ? altFromName(file.name) : "", visibility: "public" as const, state: "ready" as const, progress: 0 })),
    ]);
  }

  async function uploadOne(item: Queued) {
    update(item.key, { state: "uploading", progress: 0, error: undefined });
    try {
      const contentType = CANONICAL[item.file.type] ?? item.file.type;
      const intent = await requestUpload({ filename: item.file.name, contentType, size: item.file.size, sha256: await sha256Hex(item.file), alt: item.alt, visibility: item.visibility, context: "library" });
      if (!intent.ok) throw new Error(intent.error);
      await new Promise<void>((resolve, reject) => {
        const req = new XMLHttpRequest();
        current.current = req;
        req.open("PUT", intent.uploadUrl);
        for (const [k, v] of Object.entries(intent.headers)) req.setRequestHeader(k, v);
        req.upload.onprogress = (ev) => ev.lengthComputable && update(item.key, { progress: Math.round((ev.loaded / ev.total) * 100) });
        req.onload = () => (req.status >= 200 && req.status < 300 ? resolve() : reject(new Error(`Upload failed (HTTP ${req.status}). Check the bucket's CORS policy.`)));
        req.onerror = () => reject(new DirectUploadBlocked(`The browser could not upload to Cloudflare R2: the bucket's CORS policy must allow PUT from ${window.location.origin} (docs/MEDIA.md, deploy/r2/cors.json).`));
        req.onabort = () => reject(new Error("Cancelled."));
        req.send(item.file);
      });
      const done = await finishUpload(intent.id);
      if (!done.ok) throw new Error(done.error);
      update(item.key, { state: "done", progress: 100 });
    } catch (err) {
      // Images can still be uploaded through the site (it writes to R2 server-side, so CORS does not apply).
      if (err instanceof DirectUploadBlocked && item.file.type.startsWith("image/") && item.file.size <= RELAY_MAX_BYTES && item.visibility === "public") {
        const form = new FormData();
        form.set("file", item.file);
        form.set("alt", item.alt);
        form.set("context", "library");
        const relayed = await uploadMedia(form).catch(() => null);
        if (relayed?.ok) return update(item.key, { state: "done", progress: 100 });
        if (relayed && !relayed.ok) return update(item.key, { state: "error", error: relayed.error });
      }
      update(item.key, { state: "error", error: (err as Error).message });
    } finally {
      current.current = null;
    }
  }

  async function uploadAll() {
    const todo = queue.filter((x) => x.state === "ready" || x.state === "error");
    const missing = todo.filter((x) => x.file.type.startsWith("image/") && !x.alt.trim());
    if (missing.length) {
      for (const m of missing) update(m.key, { state: "error", error: "Alt text is required for images." });
      return;
    }
    setBusy(true);
    cancelled.current = false;
    for (const item of todo) {
      if (cancelled.current) break;
      await uploadOne(item);
    }
    setBusy(false);
    router.refresh();
  }

  // Paste anywhere on the page (Cmd/Ctrl+V): copied files or a screenshot join the upload list.
  const addRef = useRef(add);
  useEffect(() => {
    addRef.current = add;
  });
  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => {
      const files = e.clipboardData?.files;
      if (!files?.length || busy) return;
      e.preventDefault();
      addRef.current(files);
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [busy]);

  const pending = queue.filter((x) => x.state === "ready" || x.state === "error").length;

  return (
    <div className="space-y-4">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          if (!busy && e.dataTransfer.files.length) add(e.dataTransfer.files);
        }}
        className={`flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-4 py-8 text-center transition-colors ${over ? "border-accent bg-accent-soft" : "border-line-strong"}`}
      >
        <p className="text-base font-semibold text-fg">Drop or paste files to upload</p>
        <p className="text-sm text-fg-subtle">or</p>
        <Button type="button" variant="secondary" onClick={() => input.current?.click()} disabled={busy}>Select files</Button>
        <input ref={input} type="file" multiple accept={ACCEPT} className="sr-only" tabIndex={-1} aria-hidden="true" onChange={(e) => { if (e.target.files?.length) add(e.target.files); e.target.value = ""; }} />
        <p className="mt-1 text-xs text-fg-subtle">Paste a screenshot or copied files with ⌘V / Ctrl+V anywhere on this page. Images up to 10 MB · MP4/WebM up to 200 MB · MP3/M4A/Ogg/WAV up to 50 MB · PDF up to 20 MB · up to {MAX_FILES} at a time.</p>
      </div>
      {notice && <Alert tone="info">{notice}</Alert>}

      {queue.length > 0 && (
        <div className="space-y-3">
          <ul className="divide-y divide-line rounded-xl border border-line">
            {queue.map((x) => {
              const image = x.file.type.startsWith("image/");
              const editable = x.state === "ready" || x.state === "error";
              return (
                <li key={x.key} className="grid gap-2 p-3 sm:grid-cols-[minmax(0,14rem)_minmax(0,1fr)_9rem_auto] sm:items-center">
                  <div className="min-w-0 text-sm">
                    <p className="truncate font-medium text-fg" title={x.file.name}>{x.file.name}</p>
                    <p className="text-xs text-fg-subtle">{(x.file.size / 1024 / 1024).toFixed(1)} MB</p>
                  </div>
                  <div>
                    <label className="sr-only" htmlFor={`alt-${x.key}`}>Alt text for {x.file.name}</label>
                    <Input id={`alt-${x.key}`} value={x.alt} maxLength={300} disabled={!editable || busy} placeholder={image ? "Alt text (required): what the image shows" : "Description (optional)"} aria-invalid={image && !x.alt.trim() ? true : undefined} onChange={(e) => update(x.key, { alt: e.target.value })} />
                  </div>
                  <div>
                    <label className="sr-only" htmlFor={`vis-${x.key}`}>Visibility</label>
                    <Select id={`vis-${x.key}`} value={x.visibility} disabled={!editable || busy} onChange={(e) => update(x.key, { visibility: e.target.value as Queued["visibility"] })}>
                      <option value="public">Public</option>
                      <option value="private">Private</option>
                    </Select>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    {x.state === "uploading" && <span className="tabular-nums text-fg-muted">{x.progress}%</span>}
                    {x.state === "done" && <span className="font-medium text-emerald-700 dark:text-emerald-300">Uploaded</span>}
                    {editable && !busy && <button type="button" className="text-fg-subtle underline" onClick={() => setQueue((q) => q.filter((y) => y.key !== x.key))}>Remove</button>}
                  </div>
                  {x.state === "uploading" && (
                    <div className="h-1.5 overflow-hidden rounded-full bg-surface-sunken sm:col-span-4" role="progressbar" aria-valuenow={x.progress} aria-valuemin={0} aria-valuemax={100} aria-label={`Uploading ${x.file.name}`}>
                      <div className="h-full bg-accent transition-[width]" style={{ width: `${x.progress}%` }} />
                    </div>
                  )}
                  {x.error && <p className="text-sm text-red-600 sm:col-span-4">{x.error}</p>}
                </li>
              );
            })}
          </ul>
          <div className="flex flex-wrap gap-2">
            {busy ? (
              <Button type="button" variant="secondary" onClick={() => { cancelled.current = true; current.current?.abort(); }}>Cancel</Button>
            ) : (
              <Button type="button" onClick={uploadAll} disabled={pending === 0}>Upload {pending} file(s)</Button>
            )}
            {!busy && <Button type="button" variant="ghost" onClick={() => setQueue([])}>Clear list</Button>}
          </div>
        </div>
      )}
    </div>
  );
}
