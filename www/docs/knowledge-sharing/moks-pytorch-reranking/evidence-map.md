# Evidence map

Each implementation claim in the article and where it comes from, at MOKS `4928f09`.

| Claim | Source |
|---|---|
| Order of the search pipeline | [service.py L983-L1070](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/rag/service.py#L983-L1070), docstring and body |
| Grants first; empty answer with none | [service.py L992-L995](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/rag/service.py#L992-L995) |
| Pool `max(k*4, 20)`, ×3 up to 400 | [service.py L1009-L1040](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/rag/service.py#L1009-L1040), `MAX_POOL` at L817 |
| Identifier ranking counted twice | [service.py L932-L934](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/rag/service.py#L932-L934) |
| Identifiers need 4+ characters | [service.py L814-L825](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/rag/service.py#L814-L825) |
| Authoritative PostgreSQL check, "only a suggestion" | [service.py L1017-L1036](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/rag/service.py#L1017-L1036) |
| Scoring signals and their sizes | [service.py L1081-L1109](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/rag/service.py#L1081-L1109) |
| Window: 30, 4 per document, no repeated text | [service.py L1112-L1125](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/rag/service.py#L1112-L1125), [rerank.py L48-L54](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/rag/rerank.py#L48-L54) |
| Pin exact identifiers, superseded last, ties by previous order | [service.py L1128-L1146](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/rag/service.py#L1128-L1146) |
| Recheck only when applied; `removed_after_recheck` | [service.py L1149-L1167](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/rag/service.py#L1149-L1167) |
| 3 per document, near duplicates per scope | [service.py L1170-L1194](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/rag/service.py#L1170-L1194), `PER_DOCUMENT` at L818 |
| Ranking removed before the model; citations returned | [phase2.py L174-L184](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/tools/phase2.py#L174-L184) |
| `<untrusted_data>` wrapping | [prompts.py L1-L77](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/orchestrator/prompts.py#L1-L77) |
| Documentation is a separate evidence kind | [evidence.py L1-L25](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/orchestrator/evidence.py#L1-L25) |
| LangGraph node order | [graph.py L1-L16](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/orchestrator/graph.py#L1-L16) |
| Client ceilings, clipping, timeout +100 ms | [rerank.py L23-L134](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/rag/rerank.py#L23-L134) |
| All-or-nothing validation, model match | [rerank.py L74-L88](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/rag/rerank.py#L74-L88) |
| Circuit breaker: 5 failures, 30 s, Retry-After | [rerank.py L29-L72](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/rag/rerank.py#L29-L72), [L171-L175](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/rag/rerank.py#L171-L175) |
| Enabled only with URL, model and revision | [rerank.py L157-L168](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/rag/rerank.py#L157-L168) |
| Public API shows only state and note | [knowledge.py L160-L167](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/api/knowledge.py#L160-L167) |
| Token required, constant-time check | [app.py L39-L41, L82-L85](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/reranker/app.py#L38-L85) |
| Load, warm-up, not-ready on failure, drain | [app.py L44-L62](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/reranker/app.py#L44-L62) |
| Validation errors do not echo input | [app.py L66-L69](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/reranker/app.py#L66-L69) |
| Shielded wait, 429, 504, output check, logging fields | [app.py L81-L130](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/reranker/app.py#L81-L130) |
| Graceful shutdown setting | [app.py L135-L142](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/reranker/app.py#L135-L142) |
| Slots owned by computation; close waits | [engine.py L36-L76](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/reranker/engine.py#L36-L76) |
| CPU, local files, no remote code, safetensors, identity, threads | [engine.py L92-L107](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/reranker/engine.py#L92-L107) |
| Batches, deadline between batches, truncation report | [engine.py L115-L128](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/reranker/engine.py#L115-L128) |
| Schema ceilings, `extra=forbid`, id pattern | [schemas.py](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/reranker/schemas.py) |
| Model pin and hashes | [model.lock.json](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/reranker/model.lock.json), [fetch_model.py](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/reranker/fetch_model.py) |
| Offline env, non-root, build stages | [Dockerfile](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/reranker/Dockerfile) |
| Pinned packages, CPU torch index | [requirements.txt](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/reranker/requirements.txt) |
| CI tests, arm64 build, smoke test, tags | [ci.yml L160-L218](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/.github/workflows/ci.yml#L160-L218) |
| Kubernetes objects, probes, security, NetworkPolicy | [reranker.yaml](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/deploy/helm/moks/templates/reranker.yaml), [_helpers.tpl L40-L45](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/deploy/helm/moks/templates/_helpers.tpl#L40-L45) |
| API and worker egress to the reranker | [networkpolicy.yaml L37-L40](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/deploy/helm/moks/templates/networkpolicy.yaml#L37-L40) |
| ConfigMap keys | [_configmap.yaml L47-L56](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/deploy/helm/moks/templates/_configmap.yaml#L47-L56) |
| Defaults, resources "PROVISIONAL" | [values.yaml L246-L278](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/deploy/helm/moks/values.yaml#L246-L278) |
| mk4 both switches on; EKS off | [values-minikube.yaml L152-L158](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/deploy/helm/moks/values-minikube.yaml#L152-L158), [values-eks.yaml L137-L139](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/deploy/helm/moks/values-eks.yaml#L137-L139) |
| Argo CD Applications | [minikube/apps/moks-reranker.yaml](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/deploy/argocd/minikube/apps/moks-reranker.yaml), [eks/optional/roboshop-demo-moks-reranker.yaml](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/deploy/argocd/eks/optional/roboshop-demo-moks-reranker.yaml) |
| Evaluation method, metrics, gates, 5000 ms timeout | [rerank_eval.py](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/evals/rerank_eval.py), [gates.py L85-L88](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/evals/gates.py#L85-L88) |
| Fallback gate in the RAG evaluation | [gates.py L276-L294](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/evals/gates.py#L276-L294) |
| Dataset and thresholds | [rerank.yaml](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/evals/datasets/rerank.yaml) |
| Recorded results and environment | [rerank-evaluation-2026-11-02.json](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/docs/examples/rerank-evaluation-2026-11-02.json) |
| Benchmarks, load test, stopped-service run, NetworkPolicy caveat | [RERANKING.md](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/docs/RERANKING.md) |
| Evaluation API route | [evals.py L33-L36](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/api/evals.py#L33-L36) |
| CLI printer fields | [cli.py L309-L322](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/cli.py#L309-L322), [runner.py L120-L133](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/moks/evals/runner.py#L120-L133) |
| Tests cited | [reranker/tests/test_service.py](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/reranker/tests/test_service.py), [backend/tests/test_rerank.py](https://github.com/mrjithendar/moks/blob/4928f094e1dab364156103234859f7e8efe7072d/backend/tests/test_rerank.py) |
