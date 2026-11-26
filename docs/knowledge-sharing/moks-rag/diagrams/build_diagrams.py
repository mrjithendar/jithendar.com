#!/usr/bin/env python3
"""Figures for content/blog/shared-hybrid-rag-platform-qdrant-bge-m3-k3s-hetzner.mdx (the shared RAG platform in
namespace rag on mk4).

    python3 docs/knowledge-sharing/moks-rag/diagrams/build_diagrams.py   # writes the .drawio files
    bash docs/knowledge-sharing/moks-rag/diagrams/export.sh              # draw.io CLI → public/images/moks-rag/

If you edit a .drawio file by hand, run only export.sh afterwards. Running this script overwrites the edits.

Facts come from mrjithendar/moks-rag main at dc91b07 (app/src/rag_api, deploy/k8s, deploy/argocd,
.github/workflows), k8s-deployments #35 (edge delegates) and the read-only checks on 26 November 2026 in
../evidence/checks.txt.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio_model import ARROWS, TEXT, Diagram  # noqa: E402

ARROWS["planned"] = ("#94a3b8", 1.5, "6 4", "Planned, not built yet")

HERE = Path(__file__).resolve().parent


def architecture():
    d = Diagram("moks-rag-architecture", 1000, 560,
                "One RAG platform in namespace rag: what ingests, what answers, and what leaves the cluster")
    d.zone("z-callers", "Callers", 20, 50, 190, 420, "plain")
    d.zone("z-rag", "Namespace rag: Istio STRICT mTLS, deny by default", 225, 50, 555, 420, "cluster")
    d.zone("z-out", "Generation backends", 795, 50, 185, 420, "plain")

    d.node("browser", "client", 30, 85, 170, 60, "Browser", "jithendar.com/chat")
    d.node("sre", "optional", 30, 180, 170, 76, "moks-sre-agent", "sre_knowledge", "not connected yet")
    d.node("cms", "optional", 30, 275, 170, 76, "moks-cms", "cms_content", "not connected yet")
    d.node("seo", "optional", 30, 370, 170, 76, "moks-seo-agent", "seo_intel + cms_content", "not connected yet")

    d.node("owui", "service", 240, 85, 220, 76, "open-webui", "Open WebUI 0.13.5", "3 virtual models")
    d.node("rag", "service", 240, 200, 220, 220, "rag-api (FastAPI)", ":8000, served under /rag",
           "Bearer token on every call", "/ingest  /query  /documents", "OpenAI-style /v1/* for the UI",
           "chunks 1500 chars, overlap 200", "sparse: hashed BM25 terms")

    d.node("docling", "compute", 530, 85, 240, 76, "docling-serve (CPU)", ":5001  PDF, DOCX, HTML → Markdown",
           "for uploads that aren't text")
    d.node("bge", "ai", 530, 185, 240, 76, "bge-m3 on Ollama 0.40.16", ":8001, and :11434 for old callers",
           "dense 1024-d only, no sparse")
    d.node("qdrant", "data", 530, 280, 240, 92, "Qdrant 1.20.2 (Helm chart)", ":6333  three collections",
           "named vectors: dense + sparse", "sparse modifier: IDF", shape="db")
    d.node("litellm", "ai", 530, 390, 240, 66, "LiteLLM proxy", ":4000, one key, no spend DB")

    d.node("anthropic", "external", 808, 390, 162, 66, "Anthropic API", "Sonnet 5.5, Haiku 5.5")
    d.node("gpu", "optional", 808, 280, 162, 76, "GPU node + vLLM", "later, behind the", "same LiteLLM")

    d.edge("browser", "owui", "/chat", exit=(1, 0.5), entry=(0, 0.4))
    # caller arrows enter rag-api at the callers' own heights, so they stay straight
    d.edge("sre", "rag", kind="planned", exit=(1, 0.5), entry=(0, 18 / 220))
    d.edge("cms", "rag", kind="planned", exit=(1, 0.5), entry=(0, 113 / 220))
    d.edge("seo", "rag", kind="planned", exit=(1, 0.5), entry=(0, 208 / 220))
    d.edge("owui", "rag", "/v1 + token", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("rag", "docling", "files", exit=(1, 0.05), entry=(0, 0.6))
    d.edge("rag", "bge", "embed", exit=(1, 44 / 220), entry=(0, 59 / 76))
    d.edge("rag", "qdrant", "RRF", exit=(1, 121 / 220), entry=(0, 41 / 92))
    d.edge("rag", "litellm", "prompt", exit=(1, 209 / 220), entry=(0, 19 / 66))
    d.edge("litellm", "anthropic", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("litellm", "gpu", kind="planned", exit=(1, 0.15), entry=(0, 0.5), via=((789, 400), (789, 318)))

    d.text("note", 20, 482, 960, 36, "<b>Live on 26 November 2026:</b> every workload is Synced and Healthy in Argo CD. "
           "The three collections exist and hold 0 points, and no service calls rag-api yet. Only rag-api (/rag) and "
           "Open WebUI (/chat) have routes from the gateway. Everything else is ClusterIP only.", color=TEXT)
    d.legend(528, labels={"client": "People", "optional": "Not built or not connected", "service": "Our code and UI",
                          "compute": "Parsing", "ai": "Models", "data": "Vector store",
                          "external": "Outside the cluster"})
    return d


def collections():
    d = Diagram("moks-rag-collections", 1000, 600,
                "Three collections behind one API: what keeps the data apart, and what doesn't yet")
    d.zone("z-callers", "Callers (planned)", 20, 50, 220, 330, "plain")
    d.zone("z-api", "rag-api checks the token", 255, 50, 260, 330, "cluster")
    d.zone("z-q", "Qdrant: one collection per service", 530, 50, 450, 330, "cluster")

    d.node("sre", "optional", 35, 85, 190, 76, "moks-sre-agent", "investigations look up", "runbooks")
    d.node("cms", "optional", 35, 185, 190, 76, "moks-cms", "on publish, unpublish", "and delete")
    d.node("seo", "optional", 35, 285, 190, 76, "moks-seo-agent", "internal links and", "cannibalisation checks")

    d.node("q-sre", "data", 545, 85, 420, 76, "sre_knowledge", "runbooks, post-mortems, manifests;",
           "exact error codes need the sparse side", shape="db")
    d.node("q-cms", "data", 545, 185, 420, 76, "cms_content", "published articles; upsert by doc_id,",
           "DELETE /documents/{doc_id} on unpublish", shape="db")
    d.node("q-seo", "data", 545, 285, 420, 76, "seo_intel", "audits, SERP and keyword notes;",
           "seo-agent also reads cms_content", shape="db")

    d.text("api-note", 270, 140, 230, 40, "every request: the token, one collection name and X-Service-Name",
           color=TEXT)
    d.edge("sre", "q-sre", "read + write", kind="planned", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("cms", "q-cms", "write", kind="planned", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("seo", "q-seo", "read + write", kind="planned", exit=(1, 0.3), entry=(0, 0.3))
    d.edge("seo", "q-cms", "read", kind="planned", exit=(1, 0.8), entry=(0, 0.8), via=((500, 346), (500, 246)))

    d.node("checks", "security", 20, 395, 470, 92, "Enforced today", "one shared Bearer token; every request names one collection",
           "a keyword index on doc_id, so upsert and delete hit one document",
           "ingested_by (from X-Service-Name) saved on every chunk", align="left")
    d.node("gaps", "security", 510, 395, 470, 92, "Not enforced yet", "any token holder may read or write any collection",
           "X-Service-Name is a claim anyone can make; no per-service budget",
           "no cross-collection query: seo-agent makes two calls", align="left")

    d.zone("z-next", "Next: one token per service, mapped to the collections it may use", 20, 502, 960, 60, "risk")
    d.text("next", 35, 527, 930, 30, "moks-sre-agent: sre_knowledge (read, write) · moks-cms: cms_content (write) · "
           "moks-seo-agent: seo_intel (read, write), cms_content (read) · Open WebUI: read only", color=TEXT)
    d.legend(575, labels={"optional": "Callers, not connected yet", "security": "rag-api rules",
                          "data": "Collections"})
    return d


def delivery():
    d = Diagram("moks-rag-delivery", 1000, 560,
                "How a commit to moks-rag reaches the cluster: two workflows, three Argo CD objects")
    d.zone("z-gh", "GitHub: mrjithendar/moks-rag", 20, 50, 310, 420, "plain")
    d.zone("z-argo", "Namespace argocd", 380, 50, 280, 420, "cluster")
    d.zone("z-rag", "Namespace rag", 710, 50, 270, 420, "cluster")

    d.node("build", "ops", 35, 85, 280, 124, "build-and-deploy.yaml (app/**)", "ruff + pytest",
           "buildx arm64 + amd64 (QEMU)", "push GHCR :<sha> and :latest", "commit newTag to main [skip ci]",
           align="left")
    d.node("ghcr", "data", 35, 230, 280, 60, "GHCR", "ghcr.io/mrjithendar/moks-rag-api", shape="db")
    d.node("apps", "ops", 35, 310, 280, 140, "deploy-argocd-apps.yaml", "(deploy/argocd/**)",
           "validate YAML, render Kustomize", "apply AppProject + 2 Applications", "hard refresh, wait for Healthy",
           "token: github-rag-argocd-deployer", align="left")

    d.node("proj", "security", 395, 200, 250, 108, "AppProject moks-rag", "sources: this repo, Qdrant charts",
           "destination: namespace rag", "no Secret kind: Argo never", "stores or prunes rag-secrets", align="left")
    d.node("stack", "ops", 395, 85, 250, 92, "Application moks-rag-stack", "path deploy/k8s (Kustomize)",
           "prune, selfHeal, server-side", "apply", align="left")
    d.node("qapp", "ops", 395, 330, 250, 92, "Application", "moks-rag-qdrant: chart qdrant 1.*",
           "multi-source, values from", "deploy/argocd/qdrant-values.yaml", align="left")

    d.node("work", "compute", 725, 85, 240, 108, "5 Deployments", "rag-api, bge-m3, docling-serve,",
           "litellm, open-webui; Istio", "routes and policies; images", "pulled from GHCR, Docker Hub", align="left")
    d.node("secret", "security", 725, 215, 240, 76, "Secret rag-secrets", "created by hand with kubectl,",
           "never in Git", align="left")
    d.node("sts", "data", 725, 325, 240, 92, "StatefulSet qdrant", "qdrant/qdrant:v1.20.2",
           "15 Gi hcloud-volumes claim", shape="db")

    d.edge("build", "ghcr", "push", kind="control", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("build", "stack", "new tag", kind="control", exit=(1, 46.5 / 124), entry=(0, 0.5))
    d.edge("apps", "proj", "apply", kind="control", exit=(1, 0.1), entry=(0, 0.5), via=((364, 324), (364, 254)))
    d.edge("stack", "work", "sync", kind="control", exit=(1, 0.5), entry=(0, 46 / 108))
    d.edge("qapp", "sts", "sync", kind="control", exit=(1, 0.5), entry=(0, 51 / 92))
    d.marker(1, 315, 437)

    d.text("note", 20, 482, 960, 36, "<b>1 · Gap:</b> the CI token may create any Application in namespace argocd, and "
           "an Application can name the <i>default</i> project, which on mk4 allows every repository, namespace and "
           "cluster-wide kind. Restrict the default project, or the token is cluster-admin by another name.",
           color=TEXT)
    d.legend(528, failure=True, labels={"ops": "Workflows and Applications", "data": "Images and storage",
                                        "security": "Boundaries and secrets", "compute": "Workloads"})
    return d


def edge():
    d = Diagram("moks-rag-edge", 1000, 560,
                "From the internet to rag-api and Open WebUI: who checks what, and why chat needs its own host")
    d.zone("z-net", "Internet", 20, 50, 165, 225, "plain")
    d.zone("z-cf", "Cloudflare (proxied)", 200, 50, 190, 225, "plain")
    d.zone("z-mk4", "mk4: Istio ingress gateway and namespace rag", 405, 50, 575, 410, "cluster")

    d.node("browser", "client", 30, 85, 145, 60, "Browser", "/chat")
    d.node("client", "client", 30, 175, 145, 76, "Service client", "/rag + Bearer", "+ X-Service-Name")
    d.node("cache", "network", 215, 85, 160, 124, "Site cache rule", "caches responses", "with no", "Cache-Control",
           "for an hour")

    d.node("root", "network", 440, 85, 215, 92, "Root VirtualService", "jithendar-com, istio-ingress",
           "/rag  → rag/rag-api", "/chat → rag/open-webui", align="left")
    d.node("vs-rag", "network", 440, 215, 215, 76, "VirtualService rag-api", "/rag/ and /rag → rewrite /",
           align="left")
    d.node("vs-ui", "network", 440, 320, 215, 108, "VirtualService", "open-webui", "/chat → 308 /chat/",
           "/chat/ → rewrite /", "no timeout: SSE, WebSocket", align="left")

    d.node("api", "service", 700, 85, 265, 92, "rag-api :8000", "token checked in the app;", "/health, /docs and",
           "/openapi.json are open", align="left")
    d.node("ui", "service", 700, 195, 265, 92, "open-webui :8080", "SvelteKit build patched at", "start-up for /chat",
           "one admin, signup off", align="left")
    d.node("pol", "security", 700, 305, 265, 140, "AuthorizationPolicies", "rag-api ← istio-ingress, rag,",
           "moks-sre, jithendar", "open-webui ← istio-ingress", "qdrant, docling, litellm ← rag",
           "bge-m3 ← 3 service accounts", "everything else: denied", align="left")

    d.edge("browser", "cache", exit=(1, 0.5), entry=(0, 0.25))
    d.edge("client", "cache", exit=(1, 0.3), entry=(0, 0.75))
    d.edge("cache", "root", exit=(1, 0.3), entry=(0, 37 / 92))
    d.edge("root", "vs-rag", "/rag", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("root", "vs-ui", "/chat", exit=(0, 0.85), entry=(0, 0.5), via=((424, 163), (424, 374)))
    d.edge("vs-rag", "api", exit=(1, 0.5), entry=(0, 0.75), via=((670, 253), (670, 154)))
    d.edge("vs-ui", "ui", exit=(1, 0.2), entry=(0, 0.75), via=((686, 342), (686, 264)))
    d.marker(1, 375, 100)

    d.node("sub", "optional", 20, 295, 370, 140, "Next: chat.jithendar.com", "its own origin: no patched bundle,",
           "its own cookies and localStorage,", "its own cache rule (bypass), and /chat",
           "a redirect, like /harbor → registry", align="left")

    d.text("note", 20, 472, 960, 52, "<b>1 · Found on 26 November:</b> Cloudflare returned /rag/health, /rag/openapi.json "
           "and Open WebUI's /chat/api/config from its cache (HIT, max-age 3600). The cached config was 32 minutes "
           "old and still said onboarding: true, though the admin account existed. Responses marked no-store "
           "(the auth endpoints) bypass the cache.", color=TEXT)
    d.legend(530, failure=True, labels={"client": "Callers", "network": "Edge and routes",
                                        "service": "Workloads", "security": "Mesh policy",
                                        "optional": "Planned"})
    return d


FIGURES = [architecture, collections, delivery, edge]

if __name__ == "__main__":
    names = []
    for build in FIGURES:
        d = build()
        (HERE / f"{d.name}.drawio").write_text(d.xml() + "\n")
        names.append(d.name)
        print(f"wrote {d.name}.drawio ({d.w}x{d.h})")
    (HERE / "figures.txt").write_text("\n".join(names) + "\n")
