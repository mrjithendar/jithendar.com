#!/usr/bin/env python3
"""Generate the SVGs of the 2026-10-31 version of content/blog/moks-rag-and-skills-design.mdx (standard library only).
The live post still uses them. The 2026-11-01 update uses the .mmd sources in this folder instead.

    python3 docs/diagrams/moks-rag-skills/build_diagrams.py   (from www/)

Writes public/images/moks/moks-*.svg, reusing the drawing helpers of the RoboShop AI diagrams. This
script is the editable source. Figures describe moks commit 9b94516: when a component or call changes,
update it and re-run.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "roboshop-ai-microservices"))
import build_diagrams as base  # noqa: E402  the sibling generator, not this file

Svg = base.Svg
base.OUT = HERE.parents[2] / "public" / "images" / "moks"


def trust():
    s = Svg(720, 650, "MOKS: where skills and knowledge enter an investigation",
            "An investigation runs triage, logs, skills, a bounded plan and act loop, correlation and a report. "
            "SKILL.md files enter on the trusted side, as tool steps and prompt instructions. Knowledge, logs and tool "
            "output enter on the untrusted side, through kb_search and other read-only tools, and every tool call passes "
            "the ToolExecutor. The report is then validated against the evidence collected.")
    s.text(24, 40, "Where skills and knowledge enter an investigation", 20, 700, "#0f172a", "start")
    s.text(24, 62, "Skills are reviewed instructions. Knowledge is untrusted data. Neither can act without the ToolExecutor.", 12.5, 400, "#475569", "start")

    s.band(12, 84, 200, 540, "Trusted", "reviewed in Git")
    s.band(232, 84, 256, 540, "Investigation", "LangGraph, bounded")
    s.band(508, 84, 200, 540, "Tools and data", "results fenced as untrusted")

    cx, w = 262, 196
    s.node(cx, 136, w, 46, "client", "triage", ["baseline, detectors"])
    s.node(cx, 202, w, 46, "client", "logs", ["read before any skill"])
    s.node(cx, 268, w, 46, "ai", "skills", ["select, run steps"])
    s.node(cx, 334, w, 46, "ai", "plan <-> act", ["up to 4 rounds"], bold=True)
    s.node(cx, 400, w, 46, "client", "correlate", ["changes vs symptoms"])
    s.node(cx, 466, w, 46, "client", "report", ["facts cite E-refs"])
    s.node(cx, 548, w, 56, "edge", "report validation", ["uncited facts dropped"], bold=True)
    for a, b in ((182, 202), (248, 268), (314, 334), (380, 400), (446, 466), (512, 548)):
        s.arrow([(360, a), (360, b)])

    s.node(28, 268, 168, 70, "ai", "SKILL.md", ["published generation,", "pinned by digest"])
    s.arrow([(196, 291), (262, 291)], label="steps", at=(229, 283))
    s.arrow([(112, 338), (112, 372), (262, 372)], label="body joins prompt", at=(176, 364))

    s.node(524, 202, 168, 70, "edge", "ToolExecutor", ["allowlist, schema,", "RBAC, scope, budget"], bold=True)
    s.node(524, 318, 168, 56, "svc", "live systems", ["Kubernetes, metrics, logs"])
    s.cylinder(524, 410, 168, 76, "store", "knowledge", ["kb_search, cited"])
    s.arrow([(458, 291), (492, 291), (492, 237), (524, 237)])
    s.arrow([(458, 357), (500, 357), (500, 255), (524, 255)])
    s.arrow([(608, 272), (608, 318)])
    s.arrow([(540, 272), (540, 296), (514, 296), (514, 448), (524, 448)])
    s.text(608, 516, "Tool results return", 12, 400, "#475569")
    s.text(608, 533, "as evidence E1, E2, ...", 12, 400, "#475569")
    s.text(608, 550, "inside random-tagged", 12, 400, "#475569")
    s.text(608, 567, "data blocks", 12, 400, "#475569")
    s.render("moks-trust-model")


def ingestion():
    s = Svg(720, 610, "MOKS: knowledge ingestion",
            "A sync pass pins one Git commit and reads at most 500 files, least recently tried first. Files that look like "
            "secrets are excluded and the rest is redacted and chunked. Documents, chunks and an outbox event commit in one "
            "PostgreSQL transaction. After commit a worker takes a per-document lock, embeds the chunks and writes the "
            "external index, which can always be rebuilt from PostgreSQL.")
    s.text(24, 40, "Ingestion: PostgreSQL first, indexes second", 20, 700, "#0f172a", "start")
    s.text(24, 62, "An external index is derived data. It is written only after the change has committed.", 12.5, 400, "#475569", "start")

    s.band(12, 84, 696, 160, "1. Bounded sync pass", "up to 500 files against a persistent inventory")
    y = 146
    s.node(28, y, 150, 78, "client", "list", ["pin one commit", "resumable"])
    s.node(198, y, 150, 78, "client", "read", ["least recently", "tried first"])
    s.node(368, y, 150, 78, "edge", "filter", ["exclude secret files,", "redact the rest"], bold=True)
    s.node(538, y, 154, 78, "client", "chunk", ["350 tokens, overlap 30", "keep line ranges"])
    s.arrow([(178, y + 39), (198, y + 39)])
    s.arrow([(348, y + 39), (368, y + 39)])
    s.arrow([(518, y + 39), (538, y + 39)])

    s.band(12, 262, 696, 134, "2. One PostgreSQL transaction", "the event exists exactly when the change does")
    s.cylinder(290, 310, 190, 72, "store", "documents, chunks", ["system of record"])
    s.cylinder(502, 310, 190, 72, "store", "index_outbox", ["one revision per change"])
    s.arrow([(615, 224), (615, 253), (385, 253), (385, 310)])
    s.arrow([(480, 346), (502, 346)])

    s.band(12, 414, 696, 170, "3. After commit")
    s.text(226, 436, "external backends only; replays are harmless, older revisions are dropped", 12, 400, "#64748b", "start")
    y = 476
    s.node(28, y, 200, 86, "client", "drain_outbox", ["advisory lock per", "document, retry, then dead"])
    s.node(260, y, 200, 86, "ai", "embed", ["heading + chunk text", "failure: keyword-only"])
    s.cylinder(492, y, 200, 86, "external", "external index", ["OpenSearch or Pinecone"])
    s.arrow([(597, 382), (597, 405), (200, 405), (200, y)])
    s.arrow([(228, y + 43), (260, y + 43)])
    s.arrow([(460, y + 43), (492, y + 43)])
    s.render("moks-rag-ingestion")


def retrieval():
    s = Svg(720, 690, "MOKS: hybrid retrieval",
            "A search first turns the person's role bindings into grants. Keyword, exact identifier and vector rankers each "
            "return candidates, filtered where the backend can express the grants, and reciprocal rank fusion combines them. "
            "Every candidate is then checked again against PostgreSQL. If too few survive, the candidate pool widens up to "
            "400. Survivors are adjusted by small visible signals and deduplicated, and the passages are judged supported, "
            "weak or none.")
    s.text(24, 40, "Retrieval: ranking comes second to access", 20, 700, "#0f172a", "start")
    s.text(24, 62, "The index suggests. PostgreSQL decides. A fused score orders results and is never shown as confidence.", 12.5, 400, "#475569", "start")

    s.node(190, 84, 340, 58, "client", "query + person", ["whole bindings become grants; none means no results"])
    s.band(12, 160, 696, 136, "Rankers")
    y = 212
    s.node(28, y, 208, 68, "client", "keyword", ["BM25 or tsvector"])
    s.node(256, y, 208, 68, "edge", "exact identifier", ["counted twice"], bold=True)
    s.node(484, y, 208, 68, "ai", "vector", ["skipped if model differs"])
    s.arrow([(360, 142), (360, y)])
    s.arrow([(300, 142), (300, 152), (132, 152), (132, y)])
    s.arrow([(420, 142), (420, 152), (588, 152), (588, y)])

    s.node(230, 318, 260, 54, "ai", "reciprocal rank fusion", ["sum of 1 / (60 + rank)"])
    s.arrow([(360, 280), (360, 318)])
    s.arrow([(132, 280), (132, 306), (300, 306), (300, 318)])
    s.arrow([(588, 280), (588, 306), (420, 306), (420, 318)])

    s.node(190, 396, 340, 66, "store", "authoritative check", ["re-read from PostgreSQL: active, in scope, readable,", "not excluded as stale"], bold=True)
    s.arrow([(360, 372), (360, 396)])
    s.arrow([(530, 429), (585, 429), (585, 345), (490, 345)], "dlq", label="too few survive:\nwiden, up to 400", at=(595, 382), anchor="start")

    s.node(190, 486, 340, 66, "client", "signals and dedup", ["identifier, service, authority, stale, retired;", "at most 3 chunks per document"])
    s.arrow([(360, 462), (360, 486)])
    s.node(190, 576, 340, 66, "edge", "evidence state", ["supported, weak or none,", "from what the passages literally contain"], bold=True)
    s.arrow([(360, 552), (360, 576)])
    s.text(24, 672, "Results carry source, path, revision, line range and freshness, so an answer can be traced to a passage.", 12.5, 400, "#475569", "start")
    s.render("moks-rag-retrieval")


def skills():
    s = Svg(720, 560, "MOKS: skill release and run paths",
            "A SKILL.md is reviewed in Git, validated, stored as an immutable version named by its SHA-256 digest, and "
            "published into a generation that API, worker and detection processes follow within about 30 seconds. At run "
            "time, one policy decides eligibility, up to three skills are ranked from findings and question keywords, their "
            "read-only steps run through the ToolExecutor, and declared evidence contracts are checked. Suggested actions "
            "are plans that still need review.")
    s.text(24, 40, "Skills: released like code, run like a checklist", 20, 700, "#0f172a", "start")
    s.text(24, 62, "One generation is the exact set of versions every process runs, and each run records what it used.", 12.5, 400, "#475569", "start")

    s.band(12, 84, 696, 190, "Release path", "Git stays the review step")
    y = 146
    w = 150
    s.node(28, y, w, 104, "client", "SKILL.md", ["image or reviewed", "ConfigMap"])
    s.node(198, y, w, 104, "edge", "validate", ["read-only tools, args,", "allowlisted actions"], bold=True)
    s.node(368, y, w, 104, "store", "version", ["immutable,", "named by SHA-256"])
    s.node(538, y, 154, 104, "ai", "generation", ["followed within ~30 s;", "rollback is a new one"])
    for x in (178, 348, 518):
        s.arrow([(x, y + 52), (x + 20, y + 52)])

    s.band(12, 292, 696, 248, "Run path")
    s.text(120, 314, "one policy answers for selection, steps, detection and suggestions", 12, 400, "#64748b", "start")
    y = 354
    s.node(28, y, w, 104, "edge", "eligible?", ["published, enabled,", "connectors ready"], bold=True)
    s.node(198, y, w, 104, "ai", "select up to 3", ["findings x3,", "keywords x1"])
    s.node(368, y, w, 104, "edge", "run steps", ["through ToolExecutor,", "fair tool budget"])
    s.node(538, y, 154, 104, "ai", "contracts", ["required evidence,", "gaps in the report"])
    for x in (178, 348, 518):
        s.arrow([(x, y + 52), (x + 20, y + 52)])
    s.arrow([(615, 250), (615, 283), (102, 283), (102, y)])
    s.node(198, 476, 494, 46, "client", "suggested action plans", ["allowlisted, prefilled, and still subject to the approval policy"])
    s.arrow([(615, 458), (615, 476)])
    s.render("moks-skills-lifecycle")


if __name__ == "__main__":
    trust()
    ingestion()
    retrieval()
    skills()
