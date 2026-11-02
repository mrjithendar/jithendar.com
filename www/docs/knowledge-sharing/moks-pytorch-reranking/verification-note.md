# Verification note

For the author, before publishing. Reviewed against MOKS `4928f09` on 2026-11-02.

## What was run

| Check | Result |
|---|---|
| `reranker/tests` (pytest, scratch venv with the pinned FastAPI, Pydantic, httpx and pytest; no torch) | 34 passed, 1 failed: `test_a_missing_lock_file_refuses_to_load` needs torch, because `Model.load()` imports torch before it checks the lock file |
| `backend/tests/test_rerank.py` | **Not run**: needs PostgreSQL. The article cites these tests by name and by what they assert; I read them, I did not run them |
| `helm template` with `values-minikube.yaml`, `resourceGroup=reranker` | Rendered NetworkPolicy (`egress: []`), ServiceAccount, Service and Deployment with the env values quoted in the article |
| Read-only `kubectl --context mk4` | `moks-reranker` 1/1 ready, image `moks-reranker:latest`, pod started 04:21 UTC; `kubectl top`: 3m CPU, 443Mi at idle; ConfigMap has `MOKS_RAG_RERANK_ENABLED=true` and the pinned model and revision |
| `verify_article.py` | 11 verbatim excerpts, 26 pinned links, 3 figures: OK |
| Site tests (`npx vitest run`) | 41 files, 402 tests passed, including schema validation and the visual-editor round trip |
| External facts | Model card (license, training data, published scores, V100 figure); `config.json` at the pinned revision (6 layers, 384 hidden, 12 heads, 1 label, 512 positions, identity activation); sentence-transformers CrossEncoder docs; PyTorch 2.15 thread docs; safetensors docs |

The running pod's exact build cannot be tied to a commit from here. `reranker/` last changed in `1f82188`
(03:53 UTC) and the pod started at 04:21 UTC, so its service code very likely matches `4928f09`, but that is
an inference.

## Implementation gaps found

These are in the article, mostly in the "Gaps found" row and the sections they concern.

1. **Reranking is on for mk4 searches.** `values-minikube.yaml` sets `reranker.client.enabled: true`, but
   `docs/RERANKING.md` says to enable it only after the gates pass on real questions. They passed on synthetic
   questions only. This is the most important item for the author to decide on.
2. **`docs/RERANKING.md` is stale in two places.** Enabling step 3 says to move
   `deploy/argocd/minikube/optional/moks-reranker.yaml` to `apps/`, but it is already in `apps/`. The model table
   says identity activation is used "because the library's default sigmoid makes them look like probabilities".
   The pinned `config.json` already declares identity, so the explicit setting is a safeguard, not a fix.
3. **`moks eval rerank` from the CLI probably fails at the end.** `cli._eval` prints `r["checks"]`,
   `r["score"]` and `summary["cases"]`. Rerank rows and the rerank branch of `runner.execute` provide none of
   them. The run is saved before printing, so results survive. Read, not run. The API route
   `POST /evals/runs` avoids that printer.
4. **No `preStop` delay.** As I read Uvicorn's shutdown order, it stops listening before the lifespan shutdown
   marks the service unready. A request routed in that window gets a connection error and falls back.
5. **Supply chain.** The `python:3.12-slim` base is a tag, not a digest, and pip runs without `--require-hashes`.
6. **Provisional resources.** Requests and limits come from an arm64 Mac. At idle the pod uses 443Mi against a
   512Mi request (one reading).
7. **The evaluation timeout differs from production.** `rerank_eval._client` uses 5,000 ms, and production uses
   1,500 ms.
8. **The truncation report is approximate.** It assumes only the passage is cut.
9. **Circuit breaker scope.** It is per process, and a single 429 does not pause calls.
10. **Result scores.** After reranking, each result's `score` is still the pre-rerank fused score, so the scores
    the LLM sees are not in descending order.
11. **Token rotation.** The token is shared, so rotating it means restarting all three components, with a burst
    of `401` fallbacks in between.
12. **NetworkPolicy enforcement on mk4 is unverified** (stated in `docs/RERANKING.md`). My API-server proxy
    request to the service timed out, which proves nothing either way.

## Claims that are not measurements

- All relevance numbers come from one run of 30 synthetic cases (27 labelled), keyword candidates only, with the
  service on an arm64 Mac. The article says so next to the table.
- All latency and memory numbers come from the same Mac, except the single idle `kubectl top` reading.
- Not measured anywhere: cluster CPU and memory under load, real questions, vector candidates, the quality effect
  of truncation, the production fallback rate, and the effect on report quality.
- The S3 example at the start is labelled illustrative. The two before-and-after rows are from the recorded
  synthetic run.
- The model's MS MARCO scores and V100 throughput are quoted from its model card, and the article says they do
  not apply to this deployment.

## Owner decisions before publishing

- Whether to keep `reranker.client.enabled: true` on mk4 (gap 1). If it changes, update the "Configured" rows.
- Whether to fix `docs/RERANKING.md` and the CLI printer first. The article describes the current state, so it
  would need updating after either change.
- Whether the one `kubectl top` reading belongs in a public article.
- The first-person voice assumes you wrote MOKS. The commit history is under your name, but check the voice reads as yours.
