"""The crew from "Multi AI Agent Systems with crewAI: Six Ideas From the Course".

Three agents turn raw incident notes into a blameless postmortem: an analyst builds the
timeline, a writer drafts the postmortem (a guardrail rejects a draft with no action items),
and a reviewer removes claims the timeline does not support.

    python postmortem_crew.py [incident-notes.txt]

Without a file it uses the short sample below. CrewAI needs a model: set the API key for the
provider you use, or pass llm= to each Agent.
"""
import sys
from typing import Any, Tuple

from crewai import Agent, Crew, Process, Task, TaskOutput

SAMPLE_NOTES = """\
14:02 deploy of checkout v2.31 started
14:05 alert: checkout 5xx rate at 12 percent (normal is under 0.5 percent)
14:07 on-call paged; pods are restarting with OOMKilled, memory limit 256Mi
14:11 rollback to v2.30 started
14:14 5xx rate back under 0.5 percent
15:30 diff shows v2.31 loads the full price catalogue into memory at startup
"""

analyst = Agent(
    role="Incident Analyst",
    goal="Turn raw incident notes into an accurate timeline and a probable root cause",
    backstory="You are an SRE who only states what the notes support.",
)
writer = Agent(
    role="Postmortem Writer",
    goal="Write a blameless postmortem that an engineer can read in five minutes",
    backstory="You write for busy on-call engineers, in short sentences.",
)
reviewer = Agent(
    role="SRE Reviewer",
    goal="Catch claims in the postmortem that the timeline does not support",
    backstory="You are the sceptical senior engineer in every incident review.",
    allow_delegation=True,
)


def has_action_items(result: TaskOutput) -> Tuple[bool, Any]:
    """Reject a postmortem that has no action items section."""
    if "action items" not in result.raw.lower():
        return (False, "Add an 'Action items' section with at least one item.")
    return (True, result.raw)


build_timeline = Task(
    description="Build a timeline from these incident notes:\n\n{incident_notes}",
    expected_output="Events in time order with evidence, then one probable root cause.",
    agent=analyst,
)
write_postmortem = Task(
    description="Write a blameless postmortem from the timeline.",
    expected_output="Markdown with: Summary, Impact, Timeline, Root cause, Action items.",
    agent=writer,
    context=[build_timeline],
    guardrail=has_action_items,
)
review_postmortem = Task(
    description="Compare the postmortem with the timeline. Fix any unsupported claim.",
    expected_output="The corrected postmortem, then a short list of what you changed.",
    agent=reviewer,
    context=[build_timeline, write_postmortem],
)

crew = Crew(
    agents=[analyst, writer, reviewer],
    tasks=[build_timeline, write_postmortem, review_postmortem],
    process=Process.sequential,
    verbose=True,
)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            notes = f.read()
    else:
        notes = SAMPLE_NOTES
    result = crew.kickoff(inputs={"incident_notes": notes})
    print(result.raw)
