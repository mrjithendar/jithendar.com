import type { MouseEvent } from "react";

/**
 * Click handler for rendered comment HTML: the "Copy" buttons in code blocks (lib/comment-highlight) copy their
 * block's text. One delegated handler, because the HTML is server-rendered, not React elements.
 */
export async function copyCodeOnClick(e: MouseEvent<HTMLElement>) {
  const button = (e.target as HTMLElement).closest<HTMLButtonElement>("button[data-copy-code]");
  const pre = button?.closest(".comment-code")?.querySelector("pre");
  if (!button || !pre) return;
  try {
    await navigator.clipboard.writeText(pre.textContent ?? "");
    button.textContent = "Copied";
  } catch {
    button.textContent = "Copy failed";
  }
  setTimeout(() => (button.textContent = "Copy"), 2000);
}
