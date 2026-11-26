# Shared hybrid RAG platform (26 November 2026): evidence and review notes

Draft (status `review`, written 2026-11-26): `content/blog/shared-hybrid-rag-platform-qdrant-bge-m3-k3s-hetzner.mdx`,
about the `rag` namespace on mk4 (rag-api, bge-m3, Qdrant, docling-serve, LiteLLM, Open WebUI) and how it's deployed.

## Sources

| Source | What it gave |
|---|---|
| mrjithendar/moks-rag main at dc91b07 | `app/src/rag_api` (auth, chunking, sparse encoder, Qdrant client, endpoints), `deploy/k8s`, `deploy/argocd`, `.github/workflows`, commit history (the three fixes) |
| mrjithendar/k8s-deployments #35, 5cb029d | the `/rag` and `/chat` delegates in `deploy/minikube/istio/edge/values.yaml`; the old `embeddings` release switched off |
| moks-sre-agent `deploy/helm/moks/values-hetzner.yaml`, live seo-agent ConfigMap and NetworkPolicy | callers still on `bge-m3.embeddings:11434` |
| mk4 and the public site, read-only | `evidence/checks.txt` |
| bge-m3 measurements from 19 November | the bge-m3 article's figures (0.7 chunks/s, batch of 32 in about 45 s) |

## Open before publishing (the article's Todo)

1. **Gaps the article describes.** Fix, or decide to publish anyway:
   - `kubectl -n argocd get appproject default`: allows every repo, namespace and cluster-scoped kind, and
     `github-rag-argocd-deployer` may create Applications.
   - Cloudflare caches `/rag/*` and `/chat/*` responses that carry no `Cache-Control`.
   - `/rag/docs`, `/rag/redoc` and `/rag/openapi.json` are public.
2. **bge-m3 callers.** moks-sre-agent's seed and seo-agent's `OLLAMA_URL` and NetworkPolicy still point at namespace
   `embeddings`. Update "Moving bge-m3" when they move.
3. **No service is connected** and every collection holds 0 points. If one connects, update the collections table,
   "When rag-api is down" and the figures.
4. **No numbers yet** for query latency or retrieval quality. Add them after the first real ingest.

## Figures

```bash
python3 docs/knowledge-sharing/moks-rag/diagrams/build_diagrams.py
DRAWIO=/Applications/draw.io.app/Contents/MacOS/draw.io bash docs/knowledge-sharing/moks-rag/diagrams/export.sh
```

`drawio_model.py` is the shared writer (copied from `../public-grafana`). Edit `build_diagrams.py`, never the
exported SVG or PNG. Four figures: `moks-rag-architecture` (also the cover), `moks-rag-collections`,
`moks-rag-delivery`, `moks-rag-edge`.
