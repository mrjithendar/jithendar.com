#!/usr/bin/env python3
"""Figures for content/blog/loop-engineering-langchain-deep-agents-course-notes.mdx.

    python3 docs/knowledge-sharing/loop-engineering-deep-agents/diagrams/build_diagrams.py   # writes the .drawio files
    bash docs/knowledge-sharing/loop-engineering-deep-agents/diagrams/export.sh              # draw.io CLI → public/images/
    python3 docs/knowledge-sharing/loop-engineering-deep-agents/diagrams/render_svg.py       # fallback without draw.io

After editing a .drawio file by hand, run only export.sh, or this script overwrites the edits.

Sources (21 November 2026): the public course page, LangChain's "The Art of Loop Engineering", the Deep Agents rubric
documentation, and ../examples/loops.py (the numbers in verification-loop and learning-loop are from running it).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio_model import Diagram  # noqa: E402

HERE = Path(__file__).resolve().parent
NOTE = 11
LABELS = {"ai": "Model or agent", "service": "Code you write", "security": "Grader or decision", "data": "Saved results",
          "external": "Where work already happens", "network": "Network", "ops": "Harness change",
          "client": "Input", "optional": "Does not pass"}


def four_loops():
    d = Diagram("loop-engineering-four-loops", 960, 520, "Four loops around an agent: each loop wraps the ones inside it")
    d.zone("z4", "4 · Learning loop: an analyst reads saved runs and proposes changes to the harness", 20, 50, 920, 440, "ai")
    d.zone("z3", "3 · Event-driven loop: a chat mention, a ticket change or a schedule starts a run", 40, 85, 880, 300)
    d.zone("z2", "2 · Verification loop: a grader checks the output against a rubric and sends failures back",
           60, 190, 840, 185, "cluster", corner="right")
    d.zone("z1", "1 · Agent loop (cap on model turns)", 80, 225, 470, 130, corner="right")

    d.node("event", "external", 100, 115, 190, 60, "Event", "mention, ticket, schedule")
    d.text("tunnel", 330, 128, 560, 36, "An agent on a laptop has no address an event source can call. "
           "A tunnel or a deployed endpoint gives it one.", size=NOTE)
    d.node("model", "ai", 100, 260, 190, 80, "Model", "picks the next tool call,", "reads the result")
    d.node("tools", "service", 340, 260, 190, 80, "Tools", "files, APIs, search:", "run and return results")
    d.node("grader", "security", 620, 260, 260, 80, "Grader", "pass or fail per criterion,", "names each gap")
    d.edge("event", "model", "starts a run", kind="async", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("model", "tools", exit=(1, 0.5), entry=(0, 0.5), both=True)
    d.edge("tools", "grader", "output", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("grader", "model", "gaps go back as feedback", exit=(0.5, 1), entry=(0.5, 1), via=((750, 364), (195, 364)))

    d.node("traces", "data", 100, 400, 190, 75, "Saved runs", "outputs and the", "grader's reviews")
    d.node("analyst", "ai", 340, 400, 190, 75, "Analyst", "finds gaps that recur", "across many runs")
    d.node("change", "ops", 710, 400, 210, 75, "Harness change", "instructions, tools,", "grader rubric")
    d.edge("traces", "analyst", kind="batch", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("analyst", "change", "proposes", kind="batch", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("change", "grader", "next runs", kind="control", exit=(0.5, 0), entry=(0.75, 1))
    d.legend(504, labels=LABELS)
    return d


def verification_loop():
    d = Diagram("verification-loop", 960, 350, "Verification loop: the grader's feedback decides whether a retry helps")
    d.node("req", "client", 20, 70, 170, 90, "Request + rubric", "a task and a checklist", "of pass/fail criteria")
    d.node("agent", "ai", 230, 70, 170, 90, "Agent run", "writes a draft", "(agent loop inside)")
    d.node("grader", "security", 470, 60, 190, 110, "Grader", "checks each criterion;", "can run tools, such as", "the test suite")
    d.node("ok", "service", 700, 55, 240, 55, "satisfied", "every criterion passes")
    d.node("cap", "optional", 700, 125, 240, 55, "max_iterations_reached", "still failing at the cap")
    d.edge("req", "agent", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("agent", "grader", "draft", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("grader", "ok", exit=(1, 0.2045), entry=(0, 0.5))
    d.edge("grader", "cap", exit=(1, 0.8409), entry=(0, 0.5))
    d.edge("grader", "agent", "needs_revision: the named gaps", exit=(0.5, 1), entry=(0.5, 1), via=((565, 205), (315, 205)))

    d.text("same", 20, 232, 200, 60, "Same standard, different feedback (from the script in the article):", size=NOTE)
    d.node("vague", "optional", 230, 230, 330, 60, "\"needs improvement\"", "3 attempts, never passes")
    d.node("named", "service", 600, 230, 340, 60, "\"Missing section: assumptions\"", "passes on the second attempt")
    d.legend(310, labels=LABELS)
    return d


def event_driven_loop():
    d = Diagram("event-driven-loop", 960, 350, "Event-driven loop: an event starts the loop you already have")
    d.node("tracker", "external", 20, 60, 180, 90, "Project tracker", "a ticket changes,", "it sends a webhook")
    d.node("chat", "external", 20, 170, 180, 90, "Team chat", "someone mentions", "the bot")
    d.node("tunnel", "network", 270, 115, 190, 90, "Tunnel or endpoint", "a public address for", "an agent on a laptop")
    d.node("handler", "service", 530, 115, 170, 90, "Event handler", "turns the event", "into a run")
    d.node("loop", "ai", 770, 115, 170, 90, "Verification loop", "agent + grader,", "not rebuilt")
    d.edge("tracker", "tunnel", kind="async", exit=(1, 0.5), entry=(0, 0.25))
    d.edge("chat", "tunnel", kind="async", exit=(1, 0.5), entry=(0, 0.75))
    d.edge("tunnel", "handler", kind="async", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("handler", "loop", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("loop", "chat", "the result goes back to the thread or the ticket", exit=(0.5, 1), entry=(0.5, 1),
           via=((855, 285), (110, 285)))
    d.legend(310, labels=LABELS)
    return d


def learning_loop():
    d = Diagram("learning-loop", 960, 400, "Learning loop: change the instructions only when first drafts get better")
    d.node("reviews", "data", 20, 60, 180, 90, "Saved reviews", "the grader's results", "from earlier runs")
    d.node("analyst", "ai", 250, 60, 180, 90, "Analyst", "finds gaps that recur", "across runs")
    d.node("proposal", "ops", 480, 60, 190, 90, "Proposed instructions", "one change per", "recurring gap")
    d.node("before", "service", 250, 200, 180, 90, "First drafts: before", "the same 5 requirements,", "original instructions", "script: 5/15 checks")
    d.node("after", "service", 480, 200, 190, 90, "First drafts: after", "the same 5 requirements,", "proposed instructions", "script: 15/15 checks")
    d.node("decision", "security", 740, 130, 200, 100, "Decision record", "update or keep, the reason,", "the comparison, the outcome")
    d.edge("reviews", "analyst", kind="batch", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("analyst", "proposal", kind="batch", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("proposal", "after", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("proposal", "decision", kind="control", exit=(1, 0.5), entry=(0, 0.25))
    d.edge("after", "decision", kind="control", exit=(1, 0.5), entry=(0, 0.75))
    d.edge("before", "decision", "compared per criterion", kind="control", exit=(0.5, 1),
           entry=(0.5, 1), via=((340, 320), (840, 320)))
    d.text("rule", 20, 336, 920, 34, "The script adopts a proposal only if the total goes up and no criterion gets worse. "
           "The verification loop still runs; the learning loop makes its first attempt pass more often.", size=NOTE)
    d.legend(380, labels=LABELS)
    return d


if __name__ == "__main__":
    for figure in (four_loops, verification_loop, event_driven_loop, learning_loop):
        d = figure()
        (HERE / f"{d.name}.drawio").write_text(d.xml() + "\n")
        print(f"{d.name}.drawio  {d.w}x{d.h}")
