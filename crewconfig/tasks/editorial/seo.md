---
crew: editorial
key: seo
agent: seo_editor
label: SEO metadata
expected_output: One JSON object with title, slug_suggestion, meta_description, outline, sources, fact_check_flags and internal_links (no body).
variables: []
contract: Then the brief and any feedback. The answer is parsed as SeoMetadata (title, slug, meta description, outline, sources, flags, internal links).
output_editable: true
---

Produce the article's metadata as JSON matching the schema: title (≤ 60 chars), slug_suggestion, meta_description (120–155 chars), outline (the H2s of the reviewed body), sources (only URLs from the research), fact_check_flags (from the review), internal_links (≤ 3, only existing site paths from vector_search). Use gsc_queries_for_topic for the target queries. Do NOT include the article body: it is taken from the technical review unchanged.
