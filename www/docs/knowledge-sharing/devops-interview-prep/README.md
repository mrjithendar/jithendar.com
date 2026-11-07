# DevOps interview prep article: review package

Article: `content/blog/devops-interview-preparation-guide.mdx` (status `review`, written 2026-11-07).

## SEO

| Field | Value |
| --- | --- |
| SEO title (55 chars) | DevOps Interview Prep: Linux, K8s, AWS, Python, MCP, AI |
| Meta description (155 chars) | DevOps interview preparation for 2026: a 7-week roadmap, model answers for Linux, Kubernetes, AWS, Python and MCP, and two full system design walkthroughs. |
| URL slug | `/blog/devops-interview-preparation-guide` |
| Main keyword | DevOps interview preparation (intro, an H2, conclusion, first FAQ) |
| Category | `devops-sre` |
| Content type | `tutorial` |

Keywords: DevOps interview preparation, SRE interview questions, Kubernetes interview questions, AWS interview questions, Linux interview questions, Python for DevOps interview, MCP Model Context Protocol, AI system design interview, platform engineer interview, RAG system design.

Tags (in the front matter): DevOps Interview, SRE Interview, Kubernetes, AWS, Linux, Python, MCP, AI System Design, Career.

Cover image alt text, for when a cover is added: "A study desk with a laptop showing a Kubernetes dashboard, a terminal and an architecture diagram, next to an interview prep checklist."

## How the brief's front matter maps to this site

The site's schema (`src/lib/content/schema.ts`) is strict, so unknown keys fail to load.

| Brief | Site |
| --- | --- |
| `title`, `description`, `slug`, `tags` | same names |
| `date` | `publishedAt`, set when publishing (required for `published` and `scheduled`) |
| `cover_image_alt` | `featuredImage.alt`, which also needs `src`, `width` and `height`, so it goes in with the image |
| SEO title and meta description | `seoTitle`, `seoDescription` |

`📝 AUTHOR NOTE` markers are wrapped in `<Todo>`, which the site hides in production. A plain blockquote would have been published.

## FAQ schema

The FAQ is an H2 with H3 questions, the same format as the RoboShop articles. The site emits only Article and BreadcrumbList JSON-LD (`src/lib/pages/article.tsx`); there is no FAQPage output. Google has also shown FAQ rich results only for well-known government and health sites since 2023, so FAQPage markup would mostly help other consumers, not Google results.

## Verification

```bash
python3 -m venv /tmp/prep-venv && /tmp/prep-venv/bin/pip install pytest "mcp>=2,<3"
python3 docs/knowledge-sharing/devops-interview-prep/verify_examples.py --python /tmp/prep-venv/bin/python
```

22 checks, all passing on 2026-11-07 with Python 3.15.2, pytest 9.2.0 and MCP Python SDK 2.3.0: each Python block in the article equals its file in `examples/`, the retry tests pass, the log parser and health checker give the expected output against a sample log and a local HTTP server, and the MCP server answers in-process calls and an `initialize` plus `tools/list` handshake over stdio.

Also checked: both YAML blocks and the JSON policy parse; every bash block passes `bash -n`; the article loads through `loadContent()` and compiles with `compileMdx()`; all six internal links point at existing posts.

Not run: the shell, kubectl, AWS CLI and Velero commands against real systems. They are standard commands, but no cluster or AWS account was touched for this draft.

## Facts worth rechecking before publishing

- MCP Python SDK 2.x renamed `FastMCP` to `MCPServer` (`from mcp.server.mcpserver import MCPServer`). The article says so; recheck if the SDK changes again.
- ingress-nginx retirement, maintenance ending March 2026 (Kubernetes blog, 2025-11-11).
- Free-threaded CPython officially supported since 3.14, not the default (PEP 779).
- kubelet may lag the API server by up to three minor versions (version skew policy).
- "In MOKS … read-only diagnostics run without approval but restores wait for a human" comes from the MOKS approval rules; confirm it still holds.

## Length

About 6,800 words of prose excluding code and hidden notes, inside the brief's 5,000–7,000. With code it is about 8,600 words, so the displayed reading time will be well over the 15 minutes the 2026-11-06 editorial round aimed for. The brief asked for this length.
