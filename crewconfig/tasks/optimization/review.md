---
crew: optimization
key: review
agent: reviewer
label: Technical review
expected_output: The final JSON object.
variables: []
contract: Then the change-set JSON contract; the answer is parsed as OptimizationResult.
output_editable: false
---

Check every command, version or technical claim the editor changed against official documentation (fetch_allowlisted_docs). Remove or fix any change you can prove wrong; list anything you cannot verify in needs_fact_check. Return the final JSON object.
