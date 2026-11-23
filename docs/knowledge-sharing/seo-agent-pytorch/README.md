# PyTorch in the seo-agent: evidence and review notes

Draft (status `review`, written 2026-11-23): `content/blog/pytorch-onnx-reranker-seo-agent-ask-the-blog.mdx`, how
PyTorch exports and verifies a cross-encoder reranker for the seo-agent, how ONNX Runtime runs it behind a gate and a
live setting, and what the evaluation measured. Companion to `pytorch-rag-reranking-moks-sre-agent` (MOKS runs the same
model with PyTorch in its own service) and `rag-eval-yaml-question-set-ask-the-blog` (the eval set used here).

## Sources

| Repository | Commit | Files |
|---|---|---|
| `mrjithendar/moks-seo-agent` | `b69c3f5` (master, merge of PR #31; PR head `f751033`) | `app/reranker.py`, `app/index.py` (`ranked_hits`), `app/config.py`, `app/admin_settings/groups/retrieval.py`, `app/main.py`, `app/metrics.py`, `app/news/desk.py`, `app/seo_ml/train.py`, `scripts/reranker_model.py`, `scripts/rag_eval.py`, `Dockerfile`, `pyproject.toml`, `uv.lock`, `.github/workflows/rag-eval.yml`, `README.md`, `tests/test_reranker.py` |
| `mrjithendar/jithendar.com` | `5c8cac1` | `kubernetes/seo-agent-40-seo-agent.yaml` (ConfigMap `RAG_RERANKER_ENABLED: "false"`, `ASK_BLOG_MIN_SCORE: "0.66"`; pod limits 1 CPU / 1280Mi, requests 250m / 768Mi) |
| `mrjithendar/moks-cms` | `master` on 2026-11-23 | `src/components/seo/AgentSettingsGroup.tsx` and `src/app/admin/(growth)/automation/sections/ml.tsx` (the Retrieval group is rendered from the agent's registry), `docs/seo/RAG.md` ("Reranker", now out of date) |
| Hugging Face | `cross-encoder/ms-marco-MiniLM-L6-v2` @ `233902d` | file list from the API; `model.safetensors`, `onnx/model.onnx`, `onnx/model_qint8_arm64.onnx`, `tokenizer.json` downloaded and hashed |

## Measurements

### Model files (2026-11-22, downloaded at 233902d)

| File | Bytes | gzip -c bytes | sha256 |
|---|---|---|---|
| `onnx/model.onnx` | 91,011,230 | 83,236,710 | `5d3e70fd…` |
| `onnx/model_qint8_arm64.onnx` (baked) | 23,200,716 | 18,140,807 | `3573b6b9…` (Dockerfile `RERANKER_SHA256`) |
| `onnx/model_quint8_avx2.onnx` | 23,200,716 | 17,676,680 | `c80a8b34…` |
| `tokenizer.json` | 711,396 | 208,003 | `d241a60d…`, the same as bge-small's (Dockerfile `TOKENIZER_SHA256`) |
| `model.safetensors` | 90,870,598 | | `821d1aa6…` |

Image size gate on the PR run 45003645628 (`scripts/image-size.sh`): `compressed=489598087`, baseline `480937987`
(+1.8 %). The baseline was measured on the mk4 runners' dind (see `image-size-baseline.json` in moks-seo-agent), the PR
on a GitHub-hosted runner, so only the compressed numbers compare.

### Eval runs

All on the frozen corpus (`tests/fixtures/rag_corpus`, 45 articles, 2,117 token chunks), bge-small ONNX at the
Dockerfile's pins (sha256 checked), production retrieval (vector, at most 3 per article), 95 questions (84 answerable).

| Run | Where | Result file |
|---|---|---|
| `scripts/rag_eval.py --configs token-vector-div,token-vector-rerank` (fp32 then int8, 2 threads) | M3 Pro, 2026-11-22 | the sweep repeats it; the gate path (`--reranker-threads 4`) reproduced R@3 95.2, MRR 0.899 |
| `scripts/rerank_sweep.py` (int8/fp32 × 20/10/6 candidates × 2/4 threads) | M3 Pro, 2026-11-22 | `results/2026-11-22-sweep-m3pro.txt` |
| `scripts/floor_check.py` (floor 0.66 / 0.59 / none applied inside search) | M3 Pro, 2026-11-22 | `results/2026-11-22-floor-first.txt` |
| `rag-eval.yml` runs 45102975215 (1 thread, + baseline) and 45102982603 (2 threads) | GitHub `ubuntu-24.04-arm`, 2026-11-23 | `results/2026-11-23-github-arm.txt` |
| `scripts/reranker_model.py verify --model-dir <bge-small>` on four ONNX files (959 pairs) | M3 Pro, 2026-11-22 | `results/2026-11-22-verify-*.json` |

Notes:
- "all" candidates = every candidate after the 3-per-article cap: up to 20, 959 pairs over 95 questions (≈ 10 each).
- The sweep calls `CrossEncoderReranker` directly; the gate adds nothing measurable (the gate run matched it).
- The first two verify runs (hf-int8, hf-fp32) used all the Mac's threads for PyTorch (`threads: null` in the JSON); the script was then
  changed to give PyTorch and ONNX Runtime the same `--threads`. Timings from macOS are not used in the article.
- Linux ARM Recall@3 is 94.0 against 95.2 on macOS with the same int8 file: one question drops from the top 3 to the
  top 6. Not investigated (presumably different int8 kernels in ONNX Runtime).

### PyTorch export (2026-11-22, M3 Pro)

`reranker_model.py download` then `export --int8`: fp32 90,961,538 bytes in 1.0 s, ORT int8 23,006,595 bytes. The
first export failed with `OnnxExporterError: Module onnx is not installed!` (fixed by adding `onnx==1.23.2` to the
`train` group). Warnings: the TorchScript exporter's `DeprecationWarning` (torch.export-based exporter is the default
since 2.9), a `TracerWarning` from `transformers/masking_utils.py` (padding branch for a KV cache; verify shows the
export is exact), and an opset-17 `aten::index` note.

## Read-only checks on mk4 (2026-11-23, about 02:45–03:00 UTC, current kube context)

- Nodes: `jithendar-master1` cax11 (2 CPU), `jithendar-pool-workers-worker1..3` cax21 (4 CPU), all arm64; the
  seo-agent pod is on worker3, `/proc/cpuinfo` CPU part `0xd0c` (Neoverse-N1).
- Pod `seo-agent-55545b77b8-kfrfq`, started 2026-11-23T02:40:02Z, image
  `registry.jithendar.com/jithendar/seo-agent@sha256:11943cc2…`.
- `ls -l /models/ms-marco-MiniLM-L6-v2`: `model.onnx` 23,200,716 bytes, `tokenizer.json` 711,396 bytes. Env:
  `RAG_RERANKER_DIR=/models/ms-marco-MiniLM-L6-v2`, `RAG_RERANKER_ENABLED=false`.
- `/metrics` (from inside the pod): `seo_rag_rerank_total` has no samples, `seo_rag_rerank_seconds_count 0`,
  `seo_rag_retrieval_mode{mode="vector"} 1`, `seo_rag_eval_recall_at_3 0.8452`. `/readyz`: ready, no notes.
- One read-only transaction (`set transaction read only`, rolled back):
  - `seo_agent_settings` has no `RAG_RERANKER_*` or `ASK_BLOG_MIN_SCORE` rows (nothing saved in Admin);
  - `seo_rag_eval_runs`: 2026-11-21 19:02 UTC R@3 0.881 (MRR 0.846, calibrated 0.59) and 2026-11-22 04:47 UTC R@3
    0.8452 (MRR 0.8238, calibrated 0.62), both `mode: vector`, both before the reranker image (no `reranker` key);
  - `seo_flow_runs` for `seo_ml_flow`: succeeded 2026-11-21 19:01 (manual) and 2026-11-22 04:47 (cron);
  - `seo_article_chunks`: 68 articles, 3,179 chunks.

## Contamination check

The article is indexed by Ask the Blog, and the eval set has questions whose expected answer is the MOKS PyTorch
article. `../rag-eval-yaml/scripts/dump_rows.py` on the frozen corpus with and without this article (moks-seo-agent
`b69c3f5`, bge-small): every metric unchanged (R@1 81.0, R@3 90.5, R@6 95.2, MRR 0.865, anchor 88.1, calibrated 0.59).
The article appears in one top 6: t03 at position 3 (`#a-gate-that-never-fails-a-search`, cosine 0.633); t03's rank
stays 1. No eval question is quoted in the article. Re-run after changing it:

```bash
PYTHONPATH=<moks-seo-agent> <moks-seo-agent>/.venv/bin/python docs/knowledge-sharing/rag-eval-yaml/scripts/dump_rows.py \
  <bge-small dir> <moks-seo-agent>/tests/fixtures/rag_corpus /tmp/with.json content/blog/pytorch-onnx-reranker-seo-agent-ask-the-blog.mdx
```

## Figures

`seo-agent-pytorch-where` (also the cover), `-search`, `-gate`, `-verify`, `-results` (draw.io), exported to
`public/images/seo-agent-pytorch/`.

```bash
python3 docs/knowledge-sharing/seo-agent-pytorch/diagrams/build_diagrams.py   # writes the .drawio files
bash docs/knowledge-sharing/seo-agent-pytorch/diagrams/export.sh              # draw.io CLI → public/images/seo-agent-pytorch/
```

`drawio_model.py` is the rag-eval-yaml copy plus a `fallback` arrow (red, dotted). The chart's numbers are `RESULTS`,
`ARM` and `FLOOR` in `build_diagrams.py`. After editing a `.drawio` file by hand, run only `export.sh`.

## SEO

- **SEO title (63 chars):** PyTorch to ONNX: Adding a Cross-Encoder Reranker to a RAG Agent
- **Meta description:** in the frontmatter (`seoDescription`).
- **Tags:** PyTorch, ONNX, ONNX Runtime, RAG, Reranking, Cross-Encoder, uv, AI Engineering, LLMOps

## Open items (the article's Todo)

1. The reranker is off on mk4, so its latency there is unmeasured. If it is switched on, add the p95 of
   `seo_rag_rerank_seconds` to "Is it worth switching on?" and to the results figure (`ARM`-style rows).
2. `ASK_BLOG_MIN_SCORE` 0.66 vs 0.59: the verdict for Ask the Blog depends on it (and so does the sibling article).
3. moks-cms `docs/seo/RAG.md` "Reranker" still says the reranker cannot pass on this eval set.
4. Re-run the contamination check after editing the article.
5. Then set `status: published` with a `publishedAt` time.
