# Python vs Go vs TypeScript article

Status: **draft for author review, not published.** Written 2026-11-03 against `roboshop-ai` c81e85a, `jithendar.com` f12f8cc, `moks` 74a097d and `tools` 387bd30. The files cited were clean in the working tree at those commits.

| Asset | Location |
| --- | --- |
| Article | `content/blog/python-vs-go-vs-typescript.mdx` (`status: review`, no `publishedAt`) |
| Example checker | `verify_examples.py` (this folder) |

## SEO and publishing metadata

The content schema has no excerpt or keyword field, so those live here, as for earlier drafts.

| Field | Value |
| --- | --- |
| H1 (`title`, 75 chars) | Python vs Go vs TypeScript: Similarities, Differences, and When to Use Each |
| SEO title (`seoTitle`, 71) | Python vs Go vs TypeScript: A Practical Programming Language Comparison |
| Meta description (`description`, 159) | Python vs Go vs TypeScript, compared with runnable side-by-side examples: types, errors, concurrency, tooling and real code from RoboShop AI and jithendar.com. |
| `seoDescription` (155) | A programming language comparison of Python, Go and TypeScript with runnable examples, type systems, errors, concurrency, deployment and real project code. |
| Slug | `python-vs-go-vs-typescript` |
| Excerpt | Python, Go and TypeScript share more than you'd think, and differ in exactly the places that cause bugs. This guide puts runnable examples side by side, explains the three type systems, error models and concurrency models, and follows one real request path through a TypeScript storefront, a Python gateway and a Go service. |
| Primary keyword | Python vs Go vs TypeScript |
| Secondary keywords | programming language comparison; Go vs Python; Go vs TypeScript; Python Go TypeScript examples; Go goroutines vs async await |
| Category | `ai-engineering` (**placeholder**, same as the Python vs TypeScript post; no category fits a language comparison) |
| Content type | `tutorial` |
| Internal links | `/blog/python-vs-typescript`, `/blog/roboshop-ai-architecture`, `/blog/learning-typescript-real-project-jithendar-com` (all in the live sitemap on 2026-11-03) |
| `related` | the same three posts |
| Length | About 12,500 words of prose and tables, 19,500 including code |

The front matter passes `articleFrontmatter` from `src/lib/content/schema.ts` (checked with a temporary Vitest file, since deleted). Live posts are stored in PostgreSQL, so after review the owner pastes the approved draft into the editor, as with earlier drafts.

## Verified project files used

| Repository | File | Used for |
| --- | --- | --- |
| roboshop-ai | `services/currency-service/main.go` (lines 40–48, 96–101, 169–183 quoted; 113–115, 241–273 described) | Actual Go code: JSON struct tags, pointer for nullable field, `sync.RWMutex` cache, ticker + context refresh loop, `signal.NotifyContext`, `log/slog` |
| roboshop-ai | `services/currency-service/main_test.go` (lines 112–133) | Actual Go concurrency test with a fake `RoundTripper` |
| roboshop-ai | `services/currency-service/metrics.go` (line 21–22 comment) | Shared metric names across languages |
| roboshop-ai | `services/currency-service/Dockerfile` (lines 1–12), `go.mod`, `README.md`, `.github/workflows/ci-currency-service.yml` | Multi-stage build, `CGO_ENABLED=0`, Go 1.27, `go test -race` in README and CI, no dependencies |
| roboshop-ai | `services/web/frontend/src/paths.ts` (lines 29–36, 46–58) | Actual TypeScript: hand-written `Fx` type, type guard, `fetch` with timeout |
| roboshop-ai | `services/web/frontend/package.json`, `tsconfig.json`, `scripts/build.mjs` | TypeScript 7.0.2, `tsc` emits to `dist/`, `node --test` |
| roboshop-ai | `services/ai-gateway/currency_quote.py` (lines 100–113), `lib/runtime.py` (`request`), `Dockerfile`, `requirements.txt`, `tests/test_user_service_contract.py` | Actual Python: `Decimal`, exception-based validation, `CURRENCY_URL`; Python 3.14, FastAPI 0.159.1, `unittest` |
| roboshop-ai | `services/web/nginx/snippets/routes.conf` (lines 56–66) | The boundary between browser and Go service |
| jithendar.com | `www/src/lib/content/schema.ts` (lines 39–59) | Actual Zod schema |
| jithendar.com | `www/AGENTS.md`, `www/package.json`, `www/Dockerfile`, `executor/Dockerfile`, `src/lib/content/links.ts` | Draft rules, TypeScript 6.0.3, Vitest 5.0.5, ESLint, Node 26, Python 3.13 executor, link checker |
| moks | `Dockerfile`, `frontend/package.json`, `backend/pyproject.toml` | Python 3.12, TypeScript 5.9.3, `tsc --noEmit && vite build`, Vitest |
| tools | `devops-tools/dependencies/dispatch.go` | The only Go file in tools: no `go.mod`, not referenced by any workflow; mentioned, not used |

File counts in the article's first table come from `git ls-tree` at the cited commits. No repository configures a Python linter or type checker (no ruff, mypy, Pyright or flake8 configuration in any `pyproject.toml` or config file).

## Validation (run 2026-11-03 on macOS arm64)

| Check | Result |
| --- | --- |
| `verify_examples.py` | **Pass.** 38 example groups: 99 programs run and match their `Output:` comments (Python 3.11.9, Go 1.27.3 with `-race`, Node 26.13.0); groups labelled "same output" print identical text; 1 Go example fails to build with the documented error; 3 test suites pass (pytest 9.2.0, `go test -race`, Vitest 5.0.5); every Go folder passes `gofmt -l` and `go vet`; mypy 2.4.1 `--strict` reports errors only on flagged lines; `tsc` 6.0.3 and 7.0.2 strict with `erasableSyntaxOnly` pass, with and without `noUncheckedIndexedAccess`; 10 project excerpts match their commits byte for byte |
| Currency service, copy at c81e85a | `go vet ./...` clean, `gofmt -l .` clean, `go test -race -count=1 ./...` 8/8 passed (Go 1.27.3) |
| Cross-compile, same flags as the Dockerfile | `CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w"`: arm64 7,078,048 bytes, amd64 7,626,912 bytes, both "statically linked" per `file` |
| `npx vitest run` (site suite) | 42 files, 433 tests passed. These tests use fixtures, not `content/`, so the draft was validated separately against the schema |
| Source URLs | All 36 return HTTP 200 |
| In-page anchors | 5 anchors match `rehype-slug` heading IDs |

How to rerun (from `www/`):

```bash
python3 -m venv /tmp/pgts-venv && /tmp/pgts-venv/bin/pip install mypy pytest
python3 docs/knowledge-sharing/python-vs-go-vs-typescript/verify_examples.py \
  --python /tmp/pgts-venv/bin/python --go "$(command -v go)" \
  --tsc node_modules/typescript/bin/tsc --tsc ../../roboshop-ai/node_modules/typescript/bin/tsc
```

It needs port 8000 free (local mock server) and Go 1.25+. The `/usr/local/go` on this Mac is an x86_64 build that can't run on arm64 without Rosetta, so the check used an official go1.27.3 darwin-arm64 tarball (SHA-256 verified against go.dev) unpacked in the session scratchpad. Nothing was installed system-wide.

## Limitations and open items

- **Python version.** Only CPython 3.11 is installed here; the projects run 3.12–3.14. Examples avoid newer syntax, and output (including the two exception messages shown) was observed on 3.11 only.
- **Not run:** the RoboShop gateway and storefront test suites, the MOKS tests, the site's lint/typecheck/build (no application code changed). The tools `dispatch.go` was not built.
- **No benchmarks.** The article deliberately gives no performance numbers apart from the two measured binary sizes, which are labelled as one measurement of one service.
- **Contract drift found.** `paths.ts` types `suggestedCurrency?: string`, but the Go service sends `null` when there's no suggestion. Harmless today (`fx?.suggestedCurrency || ''`), described in the article, not changed.
- **Mermaid.** The article has one ```mermaid block. Confirm client-side Mermaid rendering is deployed before publishing; the admin editor preview still shows the source.
- **Language choice reasons.** The repositories don't document why each service uses its language, so the article states only what the code shows. Add your reasons if you want them in the post.
- **Version-sensitive claims** were checked against: Go 1.22/1.25/1.27 release notes (loop variables, `WaitGroup.Go`, container-aware `GOMAXPROCS`, generic methods, `encoding/json` on v2), the cgo docs (default enablement), Node.js v26.13.0 TypeScript docs (type stripping stable, default since 22.18/23.6, no type check, ignores tsconfig), and the TypeScript 7.0 announcement (Go-based compiler, `strict` default, July 8, 2026).
