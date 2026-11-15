# Build and Train an LLM with JAX article

Status: **draft for author review, not published.** Written 2026-11-15.

| Asset | Location |
| --- | --- |
| Article | `content/blog/build-train-llm-jax-deeplearning-ai-course.mdx` |
| Runnable end-to-end example | `examples/mini_llm.py` (this folder) |

## Verification

- Course facts (Google partnership, instructor Chris Achard, 49 min, intermediate, 7 lessons + 4 code examples + quiz,
  ~20M-parameter MiniGPT, Flax NNX / Grain / Optax / Orbax) come only from the public course page, checked 2026-11-15.
- Every Python block in the article was extracted and run on an arm64 Mac CPU with JAX 0.10.2, Optax 0.2.9,
  orbax-checkpoint 0.12.10 (sharding block with `XLA_FLAGS=--xla_force_host_platform_device_count=8`). Outputs quoted
  in the article (shapes, token IDs, loss 2.665 -> 0.032, benchmark ~4.7 / ~22 / ~3.5 ms) are from those runs.
- Only the correct option of each quiz question was available; option numbers come from the author's notes.
- Question 4: the closest option swapped the definitions of token and positional embeddings; the article flags this and
  gives the correct distinction instead of the quiz wording.

Run the example:

```bash
python -m venv .venv && .venv/bin/pip install jax optax orbax-checkpoint
.venv/bin/python examples/mini_llm.py
```

## SEO metadata

| Field | Value |
| --- | --- |
| H1 | Build and Train an LLM with JAX: What 7 Course Quiz Questions Taught Me |
| SEO title (54) | Build and Train an LLM with JAX: 7 Questions Explained |
| Meta description (159) | Learning notes on DeepLearning.AI's Build and Train an LLM with JAX course: seven quiz questions on vmap, sharding, attention, JIT and tokenization, with code. |
| OG title | Build and Train an LLM with JAX: 7 Questions, Explained With Code |
| Slug | `build-train-llm-jax-deeplearning-ai-course` |
| Primary keyword | Build and Train an LLM with JAX |
| Secondary keywords | JAX tutorial; JAX XLA; JAX vmap; Transformer attention; LLM training; JAX JIT compilation; LLM tokenization |
| Category | `ai-engineering` |
| Length | About 4,150 words of prose, 5,750 with code (the brief asked for 2,000–2,500; the required per-question format makes it longer) |

`publishedAt` is deliberately unset. FAQ is in the article body under "Frequently asked questions".

## Cover image

Prompt: "Clean technical illustration, dark navy background. On the left, a short line of text turns into a row of
glowing integer tokens, then into stacked embedding vectors. In the centre, a transformer block drawn as layered
rectangles with several coloured attention arcs between tokens. On the right, a grid of eight small chip icons
(accelerators) linked by thin lines, each holding a slice of a matrix. Flat vector style, teal and amber accents,
no text, no logos, 16:9, 1600x900."

Alt text: "Diagram-style illustration of text becoming tokens and embeddings, passing through a transformer attention
block, and being split across eight accelerator chips."

Save as `public/images/build-train-llm-jax/cover.webp` (1600x900) and add `featuredImage` to the frontmatter.

## Internal links (verified live 2026-11-15)

/projects/moks, /blog/four-ai-systems-one-cluster, /blog/pytorch-rag-reranking-moks-sre-agent (in the body);
/blog/python-tutorial-beginners-real-projects (related). Candidates for later: /blog/moks-rag-and-skills-design,
/blog/deploy-roboshop-ai-amazon-eks.
