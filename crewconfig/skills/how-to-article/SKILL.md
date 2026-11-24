---
name: how-to-article
description: "Structure for step-by-step guides: prerequisites, one action per step with the expected output, verification and clean-up."
agents:
  - editorial.writer
tags:
  - intent:how-to
enabled: true
builtin: true
---

The reader wants to finish a task. Get them there with the fewest surprises.
- Open with what they will have at the end and roughly how long it takes.
- Prerequisites: the tools and the versions the steps were checked against, the access needed, and anything that costs money.
- Steps: one action per step. Each gives the command or configuration, then the output or state to expect, so the reader knows it worked before moving on.
- Name the values the reader must change (namespace, domain, region) the first time they appear, and keep the same example values throughout.
- After the steps, a verification section that proves the whole setup works end to end.
- Close with the most common failure for this setup and its fix, then how to undo or clean up.
