#!/usr/bin/env python3
"""Figures for "How I Evaluate RAG on jithendar.com" (content/blog/rag-evaluation-ask-the-blog-jithendar-com.mdx).

    python3 sites/jithendar.com/docs/knowledge-sharing/rag-eval-jithendar-com/diagrams/build_diagrams.py   (from services/www/)
    bash sites/jithendar.com/docs/knowledge-sharing/rag-eval-jithendar-com/diagrams/export.sh

The first command writes one editable .drawio file per figure beside this script; the second has the draw.io desktop
CLI export each to public/images/rag-evaluation-ask-the-blog-jithendar-com/<name>.svg and .png. After editing a .drawio
file by hand, run only export.sh, or this script overwrites the edits.

Sources (13 November 2026): .github/workflows/rag-eval.yml and ci-seo-agent.yml, services/seo-agent/scripts/rag_eval.py,
app/rag_eval.py, app/seo_ml/train.py (run_rag_eval), app/services/ask_pipeline.py, tests/fixtures/rag_eval.yaml,
kubernetes/seo-agent-40-seo-agent.yaml, docs/seo/RAG.md and docs/seo/rag-eval/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio_model import Diagram  # noqa: E402

HERE = Path(__file__).resolve().parent


def answer_path():
    d = Diagram("ask-the-blog-eval-map", 960, 700, "Ask the Blog's answer path, and which evaluation measures each step")
    d.node("q", "client", 35, 70, 200, 72, "Reader question", "at most 500 characters")
    d.node("gin", "security", 260, 70, 200, 72, "guard_input", "injection, personal data,", "off-topic patterns")
    d.node("ret", "ai", 485, 70, 200, 72, "retrieve top 6", "vector (default) or hybrid", "→ retrieval eval")
    d.node("floor", "security", 710, 70, 200, 72, "cosine floor 0.66", "ASK_BLOG_MIN_SCORE", "→ calibrated floor")
    d.node("grade", "ai", 710, 200, 200, 72, "grade_relevance", "keeps the excerpts that", "answer; Haiku")
    d.node("ans", "ai", 485, 200, 200, 72, "answer_with_citations", "[n] for every statement", "→ generation eval")
    d.node("gout", "security", 260, 200, 200, 72, "guard_output", "uncited → fallback,", "links stripped")
    d.node("reply", "client", 35, 200, 200, 72, "Answer + citations", "/blog/slug#heading links")
    d.node("fb", "optional", 710, 320, 200, 64, "Fallback", "no article on this yet,", "+ related links")
    d.edge("q", "gin", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("gin", "ret", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("ret", "floor", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("floor", "grade", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("grade", "ans", exit=(0, 0.5), entry=(1, 0.5))
    d.edge("ans", "gout", exit=(0, 0.5), entry=(1, 0.5))
    d.edge("gout", "reply", exit=(0, 0.5), entry=(1, 0.5))
    d.edge("grade", "fb", exit=(0.5, 1), entry=(0.5, 0), label="not relevant")
    d.edge("gout", "fb", exit=(0.5, 1), entry=(0, 0.5), via=[(360, 352)], label="uncited or NO_ANSWER")
    d.zone("z-ret", "Retrieval eval: rag_eval.py, every run", 20, 420, 450, 168, "ai")
    d.node("m-ret", "ops", 35, 452, 420, 120, "What it reports (k = 6)", "Recall@1/3/6: right article in the top 1, 3, 6",
           "MRR: how high the first right article ranks", "Section-anchor hit: right section in the top 6",
           "No-answer false positives at the floor", "Calibrated floor and p50/p95 latency", align="left")
    d.zone("z-gen", "Generation eval: opt-in, real Claude calls", 490, 420, 450, 168, "risk")
    d.node("m-gen", "ops", 505, 452, 420, 120, "What it reports", "Answered rate; abstain rate on no-answer questions",
           "Citation precision by labels (expected article)", "Citation precision by an LLM judge",
           "Faithfulness: claims the excerpts support", "Spend capped by --generation-max-usd", align="left")
    d.text("note", 20, 600, 920, 32, "Relevant excerpts go on to the answer step. Retrieval quality decides everything after it: the grader and the answer only ever see the "
           "excerpts the retriever found. Ask the Blog is off in the manifests (ASK_BLOG_ENABLED: \"false\").", size=11)
    d.legend(640, labels={"security": "Guard or filter", "optional": "Fallback"})
    return d


def workflow():
    d = Diagram("rag-eval-workflow", 960, 860, "rag-eval.yml: comparing retrievers with the production model")
    d.node("run", "client", 35, 56, 280, 64, "Manual run", "Actions → RAG eval (manual)")
    d.node("inputs", "ops", 340, 56, 585, 64, "Inputs (workflow_dispatch)", "configs: which retrievers to compare",
           "extra_args, e.g. --max-per-article 2")
    d.zone("z-run", "GitHub-hosted runner: ubuntu-latest, 30 minute limit", 20, 140, 920, 470, "cluster", corner="right")
    d.zone("z-setup", "Setup", 35, 170, 890, 104)
    d.node("co", "ops", 50, 198, 200, 64, "Checkout + uv sync", "locked dependencies,", "--frozen")
    d.node("model", "security", 270, 198, 200, 64, "bge-small ONNX", "revision + sha256 checks", "read from the Dockerfile")
    d.node("mdx", "service", 490, 198, 200, 64, "Blog MDX files", "content/blog/*.mdx", "the real articles")
    d.node("pg", "data", 710, 198, 200, 64, "pgvector service", "pg18, scratch database", shape="db")
    d.node("index", "ai", 50, 300, 410, 92, "Index per configuration", "chunker: v4 characters or tokens",
           "embeddings: exact cosine in numpy", "full text: Postgres (hybrid configs)")
    d.node("qs", "data", 500, 300, 425, 92, "tests/fixtures/rag_eval.yaml", "95 questions, each with expected",
           "articles and section anchors", "11 have no answer on the site")
    d.node("ret", "ai", 50, 414, 875, 64, "Retrieve the top 6 for every question, in every configuration",
           "baseline-v4 · token-vector · token-vector-div · token-hybrid-noid · token-hybrid")
    d.node("score", "ops", 50, 500, 875, 80, "Score each configuration",
           "Recall@1/3/6 · MRR · section-anchor hit rate · p50/p95 latency",
           "no-answer false positives · calibrated floor · floor table · results by type and tag")
    d.node("summary", "ops", 35, 630, 280, 64, "Job summary", "a report per configuration", "and one comparison table")
    d.node("commit", "data", 340, 630, 280, 64, "docs/seo/rag-eval/", "reports worth keeping,", "committed by hand")
    d.node("decide", "security", 645, 630, 280, 64, "A person decides", "RAG_MODE, max per article,", "ASK_BLOG_MIN_SCORE")
    d.node("cm", "ops", 645, 716, 280, 56, "seo-agent-config", "ConfigMap change, then restart")

    d.edge("run", "inputs", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("run", "z-setup", exit=(0.5, 1), entry=((175 - 35) / 890, 0), label="dispatch")
    d.edge("z-setup", "index", exit=((255 - 35) / 890, 1), entry=(0.5, 0))
    d.edge("z-setup", "qs", exit=((712.5 - 35) / 890, 1), entry=(0.5, 0))
    d.edge("index", "ret", exit=(0.5, 1), entry=((255 - 50) / 875, 0))
    d.edge("qs", "ret", exit=(0.5, 1), entry=((712.5 - 50) / 875, 0))
    d.edge("ret", "score", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("score", "summary", exit=((175 - 50) / 875, 1), entry=(0.5, 0))
    d.edge("summary", "commit", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("commit", "decide", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("decide", "cm", exit=(0.5, 1), entry=(0.5, 0), kind="control")
    d.text("note", 20, 786, 920, 32, "Nothing here touches the cluster: the run builds its own index from the MDX files and "
           "throws it away. Only a person turns a result into a setting.", size=11)
    d.legend(826)
    return d


def loops():
    d = Diagram("rag-eval-four-loops", 960, 680, "Where retrieval gets evaluated, and how real questions come back")
    d.node("set", "data", 35, 78, 190, 324, "rag_eval.yaml", "95 labelled questions", "expected articles",
           "section anchors", "types and tags", "the shared yardstick")
    rows = [
        ("z1", "Every pull request: ci-seo-agent.yml", 48, "ops",
         [("pytest", "pytest", "eval code, hashed vectors,", "in memory and Postgres"),
          ("smoke", "rag_eval.py smoke", "--embeddings hash", "checks only that it runs"),
          ("nogate", "No recall threshold", "hashed vectors are lexical:", "a gate would track tokens")]),
        ("z2", "On demand: rag-eval.yml (manual)", 178, "ai",
         [("real", "Real model", "bge-small ONNX, pinned", "revision and sha256"),
          ("cfgs", "Every configuration", "chunkers, vector, hybrid,", "diversification"),
          ("rep", "Reports and a decision", "docs/seo/rag-eval/", "ConfigMap defaults")]),
        ("z3", "Every Sunday 04:47 UTC: seo-flow-ml", 308, "ops",
         [("live", "Live retriever", "the production index", "and RAG_MODE"),
          ("runs", "seo_rag_eval_runs", "one row per run", None),
          ("gauge", "seo_rag_eval_recall_at_3", "Prometheus → Grafana", "seo-agent dashboard")]),
    ]
    for zid, label, y, tone, nodes in rows:
        d.zone(zid, label, 245, y, 695, 110, "cluster" if tone == "ai" else "plain")
        for i, (key, title, a, b) in enumerate(nodes):
            kind = "optional" if key == "nogate" else ("data" if key == "runs" else ("ai" if key in ("real", "cfgs", "live") else "ops"))
            lines = [a] + ([b] if b else [])
            d.node(key, kind, 260 + i * 225, y + 30, 210, 64, title, *lines, shape="db" if key == "runs" else "box")
        d.edge(nodes[0][0], nodes[1][0], exit=(1, 0.5), entry=(0, 0.5))
        d.edge(nodes[1][0], nodes[2][0], exit=(1, 0.5), entry=(0, 0.5))
    for key, cy in (("pytest", 110), ("real", 240), ("live", 370)):
        d.edge("set", key, exit=(1, (cy - 78) / 324), entry=(0, 0.5))
    d.zone("z4", "From real readers, once Ask the Blog is on", 20, 438, 920, 110, corner="right")
    d.node("label", "security", 35, 468, 190, 64, "A person labels", "slugs and anchors")
    d.node("mine", "ops", 260, 468, 210, 64, "rag_mine_eval.py", "read-only candidates")
    d.node("logs", "data", 485, 468, 210, 64, "seo_ask_log + gaps", "fallbacks, low scores", shape="db")
    d.node("widget", "optional", 710, 468, 210, 64, "Ask the Blog", "off in the manifests", "ASK_BLOG_ENABLED")
    d.edge("widget", "logs", exit=(0, 0.5), entry=(1, 0.5))
    d.edge("logs", "mine", exit=(0, 0.5), entry=(1, 0.5))
    d.edge("mine", "label", exit=(0, 0.5), entry=(1, 0.5))
    d.edge("label", "set", exit=(0.5, 0), entry=(0.5, 1), kind="control", label="new questions")
    d.text("note", 20, 562, 920, 46, "CI only proves the code runs; the manual workflow is where settings are decided; the weekly "
           "step watches the live index for drift. Mined questions are added only after a person labels them, so the set is "
           "never tuned to a retriever.", size=11)
    d.legend(614, labels={"optional": "Off, or deliberately absent"})
    return d


FIGURES = [answer_path, workflow, loops]


def main():
    names = []
    for make in FIGURES:
        d = make()
        (HERE / f"{d.name}.drawio").write_text(d.xml(), encoding="utf-8")
        names.append(d.name)
    (HERE / "figures.txt").write_text("\n".join(names) + "\n", encoding="utf-8")
    print(f"{len(names)} .drawio files: {', '.join(names)}")


if __name__ == "__main__":
    main()
