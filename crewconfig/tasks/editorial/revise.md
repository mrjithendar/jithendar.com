---
crew: editorial
key: revise
agent: writer
label: Revise (Improve)
expected_output: The complete article body in MDX (no front matter, no H1).
variables: []
contract: |-
  Notes for the editor never go in the body: the site renders it as plain Markdown, so a comment ({/* */} or <!-- -->), JSX or a TODO line is published as text. Put what the editor must check or add (an unsourced claim, real command output to capture, a link to confirm) after the body: a line `NEEDS_FACT_CHECK:` followed by one `- claim | reason` line each. Move any such note already in a draft there.
  Then the brief, the author's notes, the current draft, the style guide, the example articles and any feedback.
output_editable: true
---

Revise the current draft (the current_draft block) into the best version of this article, following the style guide. Do not start over.
Keep: its structure and headings unless the outline needs a section it lacks, the author's voice, every first-hand passage, and everything that is correct.
Fix: commands, flags, versions and facts that the research notes contradict; sections that are missing, thin or vague (cover every heading in the brief's outline, why before how, with the output or result to expect and the trade-off an engineer would hit); code that is incomplete, inconsistent or not runnable.
Cut: padding, repetition and generic introductions or recaps.
Facts: use only the research notes, the author's first-hand notes and what the current draft already says correctly; where none has what a section needs, say less rather than invent.
Return the complete revised article body in MDX (no front matter, no H1), not a list of changes.
