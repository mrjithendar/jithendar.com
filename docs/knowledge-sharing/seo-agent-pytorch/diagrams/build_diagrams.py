#!/usr/bin/env python3
"""Figures for content/blog/pytorch-onnx-reranker-seo-agent-ask-the-blog.mdx (PyTorch in the seo-agent).

    python3 docs/knowledge-sharing/seo-agent-pytorch/diagrams/build_diagrams.py   # writes the .drawio files
    bash docs/knowledge-sharing/seo-agent-pytorch/diagrams/export.sh              # draw.io CLI → public/images/seo-agent-pytorch/

After editing a .drawio file by hand, run only export.sh, or this script overwrites the edits.

Sources: mrjithendar/moks-seo-agent b69c3f5 (merge of PR #31: app/reranker.py, app/index.py, app/config.py,
app/admin_settings/groups/retrieval.py, scripts/reranker_model.py, scripts/rag_eval.py, Dockerfile, pyproject.toml,
tests/test_reranker.py) and the measurements in ../README.md. The chart numbers are RESULTS below, copied from those runs.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio_model import TEXT, Diagram  # noqa: E402

HERE = Path(__file__).resolve().parent


def where():
    d = Diagram("seo-agent-pytorch-where", 960, 560, "Where PyTorch runs in the seo-agent, and where it never does")
    top, zh = 50, 400
    d.zone("z-model", "Model work, outside the service", 20, top, 290, zh, "ai")
    d.zone("z-build", "CI and the image build (GitHub)", 330, top, 290, zh, "plain")
    d.zone("z-mk4", "mk4 (jithendar) · pulls :latest", 640, top, 300, zh, "cluster")

    d.node("hf", "external", 35, 85, 260, 80, "Hugging Face model repository", "cross-encoder/ms-marco-MiniLM-L6-v2",
           "revision 233902d, Apache-2.0", "safetensors and ONNX exports")
    d.node("script", "service", 35, 195, 260, 80, "scripts/reranker_model.py", "download: weights at the pinned rev",
           "export: PyTorch → ONNX (+ int8)", "verify: ONNX vs PyTorch logits")
    d.node("train", "ai", 35, 305, 260, 80, "uv sync --group train", "torch 2.15.0 (CPU-only index)",
           "transformers 5.22.2 · onnx 1.23.2", "a laptop or a manual run only")
    d.node("res", "client", 35, 400, 260, 42, "verify: int8 top-1 93 of 95")
    d.edge("hf", "script", "weights", exit=(0.5, 1), entry=(0.5, 0), kind="batch")
    d.edge("train", "script", "runs it", exit=(0.5, 0), entry=(0.5, 1), kind="control")

    d.node("ci", "ops", 345, 85, 260, 80, "ci.yml (every pull request)", "uv sync --frozen: dev group only",
           "pip-audit: the --no-dev export", "a test: no torch in the image")
    d.node("build", "compute", 345, 195, 260, 80, "docker build, build stage", "uv sync --no-dev: no groups",
           "int8 ONNX from the pinned rev", "sha256 -c, or the build fails")
    d.node("img", "data", 345, 305, 260, 90, "seo-agent:latest", "/models/bge-small-en-v1.5",
           "/models/ms-marco-MiniLM-L6-v2", "no torch, no CUDA · +1.8 %", shape="db")
    d.edge("ci", "build", "image inputs changed, or a merge", exit=(0.5, 1), entry=(0.5, 0), kind="control")
    d.edge("hf", "build", exit=(1, 0.75), entry=(0, 0.25), via=((320, 145), (320, 215)), kind="batch")
    d.edge("build", "img", exit=(0.5, 1), entry=(0.5, 0), kind="batch")

    d.node("settings", "security", 655, 85, 270, 80, "Admin → Settings → Retrieval", "Rerank passages: off (live)",
           "3 limits: 0 = no limit (live)", "CPU threads: 2 (restart)")
    d.node("pod", "service", 655, 195, 270, 96, "seo-agent pod (1 CPU limit)", "ONNX Runtime, CPU only",
           "bge-small: query embeddings", "RerankGate → int8 cross-encoder", "metrics: seo_rag_rerank_*")
    d.node("pg", "data", 655, 325, 270, 76, "PostgreSQL + pgvector", "68 articles · 3,179 chunks",
           "seo_rag_eval_runs (live eval)", shape="db")
    d.edge("settings", "pod", "read on every search", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("img", "pod", exit=(1, 0.5), entry=(0, 0.75), via=((630, 350), (630, 267)), kind="control")
    d.edge("pod", "pg", exit=(0.5, 1), entry=(0.5, 0), both=True)

    d.text("note", 20, 462, 920, 34, "<b>PyTorch runs only in the left column.</b> CI and the image install the default dependencies, which have no torch; "
           "the service runs both models on ONNX Runtime, which the image already had for bge-small.", color=TEXT)
    d.legend(504, labels={"ai": "PyTorch (train group)", "external": "Outside source", "service": "Code", "client": "Result",
                          "ops": "CI", "compute": "Image build", "data": "Image and data", "security": "Settings"})
    return d


def search():
    d = Diagram("seo-agent-pytorch-search", 960, 560, "One search with the reranker switched on")
    xs, w, y1, h1 = (20, 205, 390, 575, 760), 170, 55, 90
    d.node("q", "client", xs[0], y1, w, h1, "question", "Ask the Blog, the", "crews' vector_search,", "MCP search")
    d.node("emb", "ai", xs[1], y1, w, h1, "embed", "bge-small ONNX,", "query prefix")
    d.node("pgv", "data", xs[2], y1, w, h1, "pgvector top 20", "by cosine", "(RAG_CANDIDATES)", shape="db")
    d.node("floor", "security", xs[3], y1, w, h1, "floor (min_score)", "Ask the Blog only:", "0.66 today;", "crews and MCP: none")
    d.node("div", "service", xs[4], y1, w, h1, "≤ 3 per article", "diversify; about 10", "candidates remain")
    for a, b in (("q", "emb"), ("emb", "pgv"), ("pgv", "floor"), ("floor", "div")):
        d.edge(a, b, exit=(1, 0.5), entry=(0, 0.5))

    y2, h2 = 215, 100
    d.node("gate", "security", xs[4], y2, w, h2, "RerankGate", "switched on?", "model loaded?", "below the limit?")
    d.node("rr", "ai", xs[3], y2, w, h2, "cross-encoder", "int8, ONNX Runtime;", "the first N", "candidates")
    d.node("asm", "service", xs[2], y2, w, h2, "assemble", "reranked head,", "then the rest in", "fused order")
    d.node("out", "client", xs[1], y2, w, h2, "top k (k = 6)", "Hit.score = cosine", "→ grader → answer", "with citations")
    d.node("news", "optional", xs[0], y2, w, h2, "news desk", "duplicate check:", "rerank=False", "(it reads cosine)")
    d.edge("div", "gate", "window N", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("gate", "rr", exit=(0, 0.5), entry=(1, 0.5))
    d.edge("rr", "asm", exit=(0, 0.5), entry=(1, 0.5))
    d.edge("asm", "out", exit=(0, 0.5), entry=(1, 0.5))
    d.edge("gate", "asm", "off · unavailable · busy · timeout · error → the fused order, unchanged",
           exit=(0.5, 1), entry=(0.5, 1), via=((845, 345), (475, 345)), kind="fallback")

    d.node("score", "external", 20, 380, 450, 92, "What the model reads, one pair at a time",
           "the question + \"title › heading path\" + the passage", "(first 2,000 characters), truncated to 512 tokens",
           "→ one relevance logit; higher = a better answer", align="left")
    d.node("meas", "compute", 490, 380, 450, 92, "Measured on the 95 eval questions",
           "Recall@3, no floor: 90.5 % → 95.2 % (M3 Pro)", "with the 0.66 floor first: 85.7 % → 88.1 %",
           "p95, M3 Pro, 4 threads: 10 ms → 349 ms", "p95, Linux ARM, 1 thread: 50 ms → 2,875 ms", align="left")
    d.legend(492, labels={"client": "Caller and result", "ai": "Model", "data": "Index", "security": "Filter or gate",
                          "service": "Code", "optional": "Never reranked", "external": "Model input", "compute": "Measured"})
    return d


def gate():
    d = Diagram("seo-agent-pytorch-gate", 960, 660, "RerankGate: every way out, and when a slot is freed")
    d.zone("z-dec", "One search (app/reranker.py, app/index.py)", 20, 45, 470, 555, "plain")
    x, w, ox, ow = 35, 300, 370, 110
    steps = [
        ("d1", "security", 80, 52, ("Switched on, model folder set?", "read from Settings on every search"), ("o0", "not called")),
        ("d2", "security", 152, 68, ("Model loaded?", "the first use loads it in a thread;", "a failed load is kept until restart"), ("o1", "unavailable")),
        ("d3", "security", 240, 52, ("Below the reranks-at-once limit?", "RAG_RERANKER_MAX_CONCURRENT, 0 = none"), ("o2", "busy")),
        ("d4", "ai", 312, 68, ("Start the rerank: running + 1", "a task around asyncio.to_thread;", "its done-callback frees the slot"), None),
        ("d5", "security", 400, 68, ("Back within the time limit?", "RAG_RERANKER_TIMEOUT_MS, 0 = none;", "asyncio.shield: the work goes on"), ("o3", "timeout")),
        ("d6", "security", 488, 52, ("Same passages, only reordered?", "otherwise the answer is not trusted"), ("o4", "error")),
    ]
    for i, (id, kind, y, h, lines, out) in enumerate(steps):
        d.node(id, kind, x, y, w, h, *lines, align="left")
        if i:
            d.edge(steps[i - 1][0], id, "yes" if steps[i - 1][5] else "", exit=(0.5, 1), entry=(0.5, 0))
        if out:
            oid, label = out
            d.node(oid, "optional", ox, y + (h - 42) // 2, ow, 42, label, "fused order")
            d.edge(id, oid, "no", exit=(1, 0.5), entry=(0, 0.5), kind="fallback")
    d.node("ok", "service", x, 556, w, 34, "applied: the model's order")
    d.edge("d6", "ok", "yes", exit=(0.5, 1), entry=(0.5, 0))

    d.zone("z-time", "One slot, limit 1, time limit 20 ms (the test)", 510, 45, 430, 555, "ai")
    t0, tdl, tb, tend, tc, tx = 610, 660, 720, 830, 862, 925  # x positions on the time axis
    lanes = [("search A", 100), ("rerank work", 170), ("slot", 240), ("search B", 330), ("search C", 400)]
    for name, y in lanes:
        d.text(f"lane-{name}", 522, y + 4, 84, 18, f"<b>{name}</b>", color=TEXT)
    d.rect("axis", t0, 455, tx - t0, 2, "#475569")
    d.text("axis-t", t0, 462, 300, 18, "time →")
    # The two time guides are drawn first and stop above the lanes whose labels would cross them.
    d.rect("dl-line", tdl, 92, 1, 200, "#b91c1c")
    d.rect("end-line", tend, 160, 1, 132, "#047857")
    d.rect("a-wait", t0, 100, tdl - t0, 24, "#ddd6fe", "#6d28d9")
    d.text("a-done", tdl + 8, 98, tx - tdl - 8, 34, "20 ms: <b>timeout</b>, returns the fused order")
    d.rect("work", t0, 170, tend - t0, 24, "#c4b5fd", "#6d28d9")
    d.text("work-t", tdl + 8, 174, tend - tdl - 14, 18, "the native call runs on")
    d.rect("slot-held", t0, 240, tend - t0, 24, "#fecaca", "#b91c1c")
    d.text("slot-t", tdl + 8, 244, tend - tdl - 14, 18, "held: running = 1")
    d.rect("slot-free", tend, 240, tx - tend, 24, "#dcfce7", "#047857")
    d.text("slot-f", tend + 6, 244, tx - tend - 6, 18, "free")
    d.rect("b-mark", tb, 330, 8, 24, "#b91c1c")
    d.text("b-t", tb + 14, 326, tx - tb - 14, 34, "<b>busy</b>: the model is skipped, fused order")
    d.rect("c-mark", tc, 400, 8, 24, "#047857")
    d.text("c-t", tc - 150, 430, 210, 18, "<b>applied</b>: the model's order", align="right")
    d.text("why", 522, 492, 405, 90, "If the slot were freed when the search stops waiting, every timeout would let new work start while "
           "the old call still holds the pod's one CPU, and each search would get slower than the last. Here the slot "
           "follows the computation, so at most the limit's worth of work runs at once.")
    d.legend(616, labels={"security": "Check", "ai": "Model work", "optional": "Fused order", "service": "Reranked"})
    return d


def verify():
    d = Diagram("seo-agent-pytorch-verify", 960, 610, "Checking an ONNX file against the PyTorch model it came from")
    d.node("qs", "data", 20, 55, 280, 60, "95 eval questions", "app/data/rag_eval.yaml")
    d.node("cands", "service", 340, 55, 280, 60, "Candidates per question", "bge-small top 20, ≤ 3 per article")
    d.node("pairs", "data", 660, 55, 280, 60, "959 (question, passage) pairs", "passage_text(): title › heading + text")
    d.edge("qs", "cands", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("cands", "pairs", exit=(1, 0.5), entry=(0, 0.5))

    d.zone("z-pt", "PyTorch reference (the train group)", 20, 145, 450, 190, "ai")
    d.zone("z-ox", "The service's own code path", 490, 145, 450, 190, "cluster")
    d.node("pt1", "ai", 35, 180, 420, 60, "transformers AutoTokenizer", "pairs, truncated to 512 tokens, padded per batch")
    d.node("pt2", "ai", 35, 260, 420, 60, "BertForSequenceClassification", "model.safetensors at 233902d, eager attention")
    d.node("ox1", "service", 505, 180, 420, 60, "CrossEncoderReranker.scores()", "tokenizers + tokenizer.json, the same 512 tokens")
    d.node("ox2", "compute", 505, 260, 420, 60, "ONNX Runtime, CPU, 2 threads", "the ONNX file under test (fp32 or int8)")
    d.edge("pairs", "pt1", exit=(0.25, 1), entry=(0.75, 0), via=((730, 132), (350, 132)))
    d.edge("pairs", "ox1", exit=(0.75, 1), entry=(0.75, 0))
    d.edge("pt1", "pt2", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("ox1", "ox2", exit=(0.5, 1), entry=(0.5, 0))

    d.node("cmp", "security", 20, 365, 920, 60, "Compare, question by question",
           "max and mean |Δ logit| · Kendall τ of the two orders · the same best passage · the same top-3 set")
    d.edge("pt2", "cmp", "logits", exit=(0.5, 1), entry=(0.25, 0))
    d.edge("ox2", "cmp", "logits", exit=(0.5, 1), entry=(0.75, 0))

    d.zone("z-res", "Results, 22 November 2026", 20, 445, 920, 105, "plain")
    rows = [
        ("r1", "external", "HF fp32 export", "Δ max 0.00002", "τ 1.000 · top-1 95/95"),
        ("r2", "external", "Our PyTorch export", "Δ max 0.00001", "τ 1.000 · top-1 95/95"),
        ("r3", "service", "HF int8 (the baked file)", "Δ mean 0.16, max 0.85", "τ 0.939 · top-1 93/95"),
        ("r4", "optional", "ORT int8 of our export", "Δ mean 0.18, max 1.12", "τ 0.941 · top-1 89/95"),
    ]
    for i, (id, kind, *lines) in enumerate(rows):
        d.node(id, kind, 35 + i * 226, 475, 212, 64, *lines)
    d.edge("cmp", "z-res", exit=(0.5, 1), entry=(0.5, 0))
    d.legend(566, labels={"data": "Input", "service": "Service code / shipped", "ai": "PyTorch", "compute": "ONNX Runtime",
                          "security": "Comparison", "external": "fp32 (exact)", "optional": "Not shipped"})
    return d


# p95 of the whole search (embed + vector + rerank) and Recall@3 on the 95 questions, no floor, int8 unless named.
# M3 Pro rows: the local sweep (../README.md). GitHub ARM rows: rag-eval.yml runs on ubuntu-24.04-arm (../README.md).
RESULTS = [
    ("no reranker", "m3", 10, 90.5),
    ("int8 · all · 4 threads", "m3", 349, 95.2),
    ("int8 · all · 2 threads", "m3", 559, 95.2),
    ("int8 · 10 · 4 threads", "m3", 211, 92.9),
    ("int8 · 6 · 4 threads", "m3", 108, 91.7),
    ("fp32 · all · 2 threads", "m3", 1195, 95.2),
]
ARM = [  # rag-eval.yml runs 45102975215 (1 thread, and the baseline) and 45102982603 (2 threads), 23 November 2026
    ("no reranker", "arm", 50, 90.5),
    ("int8 · all · 2 threads", "arm", 1685, 94.0),
    ("int8 · all · 1 thread", "arm", 2875, 94.0),
]
FLOOR = [("no floor, or 0.59", 90.5, 95.2), ("floor 0.66 first (Ask the Blog today)", 85.7, 88.1)]


def results():
    rows = RESULTS + ARM
    top = 96
    rh = 34
    d = Diagram("seo-agent-pytorch-results", 960, 340 + rh * len(rows), "Recall@3 against search time: what the reranker costs")
    x0, x1, vmax = 300, 760, 3000.0
    px = (x1 - x0) / vmax
    d.text("p1", 20, 42, 920, 20, "<b>p95 of the whole search, 95 questions, no floor</b>: the bar; p95 and Recall@3 on the right", color=TEXT)
    d.text("col", 790, 70, 150, 18, "<b>p95 · Recall@3</b>", color=TEXT)
    colors = {"m3": ("#bfdbfe", "#1d4ed8"), "arm": ("#ddd6fe", "#6d28d9")}
    for i, (label, where, ms, r3) in enumerate(rows):
        y = top + i * rh
        d.text(f"l{i}", 20, y + 6, 270, 18, label + (" (Linux ARM)" if where == "arm" else " (M3 Pro)"), color=TEXT, align="right")
        fill, stroke = colors[where]
        d.rect(f"b{i}", x0, y + 4, max(2, round(ms * px)), 22, fill, stroke)
        d.text(f"v{i}", 790, y + 7, 150, 18, f"{ms:,} ms · <b>{r3} %</b>")
    yb = top + rh * len(rows)
    d.rect("axis", x0, yb, x1 - x0, 1, "#475569")
    for ms in (0, 400, 1000, 2000, 3000):
        d.rect(f"tick{ms}", x0 + round(ms * px), yb, 1, 6, "#475569")
        d.text(f"tl{ms}", x0 + round(ms * px) - 30, yb + 8, 60, 16, f"{ms} ms", align="center")
    d.rect("rule", x0 + round(400 * px), top - 6, 2, yb - top + 6, "#b91c1c")
    d.text("rule-t", x0 + round(400 * px) + 6, top - 24, 280, 16, "<b>400 ms</b>: the activation rule's limit", color="#b91c1c")

    y2 = yb + 40
    d.text("p2", 20, y2, 920, 20, "<b>Recall@3 with and without the reranker</b> (int8, every candidate, M3 Pro): the floor runs first", color=TEXT)
    lo, hi = 80.0, 100.0
    sx = (x1 - x0) / (hi - lo)
    for i, (label, before, after) in enumerate(FLOOR):
        y = y2 + 30 + i * 62
        d.text(f"fl{i}", 20, y + 14, 270, 18, label, color=TEXT, align="right")
        d.rect(f"fb{i}", x0, y, round((before - lo) * sx), 20, "#e2e8f0", "#64748b")
        d.text(f"fbt{i}", x0 + round((before - lo) * sx) + 8, y + 2, 200, 18, f"without: {before} %")
        d.rect(f"fa{i}", x0, y + 24, round((after - lo) * sx), 20, "#bbf7d0", "#047857")
        gain = round(after - before, 1)
        verdict = "passes the +3 rule" if gain >= 3 else "under the +3 rule"
        xa = x0 + round((after - lo) * sx) + 8
        d.text(f"fat{i}", xa, y + 26, 940 - xa, 18, f"with: <b>{after} %</b> (+{gain}, {verdict})")
    d.text("scale2", x0, y2 + 30 + 2 * 62 - 4, 600, 16, "bars start at 80 %")
    yk = y2 + 30 + 2 * 62 + 20
    d.h = yk + 30
    d.rect("k1", 20, yk, 22, 14, "#bfdbfe", "#1d4ed8")
    d.text("k1t", 48, yk - 1, 220, 18, "M3 Pro (macOS), the local sweep")
    if ARM:
        d.rect("k2", 260, yk, 22, 14, "#ddd6fe", "#6d28d9")
        d.text("k2t", 288, yk - 1, 400, 18, "GitHub ubuntu-24.04-arm runner (Linux)")
    return d


def main():
    for build in (where, search, gate, verify, results):
        d = build()
        (HERE / f"{d.name}.drawio").write_text(d.xml() + "\n")
        print(f"wrote {d.name}.drawio ({d.w}x{d.h})")


if __name__ == "__main__":
    main()
