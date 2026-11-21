"""Four loops around an agent, with no LLM and no dependencies (Python 3.10+).

The "model" is a deterministic stand-in: it writes a requirements review that contains only the sections its
instructions, or the grader's feedback, ask for. That is enough to show what each loop adds:

    1. agent loop         call tools until done, with a cap on model turns
    2. verification loop  a grader checks the output against pass/fail criteria and names each gap
    3. event-driven loop  an event (here a ticket change) starts a run of loop 2
    4. learning loop      an analyst reads the saved reviews and proposes an instruction change; the first drafts
                          for the same five requirements are compared before and after

Run:  python3 loops.py
"""
import json
from collections import Counter
from pathlib import Path

REQUIREMENTS = [
    "The system should respond quickly to user requests.",
    "Admins can export reports in several formats.",
    "Passwords must be secure.",
    "The app works offline when possible.",
    "Notifications are sent in a timely manner.",
]
SECTIONS = {"ambiguities": "Ambiguities:", "assumptions": "Assumptions:", "questions": "Clarification questions:"}
ORIGINAL = ["List the facts stated in the requirement.", "List the ambiguities."]
OUT = Path(__file__).with_name("activity.json")


# --- Loop 1: the agent loop --------------------------------------------------------------------------------------
def flaky_api(_requirement: str) -> str:
    raise TimeoutError("glossary service timed out")


def agent_loop(requirement: str, instructions: list[str], feedback: list[str] = (), max_turns: int = 6) -> dict:
    """One run: the model picks an action each turn until it writes a final answer or runs out of turns."""
    wanted = [key for key in SECTIONS if any(key in text.lower() for text in [*instructions, *feedback])]
    use_glossary = any("glossary" in text.lower() for text in instructions)
    for turn in range(1, max_turns + 1):
        if use_glossary:  # a model that keeps choosing the same failing tool call
            try:
                flaky_api(requirement)
            except TimeoutError:
                continue
        draft = [f"Facts: {requirement}"] + [f"{SECTIONS[key]} ..." for key in wanted]
        return {"status": "done", "turns": turn, "output": "\n".join(draft)}
    return {"status": "max_turns_reached", "turns": max_turns, "output": ""}


# --- Loop 2: the verification loop -------------------------------------------------------------------------------
def vague_grader(output: str) -> dict:
    ok = all(heading in output for heading in SECTIONS.values())
    return {"passed": ok, "gaps": [] if ok else ["needs improvement"]}


def rubric_grader(output: str) -> dict:
    """Pass/fail per criterion, and each failed criterion is named."""
    criteria = {key: heading in output for key, heading in SECTIONS.items()}
    gaps = [f"Missing section: {key}" for key, passed in criteria.items() if not passed]
    return {"passed": not gaps, "criteria": criteria, "gaps": gaps}


def verification_loop(requirement: str, instructions: list[str], grader=rubric_grader, max_iterations: int = 3) -> dict:
    feedback, reviews = [], []
    for iteration in range(1, max_iterations + 1):
        run = agent_loop(requirement, instructions, feedback)
        review = grader(run["output"])
        reviews.append(review)
        if review["passed"]:
            return {"status": "satisfied", "iterations": iteration, "reviews": reviews}
        feedback = review["gaps"]
    return {"status": "max_iterations_reached", "iterations": max_iterations, "reviews": reviews}


# --- Loop 3: the event-driven loop -------------------------------------------------------------------------------
def on_ticket_changed(event: dict, instructions: list[str]) -> dict:
    """What a webhook handler does: turn the event into a run of the loop that already exists."""
    return {"ticket": event["ticket"], **verification_loop(event["text"], instructions)}


# --- Loop 4: the learning loop -----------------------------------------------------------------------------------
def first_drafts(instructions: list[str]) -> list[dict]:
    """The grader's review of the FIRST draft for each requirement: 5 requirements x 3 criteria = 15 checks."""
    return [rubric_grader(agent_loop(req, instructions)["output"]) for req in REQUIREMENTS]


def score(reviews: list[dict]) -> dict:
    per_criterion = Counter()
    for review in reviews:
        per_criterion.update({key: int(passed) for key, passed in review["criteria"].items()})
    return {"total": sum(per_criterion.values()), "per_criterion": dict(per_criterion)}


def analyst(saved_reviews: list[dict], min_runs: int = 3) -> list[str]:
    """Read the saved reviews, find gaps that recur across runs, and propose one instruction per recurring gap."""
    recurring = Counter(gap for review in saved_reviews for gap in review["gaps"])
    return [f"Always include a section for {gap.split(': ')[1]}." for gap, n in recurring.items() if n >= min_runs]


def learning_loop() -> dict:
    before_reviews = first_drafts(ORIGINAL)
    before = score(before_reviews)
    proposal = analyst(before_reviews)
    candidate = ORIGINAL + proposal
    after = score(first_drafts(candidate))
    declined = [k for k in SECTIONS if after["per_criterion"][k] < before["per_criterion"][k]]
    adopt = bool(proposal) and after["total"] > before["total"] and not declined
    activity = {
        "decision": "update instructions" if adopt else "keep original instructions",
        "reason": f"{len(proposal)} gap(s) recurred in at least 3 of 5 saved reviews",
        "proposed_instructions": proposal,
        "comparison": {"before": before, "after": after, "criteria_declined": declined},
        "outcome": f"First-draft checks went from {before['total']}/15 to {after['total']}/15",
    }
    OUT.write_text(json.dumps(activity, indent=2) + "\n")
    return activity


if __name__ == "__main__":
    req = REQUIREMENTS[0]
    print("1. agent loop")
    print("  ", {k: v for k, v in agent_loop(req, ORIGINAL).items() if k != "output"})
    print("   failing tool:", {k: v for k, v in agent_loop(req, ORIGINAL + ["Check the glossary."]).items() if k != "output"})

    print("2. verification loop")
    for name, grader in (("vague grader", vague_grader), ("rubric grader", rubric_grader)):
        result = verification_loop(req, ORIGINAL, grader)
        print(f"   {name}: {result['status']} after {result['iterations']} iteration(s);",
              "first feedback:", result["reviews"][0]["gaps"])

    print("3. event-driven loop")
    event = {"ticket": "REQ-42", "text": REQUIREMENTS[2]}
    result = on_ticket_changed(event, ORIGINAL)
    print("  ", {k: result[k] for k in ("ticket", "status", "iterations")})

    print("4. learning loop")
    activity = learning_loop()
    for key in ("decision", "reason", "proposed_instructions", "outcome"):
        print(f"   {key}: {activity[key]}")
    print("   before:", activity["comparison"]["before"]["per_criterion"])
    print("   after: ", activity["comparison"]["after"]["per_criterion"])
    print("   saved:", OUT.name)
