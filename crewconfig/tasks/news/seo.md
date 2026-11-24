---
crew: news
key: seo
agent: seo_editor
label: Final draft (JSON)
expected_output: One JSON object matching NewsDraft.
variables:
  - digest_items
contract: "Starts with the crew's rules (CREW_RULES: sources only, no copying, no invented facts, a Why it matters section, no Sources section). Then the story block and any feedback; the answer is parsed as NewsDraft. {digest_items} is ', digest_items' in a digest, else empty."
output_editable: false
---

Produce the final draft as JSON matching NewsDraft: title (≤ 60 chars), dek, meta_description (120–155), slug_suggestion, body_mdx (the fact-checked body), key_takeaways, why_it_matters, headings, sources (only URLs from the fact sheet, with publisher), fact_check_report, categories and tags (from the suggestions), internal_links (≤ 3, only paths from vector_search_site), schema_jsonld (@type NewsArticle, headline, description), reading_time_minutes, confidence, warnings{digest_items}.
