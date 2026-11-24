---
name: news-analysis
description: Turning a news story into practical analysis for engineers who run production systems.
agents:
  - news.analyst
  - news.writer
tags: []
enabled: true
builtin: true
---

- Say what changed in one or two sentences, then spend the article on what it means in practice.
- Who is affected: be specific about versions, platforms, configurations or plans, and say who is not affected.
- What to do: concrete actions with a timeframe (now, at the next upgrade, nothing needed), and how to check whether you are affected.
- Context: how this compares with the previous version or the alternatives, only from sources.
- No speculation about motives, the future or market impact.
