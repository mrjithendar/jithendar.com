# TypeScript advantages over Python and Go article

Status: **draft for author review, not published.** Written 2026-11-04 against `jithendar.com` be1287a. The files quoted were clean in the working tree at that commit.

| Asset | Location |
| --- | --- |
| Article | `content/blog/typescript-advantages-over-python-and-go.mdx` (`status: review`, no `publishedAt`) |
| Runnable examples | `examples/` (this folder): `ts/`, `python/`, `go/`, `go-mistake/`, `go-nil/`, `python-ai-service/`, `cases.json` |
| Example checker | `verify_examples.py` (this folder) |

## SEO and publishing metadata

The content schema has no excerpt, keyword or FAQ field, so those live here, as for earlier drafts.

| Field | Value |
| --- | --- |
| H1 (`title`, 81 chars) | Advantages of TypeScript Over Python and Go: When TypeScript Is the Better Choice |
| SEO title (`seoTitle`, 65) | TypeScript vs Python and Go: When TypeScript Is the Better Choice |
| Meta description (`seoDescription`, 158) | TypeScript's real advantages over Python and Go for web apps, APIs, dashboards and AI products, with runnable examples and a fair guide to when not to use it. |
| `description` (149, used for cards and RSS) | Where TypeScript beats Python and Go: one language for browser and server, shared API types, streaming UIs and AI product glue. And where it doesn't. |
| Slug | `typescript-advantages-over-python-and-go` |
| Excerpt | TypeScript is the only one of the three that runs on both sides of a web app. This guide shows what that buys you (shared API types, compile-time checks, streaming UIs, AI product glue), where Python and Go are still the better tools, and a decision guide for five common projects. Every example was run. |
| Primary keyword | TypeScript vs Python and Go |
| Secondary keywords | advantages of TypeScript; TypeScript for backend; TypeScript for AI applications; full-stack TypeScript; when to use Go; Zod validation |
| Category | `ai-engineering` (**placeholder**, same as the two earlier language comparisons; no web-development category exists) |
| Content type | `tutorial` (blog allows analysis, tutorial, opinion, curated; `analysis` would add it to the Google News sitemap, which doesn't suit an evergreen guide) |
| Length | 2,342 words of prose, excluding code and tables (3,393 including them) |

## FAQs

The site has no FAQ block, so these aren't in the article body. Add them as a final section if you want them on the page.

**Is TypeScript faster than Python or Go?**
Not in general. TypeScript compiles to JavaScript, so its speed is the speed of the JavaScript engine (V8 in Node.js). For I/O-bound web work, all three are usually limited by the database or network, not the language. For CPU-heavy work, Go is generally faster, and Python relies on native libraries such as NumPy.

**If I use TypeScript, do I still need to validate input?**
Yes. Types are erased when the code is compiled, so nothing checks a JSON body at runtime unless you add it. Use a schema library such as Zod for anything that crosses a boundary: requests, webhooks, responses from other services and model output.

**Can I build AI applications with TypeScript?**
Yes, for the product layer: chat interfaces, dashboards, calling hosted model APIs, validating and streaming their output. For training models, data pipelines and scientific computing, Python has the much stronger ecosystem, and a common design pairs a TypeScript app with a Python AI service.

**My frontend is React. Should my backend be TypeScript too?**
Often, yes, if the backend mainly reads and writes data and calls other APIs. One language lets the frontend and backend share types and tooling. Choose Python or Go for the backend when it needs their strengths, and connect them with an OpenAPI or Protocol Buffers contract.

**When should I choose Go instead of TypeScript?**
For command-line tools, infrastructure and Kubernetes tooling, and services that must handle many concurrent connections while using every CPU core. Go builds a single binary with no runtime to install, which TypeScript can't match.

## Internal links

Checked 2026-11-04: each returns HTTP 200 on jithendar.com (an unknown slug returns 404, so these are not soft 404s), and each has a source file in `content/blog/`.

| Link | Topic | Used in article |
| --- | --- | --- |
| `/blog/python-vs-go-vs-typescript` | All three languages | Yes, closing paragraph; `related` |
| `/blog/python-vs-typescript` | Python vs TypeScript | Yes; `related` |
| `/blog/learning-typescript-real-project-jithendar-com` | TypeScript | Yes; `related` |
| `/blog/fastapi-and-fastmcp-ai-projects` | Python AI services | Yes |
| `/blog/python-tutorial-beginners-real-projects` | Python | Suggested, near "Choose Python" |
| `/blog/shell-scripting-vs-python` | Automation | Suggested, near the automation-script scenario |
| `/blog/langchain-vs-langgraph-sre-agent-moks` | AI engineering | Suggested, near the AI assistant scenario |
| `/blog/pytorch-rag-reranking-moks-sre-agent` | AI/ML in Python | Suggested, near "Training models…" |

**No Go article exists on the site.** The only Go coverage is inside `/blog/python-vs-go-vs-typescript`. No Go link is invented.

## Verified project files used (be1287a)

| File | Used for |
| --- | --- |
| `www/package.json`, `node_modules/typescript`, `node_modules/zod` | Next 16.4.3, React 19.3.1, TypeScript 6.0.3, Zod 4.6.7; 62 of 65 direct dependencies pinned exactly (`@tailwindcss/typography`, `eslint`, `fast-xml-parser` use ranges); `typecheck` script |
| `www/tsconfig.json` | `strict`, `noUncheckedIndexedAccess` |
| `www/src/app/api/practice/problems/[slug]/assist/route.ts` lines 9–12 | Quoted: Zod union on request input |
| `www/src/lib/practice/executor-client.ts` lines 6, 8–39, 70 | Described: hand-mirrored Python models, `return data as T` |
| `executor/app/main.py` line 49 | Described: FastAPI with `openapi_url=None` |
| `www/src/lib/practice/ai/providers.ts` lines 49–90 | Described: OpenAI-compatible and Gemini calls via `fetch` |
| `www/src/lib/practice/ai/tutor.ts` lines 55, 181 | Quoted: model output parsed with Zod |
| `www/src/components/MermaidBlock.tsx` | Mermaid is committed (49339f9) and the live Mermaid article serves its markup, so the diagram will render |

## Validation (run 2026-11-04 on macOS arm64)

| Check | Result |
| --- | --- |
| `verify_examples.py` | **Pass, 29 checks.** Same four inputs give identical output in TypeScript (Node 26.13.0 type stripping), Python 3.15.2 (Pydantic 2.14.2, strict) and Go 1.27.3; `tsc` 6.0.3 strict passes on the examples and reports exactly the TS2339 and TS2551 errors shown in the article; mypy 2.4.1 `--strict` passes on the examples, flags the typo and the unchecked `Ok \| Err` union; Python raises `AttributeError` without mypy; `go build` rejects the typo; the unchecked Go version compiles and panics; `gofmt`/`go vet` clean; the TypeScript route and client stream from the FastAPI service (FastAPI 0.162.0, uvicorn 0.54.0) in several chunks and reject an empty body with 400; all 12 article code blocks match their example files or the be1287a sources |
| Front matter | Passes `collectionSchema("blog")` (temporary Vitest file, since deleted) |
| Editor round trip | `fidelity(body)` is lossless |
| Internal links | All 4 in-body links resolve to content files; `tests/links.test.ts` passes |
| Source URLs | All 23 return HTTP 200 |

Run it again from `www/`:

```sh
python3 docs/knowledge-sharing/typescript-advantages/verify_examples.py \
  --python /path/to/venv/bin/python --go /path/to/go/bin/go
```

The venv needs `pydantic mypy fastapi uvicorn`. Use Node 26 (`export PATH=/opt/homebrew/bin:$PATH`; `/usr/local/bin/node` is v20). `/usr/local/go` is an x86_64 build that won't run on this Mac, so use the official darwin-arm64 tarball.

## Things for the author to check

- **TypeScript 7.0 date.** The article says "released in July 2026"; the official post is dated 8 July 2026.
- **Executor client.** `executor-client.ts` trusts the Python service's JSON (`data as T`). The article uses it as a teaching example; whether to add a Zod check there is a separate code decision.
- **Tutor schema mismatch.** In `tutor.ts`, the JSON schema sent to the model says "At most five" points, but `answerShape` allows `.max(8)`. That's harmless (it's more lenient), but the excerpt shows the 8.
- **Excerpts are partial.** The Python and Go blocks in the three-language section omit imports and the response types; the full files are in `examples/`.
- **Python version.** The examples ran on Python 3.15.2, not the 3.13 the executor uses. Nothing in them depends on 3.15.
- **Publishing.** Live posts are in PostgreSQL. After review, paste the approved draft into the editor, as with earlier drafts.
