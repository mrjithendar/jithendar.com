# Inside rag_eval.yaml: evidence and review notes

Draft (status `review`, written 2026-11-22): `content/blog/rag-eval-yaml-question-set-ask-the-blog.mdx`, a field-by-field
tour of `app/data/rag_eval.yaml` in `mrjithendar/moks-seo-agent`, how each field is scored, and the first run of all 95
questions with the production embedding model. Companion to `rag-evaluation-ask-the-blog-jithendar-com` (the workflow
and the settings it chose).

## Sources

| Repository | Commit | Files |
|---|---|---|
| `mrjithendar/moks-seo-agent` | `e4669f7` (master, merge of PR #30) | `app/data/rag_eval.yaml`, `app/rag_eval.py`, `app/seo_ml/train.py` (`run_rag_eval`), `app/flows/ml.py`, `app/embeddings.py` (query prefix, h1–h3 chunking), `scripts/rag_eval.py`, `scripts/rag_mine_eval.py`, `.github/workflows/rag-eval.yml`, `.dockerignore`, `Dockerfile`, `tests/test_rag_v5.py`, `tests/test_review_llm_rag.py`, `tests/test_seo_ml_fixes.py` |
| `mrjithendar/moks-seo-agent` | `400e1b9` | the move from `tests/fixtures/` to `app/data/` and its commit message |
| `mrjithendar/moks-cms` | `master` on 2026-11-22 | `docs/seo/RAG.md` ("Evaluation", "Score calibration"), `docs/seo/rag-eval/2026-11-10-*.md` |
| `mrjithendar/jithendar.com` | `53a6661` | `kubernetes/seo-agent-40-seo-agent.yaml` (`RAG_MODE`, `RAG_MAX_PER_ARTICLE`, `ASK_BLOG_MIN_SCORE`, `EMBEDDINGS_PROVIDER`), `content/blog/` (the "today's blog" run) |

## The eval run (2026-11-22, local)

- moks-seo-agent `e4669f7` in a fresh worktree, `uv sync --frozen`.
- Model: `bge-small-en-v1.5` ONNX; `model.onnx` and `tokenizer.json` checked against the Dockerfile's
  `MODEL_SHA256=828e1496…` and `TOKENIZER_SHA256=d241a60d…` (both OK).
- Full text: a throwaway PostgreSQL 17.11 on 127.0.0.1 (`--dsn`), used by the two hybrid configurations.
- Corpus: `tests/fixtures/rag_corpus` (51 files, 45 not drafts, 2,117 token chunks; 1,449 v4 chunks).

```bash
uv run --frozen python scripts/rag_eval.py --embeddings onnx --model-dir <bge-small dir> \
  --dsn postgresql://postgres@127.0.0.1:<port>/rag --out <dir> --date 2026-11-22 --json
```

Reports: `results/2026-11-22-*.md` (one per configuration plus the summary), unchanged script output.

`scripts/dump_rows.py` (production configuration `token-vector-div`, one JSON row per question) and
`scripts/check_labels.py` (slug/anchor check against a blog folder; first-55 vs hard-40 split; what floor 0.66 drops)
were run with `PYTHONPATH=<moks-seo-agent>` from the moks-seo-agent virtualenv:

| Run | Result |
|---|---|
| `check_labels.py … labels <rag_corpus> <jithendar.com/content/blog>` | no missing slugs; one missing anchor in both: `c03` `the-incident-that-forced-the-issue` (heading is now "The incident that forced the issue (on Minikube)") |
| `check_labels.py … eval <rag_corpus>` | first 55: R@3 100, calibrated 0.68; hard 40: R@1 62.2, R@3 78.4, R@6 89.2, MRR 0.721, calibrated 0.59; lost at 0.66: x03 0.651, x07 0.621, x08 0.600, x18 0.659; not in top 6: x06, x09, x15, x16; the earlier RAG eval article in the top 6 of n05 (2), x09 (2, 3, 4), x36 (5) |
| `check_labels.py … eval <jithendar.com/content/blog>` | 53 articles, 2,497 chunks: R@1 78.6, R@3 89.3, R@6 95.2, MRR 0.848, anchor 86.9; paraphrase R@3 63.2; hard 40 R@3 75.7 |
| `dump_rows.py … <rag_corpus> <out> <this article>` (first draft, x27 example) | x27 rank 1 → 2 (article chunk 0.818 vs Valkey 0.769); R@1 81.0 → 79.8, MRR 0.865 → 0.859 |
| same, final draft (x37 example) | all metrics unchanged; the article appears in the top 6 of x03 (5), x09 (4–6), x14 (6), x37 (2, cosine 0.850 vs 0.860) |

The strip plot's data (`FLOOR_POINTS` in `diagrams/build_diagrams.py`) is the `best_expected` / `best` column of the
`dump_rows.py` run on the frozen corpus.

## Read-only checks on mk4 (2026-11-22, about 00:30 IST / 2026-11-21 19:00 UTC, current kube context)

- Pod `seo-agent-cdbb6dcdd-cptzq` (started 2026-11-21T18:43:07Z): `ls /srv/app/data` → `rag_eval.yaml`.
- One read-only transaction from the pod (`set transaction read only`):
  - `seo_rag_eval_runs`: 0 rows.
  - `seo_flow_runs` for `seo_ml_flow`: 2026-11-18 17:15 UTC failed (`rag_eval: FileNotFoundError … /srv/tests/fixtures/rag_eval.yaml`);
    2026-11-20 17:11 failed (`query_clusters: Truncated …`); 2026-11-20 17:12 failed (rag_eval FileNotFoundError);
    2026-11-21 18:12 failed (`interrupted by a restart`).
  - `seo_article_chunks`: 52 articles, 2,514 chunks, model `onnx:bge-small-en-v1.5`.
  - `seo_ask_log`: 6 rows (14–16 November), all `fallback` with no retrieval recorded; `seo_ask_gaps`: 4 open, 1 sent.
    The article only says "a handful of questions"; the empty retrieval on those fallbacks is worth a look.
- A later query was cut off (exit 137) because the pod was replaced by a rollout (five seo-agent ReplicaSets in 47
  minutes that evening); nothing else was run.

## Figures

`rag-eval-yaml-anatomy`, `rag-eval-yaml-scoring`, `rag-eval-yaml-floor`, `rag-eval-yaml-move` (draw.io), exported to
`public/images/rag-eval-yaml/`.

```bash
python3 docs/knowledge-sharing/rag-eval-yaml/diagrams/build_diagrams.py   # writes the .drawio files
bash docs/knowledge-sharing/rag-eval-yaml/diagrams/export.sh              # draw.io CLI → public/images/rag-eval-yaml/
```

`drawio_model.py` is the mk4-github-runners copy plus `dot()` for the strip plot. After editing a `.drawio` file by
hand, run only `export.sh`.

## SEO

- **SEO title (63 chars):** rag_eval.yaml Explained: Building a RAG Evaluation Question Set
- **Meta description:** in the frontmatter (`seoDescription`, 151 chars).
- **Tags:** RAG, Retrieval Evaluation, Evaluation Dataset, Embeddings, bge-small, Recall@k, MRR, AI Engineering, LLMOps

## Open items (the article's Todo)

1. `ASK_BLOG_MIN_SCORE` 0.66 drops x03, x07, x08, x18 (all hard-set paraphrases); 0.59 is the calibrated floor on all
   95. Not changed: the owner decides.
2. moks-seo-agent: fix `c03`'s stale anchor (`the-incident-that-forced-the-issue-on-minikube`) and the header comment's
   old paths (`sites/jithendar.com/…`, `services/www/…`). A test that checks anchors the way `test_eval_set_shape`
   checks slugs would catch the next one.
3. After the first finished `seo_ml_flow` run with the file in place, add its live Recall@3 to the article and update
   the move figure's "On 22 November" box.
4. The companion article still says the live check runs from a Sunday CronJob and that Ask the Blog is off
   (`ASK_BLOG_ENABLED` is `"true"` in both manifests now; schedules live in Admin → CrewAI console);
   if it is published, edits go through Admin → Posts.
