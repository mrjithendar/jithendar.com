# Python tutorial through real projects

Status: **draft for author review, not published.** Written 2026-11-03 against `moks` ef6908a and `roboshop-ai` c81e85a. Nothing in either repository was changed, and no application code in this site was changed.

| Asset | Location |
| --- | --- |
| Article | `content/blog/python-tutorial-beginners-real-projects.mdx` (`status: review`, no `publishedAt`) |
| Checker | `docs/knowledge-sharing/python-tutorial/verify_article.py` |

Live posts are in Postgres, and the bundled import refuses existing slugs, so once approved the article is pasted into the editor, as with the earlier drafts.

## SEO metadata

The content schema has no keyword or excerpt field, so those live here and in the article's `<Todo>` note.

| Field | Value |
| --- | --- |
| H1 (title, 71) | Learning Python Through Real Projects: From Basics to APIs and AI Tools |
| SEO title (59) | Python Tutorial for Beginners: Learn With Real Project Code |
| Meta description (150) | Learn Python from the basics to APIs and AI tools, with runnable Python examples and real code from MOKS, a FastAPI service. Python for DevOps and AI. |
| Slug | `python-tutorial-beginners-real-projects` |
| Excerpt (166) | Learn Python from the first print() to FastAPI routes, HTTP clients, async code and tests, using small runnable examples and real code from MOKS, a Python SRE portal. |
| Primary keyword | Python tutorial for beginners |
| Secondary keywords | Python examples; Python for DevOps and AI |
| Category | `devops-sre` (placeholder: there is no Python or programming category) |
| Tags | Python, Python Tutorial, FastAPI, Pydantic, HTTPX, pytest, asyncio |
| Length | About 10,200 words of prose, plus code |

Internal links, each returning 200 on 2026-11-03: `/projects/moks`, `/projects/roboshop-ai` (via `related`), `/blog/roboshop-ai-mcp-server`, `/blog/fastapi-and-fastmcp-ai-projects`, `/blog/langchain-vs-langgraph-sre-agent-moks`, `/blog/moks-rag-and-skills-design`. `/python-practice` is named in plain text, not linked: see "Gaps" below.

## Project files used as examples

MOKS at ef6908a (`backend/` unless noted):

| File | Used for |
| --- | --- |
| `pyproject.toml`, `requirements.txt`, `../Dockerfile`, `../.github/workflows/ci.yml` | Python version (3.12 image and CI, `>=3.11`), pip and venv tooling, `[project.scripts]` |
| `moks/config.py` | Typed settings, set comprehension, Pydantic settings, validator, `repr=False` for secrets |
| `moks/rag/chunking.py` | Sets, `kind_of` conditions, `ChunkPiece` dataclass, `chunk()` retrieval preparation |
| `moks/orchestrator/intent.py` | `WORKFLOW` dictionary |
| `moks/api/investigations.py` | `window_from_question`, `CreateIn`, the `POST /investigations` route and end-to-end trace |
| `moks/connectors/base.py` | `resolve_credential`, `ConnectorError`, `HttpLimits`, `BoundedHttp` status classification and idempotent retries |
| `moks/main.py` | `/readyz` broad except, app factory, middleware |
| `moks/auth/deps.py`, `moks/db.py`, `moks/auth/routes.py` | `get_auth` and `get_db` dependencies, `MeOut` response model |
| `moks/llm/providers.py` | `_post` model client, `_content_text`, Bedrock via `asyncio.to_thread` (simplified) |
| `moks/orchestrator/worker.py` | `claim()` with `FOR UPDATE SKIP LOCKED` (described, not quoted) |
| `moks/cli.py` | `if __name__ == "__main__":`, `moks serve` runs Uvicorn |
| `moks/observability.py` | JSON logging (described) |
| `tests/test_bounds_connectors.py`, `tests/conftest.py` | Mock transport test, PostgreSQL test setup |

RoboShop AI at c81e85a: `services/mcp-server/server.py` (FastMCP tool registration), and each service's `requirements.txt` and `Dockerfile` for the "which projects use Python" table.

## Validation

All runs were local on 2026-11-03. Nothing called a paid API, a cloud service or a cluster.

| Command (working directory) | Result |
| --- | --- |
| `python docs/knowledge-sharing/python-tutorial/verify_article.py ../..` (`www/`), with a Python 3.11.9 venv holding MOKS `requirements.txt` + pytest 9.2.0 + pytest-asyncio | **OK**: 29 actual excerpts are verbatim at the pinned commits with correct line anchors; 1 simplified block names a real file; 51 standalone files written; all 45 `$ python3 ...` outputs match; 31 pinned links resolve |
| Same checker, with a fresh venv built exactly as section 2 says (`fastapi==0.162.0 httpx==0.28.1 httpx2==2.16.0 pytest==9.2.0 uvicorn==0.54.0`) | 44 of 45 outputs match. `chunk_demo.py` fails with `ModuleNotFoundError: pydantic_settings`, as expected: the article says it needs MOKS's own requirements. Before `httpx2` was added, `try_api.py` and the pytest runs printed a Starlette deprecation warning, which is why the install line has it |
| `uvicorn teaching_api:app --port 8765` (scratch folder, reader venv) | Started; `GET /health` 200, `GET /docs` 200, `POST /questions` 201. The article uses the default port 8000. `--reload` was not tried |
| `printf '45\n' \| python ask.py` | Prints `<class 'str'>` and `That is 2700 seconds.` (the checker cannot type into `input()`) |
| `python -m pytest -q tests/test_bounds_connectors.py tests/test_rag.py tests/test_investigations.py tests/test_observability.py` (`moks/backend`, throwaway PostgreSQL 17 on port 55432) | **51 passed** |
| A scratch test (outside the repo) posting an invalid body to `/moks/api/investigations` | Unsigned: **401** `Not signed in`. Signed in: **422**, errors at `body.question` and `body.minutes`. `GET /moks/api/health` 200 |
| Direct calls to `kind_of`, `estimate_tokens`, `chunk`, `window_from_question`, `CreateIn`, `Settings`, `_content_text`, `BoundedHttp` with a mock transport | Every value quoted in the article came from these runs |
| `npx vitest run tests/content.test.ts tests/editor-workflow.test.ts tests/links.test.ts` (`www/`) | Pass (13 + 41 tests on the last runs). The editor round trip first failed on an indented code line inside exercise 2, which is now a separate code block. The link test first failed on `/python-practice` |
| `npm test` (`www/`) | Last run: 428 passed, 1 failed. Three full runs each failed a **different** unrelated test with a 30 s timeout (an XSS render, the cover-image route, a fidelity hook for another article). Another session was editing `package.json`, `CodeBlock.tsx`, `globals.css` and adding `MermaidBlock.tsx` at the same time. Every test that reads this article passes on its own |

Not run: `npm run lint`, `typecheck` and `build` (no application code changed). The standalone examples were run on **Python 3.11.9 only**, because 3.12 is not installed here. Syntax is 3.11-compatible, but the traceback layouts in sections 1, 17 and 18 should be checked once on 3.12.

To repeat the checks:

```bash
# from www/, in a venv with fastapi, httpx, httpx2, pytest and MOKS's requirements installed
python docs/knowledge-sharing/python-tutorial/verify_article.py ../..
```

The checker writes examples into a temporary folder, runs them with the same interpreter, and sets `PYTHONPATH` to `../../moks/backend` so `chunk_demo.py` can import MOKS. It disables the pytest-asyncio plugin for the article's pytest commands, because a reader's environment from section 2 does not have it.

## Decisions

- **Main project: MOKS backend.** It is the largest Python codebase here, with FastAPI, Pydantic, HTTPX, async code and pytest in one place. RoboShop AI appears once, for FastMCP, because MOKS has no MCP.
- **No Mermaid.** The committed renderer has no Mermaid support, so the end-to-end trace is a `text` diagram plus a numbered list. Another session was adding `src/components/MermaidBlock.tsx` while this was written. If that lands, section 16's diagram could be converted.
- **No motivations.** The repositories do not say why Python or any library was chosen, so the article gives no reasons. First-person statements are limited to what I ran and checked.
- **Standalone files include their `# name.py` comment.** That makes every reported line number one higher than the code's own count; the article's error outputs and prose use the real numbers and say why once.

## Gaps found (not in the article's claims, for the owner)

1. **`/python-practice` is not known to the link checker.** `STATIC_ROUTES` in `src/lib/content/links.ts` omits it, so `tests/links.test.ts` fails on any article that links it, although the page is live. The TypeScript draft found the same thing. To restore the link, add the route there, then change the plain-text mention in "Where to go next" back to `[Python practice problems](/python-practice)`.
2. **Blocking read on the event loop (MOKS, minor).** `OpenAIProvider._headers` calls `resolve_credential`, which can read a credential file with `path.read_text()`, from async code. The article mentions it as small. Wrapping it in `asyncio.to_thread`, or caching the value, would remove it.
3. **No static type checker in MOKS.** `pyproject.toml` and `ci.yml` configure no mypy or pyright, although the code is heavily annotated. The article states this as fact, not as a recommendation.
4. **`TestClient` with `httpx` is deprecated by Starlette 1.10.** Readers need `httpx2` installed to avoid a warning. MOKS's own tests use `httpx.AsyncClient` with `ASGITransport`, not `TestClient`, so they are unaffected today.
5. **MOKS tests need PostgreSQL even for pure functions.** The session-wide `database` fixture in `tests/conftest.py` is autouse, so testing `kind_of` alone still needs a server.
