# Loop Engineering with LangChain Deep Agents article

Status: **draft for author review, not published.** Written 2026-11-21.

| Asset | Location |
| --- | --- |
| Article | `content/blog/loop-engineering-langchain-deep-agents-course-notes.mdx` |
| Runnable example (all four loops, no LLM, no dependencies) | `examples/loops.py` (this folder) |

## Verification

- Course facts (LangChain partnership, instructors, intermediate, 1h16m, 8 video lessons, 4 code examples, lesson
  titles, the requirements-review example, both names of the fourth loop) come from the public course page, read
  2026-11-21.
- The nesting of the loops and the cost of verification come from LangChain's "The Art of Loop Engineering".
- `RubricMiddleware` (import, `model`, `max_iterations`, the `rubric` state key, verdicts, `_rubric_status`,
  `deepagents>=0.6.5`, beta) comes from the Deep Agents rubric documentation, read 2026-11-21. The Deep Agents
  snippet in the article is adapted from that page and was **not run**: `deepagents` could not be installed where
  the article was written.
- Every other code block is an excerpt of `examples/loops.py`, and every output block is from running it with
  Python 3.13.18. The model in it is a deterministic stand-in, so 5/15 to 15/15 shows the mechanism, not a result.
- Quiz: the seven scenarios are paraphrased from the author's quiz screen; the options are not reproduced.
- Lab: the scoring rules and the 0/100 first submission ("no saved capstone activity") are from the author's lab
  screen on 2026-11-21. What happened after that submission is not in the article.
- Not verified: the name of the setting the course uses for the cap on model turns.

Run the example:

```bash
python3 examples/loops.py        # writes examples/activity.json
```

## SEO metadata

| Field | Value |
| --- | --- |
| H1 | Loop Engineering with LangChain Deep Agents: Four Loops, a Quiz and a Failed Lab |
| SEO title (57) | Loop Engineering with LangChain Deep Agents: Course Notes |
| Slug | `loop-engineering-langchain-deep-agents-course-notes` |
| Primary keyword | Loop Engineering with LangChain Deep Agents |
| Secondary keywords | loop engineering; verification loop; RubricMiddleware; Deep Agents; LLM-as-a-judge; event-driven agents |
| Category | `ai-agents` |

`publishedAt` is deliberately unset. FAQ is in the article body under "Frequently asked questions".

## Cover image

Prompt: "Clean technical illustration, dark navy background. Four concentric rounded loops drawn as glowing tracks,
the innermost around a small chip icon, each outer loop a different accent colour (teal, amber, violet, white) with
a small arrowhead showing direction. A checkmark sits on the second loop, a lightning bolt on the third and a small
upward-stepping line on the fourth. Flat vector style, no text, no logos, 16:9, 1600x900."

Alt text: "Four nested loops around a model chip, representing the agent, verification, event-driven and learning
loops."

Save as `public/images/loop-engineering-deep-agents/cover.webp` (1600x900) and add `featuredImage` to the frontmatter.
