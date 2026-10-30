import type { Element, ElementContent, Root as HastRoot } from "hast";
import { createHighlighterCoreSync, type HighlighterCore } from "shiki/core";
import { createJavaScriptRegexEngine } from "shiki/engine/javascript";
import css from "shiki/langs/css.mjs";
import diff from "shiki/langs/diff.mjs";
import dockerfile from "shiki/langs/dockerfile.mjs";
import go from "shiki/langs/go.mjs";
import hcl from "shiki/langs/hcl.mjs";
import html from "shiki/langs/html.mjs";
import ini from "shiki/langs/ini.mjs";
import java from "shiki/langs/java.mjs";
import javascript from "shiki/langs/javascript.mjs";
import json from "shiki/langs/json.mjs";
import jsx from "shiki/langs/jsx.mjs";
import markdown from "shiki/langs/markdown.mjs";
import nginx from "shiki/langs/nginx.mjs";
import python from "shiki/langs/python.mjs";
import rust from "shiki/langs/rust.mjs";
import shellscript from "shiki/langs/shellscript.mjs";
import shellsession from "shiki/langs/shellsession.mjs";
import sql from "shiki/langs/sql.mjs";
import terraform from "shiki/langs/terraform.mjs";
import toml from "shiki/langs/toml.mjs";
import tsx from "shiki/langs/tsx.mjs";
import typescript from "shiki/langs/typescript.mjs";
import yaml from "shiki/langs/yaml.mjs";
import githubDark from "shiki/themes/github-dark.mjs";
import githubLight from "shiki/themes/github-light.mjs";
import { visit } from "unist-util-visit";
import { LANGUAGE_LABELS } from "./code-languages";

/**
 * Code blocks in comments (lib/comment-markdown): Shiki highlighting with the articles' themes, a language label
 * and a copy button (wired up by CommentItem). Runs after the sanitiser and builds its markup from the code's
 * text alone, so nothing from the comment's source reaches an attribute. A fixed set of languages, loaded once,
 * with the JavaScript regex engine: highlighting is synchronous, like the rest of comment rendering.
 */
const LANGS = [css, diff, dockerfile, go, hcl, html, ini, java, javascript, json, jsx, markdown, nginx, python, rust, shellscript, shellsession, sql, terraform, toml, tsx, typescript, yaml];
const THEMES = { light: "github-light", dark: "github-dark" } as const;
/** Longer blocks are shown plain (comments are capped at 5000 characters anyway). */
const MAX_HIGHLIGHT_CHARS = 10_000;
const LANGUAGE_CLASS = /^language-([a-z0-9][a-z0-9+#_-]{0,23})$/i;

let highlighter: HighlighterCore | undefined;
let known: Set<string> | undefined;
function getHighlighter() {
  highlighter ??= createHighlighterCoreSync({ themes: [githubLight, githubDark], langs: LANGS.flat(), engine: createJavaScriptRegexEngine() });
  known ??= new Set(highlighter.getLoadedLanguages());
  return { highlighter, known };
}

/** The language of a fenced block from remark's className (["language-bash"]), lower-cased; null if absent or odd. */
export function codeLanguage(className: unknown): string | null {
  const classes = Array.isArray(className) ? className : typeof className === "string" ? className.split(/\s+/) : [];
  for (const c of classes) {
    const m = typeof c === "string" ? LANGUAGE_CLASS.exec(c) : null;
    if (m) return m[1]!.toLowerCase();
  }
  return null;
}

const el = (tagName: string, properties: Element["properties"], children: ElementContent[]): Element => ({ type: "element", tagName, properties, children });

function codeBlock(pre: Element): Element {
  const code = pre.children.find((c): c is Element => c.type === "element" && c.tagName === "code");
  const text = code ? code.children.map((c) => (c.type === "text" ? c.value : "")).join("") : "";
  const lang = code ? codeLanguage(code.properties?.className) : null;
  const { highlighter, known } = getHighlighter();
  let body: Element = el("pre", { tabIndex: 0 }, [el("code", {}, [{ type: "text", value: text }])]);
  if (lang && known.has(lang) && text.length <= MAX_HIGHLIGHT_CHARS) {
    const root = highlighter.codeToHast(text.replace(/\n$/, ""), { lang, themes: THEMES, defaultColor: "light" });
    const highlighted = root.children.find((c): c is Element => c.type === "element" && c.tagName === "pre");
    if (highlighted) body = highlighted;
  }
  const label = lang ? (LANGUAGE_LABELS[lang] ?? (known.has(lang) ? lang : "")) : "";
  return el("div", { className: ["comment-code"] }, [
    el("div", { className: ["comment-code-bar"] }, [
      el("span", { className: ["comment-code-lang"] }, label ? [{ type: "text", value: label }] : []),
      el("button", { type: "button", className: ["comment-code-copy"], dataCopyCode: "" }, [{ type: "text", value: "Copy" }]),
    ]),
    body,
  ]);
}

/** Rehype step: wraps every <pre> (after sanitising) in a labelled, copyable, highlighted block. */
export function highlightComment() {
  return (tree: HastRoot) => {
    visit(tree, "element", (node, index, parent) => {
      if (node.tagName !== "pre" || index === undefined || !parent) return;
      parent.children[index] = codeBlock(node);
      return "skip";
    });
  };
}
