"use client";

import { useEffect, useId, useRef, useState, useSyncExternalStore, type ComponentProps } from "react";

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

/**
 * A ```mermaid fence drawn as a diagram in the browser. The server sends the highlighted source, so
 * readers without JavaScript (and crawlers) still get the text; the Mermaid library is only downloaded
 * on pages that contain a diagram. `securityLevel: "strict"` sanitises labels and disables click handlers,
 * so a diagram can never run script. If the source does not parse, the code block stays as it is.
 */
export function MermaidBlock(props: ComponentProps<"pre">) {
  const pre = useRef<HTMLPreElement>(null);
  const id = `mermaid-${useId().replace(/[^a-zA-Z0-9_-]/g, "")}`;
  const dark = useSyncExternalStore(subscribeTheme, siteIsDark, () => false);
  const [svg, setSvg] = useState<string | null>(null);
  const [showSource, setShowSource] = useState(false);

  useEffect(() => {
    const source = pre.current?.textContent ?? "";
    let cancelled = false;
    import("mermaid")
      .then(async ({ default: mermaid }) => {
        mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: dark ? "dark" : "default" });
        const { svg } = await mermaid.render(id, source);
        if (!cancelled) setSvg(svg);
      })
      .catch(() => {
        if (!cancelled) setSvg(null);
      });
    return () => {
      cancelled = true;
    };
  }, [id, dark]);

  return (
    <div className="code-block not-prose">
      <div className="flex h-10 items-center justify-between gap-3 border-b border-line pl-4 pr-1.5">
        <span className="font-mono text-xs text-fg-subtle">{svg ? "Diagram" : "Mermaid"}</span>
        {svg && (
          <button
            type="button"
            onClick={() => setShowSource((s) => !s)}
            aria-pressed={showSource}
            className="inline-flex h-8 items-center rounded-md px-2.5 font-sans text-xs font-medium text-fg-muted transition-colors hover:bg-surface-sunken hover:text-fg"
          >
            {showSource ? "Show diagram" : "Show source"}
          </button>
        )}
      </div>
      {svg && !showSource && (
        // Mermaid's SVG carries its own role and accessible title.
        <div className="mermaid-diagram" dangerouslySetInnerHTML={{ __html: svg }} />
      )}
      <pre ref={pre} {...props} hidden={Boolean(svg) && !showSource} tabIndex={0} />
    </div>
  );
}
