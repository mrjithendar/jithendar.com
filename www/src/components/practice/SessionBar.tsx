"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/form";
import { MODE_INFO, type Mode } from "@/lib/practice/types";
import { api } from "./api";

/**
 * Session navigation and countdown. The deadline is the server's: the page receives the remaining milliseconds
 * at render time and counts down from there; at zero it asks the server again, which finalises the session.
 */
export function SessionBar({
  id,
  mode,
  remainingMs,
  current,
  items,
}: {
  id: string;
  mode: Mode;
  remainingMs: number | null;
  current: number;
  items: { position: number; title: string; status: string }[];
}) {
  const router = useRouter();
  const [deadline] = useState(() => (remainingMs === null ? null : Date.now() + remainingMs));
  const [left, setLeft] = useState(remainingMs);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (deadline === null) return;
    const t = setInterval(() => {
      const ms = Math.max(0, deadline - Date.now());
      setLeft(ms);
      if (ms === 0) {
        clearInterval(t);
        router.refresh();
      }
    }, 500);
    return () => clearInterval(t);
  }, [deadline, router]);
  async function act(action: "skip" | "finish" | "goto", position?: number) {
    if (action === "finish" && !confirm("Finish this session? Unsubmitted questions score zero.")) return;
    setBusy(true);
    try {
      await api(`/api/practice/sessions/${id}`, { body: { action, position } });
      if (action === "skip") router.push(`/python-practice/session/${id}?q=${Math.min(position! + 1, items.length - 1)}`);
      router.refresh();
    } finally {
      setBusy(false);
    }
  }
  const mm = left === null ? null : Math.floor(left / 60000);
  const ss = left === null ? null : Math.floor((left % 60000) / 1000);
  const urgent = left !== null && left < 5 * 60_000;
  return (
    <div className="flex flex-wrap items-center gap-3 border-b border-line bg-surface-muted px-4 py-2">
      <span className="text-sm font-medium text-fg">{MODE_INFO[mode].label}</span>
      <nav aria-label="Questions" className="flex flex-wrap gap-1">
        {items.map((it) => (
          <Link
            key={it.position}
            href={`/python-practice/session/${id}?q=${it.position}`}
            aria-current={it.position === current ? "step" : undefined}
            title={`${it.title} (${it.status})`}
            className={`inline-flex h-8 min-w-8 items-center justify-center rounded-md border px-2 text-sm ${it.position === current ? "border-accent bg-accent-soft text-accent-text" : "border-line bg-surface text-fg-muted"} ${it.status === "submitted" ? "font-semibold" : ""}`}
          >
            {it.position + 1}
            {it.status === "submitted" ? "✓" : it.status === "skipped" ? "↷" : ""}
          </Link>
        ))}
      </nav>
      {left !== null && (
        <span role="timer" aria-live={urgent ? "assertive" : "off"} className={`ml-auto font-mono text-lg tabular-nums ${urgent ? "text-red-700 dark:text-red-300" : "text-fg"}`}>
          {String(mm).padStart(2, "0")}:{String(ss).padStart(2, "0")}
        </span>
      )}
      <div className={`flex gap-2 ${left === null ? "ml-auto" : ""}`}>
        <Button variant="ghost" size="sm" disabled={busy} onClick={() => void act("skip", current)}>
          Skip
        </Button>
        <Button variant="secondary" size="sm" disabled={busy} onClick={() => void act("finish")}>
          Finish
        </Button>
      </div>
    </div>
  );
}
