import type { Element, ElementContent, Root as HastRoot, RootContent } from "hast";
import { toString as hastToString } from "hast-util-to-string";
import type { Root as MdastRoot } from "mdast";
import rehypeStringify from "rehype-stringify";
import remarkGfm from "remark-gfm";
import remarkParse from "remark-parse";
import remarkRehype from "remark-rehype";
import { unified } from "unified";
import { visit } from "unist-util-visit";
import { codeLanguage, highlightComment } from "./comment-highlight";

/**
 * Comment Markdown → safe HTML. Readers get the basics (paragraphs, emphasis, links, lists, quotes, inline code
 * and code blocks, simple tables); everything else is reduced to its text:
 * - raw HTML in the source is shown as literal text, never parsed;
 * - only the elements in ALLOWED survive, with no attributes except a vetted `href` (http, https, mailto)
 *   and an ordered list's `start`; images become their alt text; headings become paragraphs;
 * - every link gets rel="nofollow ugc noopener noreferrer", and links whose text hides the destination are
 *   followed by its domain (e.g. "(github.com)") so readers see where they lead;
 * - fenced code blocks with a known language (```bash, ```yaml…) are highlighted with Shiki after sanitising,
 *   from the code's text only (lib/comment-highlight), and every code block gets a copy button.
 * The output of this function is the only comment HTML ever sent to the browser.
 */
const ALLOWED = new Set(["p", "br", "strong", "em", "del", "code", "pre", "blockquote", "ul", "ol", "li", "a", "hr", "table", "thead", "tbody", "tr", "th", "td"]);
const BLOCKS_AS_PARAGRAPH = new Set(["h1", "h2", "h3", "h4", "h5", "h6"]);
const SAFE_HREF = /^(https?:\/\/|mailto:)/i;

function rawHtmlAsText() {
  return (tree: MdastRoot) => {
    visit(tree, "html", (node) => {
      (node as unknown as { type: string }).type = "text";
    });
  };
}

function sanitize(children: (RootContent | ElementContent)[]): ElementContent[] {
  const out: ElementContent[] = [];
  for (const node of children) {
    if (node.type === "text") out.push(node);
    else if (node.type === "element") out.push(...sanitizeElement(node));
    // Comments, doctypes and raw nodes are dropped.
  }
  return out;
}

function sanitizeElement(node: Element): ElementContent[] {
  const children = sanitize(node.children);
  if (node.tagName === "img") {
    const alt = typeof node.properties?.alt === "string" ? node.properties.alt : "";
    return alt ? [{ type: "text", value: alt }] : [];
  }
  if (BLOCKS_AS_PARAGRAPH.has(node.tagName)) return [{ type: "element", tagName: "p", properties: {}, children }];
  if (!ALLOWED.has(node.tagName)) return children;
  const properties: Element["properties"] = {};
  if (node.tagName === "a") {
    const href = typeof node.properties?.href === "string" ? node.properties.href.trim() : "";
    // A link without a safe target keeps its text only.
    if (!SAFE_HREF.test(href)) return children;
    properties.href = href;
    properties.rel = ["nofollow", "ugc", "noopener", "noreferrer"];
    const link: Element = { type: "element", tagName: "a", properties, children };
    const host = linkHost(href);
    // Bare URLs already show their domain; [text](url) links get it appended.
    if (!host || hastToString(link).toLowerCase().includes(host)) return [link];
    return [link, { type: "text", value: " " }, { type: "element", tagName: "span", properties: { className: ["comment-link-host"] }, children: [{ type: "text", value: `(${host})` }] }];
  }
  // Fenced code keeps only a vetted language name, for highlighting below.
  if (node.tagName === "code") {
    const lang = codeLanguage(node.properties?.className);
    if (lang) properties.className = [`language-${lang}`];
  }
  if (node.tagName === "ol" && typeof node.properties?.start === "number" && node.properties.start > 1) {
    properties.start = Math.min(node.properties.start, 1_000_000);
  }
  return [{ type: "element", tagName: node.tagName, properties, children }];
}

/** "github.com" for https://www.github.com/x; null for mailto: and unparsable URLs. */
function linkHost(href: string): string | null {
  if (!/^https?:/i.test(href)) return null;
  try {
    return new URL(href).hostname.replace(/^www\./, "").toLowerCase() || null;
  } catch {
    return null;
  }
}

function sanitizeTree() {
  return (tree: HastRoot) => {
    // Loose text at the top level (e.g. a raw HTML block shown as text) goes into a paragraph.
    tree.children = sanitize(tree.children).map((node) =>
      node.type === "text" && node.value.trim() ? { type: "element", tagName: "p", properties: {}, children: [node] } : node,
    );
  };
}

const processor = unified()
  .use(remarkParse)
  .use(remarkGfm, { singleTilde: false })
  .use(rawHtmlAsText)
  // No allowDangerousHtml: raw HTML is already text; nothing else can produce it.
  .use(remarkRehype)
  .use(sanitizeTree)
  // After sanitising: generates its own markup from code text, never from the source's markup.
  .use(highlightComment)
  .use(rehypeStringify);

export function renderCommentMarkdown(source: string): string {
  return String(processor.processSync(source)).trim();
}
