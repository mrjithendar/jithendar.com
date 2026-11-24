---
crew: editorial
key: write
agent: writer
label: Write (new article)
expected_output: The complete article body in MDX (no front matter, no H1).
variables: []
contract: |-
  Notes for the editor never go in the body: the site renders it as plain Markdown, so a comment ({/* */} or <!-- -->), JSX or a TODO line is published as text. Put what the editor must check or add (an unsourced claim, real command output to capture, a link to confirm) after the body: a line `NEEDS_FACT_CHECK:` followed by one `- claim | reason` line each. Move any such note already in a draft there.
  Then the brief, the author's notes, the style guide, the example articles and any feedback.
output_editable: true
---

Write the full article as MDX following the style guide.
Facts: use only the research notes and the author's first-hand notes. The author's notes are their own experience (what they built, ran, measured or decided): write those parts in the first person and keep their commands, versions and numbers exactly. Where neither has what a section needs, say less rather than invent.
Depth: cover every heading in the brief's outline. Each section explains why before how, shows the command or configuration with the output or result to expect, and names the trade-off, limit or failure mode an engineer would hit. Prefer one worked example carried through the article over several disconnected snippets. Use a table for a comparison, a list for steps, and a mermaid diagram where the brief asks for one. Aim for the brief's reading time (about 220 words a minute); without one, write 1,500 to 2,500 words of prose.
Opening and ending: open with the concrete problem or result in two or three sentences, with no generic introduction; end with what to check or do next, not a recap.
Code: every block declares its language and is complete enough to copy and run; no placeholders that hide the hard part.
The example articles show the voice, depth and structure to match. Take nothing factual from them and do not reuse their sentences.
