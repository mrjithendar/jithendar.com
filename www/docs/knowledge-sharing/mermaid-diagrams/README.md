# Mermaid diagrams article

Status: **draft for author review, not published.** Written 2026-11-03 against `jithendar.com` dc249e8 plus the uncommitted Mermaid change (see `docs/PROGRESS.md`, "Mermaid diagrams in articles"). **Publish only after that change is deployed**, or the diagrams show as code.

| Asset | Location |
| --- | --- |
| Article | `content/blog/mermaid-diagrams-on-jithendar-com.mdx` (`status: review`, no `publishedAt`) |
| Diagrams | 5 Mermaid blocks inside the article (flowcharts, a sequence diagram, a state diagram); no image files |

## SEO and publishing metadata

| Field | Value |
| --- | --- |
| H1 (`title`) | Mermaid Diagrams on a Next.js Blog: What Mermaid Is, Why It Matters, and How I Added It to jithendar.com |
| SEO title (`seoTitle`, 52) | Mermaid Diagrams in a Next.js Blog: What, Why and How |
| Meta description (148) | What Mermaid is, why text-based diagrams suit a technical blog, and how jithendar.com renders Mermaid code blocks as diagrams in Next.js, with code. |
| Slug | `mermaid-diagrams-on-jithendar-com` |
| Primary keyword | Mermaid diagrams |
| Secondary keywords | Mermaid in Next.js; Mermaid for blogs; text-based diagrams |
| Category | `devops-sre` (**placeholder**: no web-development category exists) |
| Content type | `tutorial` |
| `related` | `blog/roboshop-ai-architecture`, `blog/moks-rag-and-skills-design` |

## Verified files and facts

| Source | Used for |
| --- | --- |
| `src/components/MermaidBlock.tsx`, `src/components/CodeBlock.tsx`, `src/app/globals.css` | Code excerpts (copied from the working tree) |
| `src/lib/mdx/compile.ts` | Pipeline description; articles compiled as plain Markdown |
| `src/lib/comment-markdown.ts` | Comments use a separate pipeline (no Mermaid) |
| `src/lib/seo/feed.ts` | RSS carries descriptions only, so the article makes no feed-reader claim |
| `next.config.ts` | Read-only root filesystem for pods |
| mermaid.js.org intro and config schema | Self-description, creator, doc rot, `securityLevel: strict` wording |
| github.blog (2022-02-14) | GitHub renders Mermaid in Markdown |
| github.com/remcohaszing/rehype-mermaid | Needs Playwright outside a browser |

## Validation

- All 5 diagrams render with Mermaid 12.2.0 (`securityLevel: "strict"`) in headless Chrome, in the `default` and `dark` themes, with no `<script>` in the output. A screenshot was checked by eye.
- `tests/content.test.ts`, `tests/links.test.ts`, `tests/editor-workflow.test.ts`: 56 passed.
- Not checked: the article on a real page after deployment (light, dark, phone).
