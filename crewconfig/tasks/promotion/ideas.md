---
crew: promotion
key: ideas
agent: strategist
label: Article ideas
expected_output: 'One JSON object {"ideas": [...]}.'
variables:
  - limit
contract: Then the ideas JSON contract and the signal blocks (Search Console topics and queries, Reddit threads, channels, covered, planned).
output_editable: true
---

Propose up to {limit} ideas for new articles on this site (DevOps, cloud, Kubernetes, platform and AI engineering), chosen because they would be easy to promote: people are already searching for or discussing the subject.
Rules:
- Every idea needs at least one item of evidence copied EXACTLY from the signals: a Search Console query (type gsc_query, value = the query text), a Search Console topic (type gsc_topic, value = the topic) or a Reddit thread (type reddit, value = its url). Prefer ideas backed by both search demand and a discussion.
- Do not propose anything already in covered (published articles) or planned (the calendar and earlier ideas), or a near-duplicate of one.
- title: at most 70 characters, specific, no clickbait. angle: one or two sentences on what would make it worth reading and sharing (first-hand, concrete, a real problem).
- outline: 4 to 7 section headings. target_query: one query from search_console_queries, or null.
- channels: ids from the channels block where the finished article would fit.
- If the signals support fewer ideas, return fewer. Never invent a query, a thread or a number.
