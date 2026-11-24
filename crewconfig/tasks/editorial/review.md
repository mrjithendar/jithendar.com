---
crew: editorial
key: review
agent: reviewer
label: Technical review
expected_output: "The complete corrected MDX body, then NEEDS_FACT_CHECK: and the list."
variables: []
contract: "Then the author's notes, and: Return the complete corrected MDX body (this is the body that will be published; do not shorten it), then a line `NEEDS_FACT_CHECK:` followed by one line per claim you could not verify and per note for the editor (the writer's list after its body, and any note left in the body), as `- claim | reason` (or `- none`)."
output_editable: false
---

Check every command, flag and version in the draft against the research sources (fetch_allowlisted_docs when needed). Statements that come from the author's first-hand notes are the author's own experience: keep them and do not flag them unless they contradict a source. Correct what is wrong; do not shorten, summarise or restyle the article, and keep every section and code block. Leave no note for the editor in the body (a {/* */} or <!-- --> comment, JSX, a TODO line): the site renders plain Markdown and would publish it as text.
