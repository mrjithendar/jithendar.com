---
crew: news
key: write
agent: writer
label: Draft
expected_output: Title, dek, key takeaways and the MDX body.
variables:
  - digest
contract: "Starts with the crew's rules (CREW_RULES: sources only, no copying, no invented facts, a Why it matters section, no Sources section). Then the story block, the writing profile and any feedback. {digest} is the digest instruction in a digest, else empty."
output_editable: true
---

Write the article body in MDX (no H1, no Sources section) following the writing profile. Include a '## Why it matters' section. {digest}
