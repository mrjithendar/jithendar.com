---
name: troubleshooting-article
description: "Structure for error-and-fix articles: the exact symptom, how to diagnose, causes ranked by likelihood, fix and verify."
agents:
  - editorial.writer
tags:
  - intent:troubleshooting
enabled: true
builtin: true
---

The reader has a broken system and an error message, and skims for their exact symptom.
- Put the exact error message or symptom in the opening and, where it fits, in a heading, as the reader would paste it into a search engine.
- Diagnose first: the commands that show which cause applies, and what each output means.
- List causes from most to least likely. For each: how to confirm it, the fix, and how to verify the fix worked.
- Keep each fix self-contained, so a reader who jumps straight to it does not need the previous section.
- Say which fixes are safe in production and which restart, delete or reset something.
- End with prevention: the setting, check or alert that would have caught it.
