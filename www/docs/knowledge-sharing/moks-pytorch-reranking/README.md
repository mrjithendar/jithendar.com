# PyTorch reranking in MOKS: article package

Draft for author review. **Not published.** The article file has `status: review`. Live posts are stored in
Postgres, so publishing means pasting the approved draft into the editor (see `docs/CONTENT_AUDIT.md`).

| File | Purpose |
|---|---|
| `content/blog/pytorch-rag-reranking-moks-sre-agent.mdx` | The article |
| `docs/knowledge-sharing/moks-pytorch-reranking/verification-note.md` | Implementation gaps, unmeasured claims, what was run |
| `docs/knowledge-sharing/moks-pytorch-reranking/evidence-map.md` | Each claim and the file and lines it rests on |
| `docs/knowledge-sharing/moks-pytorch-reranking/verify_article.py` | Checks excerpts, pinned links, figures, metadata |
| `docs/knowledge-sharing/moks-pytorch-reranking/diagrams/*.drawio` | Editable figures |
| `docs/knowledge-sharing/moks-pytorch-reranking/diagrams/build_diagrams.py` | Writes the `.drawio` files and SVGs from one layout model |
| `public/images/moks-pytorch-reranking/*.svg`, `*.png` | Figures for the article; the PNGs are 2x previews |

Reviewed source: MOKS commit `4928f094e1dab364156103234859f7e8efe7072d` (`origin/master` on 2026-11-02). Every
GitHub link in the article is pinned to it.

## SEO metadata

| Field | Value |
|---|---|
| H1 (`title`, 69 chars) | How I Added a PyTorch Cross-Encoder Reranker to MOKS, My AI SRE Agent |
| SEO title (50 chars) | PyTorch RAG Reranking in an SRE Agent: Inside MOKS |
| Meta description (152 chars) | How MOKS reorders authorized RAG passages with a PyTorch cross-encoder on CPU: the service, fallback rules, Kubernetes deployment and what was measured. |
| Slug | `pytorch-rag-reranking-moks-sre-agent` |
| Category / type | `ai-agents` / `analysis` |

**Excerpt** (for the listing card or social post):

> MOKS reorders documentation passages with a small PyTorch cross-encoder on CPU, but only after PostgreSQL has
> authorized them, and it keeps the existing order whenever anything goes wrong. This covers the service, the
> fallback rules, the Kubernetes deployment, and what one synthetic evaluation does and does not show.

**Title choice:** the suggested title said "PyTorch reranking". The implementation is specifically a cross-encoder,
so the H1 names that. The SEO title carries the search phrase "PyTorch RAG reranking".

**Keywords in the body:** "PyTorch RAG reranking" 1, "SRE agent" 2, "cross-encoder" 11, "Kubernetes" 7, and
"MOKS" throughout. No stuffing, and no "production-ready" claims (the verifier rejects that phrase).

**Headings:** one H1 from the title, 13 H2s and 22 H3s, checked by rendering the body through `markdownToHtml`.

### Internal links

All returned HTTP 200 on 2026-11-02 and are used in the article and in `related`:

- `/blog/moks-rag-and-skills-design`
- `/blog/langchain-vs-langgraph-sre-agent-moks`
- `/blog/fastapi-and-fastmcp-ai-projects` (in `related` only)
- `/projects/moks`

Not used: `/blog/deploy-nextjs-kubernetes-github-actions` returned 404 (the draft exists locally but is not live).

### Figures and alt text

The full alt text is in the article. Each one describes every box and arrow, so a reader who cannot see the
image gets the same information.

| Figure | Shows |
|---|---|
| `moks-reranker-architecture.svg` | Components, trust boundaries, what crosses into the reranker pod |
| `moks-rerank-sequence.svg` | `kb_search` → search → PostgreSQL → reranker → validation, fallback, recheck |
| `moks-reranker-deployment.svg` | CI build and model pin, Argo CD, Kubernetes objects, pod lifecycle |

## Rebuilding and checking

From `www/`:

```bash
python3 docs/knowledge-sharing/moks-pytorch-reranking/diagrams/build_diagrams.py
sh docs/knowledge-sharing/moks-pytorch-reranking/diagrams/render_png.sh      # needs Google Chrome
python3 docs/knowledge-sharing/moks-pytorch-reranking/verify_article.py ../..   # needs ../../moks checked out
npx vitest run tests/content.test.ts tests/editor-workflow.test.ts
```

**About the diagrams.** The SVGs are rendered by `build_diagrams.py` from the same layout model that writes the
`.drawio` files, using the RoboShop AI series library. They are not draw.io exports, because draw.io is not
installed on this Mac. If you edit a `.drawio` file in draw.io, export that page over the matching SVG, or change
the layout in `build_diagrams.py` and rebuild. I inspected all three PNG previews and fixed two label overlaps.
