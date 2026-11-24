---
name: search-cluster-coverage
description: "When the brief comes from an ML query cluster: answer each question the searches show, in the readers' own words."
agents:
  - editorial.writer
  - editorial.seo_editor
tags:
  - source:ml
  - queries:many
enabled: true
builtin: true
---

The brief's supportingQueries are real Search Console searches that the query-clustering model grouped as one topic. They show what readers want to know.
- Answer the first (most common) query in the opening two or three sentences.
- Group the other queries by the question behind them. Each distinct question gets a section, or a clearly marked answer inside one.
- Use the readers' wording in headings where it reads naturally; never repeat a query word for word just to include it.
- A query that needs a different article (another intent or another product) is out of scope: leave it out rather than bolting on a section.
- SEO editor: the title targets the cluster's main query, and the meta description promises only answers the article gives.
