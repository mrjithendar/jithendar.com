# bge-m3 articles: evidence and review notes

Drafts (status `review`, written 2026-11-19):

- `content/blog/bge-m3-ollama-pgvector-moks-sre-retire-opensearch.mdx`: the shared bge-m3 service and MOKS moving from
  OpenSearch to PostgreSQL + pgvector
- `content/blog/switch-embedding-model-bge-m3-seo-agent-jithendar-com.mdx`: preparing seo-agent (Ask the Blog, news
  desk) to switch from bge-small to bge-m3

## Sources

Every snippet was matched against these commits (whitespace and elisions marked `...` aside):

| Article | Repository | Commit | Files |
|---|---|---|---|
| both | `moks-tech/kubernetes` | `d9b6c49` | `minikube-infrastructure/embeddings.tf`, `vars/mk4.tfvars`, `deploy/minikube/embeddings/bge-m3/` |
| MOKS | `mrjithendar/moks-sre` | `982dd05` | `deploy/helm/moks/values-hetzner.yaml`, `backend/moks/rag/backends.py`, `service.py`, `docs/OPERATOR_GUIDE.md` |
| seo-agent | `moks-tech/moks-seo-agent` | `2a90fd7` | `app/embeddings.py`, `app/calibration.py`, `app/index.py`, `app/news/desk.py`, `app/news/quality.py`, `scripts/calibrate_embeddings.py`, `.github/workflows/ci.yml` |
| seo-agent | `moks-tech/moks-cms` | master | `src/db/migrations/0015_seo_agent.sql`, `0017_news_desk.sql` |

Pull requests described: kubernetes#10 and #12, moks-sre#55 and #67, moks-seo-agent#8 and #9 (all merged 2026-11-19).

Read-only checks on mk4 (2026-11-19, about 12:00 UTC):

- bge-m3 pod `Running` on worker3, about 1.3 GiB in use; Ollama log shows `OLLAMA_NUM_PARALLEL:2` but the runner
  started with `-np 1` (`n_seq_max = 1`), `n_ctx = 2048`, `threads = 4`; `fetch-model` logged the pinned digest.
- MOKS: `embedding_indexes` holds one generation, `opensearch` / `keyword-only` / no dimensions, created 2026-11-10;
  730 chunks; `llm_configs` has `bge-m3` (ollama, 1024) active; pgvector 0.8.6 installed, `chunk_embeddings.embedding`
  not yet present (added by the next index build); `MOKS_RAG_BACKEND=postgres`; StatefulSet `moks-opensearch` (2Gi
  requested) and Deployment `moks-opensearch-dashboards` (512Mi) still running, Argo app `moks-opensearch` OutOfSync.
- seo-agent: `EMBEDDINGS_PROVIDER: onnx` in `seo-agent-config`; the running image contains the `BGE_M3` row;
  `ASK_BLOG_ENABLED: "true"`.
- Measurements quoted from the PRs and the 2026-11-19 sessions: cold load 5 s, warm query ~650 ms, ~0.7 chunks/s,
  batch of 32 ~45 s, ~3.5 of 4 cores. bge-small `rag_eval.py` (token-vector-div): 2,117 chunks, Recall@1/3/6 81.0 /
  90.5 / 95.2, MRR 0.865, calibrated floor 0.59. Calibration numbers: moks-seo-agent#9 and `app/calibration.py`.

## Figures

`diagrams/build_diagrams.py` writes the editable `.drawio` files; `diagrams/export.sh` has the draw.io desktop CLI
export them to `public/images/bge-m3-embeddings/` (SVG for the articles, 2x PNG for featured images). Run both from the
repository root:

```bash
python3 docs/knowledge-sharing/bge-m3-embeddings/diagrams/build_diagrams.py
bash docs/knowledge-sharing/bge-m3-embeddings/diagrams/export.sh
```

`drawio_model.py` is a copy of the rag-eval one plus `rect()` and `line()`. After editing a `.drawio` file by hand, run
only `export.sh`.

| Figure | Used in |
|---|---|
| `bge-m3-shared-service` | MOKS article |
| `moks-search-before-after` | MOKS article (featured image and body) |
| `moks-bge-m3-rollout` | MOKS article |
| `seo-agent-embedding-touchpoints` | seo-agent article (featured image and body) |
| `bge-m3-cutoff-mapping` | seo-agent article |
| `seo-agent-bge-m3-rollout` | seo-agent article |

## To do before publishing

| Item | Article | Status |
|---|---|---|
| Rebuild the MOKS index; record duration, vector coverage, `moks eval` hybrid vs keyword | MOKS | `<Todo>` in the article |
| Delete the leftover OpenSearch objects (runbook in `moks-sre/docs/OPERATOR_GUIDE.md`) | MOKS | not done; the article says so |
| Confirm the stated reasons for PostgreSQL + pgvector over LanceDB | MOKS | written from the PRs, not from the author |
| "Up to roughly 11 s" queue wait for a MOKS question during a seo-agent reindex | MOKS | estimate (one batch of 8 at 0.7 chunks/s), labelled as such |
| `rag_eval.py --embeddings ollama` on bge-m3: fill the table row and the measured Ask floor | seo-agent | two earlier runs did not finish; `<Todo>` in the article |
| Switch jithendar.com (`EMBEDDINGS_PROVIDER: ollama`, egress), restart, full reindex; rewrite the rollout section | seo-agent | prepared, not opened |

## Not run

`scripts/check-content.sh` needs Docker, which was not available; `content.yml` runs it on the push and stops before
sending anything if an article is invalid. Both bodies were compiled with `@mdx-js/mdx` plus `remark-gfm` and
`remark-directive` (the plugins in `moks-cms/src/lib/mdx/compile.ts`), and frontmatter limits, related refs and image
paths were checked against `moks-cms/src/lib/content/schema.ts`.
