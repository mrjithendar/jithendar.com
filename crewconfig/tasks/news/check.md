---
crew: news
key: check
agent: fact_checker
label: Fact check
expected_output: Corrected MDX body, removed claims, flagged claims.
variables: []
contract: "Starts with the crew's rules (CREW_RULES: sources only, no copying, no invented facts, a Why it matters section, no Sources section)."
output_editable: true
---

Fact-check the draft against the fact sheet. Return the corrected body, then a list of removed claims and flagged claims with reasons.
