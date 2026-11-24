---
name: explainer-article
description: "Structure for concept explainers and reference pages: the problem first, the mechanism, one worked example, and the limits."
agents:
  - editorial.writer
tags:
  - intent:explainer
  - intent:reference
enabled: true
builtin: true
---

The reader wants to understand something well enough to make a decision or debug it.
- Start with the problem the concept solves, in one or two sentences, before any definition.
- Explain the mechanism: what happens, in order, between the parts involved. A mermaid diagram helps when three or more parts interact.
- Carry one concrete example (a real resource, request or configuration) through the whole article instead of switching examples per section.
- Include the limits: the trade-offs, and the cases where a simpler option is better.
- If there is a common misconception about the topic, correct it and say where it comes from.
- Reference pages: tables for options, defaults and versions, every row from a source.
