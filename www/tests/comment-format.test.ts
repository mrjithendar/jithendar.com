import { describe, expect, it } from "vitest";
import { applyFormat } from "@/components/discussion/markdown-format";
import { renderCommentMarkdown } from "@/lib/comment-markdown";

describe("composer toolbar", () => {
  it("wraps the selection, or inserts a selected placeholder", () => {
    expect(applyFormat("bold", "make this loud", 10, 14)).toEqual({ value: "make this **loud**", start: 12, end: 16 });
    expect(applyFormat("italic", "", 0, 0)).toEqual({ value: "_italic text_", start: 1, end: 12 });
    expect(applyFormat("code", "run kubectl", 4, 11)).toEqual({ value: "run `kubectl`", start: 5, end: 12 });
  });

  it("links: the selection becomes the text with https:// selected, or a selected URL becomes the target", () => {
    const e = applyFormat("link", "see the docs", 4, 12);
    expect(e.value).toBe("see [the docs](https://)");
    expect(e.value.slice(e.start, e.end)).toBe("https://");
    const u = applyFormat("link", "https://k8s.io", 0, 14);
    expect(u.value).toBe("[link text](https://k8s.io)");
    expect(u.value.slice(u.start, u.end)).toBe("link text");
  });

  it("puts code blocks on their own lines with the chosen language", () => {
    expect(applyFormat("codeBlock", "Try this kubectl get pods", 9, 25, { language: "bash" }).value).toBe("Try this \n\n```bash\nkubectl get pods\n```");
    expect(applyFormat("codeBlock", "", 0, 0, { language: "text" }).value).toBe("```\npaste code here\n```");
  });

  it("prefixes every selected line for quotes and lists", () => {
    expect(applyFormat("list", "a\nb\nc", 0, 3).value).toBe("- a\n- b\nc");
    expect(applyFormat("quote", "intro\nquoted", 8, 8).value).toBe("intro\n> quoted");
  });
});

describe("rich comment rendering", () => {
  it("highlights fenced code with a known language, with a label and copy button", () => {
    const html = renderCommentMarkdown('```bash\nkubectl get pods "<b>"\n```');
    expect(html).toContain('<div class="comment-code"><div class="comment-code-bar"><span class="comment-code-lang">Bash</span><button type="button" class="comment-code-copy" data-copy-code="">Copy</button></div>');
    expect(html).toMatch(/<pre class="shiki shiki-themes github-light github-dark"/);
    expect(html).toContain("&#x3C;b>"); // code text stays text
    expect(html).not.toContain("<b>");
  });

  it("keeps unknown or hostile languages plain, and never lets them into markup", () => {
    const html = renderCommentMarkdown('```evil" onclick="alert(1)\nhi\n```\n\n```\n<script>x</script>\n```');
    expect(html).not.toMatch(/onclick|<script/i);
    expect(html).not.toContain("shiki");
    expect(html.match(/class="comment-code"/g)).toHaveLength(2);
  });

  it("shows where [text](url) links lead; bare URLs already do", () => {
    expect(renderCommentMarkdown("[the docs](https://www.github.com/x)")).toBe(
      '<p><a href="https://www.github.com/x" rel="nofollow ugc noopener noreferrer">the docs</a> <span class="comment-link-host">(github.com)</span></p>',
    );
    expect(renderCommentMarkdown("https://k8s.io/docs")).toBe('<p><a href="https://k8s.io/docs" rel="nofollow ugc noopener noreferrer">https://k8s.io/docs</a></p>');
    expect(renderCommentMarkdown("[mail me](mailto:a@example.com)")).not.toContain("comment-link-host");
  });
});
