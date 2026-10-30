/**
 * Comment composer toolbar: Markdown edits on a textarea's value and selection. Pure, so it is unit-tested
 * (tests/comment-format.test.ts); the composer applies the result and restores the selection.
 */
export type Format = "bold" | "italic" | "code" | "link" | "codeBlock" | "quote" | "list";
export type Edit = { value: string; start: number; end: number };

/** Code-block languages offered in the composer (highlighted by lib/comment-highlight). */
export const CODE_LANGUAGES = ["bash", "yaml", "json", "typescript", "javascript", "python", "go", "dockerfile", "hcl", "sql", "diff", "text"] as const;

const PLACEHOLDER: Record<Format, string> = { bold: "bold text", italic: "italic text", code: "code", link: "link text", codeBlock: "paste code here", quote: "quote", list: "item" };

/** Surround the selection (or a placeholder, selected) with `before`/`after`. */
function wrap(v: string, s: number, e: number, before: string, after: string, placeholder: string): Edit {
  const text = v.slice(s, e) || placeholder;
  return { value: v.slice(0, s) + before + text + after + v.slice(e), start: s + before.length, end: s + before.length + text.length };
}

/** Prefix every line touched by the selection (quote, list). */
function prefixLines(v: string, s: number, e: number, prefix: string, placeholder: string): Edit {
  const lineStart = v.lastIndexOf("\n", s - 1) + 1;
  const nextBreak = v.indexOf("\n", e);
  const lineEnd = nextBreak === -1 ? v.length : nextBreak;
  const block = v.slice(lineStart, lineEnd) || placeholder;
  const out = block.split("\n").map((l) => prefix + l).join("\n");
  return { value: v.slice(0, lineStart) + out + v.slice(lineEnd), start: lineStart, end: lineStart + out.length };
}

/** Put a block on its own lines: a blank line before and after unless already at an edge. */
function ownLines(v: string, s: number, e: number) {
  const pre = s === 0 || v.slice(0, s).endsWith("\n\n") ? "" : v.slice(0, s).endsWith("\n") ? "\n" : "\n\n";
  const post = e === v.length || v.slice(e).startsWith("\n\n") ? "" : v.slice(e).startsWith("\n") ? "\n" : "\n\n";
  return { pre, post };
}

export function applyFormat(kind: Format, v: string, s: number, e: number, opts: { language?: string } = {}): Edit {
  switch (kind) {
    case "bold":
      return wrap(v, s, e, "**", "**", PLACEHOLDER.bold);
    case "italic":
      return wrap(v, s, e, "_", "_", PLACEHOLDER.italic);
    case "code":
      return wrap(v, s, e, "`", "`", PLACEHOLDER.code);
    case "link": {
      const selected = v.slice(s, e);
      // A selected URL becomes the target; otherwise the selection is the text and "https://" is selected to replace.
      if (/^https?:\/\/\S+$/i.test(selected)) {
        const text = PLACEHOLDER.link;
        return { value: `${v.slice(0, s)}[${text}](${selected})${v.slice(e)}`, start: s + 1, end: s + 1 + text.length };
      }
      const text = selected || PLACEHOLDER.link;
      const head = `${v.slice(0, s)}[${text}](`;
      return { value: `${head}https://)${v.slice(e)}`, start: head.length, end: head.length + "https://".length };
    }
    case "codeBlock": {
      const { pre, post } = ownLines(v, s, e);
      const fence = "```" + (opts.language && opts.language !== "text" ? opts.language : "");
      const edit = wrap(v, s, e, `${pre}${fence}\n`, `\n\`\`\`${post}`, PLACEHOLDER.codeBlock);
      return edit;
    }
    case "quote":
      return prefixLines(v, s, e, "> ", PLACEHOLDER.quote);
    case "list":
      return prefixLines(v, s, e, "- ", PLACEHOLDER.list);
  }
}
