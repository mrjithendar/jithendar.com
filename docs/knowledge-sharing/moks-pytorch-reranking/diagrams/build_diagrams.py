#!/usr/bin/env python3
"""Figures for the MOKS PyTorch reranking article: one editable .drawio file per figure and a matching SVG.

Reuses the layout, palette and draw.io writer of the RoboShop AI series, so the figures look alike and
the colours keep their meaning. Run from www/. The SVGs are rendered here, not exported by draw.io:
if a .drawio file is edited by hand, re-export that page from draw.io over the matching SVG.
Labels follow moks commit 4928f094e1dab364156103234859f7e8efe7072d.
"""
import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[3] / "public" / "images" / "moks-pytorch-reranking"
spec = importlib.util.spec_from_file_location("series_diagrams", HERE.parents[1] / "roboshop-ai" / "diagrams" / "build_diagrams.py")
series = importlib.util.module_from_spec(spec)
sys.modules["series_diagrams"] = series
spec.loader.exec_module(series)
Page, Sequence = series.Page, series.Sequence


def architecture():
    p = Page("moks-reranker-architecture", "Architecture", 620, 712, "MOKS architecture with the PyTorch reranker and its trust boundaries",
             "An engineer's browser reaches moks-api. The moks-worker runs a LangGraph investigation whose plan node asks an external LLM provider for tool "
             "calls, including kb_search. Both processes call the same search function, which takes candidates from OpenSearch or PostgreSQL, checks access "
             "and lifecycle in PostgreSQL, and sends only authorized passage text with ids to the moks-reranker pod. The reranker runs a PyTorch cross-encoder "
             "on CPU, returns ids and scores, and has no egress, no database access and no ServiceAccount token. Reviewed skills are selected without "
             "reranker scores.")
    p.zone("Outside the cluster", 15, 12, 590, 92)
    p.zone("Namespace moks", 15, 116, 590, 584)
    p.zone("Trust boundary: moks-reranker pod", 325, 382, 270, 196, "br")
    p.node("browser", "browser", 30, 36, 170, 56, "Engineer", "browser, signed in")
    p.node("llm", "external", 225, 36, 170, 56, "LLM provider", "chosen by an admin")
    p.node("embed", "external", 420, 36, 170, 56, "Embedding API", "optional")
    p.node("api", "gateway", 30, 148, 170, 64, "moks-api", "FastAPI", "knowledge search")
    p.node("worker", "agent", 225, 148, 365, 64, "moks-worker", "LangGraph investigation", "plan node requests kb_search")
    p.node("search", "gateway", 30, 262, 560, 72, "rag.service.search()", "grants, candidates, PostgreSQL check, rerank,",
           "diversity, recheck, citations")
    p.node("pg", "store", 30, 400, 250, 72, "PostgreSQL", "authority: grants, lifecycle", "chunks, pgvector, audit")
    p.node("os", "store", 30, 504, 250, 64, "OpenSearch", "optional candidate index", "a suggestion, not authority")
    p.node("rr", "model", 340, 404, 240, 96, "moks-reranker", "FastAPI + PyTorch, CPU only", "ms-marco-MiniLM-L6-v2",
           "revision 233902d", "ClusterIP :8090, Bearer token")
    p.note(340, 512, "No egress, no database access,\nno ServiceAccount token", 12, "#be185d", True)
    p.node("skills", "service", 30, 604, 250, 72, "Reviewed skills", "chosen by policy and rules", "never by reranker scores")
    p.node("report", "absent", 340, 604, 250, 72, "Investigation report", "cited passages are", "documentation, not live state")
    p.edge("browser", "api", label="HTTPS", dx=62)
    p.edge("worker", "llm", a_side="t", b_side="b", a_at=0.233, label="untrusted_data", dx=0)
    p.edge("worker", "embed", a_side="t", b_side="b", a_at=0.767, label="query vector", dx=0)
    p.edge("api", "search", b_at=0.152)
    p.edge("worker", "search", b_at=0.673, label="kb_search tool", dx=0)
    p.edge("search", "pg", a_at=0.223, label="authoritative check", dx=0, t=-0.1)
    p.edge("search", "os", a_side="l", b_side="l", via=[(22, 298), (22, 536)])
    p.edge("search", "rr", a_at=0.777, both=True, kind="write", label="authorized ids + text,\nids + scores back", dy=-4)
    return p


def sequence():
    p = Page("moks-rerank-sequence", "Rerank sequence", 620, 790, "Retrieval, reranking and context selection in MOKS, including fallback",
             "kb_search calls search with the question and the investigation's scope. Search resolves grants, gathers keyword, identifier and vector "
             "candidates and fuses them, then asks PostgreSQL which chunks are active and readable. It applies small scoring signals and prepares up to "
             "30 candidates with at most 4 per document, then posts them to moks-reranker with a bearer token and a 1500 ms deadline. The service queues "
             "at most 4 requests behind 1 worker and scores in batches of 16. Search accepts the answer only if it scores exactly the ids it sent with the "
             "pinned model and revision; on a timeout, overload, error or mismatch it keeps the existing order. It then pins exact identifiers, moves "
             "superseded documents last, selects at most 3 passages per document, rechecks PostgreSQL when reranking was applied, and returns passages with citations.")
    s = Sequence(p, [("w", "agent", "kb_search", "moks-worker"), ("s", "gateway", "search()", "rag/service.py"),
                     ("d", "store", "PostgreSQL", "authority"), ("r", "model", "moks-reranker", "PyTorch, CPU")], bottom=774)
    s.message(96, "w", "s", "query and scope")
    s.self_note(108, "s", "Grants for the scope\nkeyword, identifier, vector\nfused with RRF", 62, 214)
    s.message(206, "s", "d", "chunk rows by id")
    s.message(238, "d", "s", "active and readable only", kind="dashed")
    s.self_note(250, "s", "_score: small signals\n_prepare: at most 30,\n4 per document, no repeats", 62, 214)
    s.message(352, "s", "r", "POST /rerank, Bearer\nids + text, 1500 ms", kind="write")
    s.self_note(364, "r", "Gate: 1 worker, 4 queued\n429 if full, 504 at deadline\nbatches of 16, raw logits", 62, 214, "model")
    s.message(458, "r", "s", "ids, scores, model, revision", kind="dashed")
    s.message(490, "r", "s", "timeout, 429, 5xx: fallback", kind="reject", number=False)
    s.self_note(502, "s", "Accept only the exact ids,\nfinite scores, same revision;\nelse keep the existing order", 62, 214, "reject")
    s.self_note(574, "s", "Pin exact identifiers,\nsuperseded last; _select:\n3 per document, no near repeats", 62, 214)
    s.message(668, "s", "d", "recheck, only if reranked")
    s.message(700, "d", "s", "documents still usable", kind="dashed")
    s.message(740, "s", "w", "passages + citations", kind="dashed")
    return p


def deployment():
    p = Page("moks-reranker-deployment", "Deployment", 620, 708, "Kubernetes deployment and model-loading lifecycle of moks-reranker",
             "On a push to master, GitHub Actions on an arm64 runner installs pinned dependencies with CPU-only torch, downloads the model at revision "
             "233902d and checks the SHA-256 of every file, smoke-tests the image with no network and a read-only root, and pushes a commit tag and latest "
             "to ECR. The Argo CD Application moks-reranker renders the reranker resource group from values-minikube.yaml on manual sync. In namespace moks "
             "a Secret, a Deployment, a ClusterIP Service and a NetworkPolicy with no egress are created. The pod loads local safetensors weights without "
             "remote code, warms up, then reports ready; on SIGTERM it refuses new work and finishes accepted work within 20 seconds.")
    p.zone("Build: GitHub Actions, ubuntu-24.04-arm, push to master", 15, 12, 590, 152)
    p.node("pip", "service", 30, 44, 130, 100, "pip install", "pinned versions", "CPU-only torch")
    p.node("fetch", "service", 175, 44, 130, 100, "fetch_model.py", "revision 233902d", "SHA-256 per file")
    p.node("smoke", "service", 320, 44, 130, 100, "Smoke test", "--network none", "--read-only", "/readyz 200")
    p.node("ecr", "store", 465, 44, 125, 100, "Push to ECR", "tag: commit SHA", "tag: latest")
    p.edge("pip", "fetch", a_side="r", b_side="l")
    p.edge("fetch", "smoke", a_side="r", b_side="l")
    p.edge("smoke", "ecr", a_side="r", b_side="l")
    p.zone("Git and Argo CD", 15, 176, 590, 92)
    p.node("repo", "external", 30, 200, 260, 56, "moks repo, master", "values-minikube.yaml")
    p.node("argo", "edge", 330, 200, 260, 56, "Argo CD: moks-reranker", "resourceGroup reranker, manual")
    p.edge("repo", "argo", a_side="r", b_side="l", label="Helm", dy=-12)
    p.zone("Namespace moks on Minikube (mk4)", 15, 280, 590, 416)
    p.node("secret", "reject", 30, 312, 170, 74, "Secret", "moks-reranker-secrets", "bearer token")
    p.node("deploy", "model", 215, 312, 375, 74, "Deployment moks-reranker", "1 replica, user 10001, read-only root",
           "requests 250m / 512Mi, limits 2 / 1Gi")
    p.node("svc", "gateway", 30, 404, 170, 56, "Service", "ClusterIP :8090")
    p.node("np", "reject", 215, 404, 375, 56, "NetworkPolicy", "in: api, worker :8090; monitoring :9464; no egress")
    p.edge("argo", "deploy", b_at=0.653, label="sync", dx=22)
    p.edge("secret", "deploy", a_side="r", b_side="l")
    p.zone("Pod lifecycle", 22, 476, 576, 210, "br")
    p.node("load", "model", 30, 500, 130, 84, "Load", "local files only", "safetensors", "no remote code")
    p.node("warm", "model", 175, 500, 130, 84, "Warm up", "one scoring call", "/readyz stays 503")
    p.node("ready", "service", 320, 500, 130, 84, "Ready", "/readyz 200", "startup probe", "up to 180 s")
    p.node("term", "reject", 465, 500, 125, 84, "SIGTERM", "refuse new work", "finish accepted", "drain up to 20 s")
    p.edge("load", "warm", a_side="r", b_side="l")
    p.edge("warm", "ready", a_side="r", b_side="l")
    p.edge("ready", "term", a_side="r", b_side="l")
    p.node("fail", "reject", 30, 604, 275, 60, "Load failure", "pod stays up, not ready", "error type shown in /readyz")
    p.node("probes", "absent", 320, 604, 270, 60, "Probes", "startup and readiness: /readyz", "liveness: /healthz")
    p.edge("load", "fail", a_at=0.5, b_at=0.236, kind="reject")
    return p


FILES = {
    "moks-reranker-architecture": architecture,
    "moks-rerank-sequence": sequence,
    "moks-reranker-deployment": deployment,
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    built = []
    for name, make in FILES.items():
        page = make()
        for e in page.edges:
            for x, y in e["points"]:
                if not (0 <= x <= page.w and 0 <= y <= page.h):
                    raise SystemExit(f"{page.figure}: edge {e['id']} leaves the page")
        for n in page.nodes.values():
            if n["x"] < 0 or n["y"] < 0 or n["x"] + n["w"] > page.w or n["y"] + n["h"] > page.h:
                raise SystemExit(f"{page.figure}: {n['id']} leaves the page")
        mxfile = ET.Element("mxfile", host="app.diagrams.net", agent="build_diagrams.py", version="24.7.17", type="device")
        mxfile.append(series.page_xml(page, 0))
        ET.indent(mxfile)
        (HERE / f"{name}.drawio").write_bytes(ET.tostring(mxfile, encoding="utf-8", xml_declaration=False))
        (OUT / f"{page.figure}.svg").write_text(series.page_svg(page), encoding="utf-8")
        built.append((page.figure, page.w, page.h))
    (HERE / "figures.txt").write_text("".join(f"{f} {w} {h}\n" for f, w, h in built), encoding="utf-8")
    print(f"{len(built)} .drawio files and SVGs")


if __name__ == "__main__":
    main()
