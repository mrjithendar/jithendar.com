# Multi AI Agent Systems with crewAI article

Status: **draft for author review, not published.** Written 2026-11-16.

| Asset | Location |
| --- | --- |
| Article | `content/blog/multi-ai-agent-systems-with-crewai-course-notes.mdx` |
| Example crew (the article's three Python blocks in one file) | `examples/postmortem_crew.py` (this folder) |

## Verification

- Course facts (instructor João Moura, founder and CEO of CrewAI; beginner; 3 h 6 min; 18 video lessons, 7 code
  examples, graded quiz; the six components; the six business processes) come only from the public course page, checked
  2026-11-16. Completion on 2026-11-16 and "graded quiz passed" come from the author's accomplishment page, checked the
  same day.
- The six ideas follow the author's notes of the seven quiz questions (questions 2 and 3 are the same question). The
  article does not quote the questions or the answer options and does not say which option is correct. The six
  "Check yourself" questions were written for the article.
- CrewAI facts were read from docs.crewai.com on 2026-11-16 (versions 1.15.x): `role`, `goal` and `backstory` required;
  `allow_delegation` default `False` (an older docs page lists `True`); `max_iter` default 20; `description` and
  `expected_output` required on a task; `context` and `async_execution`; function and plain-text guardrails,
  `guardrail_max_retries` default 3; sequential and hierarchical processes (`manager_llm` or `manager_agent`); the
  single `Memory` class, facts stored after each task and recalled before each task, default weights 0.5 / 0.3 / 0.2,
  default embedder `text-embedding-3-large`, LanceDB under `./.crewai/memory`, `CREWAI_STORAGE_DIR`; `crew.jsonc` and
  `agents/` for new projects, `--classic` for YAML; Flows; telemetry on by default and `CREWAI_DISABLE_TELEMETRY`.
- Statements about this site and MOKS come from two existing articles: `how-i-built-jithendar-com` (`seo-agent` runs
  every AI workflow as a CrewAI Flow; Flows orchestrate, crews do the reasoning, plain Python does the data work) and
  `four-ai-systems-one-cluster` (three CrewAI agents; telemetry turned off; memory, knowledge and planning off).
- **Not run: the Python.** CrewAI was not installed in the drafting session and there was no model key. Every block
  parses (`ast.parse`), and `examples/postmortem_crew.py` is generated from the article's blocks. Run it once before
  publishing.
- **Not rendered: the Mermaid diagram.** Check it in preview.
- **Not the author's words yet:** the reason given in the intro for taking the course, and the opinions under
  "Is the course worth your time?".
- The pod-restart remark about `./.crewai/memory` is general Kubernetes behaviour (a container's filesystem is not
  kept across restarts), not a statement from the CrewAI docs.

Run the example (CrewAI needs Python 3.10 to 3.13):

```bash
python -m venv .venv && .venv/bin/pip install crewai
export CREWAI_DISABLE_TELEMETRY=true
# set the API key for the model you use, or pass llm= to each Agent
.venv/bin/python examples/postmortem_crew.py                      # the built-in sample notes
.venv/bin/python examples/postmortem_crew.py incident-notes.txt   # your own notes
```

## SEO metadata

| Field | Value |
| --- | --- |
| H1 | Multi AI Agent Systems with crewAI: Six Ideas From the Course |
| SEO title (48) | Multi AI Agent Systems with crewAI: Course Notes |
| Meta description (159) | Six ideas from DeepLearning.AI's crewAI course: roles, focus, tools, cooperation, guardrails and memory, with Python code and notes on the current CrewAI docs. |
| OG title | Multi AI Agent Systems with crewAI: Six Ideas, With Code |
| Slug | `multi-ai-agent-systems-with-crewai-course-notes` |
| Primary keyword | Multi AI Agent Systems with crewAI |
| Secondary keywords | CrewAI tutorial; CrewAI agents and tasks; CrewAI memory; CrewAI guardrails; multi-agent systems; CrewAI allow_delegation |
| Category | `ai-agents` |
| Length | About 2,100 words outside code blocks (10 minutes by the site's `readingTimeMinutes`, 220 words per minute), plus 56 lines of Python and one diagram |

`publishedAt` is deliberately unset.

## Cover image

Prompt: "Clean technical illustration, dark navy background. Three simple robot figures stand in a row, each holding
a different object: a magnifying glass over a timeline, a pen over a document, and a checklist with a tick. Thin
arrows pass a sheet of paper from the first to the second to the third, and a small gate with a tick sits between
the second and third. Flat vector style, teal and amber accents, no text, no logos, 16:9, 1600x900."

Alt text: "Illustration of three AI agents working in sequence: one builds a timeline, one writes a document, and
one reviews it, with a check gate between the writer and the reviewer."

Save as `public/images/crewai-multi-agent-course/cover.webp` (1600x900) and add `featuredImage` to the frontmatter.

## Internal links

In the body: /blog/how-i-built-jithendar-com, /projects/moks, /blog/four-ai-systems-one-cluster. In `related`: those
three plus /blog/build-train-llm-jax-deeplearning-ai-course. All four exist as content files. They were not checked
on the live site (it was not reachable from the drafting session), so confirm they are published before this article
is.
