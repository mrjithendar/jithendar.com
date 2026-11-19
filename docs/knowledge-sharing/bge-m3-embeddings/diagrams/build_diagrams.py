#!/usr/bin/env python3
"""Figures for the two bge-m3 articles:

- content/blog/bge-m3-ollama-pgvector-moks-sre-retire-opensearch.mdx (MOKS)
- content/blog/switch-embedding-model-bge-m3-seo-agent-jithendar-com.mdx (seo-agent)

    python3 docs/knowledge-sharing/bge-m3-embeddings/diagrams/build_diagrams.py   # writes the .drawio files
    bash docs/knowledge-sharing/bge-m3-embeddings/diagrams/export.sh              # draw.io CLI → public/images/bge-m3-embeddings/

After editing a .drawio file by hand, run only export.sh, or this script overwrites the edits.

Sources (19 November 2026): moks-tech/kubernetes d9b6c49 (minikube-infrastructure/embeddings.tf,
deploy/minikube/embeddings/bge-m3), mrjithendar/moks-sre 982dd05 (deploy/helm/moks/values-hetzner.yaml,
backend/moks/rag/backends.py, service.py, docs/OPERATOR_GUIDE.md), moks-tech/moks-seo-agent 2a90fd7 (app/embeddings.py,
app/calibration.py, app/index.py, app/news/desk.py, scripts/calibrate_embeddings.py), and read-only checks on mk4.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio_model import Diagram  # noqa: E402

HERE = Path(__file__).resolve().parent
NOTE = 11


def shared_service():
    d = Diagram("bge-m3-shared-service", 960, 640, "bge-m3 on mk4: one Ollama pod, pinned weights, two allowed callers")
    d.node("tf", "ops", 35, 70, 220, 72, "embeddings.tf (Terraform)", "helm_release bge-m3,", "local chart, timeout ≥ 1200 s")
    d.node("reg", "external", 35, 190, 220, 72, "registry.ollama.ai", "bge-m3:567m, F16, 1.16 GB", "HTTPS, public addresses only")
    d.zone("z-ns", "namespace embeddings · Istio sidecar, STRICT mTLS", 285, 50, 405, 400, "cluster")
    d.node("init", "ops", 305, 80, 205, 88, "init: fetch-model", "pull once onto the volume", "refuse any other digest",
           "skip when already there")
    d.node("pvc", "data", 530, 80, 140, 88, "Model volume", "hcloud, 10 Gi", "policy: keep", shape="db")
    d.node("oll", "ai", 305, 195, 365, 110, "ollama serve 0.40.16 (pinned digest)", "keep-alive -1: the model stays loaded",
           "context 2048 tokens, longer input truncated", "one request at a time (-np 1)",
           "1.5 GiB request, 2.5 GiB limit, no CPU limit")
    d.node("pol", "security", 305, 335, 170, 90, "Two policies", "NetworkPolicy", "AuthorizationPolicy", "enforced, not dry run")
    d.node("svc", "network", 495, 335, 175, 90, "Service :11434", "bge-m3.embeddings", "/api/embed", "/v1/embeddings")
    d.node("other", "optional", 720, 190, 220, 72, "Any other pod", "e.g. moks executor, terminal", "refused by both policies")
    d.node("seo", "service", 720, 300, 220, 64, "seo-agent", "ns jithendar · sa default")
    d.node("moks", "service", 720, 380, 220, 64, "moks api, worker, crewai", "ns moks · sa moks")
    d.edge("tf", "init", "installs", kind="control", exit=(1, 0.5), entry=(0, 0.3))
    d.edge("init", "reg", "first start", exit=(0, 0.8), entry=(1, 0.5))
    d.edge("init", "pvc", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("pvc", "oll", "loads once", exit=(0.5, 1), entry=(0.81, 0))
    d.edge("svc", "oll", exit=(0.5, 0), entry=(0.76, 1))
    d.edge("seo", "svc", exit=(0, 0.5), entry=(1, 0.3))
    d.edge("moks", "svc", exit=(0, 0.5), entry=(1, 0.7))
    d.text("meas", 20, 475, 450, 110,
           "<b>Measured on mk4 (Hetzner cax21: 4 arm64 cores, 8 GiB)</b><br>1024 dimensions, L2-normalised, no prefix<br>"
           "cold load 5 s; one warm query about 650 ms<br>about 0.7 chunks/s; a batch of 32 takes about 45 s<br>"
           "about 1.3 GiB resident; about 3.5 of 4 cores while embedding", size=12)
    d.text("why", 490, 475, 450, 110,
           "<b>Why Ollama and not Hugging Face TEI</b><br>TEI publishes CPU images for amd64 only, and mk4's nodes are arm64."
           "<br>Ollama serves bge-m3's dense vectors only, not its sparse or multi-vector output: both callers keep "
           "keyword search in PostgreSQL.<br>OLLAMA_NUM_PARALLEL is 2, but the runner embeds with -np 1.", size=12)
    d.legend(600, labels={"optional": "Refused", "security": "Policy", "external": "Outside the cluster"})
    return d


def moks_before_after():
    d = Diagram("moks-search-before-after", 960, 600, "MOKS knowledge search on mk4: OpenSearch before, PostgreSQL + pgvector after")
    d.zone("z-before", "Before: rag.backend opensearch (2026-11-10 to 11-19)", 20, 50, 450, 400, "risk")
    d.node("api", "service", 40, 85, 410, 64, "moks api + worker", "index on every sync; search for every question")
    d.node("os", "data", 40, 185, 200, 110, "moks-opensearch", "BM25 keyword index", "no vectors: keyword-only",
           "2 GiB requested", "20 Gi PV on worker2", shape="db")
    d.node("pg", "data", 250, 185, 200, 110, "PostgreSQL", "documents, chunk text,", "access rules, history", shape="db")
    d.node("dash", "service", 40, 330, 200, 64, "OpenSearch Dashboards", "512 Mi requested")
    d.node("edge", "network", 250, 330, 200, 64, "/opensearch routes", "public, basic auth")
    d.edge("api", "os", "BM25 search", exit=(0.24, 1), entry=(0.5, 0))
    d.edge("api", "pg", "text, access", exit=(0.76, 1), entry=(0.5, 0))
    d.edge("dash", "os", exit=(0.5, 0), entry=(0.5, 1))
    d.edge("edge", "os", exit=(0.15, 0), entry=(0.85, 1))
    d.zone("z-after", "After: rag.backend postgres", 490, 50, 450, 400, "cluster")
    d.node("api2", "service", 510, 85, 410, 64, "moks api + worker", "same code, the PostgresBackend")
    d.node("m3", "ai", 510, 185, 195, 110, "bge-m3 (shared)", "question → 1024-d vector", "one call at a time,",
           "waits 2 s for the slot,", "else keyword-only")
    d.node("pg2", "data", 725, 185, 195, 110, "PostgreSQL (CNPG)", "tsvector keyword", "identifier match", "pgvector k-NN (<=>)",
           shape="db")
    d.node("rrf", "service", 510, 330, 410, 90, "Fused in moks: RRF (k = 60)", "keyword + identifier + vector rankings,",
           "then the access check on every chunk,", "then optional reranking")
    d.edge("api2", "m3", "question", exit=(0.24, 1), entry=(0.5, 0))
    d.edge("api2", "pg2", "three rankings", exit=(0.76, 1), entry=(0.5, 0))
    d.edge("m3", "pg2", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("pg2", "rrf", "ranked ids", exit=(0.5, 1), entry=(0.84, 0))
    d.text("ledger", 20, 470, 920, 54,
           "<b>Memory requests:</b> OpenSearch 2 GiB + Dashboards 512 Mi go; bge-m3 1.5 GiB comes, shared with seo-agent. "
           "<b>Index:</b> 730 chunks. On mk4 OpenSearch only ever held a keyword-only index (no embedding model was "
           "active), so the move also adds vector search for the first time.", size=12)
    d.legend(540, labels={"security": "Policy"})
    return d


def moks_rollout():
    d = Diagram("moks-bge-m3-rollout", 960, 420, "MOKS on bge-m3: four merged changes and two steps left (19 November 2026)")
    xs = (20, 255, 490, 725)
    steps = (
        ("kubernetes#10", "bge-m3 chart + Terraform", "applied: pod on worker3"),
        ("moks-sre#55", "seed the bge-m3 config", "egress to embeddings:11434"),
        ("kubernetes#12", "pgvector for the moks DB", "/opensearch routes removed"),
        ("moks-sre#67", "rag.backend: postgres", "OpenSearch out of Argo sync"),
    )
    for i, (x, (title, *lines)) in enumerate(zip(xs, steps)):
        d.node(f"s{i}", "ops", x, 60, 215, 72, title, *lines)
    for i in range(3):
        d.edge(f"s{i}", f"s{i + 1}", kind="control", exit=(1, 0.5), entry=(0, 0.5))
    d.text("order", 500, 140, 300, 20, "#12 and #67 are safe to merge in either order", size=NOTE)
    d.node("rebuild", "optional", 20, 200, 450, 90, "Rebuild index", "Knowledge → Rebuild index, or moks reindex",
           "730 chunks at about 0.7 chunks/s: about 17 minutes", "adds the vector column; keyword-only until then")
    d.node("clean", "optional", 490, 200, 450, 90, "Delete what Argo CD left behind", "Application, StatefulSet, Deployment,",
           "Services, NetworkPolicies, VirtualServices,", "PVC, the Retain PV and its directory on worker2")
    d.edge("s3", "rebuild", kind="control", exit=(0.5, 1), entry=(0.5, 0), via=[(832, 175), (245, 175)])
    d.edge("rebuild", "clean", kind="control", exit=(1, 0.5), entry=(0, 0.5))
    d.text("note", 20, 305, 920, 34, "Argo CD never prunes on mk4, so merging #67 stopped syncing OpenSearch but left it "
           "running. Its 2 GiB comes back only after the clean-up.", size=NOTE)
    d.legend(355, labels={"ops": "Merged and applied", "optional": "Still to do"})
    return d


def seo_touchpoints():
    d = Diagram("seo-agent-embedding-touchpoints", 960, 640, "What one embeddings setting touches in seo-agent")
    d.node("prov", "ai", 280, 55, 400, 90, "EMBEDDINGS_PROVIDER + model", "today: onnx, bge-small in the image, 384-d",
           "next: ollama, bge-m3 on mk4, 1024-d", "cutoffs: app/calibration.py, one row per model")
    d.zone("z-ask", "Ask the Blog: the article index", 20, 185, 450, 335, "ai")
    d.node("chunks", "data", 40, 220, 200, 100, "seo_article_chunks", "vector(384) today;", "builds _next at 1024,",
           "then swaps it in", shape="db")
    d.node("floor", "security", 250, 220, 200, 100, "Ask floor", "bge-small 0.66 (measured)", "bge-m3 0.52 (interim)",
           "ASK_BLOG_MIN_SCORE wins")
    d.node("lance", "optional", 40, 345, 200, 80, "LanceDB copy", "rewrites itself", "at 1024-d")
    d.node("eval", "ops", 250, 345, 200, 80, "rag_eval.py", "95 labelled questions:", "measures the real floor")
    d.text("ask-note", 40, 440, 410, 64, "During the rebuild the live table no longer fits the question vectors: Ask the Blog "
           "answers with its fallback until the swap.", size=NOTE)
    d.edge("eval", "floor", "sets", kind="control", exit=(0.5, 0), entry=(0.5, 1))
    d.zone("z-news", "News desk: news_items and news_clusters (real[])", 490, 185, 450, 335, "ai")
    d.node("dedupe", "service", 510, 220, 200, 72, "Deduper", "semantic copy 0.95 → 0.93")
    d.node("cluster", "service", 720, 220, 200, 72, "Clusterer", "join 0.80 → 0.70", "entity 0.66 → 0.52")
    d.node("gate", "service", 510, 305, 200, 72, "Quality gate", "paraphrase 0.93 → 0.92", "300 paragraphs per draft")
    d.node("clf", "ai", 720, 305, 200, 72, "Topic classifier", "trained on 384-d vectors:", "rules until retrained")
    d.node("stored", "data", 510, 395, 410, 100, "Stored vectors after the switch",
           "window items: re-embedded, 200 per run, newest first", "labelled items: up to 400 per training run",
           "old centroids: rebuilt from their members", shape="db")
    d.edge("prov", "z-ask", "article and question vectors", exit=(0.2, 1), entry=(0.75, 0))
    d.edge("prov", "z-news", "item and paragraph vectors", exit=(0.8, 1), entry=(0.25, 0))
    d.text("cms", 20, 535, 920, 40, "<b>moks-cms needed no migration.</b> It owns the database schema, but the news vectors "
           "are real[] of any size, and seo-agent creates seo_article_chunks itself because its vector(N) column depends "
           "on the model.", size=12)
    d.legend(590, labels={"security": "Cutoff", "optional": "Derived copy"})
    return d


def cutoff_mapping():
    d = Diagram("bge-m3-cutoff-mapping", 960, 650, "Same share of pairs above the line: mapping bge-small's cutoffs to bge-m3")
    amber, grey, axis = "#b45309", "#64748b", "#cbd5e1"
    x0, x1 = 170, 900

    def panel(key, title, top, lo, hi, step, cuts, medians):
        d.zone(f"z-{key}", title, 20, top, 920, 255)
        ys, ym = top + 75, top + 175
        scale = (x1 - x0) / (hi - lo)
        x = lambda v: round(x0 + (v - lo) * scale)  # noqa: E731
        for y, name in ((ys, "bge-small"), (ym, "bge-m3")):
            d.text(f"{key}-{name}", 35, y - 9, 120, 18, f"<b>{name}</b>", size=12, color="#0f172a")
            d.rect(f"{key}-{name}-axis", x0, y - 1, x1 - x0, 3, axis)
        v, k = lo, 0
        while v <= hi + 1e-9:
            d.text(f"{key}-t{k}", x(v) - 20, top + 222, 40, 16, f"{v:.2f}", size=10, color=grey, align="center")
            d.rect(f"{key}-g{k}", x(v), ym + 14, 1, 6, grey)
            v, k = v + step, k + 1
        for i, (name, a, b, share, rows) in enumerate(cuts):
            ra, rb = rows
            d.rect(f"{key}-ca{i}", x(a) - 2, ys - 11, 4, 22, amber)
            d.rect(f"{key}-cb{i}", x(b) - 2, ym - 11, 4, 22, amber)
            d.text(f"{key}-la{i}", x(a) - 55, ys - 33 - 16 * ra, 110, 16, f"<b>{name} {a:.2f}</b>", size=11, color=amber, align="center")
            d.text(f"{key}-lb{i}", x(b) - 55, ym + 15 + 16 * rb, 110, 16, f"<b>{name} {b:.2f}</b>", size=11, color=amber, align="center")
            d.line(x(a), ys + 12, x(b), ym - 12, f"{share} above")
        for i, (name, a, b) in enumerate(medians):
            d.rect(f"{key}-ma{i}", x(a) - 1, ys - 8, 3, 16, grey)
            d.rect(f"{key}-mb{i}", x(b) - 1, ym - 8, 3, 16, grey)
            # right-aligned so they end at their tick, clear of the arrows that start to their right
            d.text(f"{key}-mla{i}", x(a) - 116, ys + 12, 120, 16, f"{name} {a:.2f}", size=11, color=grey, align="right")
            d.text(f"{key}-mlb{i}", x(b) - 116, ym - 28, 120, 16, f"{name} {b:.2f}", size=11, color=grey, align="right")

    panel("a", "Cluster cutoffs, on all 17,766 pairs of news items (cosine 0.30 to 1.00)", 50, 0.30, 1.00, 0.10,
          [("entity", 0.66, 0.52, "22.4%", (0, 0)), ("join", 0.80, 0.70, "1.53%", (0, 0))],
          [("pair median", 0.61, 0.47)])
    panel("b", "Duplicate and paraphrase cutoffs, the high tail (cosine 0.88 to 1.00)", 325, 0.88, 1.00, 0.02,
          [("paragraph", 0.93, 0.92, "1.03%", (0, 0)), ("dedupe", 0.95, 0.93, "1.00%", (0, 1))],
          [("copy median", 0.98, 0.97)])
    d.text("note", 20, 595, 920, 44, "189 items from the news desk's seven default feeds: all 17,766 item pairs, plus each "
           "item with a reworded copy of itself. Spearman 0.770 between the two models' cosines. Amber: a cutoff and the "
           "share of pairs above it; grey: a median. scripts/calibrate_embeddings.py, 19 November 2026.", size=NOTE)
    return d


def seo_rollout():
    d = Diagram("seo-agent-bge-m3-rollout", 960, 470, "seo-agent on bge-m3: merged so far, and the switch still to come (19 November 2026)")
    done = (
        ("kubernetes#10", "bge-m3 on mk4;", "seo-agent is an allowed caller"),
        ("moks-seo-agent#8", "provider, cutoffs per model,", "news desk migration"),
        ("moks-seo-agent#9", "the measured bge-m3 row", "(#8 merged without it: master red)"),
    )
    for i, (x, (title, *lines)) in enumerate(zip((20, 333, 646), done)):
        d.node(f"d{i}", "ops", x, 60, 293, 72, title, *lines)
    for i in range(2):
        d.edge(f"d{i}", f"d{i + 1}", kind="control", exit=(1, 0.5), entry=(0, 0.5))
    todo = (
        ("floor", 20, 195, "Measure the Ask floor", "rag_eval.py on bge-m3: 95 questions, 2,117 chunks",
         "replaces the interim 0.52"),
        ("switch", 490, 195, "jithendar.com: switch the config", "EMBEDDINGS_PROVIDER=ollama, OLLAMA_URL, model,",
         "drop ASK_BLOG_MIN_SCORE, egress to embeddings"),
        ("reindex", 20, 315, "Restart + full reindex", "about 50 minutes at 0.7 chunks/s",
         "Ask answers with the fallback until the swap"),
        ("news", 490, 315, "News desk catches up", "200 window items per run, newest first",
         "new classifier promoted at 1024-d"),
    )
    for id, x, y, title, *lines in todo:
        d.node(id, "optional", x, y, 450, 80, title, *lines)
    d.edge("d2", "floor", kind="control", exit=(0.5, 1), entry=(0.5, 0), via=[(792, 165), (245, 165)])
    d.edge("floor", "switch", kind="control", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("switch", "reindex", kind="control", exit=(0.5, 1), entry=(0.5, 0), via=[(715, 295), (245, 295)])
    d.edge("reindex", "news", kind="control", exit=(1, 0.5), entry=(0, 0.5))
    d.text("note", 20, 410, 920, 20, "The running seo-agent image already has #8 and #9. The order matters: the old image's "
           "Ollama provider would have built a 768-d table.", size=NOTE)
    d.legend(440, labels={"ops": "Merged and running", "optional": "Still to do"})
    return d


FIGURES = (shared_service, moks_before_after, moks_rollout, seo_touchpoints, cutoff_mapping, seo_rollout)

if __name__ == "__main__":
    names = []
    for make in FIGURES:
        d = make()
        (HERE / f"{d.name}.drawio").write_text(d.xml() + "\n")
        names.append(d.name)
        print(f"{d.name}.drawio  {d.w}x{d.h}")
    (HERE / "figures.txt").write_text("\n".join(names) + "\n")
