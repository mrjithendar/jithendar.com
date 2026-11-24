---
crew: editorial
key: research
agent: researcher
label: Research
expected_output: "Compact research notes (about 1,500 words, at most 3,000), as bullets per outline section: facts, exact commands and versions, related site article paths, gaps, and a list of source URLs."
variables: []
contract: Then the brief block and the author's first-hand notes.
output_editable: true
---

Research the article in this brief so the writer can write it without guessing.
1. vector_search and read_article: what this site has already published on the topic (to link to and not repeat).
2. fetch_allowlisted_docs: the official documentation for every tool, command and feature in the outline. Open the specific pages (install, configuration reference, CLI reference, release notes), not only the landing page; a refused or failed fetch is a reason to try the next most specific official page. A long page is cut and ends with the anchors of its later sections: fetch the same URL with the anchor you need (url#anchor) rather than another page.
Report, per outline section, as short bullets: the facts the writer needs with their source URL, the exact commands, flags, defaults and current version numbers as written in the source, and the known limits and common failure modes. Say plainly which outline sections you found no source for. End with the list of every source URL you retrieved.
Keep the notes compact, about 1,500 words in total and never more than 3,000: they are notes for the writer, not a copy of the documentation. Quote a command or config snippet only when the article will use it, and only the lines that matter; summarise everything else in one line with its URL. Stop fetching once each outline section has a source.
