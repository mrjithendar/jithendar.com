---
name: news-sourcing
description: "Sourcing news: primary sources first, exact versions and dates, supporting snippets, and nothing unconfirmed."
agents:
  - news.researcher
  - news.fact_checker
tags: []
enabled: true
builtin: true
---

- Primary sources first: the vendor's release notes, security advisory, changelog, official blog or documentation. Press coverage points to the primary source; it does not replace it.
- Dates: tell apart when something was announced, released and takes effect, each with its source.
- Copy versions, CVE ids, product names and numbers exactly as the primary source writes them.
- Every fact-sheet claim carries a short verbatim snippet from a page fetched in this run that supports it.
- Rumours, leaks, roadmap hints and unnamed sources stay out of the fact sheet.
- Fact-checker: a claim whose snippet does not say what the draft says is removed, even when it is probably true.
