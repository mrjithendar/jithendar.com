"use client";

/**
 * Last-resort error page, when the root layout itself fails (database down while reading the site config, …).
 * It replaces the whole document, so it carries its own <html>/<body> and inline styles instead of the
 * layout's CSS. The digest is the same one onRequestError logs, so the editor can find the log line and trace.
 */
export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "system-ui, sans-serif", background: "#fafafa", color: "#18181b" }}>
        <main style={{ maxWidth: 520, margin: "0 auto", padding: "96px 24px", textAlign: "center" }}>
          <p style={{ fontFamily: "ui-monospace, monospace", fontSize: 14, fontWeight: 600, color: "#b91c1c" }}>Error</p>
          <h1 style={{ fontSize: 32, margin: "12px 0 0" }}>Something went wrong</h1>
          <p style={{ fontSize: 18, lineHeight: 1.6, color: "#52525b" }}>The site could not be loaded. Try again, or come back in a few minutes.</p>
          {error.digest && <p style={{ fontFamily: "ui-monospace, monospace", fontSize: 12, color: "#71717a" }}>Reference: {error.digest}</p>}
          <p style={{ marginTop: 32 }}>
            <button type="button" onClick={reset} style={{ padding: "10px 20px", fontSize: 16, borderRadius: 8, border: 0, background: "#18181b", color: "#fff", cursor: "pointer" }}>
              Try again
            </button>
          </p>
        </main>
      </body>
    </html>
  );
}
