"use client";

import { useRef, useState, type ComponentProps } from "react";
import { LANGUAGE_LABELS } from "@/lib/code-languages";
import { CheckIcon, CopyIcon } from "./icons";

/** Highlighted <pre> in a frame with its language and a keyboard-accessible, announced copy button. */
export function CodeBlock({ "data-language": language, ...props }: ComponentProps<"pre"> & { "data-language"?: string }) {
  const pre = useRef<HTMLPreElement>(null);
  const [status, setStatus] = useState("");
  const label = language && language !== "text" ? (LANGUAGE_LABELS[language] ?? language) : "";

  async function copy() {
    try {
      await navigator.clipboard.writeText(pre.current?.textContent ?? "");
      setStatus("Copied to clipboard");
    } catch {
      setStatus("Copy failed");
    }
    setTimeout(() => setStatus(""), 2000);
  }

  const copied = status === "Copied to clipboard";
  return (
    <div className="code-block not-prose">
      <div className="flex h-10 items-center justify-between gap-3 border-b border-line pl-4 pr-1.5">
        <span className="font-mono text-xs text-fg-subtle">{label}</span>
        <button
          type="button"
          onClick={copy}
          className="inline-flex h-8 items-center gap-1.5 rounded-md px-2.5 font-sans text-xs font-medium text-fg-muted transition-colors hover:bg-surface-sunken hover:text-fg"
        >
          {copied ? <CheckIcon className="h-3.5 w-3.5" /> : <CopyIcon className="h-3.5 w-3.5" />}
          {copied ? "Copied" : "Copy"}
          <span className="sr-only"> code{label ? ` (${label})` : ""}</span>
        </button>
      </div>
      <pre ref={pre} {...props} tabIndex={0} />
      <span role="status" aria-live="polite" className="sr-only">
        {status}
      </span>
    </div>
  );
}
