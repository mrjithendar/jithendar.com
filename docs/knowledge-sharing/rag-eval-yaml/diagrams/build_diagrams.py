#!/usr/bin/env python3
"""Figures for content/blog/rag-eval-yaml-question-set-ask-the-blog.mdx (the RAG evaluation question set).

    python3 docs/knowledge-sharing/rag-eval-yaml/diagrams/build_diagrams.py   # writes the .drawio files
    bash docs/knowledge-sharing/rag-eval-yaml/diagrams/export.sh              # draw.io CLI → public/images/rag-eval-yaml/

After editing a .drawio file by hand, run only export.sh, or this script overwrites the edits.

Sources (22 November 2026): mrjithendar/moks-seo-agent e4669f7 (app/data/rag_eval.yaml, app/rag_eval.py,
app/seo_ml/train.py, scripts/rag_eval.py, .dockerignore, Dockerfile, tests/test_seo_ml_fixes.py) and the eval run in
../README.md (bge-small-en-v1.5 ONNX, token chunker, vector search, at most 3 chunks per article, frozen corpus).
The strip plot's numbers are FLOOR_POINTS below, copied from that run's per-question rows.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio_model import Diagram  # noqa: E402

HERE = Path(__file__).resolve().parent


def anatomy():
    d = Diagram("rag-eval-yaml-anatomy", 960, 640, "One entry of rag_eval.yaml, and what reads each field")
    rows = [
        (("id: x37", "c, h, e, t, n = first 55; x01–x40 = hard set"),
         ("Report rows", "the per-question table in every report")),
        (("question", "Error: error getting credentials when", "Terraform pulls the Valkey chart"),
         ("search(question, k = 6)", "embedded as written, with bge-small's query prefix;",
          "min_score 0: floors are applied afterwards")),
        (("type: exact-term", "concept · how-to · exact-term ·", "troubleshooting · no-answer"),
         ("Checked, then the By question type table", "no-answer questions are scored only on",
          "the no-answer false positives and the floor")),
        (("tags: [exact]", "optional: paraphrase · multi-hop · exact ·", "near-miss"),
         ("Hard set by tag table", "Recall@3 and MRR per tag; near-miss questions are",
          "no-answer, so they land in the false-positive rate")),
        (("slugs", "[valkey-redis-sentinel-minikube-terraform]", "any one of the listed articles counts"),
         ("Rank: Recall@1/3/6, MRR, calibrated floor", "first top-6 hit whose /blog/<slug> is listed = rank;",
          "best cosine among those hits = best expected cosine;", "generation eval: label citation precision")),
        (("anchors", "[terraform-cannot-pull-the-chart-error-getting-credentials]", "acceptable sections of those articles"),
         ("Section-anchor hit rate", "a top-6 hit of an expected article whose heading",
          "anchor is listed (h1–h3, github-slugger ids)")),
    ]
    y, top = 90, 50  # zones are drawn below the boxes whatever the order (Diagram.xml)
    for i, (left, right) in enumerate(rows):
        h = max(20 + 16 * (len(left) - 1) + 6, 20 + 16 * (len(right) - 1) + 6) + 8
        d.node(f"f{i}", "data", 35, y, 440, h, *left, align="left")
        d.node(f"r{i}", "service", 540, y, 400, h, *right, align="left")
        d.edge(f"f{i}", f"r{i}", exit=(1, 0.5), entry=(0, 0.5))
        y += h + 12
    d.zone("z-yaml", "app/data/rag_eval.yaml · version 1 · 95 questions", 20, top, 470, y - top + 2, "plain")
    d.zone("z-code", "What reads it (app/rag_eval.py)", 525, top, 430, y - top + 2, "plain")
    y += 18
    d.node("check", "security", 20, y, 935, 62, "load_eval_set(): one ValueError for the whole file",
           "an unknown type or tag, or an answerable question without slugs → \"malformed eval questions: [ids]\".",
           "The version key is not read by the code; ids, rules and comments are for the people who edit the file.",
           align="left")
    d.legend(y + 78, labels={"data": "The YAML file", "service": "Code that reads it", "security": "Validation"})
    return d


def scoring():
    d = Diagram("rag-eval-yaml-scoring", 960, 600, "How one question becomes numbers (app/rag_eval.py, k = 6)")
    xs = [20, 257, 494, 731]
    w = 209
    d.node("q", "data", xs[0], 55, w, 78, "question", "from rag_eval.yaml,", "exactly as written")
    d.node("emb", "ai", xs[1], 55, w, 78, "embed", "bge-small ONNX + its", "query prefix (production)")
    d.node("cand", "service", xs[2], 55, w, 78, "20 candidates", "exact cosine over", "every chunk of the corpus")
    d.node("top", "service", xs[3], 55, w, 78, "top 6 hits", "at most 3 chunks per article,", "code windows merged")
    d.edge("q", "emb", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("emb", "cand", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("cand", "top", exit=(1, 0.5), entry=(0, 0.5))

    d.zone("z-score", "score_question(): look at hits i = 1 … 6", 20, 160, 920, 140, "plain")
    d.node("ans", "service", 35, 190, 560, 96, "Answerable question (concept, how-to, exact-term, troubleshooting)",
           "slug of hit i is in slugs, first time → rank = i", "highest cosine among those hits → best expected cosine",
           "that hit's heading anchor is in anchors → anchor hit", align="left")
    d.node("neg", "service", 610, 190, 315, 96, "no-answer question", "highest cosine of all 6 hits",
           "→ best cosine", "(rank and anchors are not used)", align="left")
    d.edge("top", "z-score", "hits with cosine, slug, anchor", exit=(0.5, 1), entry=(0.92, 0))

    d.zone("z-sum", "summarize(): one number per metric, over all 95 questions", 20, 325, 920, 125, "plain")
    boxes = [
        ("Recall@k", "answerable with", "rank ≤ k, k = 1, 3, 6"),
        ("MRR", "mean of 1 / rank,", "0 if not in the top 6"),
        ("Anchor hit rate", "answerable with an", "anchor hit in the top 6"),
        ("Calibrated floor", "lowest best expected", "cosine, rounded down"),
        ("No-answer FP @ f", "no-answer questions", "with best cosine ≥ f"),
    ]
    bw, gap = 170, 12
    for i, (t, *ls) in enumerate(boxes):
        d.node(f"m{i}", "compute", 35 + i * (bw + gap), 355, bw, 80, t, *ls)
    d.edge("z-score", "z-sum", exit=(0.5, 1), entry=(0.5, 0))

    d.node("ex", "client", 20, 470, 920, 96,
           "Worked example: x02, a paraphrase how-to (vector search, frozen corpus, 22 November 2026)",
           "hit 1 valkey-redis-sentinel… 0.70 · hit 2 devops-interview-preparation-guide 0.70 · "
           "hit 3 github-actions-authenticate-minikube 0.69",
           "→ rank 3: a miss for Recall@1, a hit for Recall@3 and Recall@6, reciprocal rank 1/3, best expected cosine 0.69.",
           "Hit 4 is the same article's #1-the-short-version, one of the listed anchors → anchor hit.", align="left")
    d.legend(582, labels={"data": "The YAML file", "ai": "Embedding model", "service": "Retrieval and scoring",
                          "compute": "Reported metric", "client": "Example"})
    return d


# (id, set, cosine). set: first55 | hard | no-answer | near-miss. Answerable: best cosine of an expected article
# within the top 6; no-answer: best cosine of any hit. x06, x09, x15 and x16 had no expected article in the top 6.
FLOOR_POINTS = [
    ("x08", "hard", 0.600), ("x07", "hard", 0.621), ("x03", "hard", 0.651), ("x18", "hard", 0.659), ("x04", "hard", 0.671),
    ("x36", "hard", 0.674), ("e03", "first55", 0.681), ("x14", "hard", 0.683), ("x10", "hard", 0.690), ("x02", "hard", 0.691),
    ("x05", "hard", 0.694), ("x19", "hard", 0.706), ("x24", "hard", 0.715), ("e07", "first55", 0.724), ("x17", "hard", 0.726),
    ("t03", "first55", 0.728), ("x13", "hard", 0.728), ("x12", "hard", 0.729), ("x22", "hard", 0.729), ("x01", "hard", 0.737),
    ("x11", "hard", 0.742), ("e09", "first55", 0.744), ("x29", "hard", 0.746), ("t04", "first55", 0.755), ("x25", "hard", 0.761),
    ("x27", "hard", 0.769), ("x28", "hard", 0.770), ("c04", "first55", 0.771), ("c11", "first55", 0.776), ("h02", "first55", 0.779),
    ("t06", "first55", 0.781), ("x33", "hard", 0.781), ("c14", "first55", 0.783), ("h07", "first55", 0.784), ("t07", "first55", 0.784),
    ("x21", "hard", 0.784), ("x30", "hard", 0.786), ("t02", "first55", 0.790), ("t01", "first55", 0.792), ("c08", "first55", 0.793),
    ("x23", "hard", 0.793), ("h05", "first55", 0.796), ("e01", "first55", 0.796), ("x34", "hard", 0.796), ("c01", "first55", 0.800),
    ("c07", "first55", 0.804), ("x26", "hard", 0.804), ("e10", "first55", 0.810), ("x35", "hard", 0.810), ("e11", "first55", 0.811),
    ("e06", "first55", 0.819), ("h09", "first55", 0.820), ("h11", "first55", 0.821), ("t05", "first55", 0.821), ("c03", "first55", 0.822),
    ("h08", "first55", 0.824), ("c12", "first55", 0.831), ("c02", "first55", 0.834), ("h12", "first55", 0.834), ("x20", "hard", 0.837),
    ("c06", "first55", 0.840), ("t10", "first55", 0.842), ("e05", "first55", 0.845), ("c09", "first55", 0.846), ("c10", "first55", 0.847),
    ("h01", "first55", 0.849), ("e08", "first55", 0.850), ("e02", "first55", 0.851), ("t09", "first55", 0.854), ("x31", "hard", 0.855),
    ("x32", "hard", 0.856), ("t08", "first55", 0.858), ("h10", "first55", 0.859), ("x37", "hard", 0.860), ("c05", "first55", 0.866),
    ("h04", "first55", 0.868), ("h03", "first55", 0.877), ("h06", "first55", 0.890), ("c13", "first55", 0.900), ("e04", "first55", 0.914),
    ("n02", "no-answer", 0.523), ("n03", "no-answer", 0.625), ("n06", "no-answer", 0.630), ("n01", "no-answer", 0.683),
    ("n07", "no-answer", 0.686), ("n08", "no-answer", 0.686), ("n04", "no-answer", 0.702), ("n05", "no-answer", 0.706),
    ("x39", "near-miss", 0.721), ("x40", "near-miss", 0.728), ("x38", "near-miss", 0.778),
]
SET_COLOURS = {"first55": "#1d4ed8", "hard": "#6d28d9", "no-answer": "#be123c", "near-miss": "#f97316"}


def floor():
    answerable = [p for p in FLOOR_POINTS if p[1] in ("first55", "hard")]
    negatives = [p for p in FLOOR_POINTS if p[1] in ("no-answer", "near-miss")]
    assert len(answerable) == 80 and len(negatives) == 11  # 84 answerable, 4 of them not in the top 6
    d = Diagram("rag-eval-yaml-floor", 960, 560, "Where a cosine floor cuts: 95 questions, production retrieval, 22 November 2026")
    lo, hi, x0, x1 = 0.50, 0.95, 160, 930

    def px(v):
        return x0 + (v - lo) / (hi - lo) * (x1 - x0)

    lanes = [("Answerable (80 of 84)", "best cosine of an", "expected article", answerable, 205),
             ("no-answer (11)", "best cosine of", "anything retrieved", negatives, 300)]
    for i, (title, l1, l2, pts, base) in enumerate(lanes):
        d.text(f"lane{i}", 20, base - 44, 130, 54, f"<b>{title}</b><br>{l1}<br>{l2}", color="#0f172a")
        d.rect(f"base{i}", x0, base + 7, x1 - x0, 1, "#cbd5e1")
        stack = {}
        for qid, kind, v in pts:
            b = math.floor(v * 100 + 1e-9)
            n = stack.get(b, 0)
            stack[b] = n + 1
            d.dot(f"d-{qid}", px(b / 100 + 0.005), base - n * 11, SET_COLOURS[kind])
    axis_y = 330
    d.rect("axis", x0, axis_y, x1 - x0, 2, "#475569")
    for i in range(10):
        v = lo + i * 0.05
        d.rect(f"tick{i}", px(v) - 1, axis_y, 2, 8, "#475569")
        d.text(f"tl{i}", px(v) - 20, axis_y + 12, 40, 16, f"{v:.2f}", align="center")
    d.text("axis-title", x0, axis_y + 30, x1 - x0, 16, "cosine similarity (bge-small-en-v1.5), one dot per question, 0.01 bins",
           align="center")
    floors = [(0.59, "#047857", "0.59"), (0.66, "#b91c1c", "0.66"), (0.70, "#475569", "0.70")]
    for v, colour, label in floors:
        d.rect(f"fl{label}", px(v) - 1, 70, 2, axis_y - 70, colour)
        d.text(f"flt{label}", px(v) - 18, 52, 36, 16, f"<b>{label}</b>", color=colour, align="center")
    y = axis_y + 62
    d.node("c59", "service", 20, y, 300, 80, "0.59: calibrated on all 95", "loses no expected answer;",
           "10 of 11 no-answer reach the grader", align="left")
    d.node("c66", "security", 330, y, 300, 80, "0.66: ASK_BLOG_MIN_SCORE today", "loses 4 answers: x08, x07, x03, x18;",
           "8 of 11 no-answer reach the grader", align="left")
    d.node("c70", "external", 640, y, 300, 80, "0.70", "loses 11 answers;", "5 of 11 no-answer reach the grader", align="left")
    ly = y + 96
    d.text("lg-title", 20, ly, 80, 18, "<b>Legend</b>", color="#0f172a")
    items = [("first55", "first 55 questions"), ("hard", "hard set (x01–x37)"), ("no-answer", "no-answer (n01–n08)"),
             ("near-miss", "near-miss (x38–x40)")]
    cx = 90
    for kind, label in items:
        d.dot(f"lg-{kind}", cx + 6, ly + 9, SET_COLOURS[kind])
        d.text(f"lgt-{kind}", cx + 16, ly + 1, 150, 18, label)
        cx += 175
    d.text("lg-miss", 20, ly + 24, 920, 18, "Not drawn: x06, x09, x15 and x16 had no expected article in the top 6, so no floor "
           "can help them.")
    d.h = ly + 50
    return d


def move():
    d = Diagram("rag-eval-yaml-move", 960, 520, "Why the question set moved from tests/fixtures to app/data (PR #30, 22 November 2026)")
    w, gap, x = 212, 16, 35
    xs = [x + i * (w + gap) for i in range(4)]
    d.zone("z-before", "Before: tests/fixtures/rag_eval.yaml", 20, 50, 920, 150, "risk")
    d.node("b1", "data", xs[0], 85, w, 95, "In the repository", "tests/fixtures/rag_eval.yaml", "beside the tests using it")
    d.node("b2", "ops", xs[1], 85, w, 95, "docker build", ".dockerignore lists tests", "→ no tests/ in the image")
    d.node("b3", "compute", xs[2], 85, w, 95, "seo-agent pod (/srv)", "seo_ml_flow, step rag_eval", "opens /srv/tests/fixtures/…")
    d.node("b4", "security", xs[3], 85, w, 95, "FileNotFoundError", "the run ends failed:", "18 and 20 November")
    for a, b in (("b1", "b2"), ("b2", "b3"), ("b3", "b4")):
        d.edge(a, b, exit=(1, 0.5), entry=(0, 0.5))
    d.marker(1, xs[3] + w - 4, 88)

    d.zone("z-after", "After: app/data/rag_eval.yaml (commit 400e1b9)", 20, 220, 920, 150, "cluster")
    d.node("a1", "data", xs[0], 255, w, 95, "In the repository", "app/data/rag_eval.yaml", "ships with the code")
    d.node("a2", "ops", xs[1], 255, w, 95, "docker build", "COPY app ./app", "→ /srv/app/data/rag_eval.yaml")
    d.node("a3", "compute", xs[2], 255, w, 95, "seo-agent pod (/srv)", "evaluate(\"live\"), live index", "no file → skipped, not failed")
    d.node("a4", "data", xs[3], 255, w, 95, "Results", "a seo_rag_eval_runs row", "seo_rag_eval_recall_at_3", shape="db")
    for a, b in (("a1", "a2"), ("a2", "a3"), ("a3", "a4")):
        d.edge(a, b, exit=(1, 0.5), entry=(0, 0.5))

    bw = 296
    d.node("n1", "ops", 20, 390, bw, 80, "Guarded by a test", "test_the_eval_set_ships_in_the_image:",
           "tests ignored, app copied, ≥ 20 questions", align="left")
    d.node("n2", "optional", 20 + bw + 16, 390, bw, 80, "On 22 November", "the pod has the file; seo_rag_eval_runs",
           "has no rows: no run has finished since", align="left")
    d.node("n3", "external", 20 + 2 * (bw + 16), 390, bw, 80, "Stays in tests/", "tests/fixtures/rag_corpus: the frozen",
           "blog copy the CI and manual runs use", align="left")
    d.legend(486, failure=True, labels={"data": "Files and results", "ops": "Build and tests", "compute": "Runtime",
                                       "security": "Failure", "optional": "Not happened yet", "external": "Unchanged"})
    return d


def main():
    for build in (anatomy, scoring, floor, move):
        d = build()
        (HERE / f"{d.name}.drawio").write_text(d.xml() + "\n")
        print(f"wrote {d.name}.drawio ({d.w}x{d.h})")


if __name__ == "__main__":
    main()
