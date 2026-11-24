---
crew: news
key: research
agent: researcher
label: Fact sheet
expected_output: "One JSON object: {claims: [{id, claim, source_url, snippet, kind}], primary_sources: [url], open_questions: []}."
variables: []
contract: "Starts with the crew's rules (CREW_RULES: sources only, no copying, no invented facts, a Why it matters section, no Sources section). Then the story and sources blocks; the answer is parsed as FactSheet."
output_editable: false
---

Build the fact sheet for this story. Read the items (read_news_item) and fetch primary sources (fetch_allowlisted) where they exist. Return JSON matching FactSheet.
