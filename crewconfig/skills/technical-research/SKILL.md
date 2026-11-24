---
name: technical-research
description: "How to research a technical article: which sources to trust, what to record, and how to report gaps."
agents:
  - editorial.researcher
tags: []
enabled: true
builtin: true
---

Trust sources in this order: the project's official documentation for the current stable version, then its release notes and changelog, then its source repository (README, docs folder, maintainers' answers in issues). Blog posts and Q&A answers are leads to check, never the source.
- Record the version each page documents. Where the docs have a version selector, use the current stable version and say which one.
- Copy commands, flags, defaults, API versions and file paths exactly, each with the URL it came from.
- Look for what changed recently: deprecations, renamed flags, removed APIs, new defaults. Readers get these wrong most often.
- When two sources disagree, report both with their URLs and say which is newer.
- For each outline section, note the failure an engineer is most likely to hit and what the docs say about it.
- Say plainly when a section has no source. A reported gap is better than a guess.
