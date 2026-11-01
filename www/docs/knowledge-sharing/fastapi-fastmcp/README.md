# FastAPI and FastMCP article

Status: **draft for author review, not published.** Written 2026-11-01 against `roboshop-ai` c81e85a and `moks` ab99cf7.

Start with `editorial-checklist.md`. `evidence-map.md` holds the source evidence table.

## Where things live

| Asset | Location |
| --- | --- |
| Article | `content/blog/fastapi-and-fastmcp-ai-projects.mdx` |
| Figures (SVG, PNG) | `public/images/fastapi-fastmcp/` |
| Editable diagrams | `docs/knowledge-sharing/fastapi-fastmcp/diagrams/*.drawio` |
| Evidence, checklist, checker | This folder |

## SEO metadata

The content schema has no keyword or excerpt field, so those live here and in the article's `<Todo>` note, as in the RoboShop series.

| Field | Value |
| --- | --- |
| H1 | How I Use FastAPI and FastMCP Across My AI Projects |
| SEO title (53) | FastAPI and FastMCP: How I Use Them in My AI Projects |
| Meta description (142) | How I use FastAPI and FastMCP in RoboShop AI and MOKS: real routes, tools, auth, transports and limits, and why the two never share a process. |
| Slug | `fastapi-and-fastmcp-ai-projects` |
| Excerpt | FastAPI and FastMCP sit in different services in my projects, and no service uses both. Here is how each one is used in RoboShop AI and MOKS, with real routes, tools, failures and limits. |
| Primary keyword | FastAPI and FastMCP |
| Secondary keywords | FastMCP server implementation; FastAPI AI applications; Python MCP server; AI agent tool integration |
| Category | `ai-agents` |
| Length | About 3,550 words of prose, 4,300 with code |

`publishedAt` is deliberately unset.

## Figures

| Figure | `.drawio` file | SVG and PNG |
| --- | --- | --- |
| 1. Overview of verified projects | `fastapi-fastmcp-overview.drawio` | `fastapi-fastmcp-overview` |
| 2. FastAPI request sequence (MOKS) | `fastapi-request-sequence.drawio` | `fastapi-request-sequence` |
| 3. MCP tool call sequence | `fastmcp-tool-call-sequence.drawio` | `fastmcp-tool-call-sequence` |
| 4. FastMCP to FastAPI integration | `fastapi-fastmcp-integration.drawio` | `fastapi-fastmcp-integration` |

Each is 620 px wide so it stays readable on a phone. Colours match the RoboShop series. Orange arrows are writes, and a dashed box means the component uses neither package. Captions and alt text are in the article.

## Diagram exports

**The SVGs and PNGs are not draw.io exports.** draw.io is not installed here, and an earlier download attempt was refused by permission policy, so I did not try again. `build_diagrams.py` writes the `.drawio` XML and the SVG from one layout, using the writer from the RoboShop series, and `render_png.sh` screenshots each SVG with Chrome. The `.drawio` files have not been opened in draw.io, so text wrapping and label positions may differ slightly.

For true exports, install draw.io desktop and run `draw.io -x -f svg -o <out> <file>` on each file.

To rebuild and check, from `www/`:

```bash
python3 docs/knowledge-sharing/fastapi-fastmcp/diagrams/build_diagrams.py
sh docs/knowledge-sharing/fastapi-fastmcp/diagrams/render_png.sh
python3 docs/knowledge-sharing/fastapi-fastmcp/verify_article.py ../..
```
