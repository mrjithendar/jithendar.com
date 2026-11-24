---
crew: report
key: write
agent: analyst
label: Write the briefing
expected_output: The briefing text only.
variables:
  - kind
contract: Then the facts block (every figure the briefing may use) and the context block (data_complete, next actions, sources). Afterwards every number in the text must equal a fact, or the report fails.
output_editable: true
---

Write the {kind} SEO briefing in 120–250 words of plain prose (no headings, no tables): what changed, the likely reasons the facts support, and the 2–3 next actions from the next-actions list. Use only figures from the facts block, copied exactly; never compute a new number, percentage or difference. If data is incomplete (data_complete=false), say so first.
