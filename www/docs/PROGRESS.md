# Progress log — jithendar.com

## CI deploy of manifests to minikube (2026-11-04, owner request)

New `.github/workflows/deploy-minikube.yml` (existing workflows unchanged): plan on PRs, apply on `master` when
`k8s/**` changes and `MINIKUBE_DEPLOY=true`. Only application kinds in namespace `jithendar`
(`scripts/ci-app-manifests.py`); RBAC, Secrets, ServiceAccounts, quotas and cluster-scoped objects stay manual. New
ServiceAccount `github-ci-applier` (`k8s/85-ci-applier.yaml`, in the kustomization), kubeconfig template
`.github/jithendar-ci-applier.yaml`, setup `scripts/setup-ci-applier.sh`; docs in DEPLOYMENT.md.

- **Checked:** filter on both renders (30 applied, 21 held back, unknown kinds and other namespaces exit 2); server
  dry-run and diff of the exact files with the owner's context (only pending change: `strip-trace-headers`);
  applier RBAC server dry-run; workflow YAML parses; `bash -n` on the setup script.
- **Not checked:** the workflow on GitHub, and the Role as the ServiceAccount itself (it does not exist until
  `scripts/setup-ci-applier.sh` runs; the script dry-runs every object as the ServiceAccount before storing the
  token). actionlint and shellcheck pass on the workflow and setup script.

## Database access from the Mac and the Hetzner host (2026-11-04, owner request)

Adminer at `https://jithendar.com/db/` and PostgreSQL at `db.jithendar.com:443` (a path cannot carry the PostgreSQL
protocol), both IP-allowlisted to 122.177.247.138 and 46.224.38.14. Not applied; order and checks in
`k8s/db-access/README.md`.

- **Found:** Traefik saw every client as `192.168.49.2` (HAProxy TCP forwarding + kube-proxy NodePort SNAT), so IP
  allowlists, site logs and per-IP rate limits all saw one address. Fix in `tools`: Traefik
  `proxyProtocol.trustedIPs: 192.168.49.0/24`, HAProxy `send-proxy-v2` (script refuses to run before Traefik).
- **Files:** `k8s/db-access/` (kustomization, allowlist, adminer, postgres-tls, README), `scripts/create-db-remote-user.sh`,
  `k8s/README.md`; `tools/deploy/minikube/traefik/values.yaml`, `README.md`, `deploy/minikube/expose-ingress.sh`.
- **Checked:** server dry-run of `k8s/db-access` (12 objects); Traefik chart 42.0.0 renders the proxyProtocol flags;
  `bash -n` on both scripts; the role SQL on a throwaway PostgreSQL 17 (create, rotate, read/write, no DDL).
- **Not checked:** PROXY protocol on the live host (no SSH key for root@jithendar.com from this Mac), Traefik's
  PostgreSQL STARTTLS/ALPN handling, Adminer under `/db/` on the real image.

## Observability review + draft article (2026-11-04, owner request)

Reviewed logs, traces and metrics against the live mk4 cluster (read-only), fixed what was verified, and drafted
`content/blog/logging-tracing-observability-jithendar-com.mdx` (`status: review`). Nothing committed or deployed.
Details and runbooks: `docs/OBSERVABILITY.md` ("Review fixes", "Runbooks").

- **App:** `src/lib/tracing-config.ts` (new: sampler without health probes or remote sampling flags, outgoing span
  names `<kind> <METHOD> <host>`, `traceparent` to the practice executor only), `src/instrumentation.ts`,
  `src/lib/request-log.ts` (`isHealthProbe`, `loggedPath`), `src/proxy.ts`; `tests/tracing-config.test.ts`.
- **Cluster manifests:** `k8s/40-middlewares.yaml` (`strip-trace-headers`), `k8s/60-ingress.yaml`, `k8s/README.md`.
- **Executor:** `executor/app/main.py` (trace id on audit lines), `executor/tests/test_executor.py`.
- **tools repo:** Alloy route/outcome patterns (mk4 + EKS copy), collector metrics listener, Jaeger config
  (`jaeger/jaeger.yaml`, `kustomization.yaml`, `max_traces: 5000`, 384Mi), Prometheus jobs and alerts, dashboards,
  observability README runbooks.
- **Figure:** `docs/knowledge-sharing/jithendar-com-observability/diagrams/` (`.drawio`, builder, PNG script) →
  `public/images/jithendar-com-observability/`.
- **Commands:** `lint`, `typecheck` pass; `npm test` 449 passed; `npm run build` passes (after deleting
  `.next/cache/turbopack`); executor pytest 19 passed; tools pytest 241 passed, 4 skipped (the real-collector test
  needs an `otelcol` binary, not run); all alert expressions evaluated on live Prometheus; `kubectl diff -k k8s`
  shows only the middleware and annotation. Local `next start` checks: no spans for `/api/health`, a `-00`
  traceparent still traced, 20/20 requests 200 with the trace endpoint unreachable, reset token redacted.
- **Not validated:** the collector, Jaeger and Alloy configs were not run with their real binaries (running
  downloaded binaries was not permitted); NetworkPolicy enforcement on 9464 was not tested from a denied pod.
- **Open:** `tests/error-handling.test.ts` prints an unhandled PGlite `ENOENT` (`.data/pglite`) when run alone; it
  predates this change. `METRICS_TOKEN` is in the Secret and DEPLOYMENT.md but unused.

## Draft article: Mermaid diagrams on jithendar.com (2026-11-03, owner request)

`content/blog/mermaid-diagrams-on-jithendar-com.mdx`, `status: review`. Explains what Mermaid is, why it suits a technical blog, and how the Mermaid change below was built, with 5 Mermaid diagrams. Nothing published or committed. **Publish only after the Mermaid change is deployed.**

- **Files:** the article; `docs/knowledge-sharing/mermaid-diagrams/README.md` (SEO metadata, sources, validation).
- **Commands:** all 5 diagrams render in headless Chrome with Mermaid 12.2.0, light and dark, no `<script>` in the SVG. `content`, `links` and `editor-workflow` tests: 56 passed (after shortening the description to fit the 160-character limit).
- **Open:** category `devops-sre` is a placeholder.

## Mermaid diagrams in articles (2026-11-03, owner request)

A ```` ```mermaid ```` fence in a post or page now shows as a diagram. Uncommitted, not deployed.

- **How:** the server still sends the Shiki-highlighted source, labelled "Mermaid" (readers without JavaScript and crawlers get the text). In the browser, `MermaidBlock` loads the `mermaid` library with a dynamic import, so only pages with a diagram download it, and draws the SVG with a "Show source" toggle. It follows the site's light/dark theme. `securityLevel: "strict"` sanitises labels and disables click handlers. If the source does not parse, the code block stays as it is.
- **New dependency:** `mermaid` 12.2.0, pinned. Justification: no existing dependency draws diagrams. Rendering on the server instead (`rehype-mermaid`) would need a headless browser in the image and in CI.
- **Files:** `src/components/MermaidBlock.tsx` (new), `src/components/CodeBlock.tsx` (routes `mermaid` fences), `src/app/globals.css` (`.mermaid-diagram`), `src/lib/code-languages.ts` (label), `tests/features.test.tsx` (server output for a mermaid fence), `package.json`, `package-lock.json`.
- **Commands:** `typecheck` passes, `lint` clean, `build` succeeds. `npm test`: 427 passed, 2 failed with 30 s timeouts. The 4 test files that timed out across runs (`api-keys`, `article-route`, `responsive-content`, `setup-action`) pass when run alone (17/17). Both diagrams in `learning-terraform-real-project-tools-repository.mdx` rendered in headless Chrome with Mermaid 12.2.0 and these settings, with no `<script>` in the SVG.
- **Not verified:** a real article page in a browser (no local database here).
- **Open:** the admin editor's preview (`/api/admin/preview` → `src/lib/mdx/html.ts`, an HTML string, not React) still shows the highlighted source, not the diagram.

## Draft article: Learning Python through real projects (2026-11-03, owner request)

`content/blog/python-tutorial-beginners-real-projects.mdx`, `status: review`, written against moks `ef6908a` and roboshop-ai `c81e85a`. Nothing published or committed. No application code changed.

- **Files:** the article, `docs/knowledge-sharing/python-tutorial/` (README with SEO metadata, files used, validation, gaps; `verify_article.py`).
- **Commands:** `verify_article.py` passes (29 verbatim excerpts, 45 example outputs matched, Python 3.11.9). MOKS tests for the quoted code: 51 passed on a throwaway PostgreSQL. `content`, `editor-workflow` and `links` tests pass alone, after two fixes: an indented code line under a list item broke the editor round trip, and `/python-practice` is now plain text because the link checker does not know the route. Full `npm test` had one 30 s timeout in a different unrelated test on each of three runs, while another session was editing `CodeBlock.tsx` and `package.json`. `lint`, `typecheck` and `build` not run: no application code changed.
- **Open:** category is a `devops-sre` placeholder; tracebacks not checked on Python 3.12; gaps listed in the package README.

## Draft article: Advantages of TypeScript over Python and Go (2026-11-04, owner request)

`content/blog/typescript-advantages-over-python-and-go.mdx`, `status: review`, written against jithendar.com `be1287a`. Nothing published or committed. No application code changed.

- **Files:** the article; `docs/knowledge-sharing/typescript-advantages/` (README with SEO metadata, FAQs, internal links, files used, validation, author checks; `examples/`; `verify_examples.py`).
- **Commands:** `verify_examples.py` passes 29 checks (identical output in TypeScript on Node 26.13.0, Python 3.15.2 with Pydantic 2.14.2 and Go 1.27.3; `tsc` 6.0.3 and mypy 2.4.1 `--strict` errors match the article; TypeScript route streams from a FastAPI service; all 12 code blocks match their sources). Front matter passes `collectionSchema("blog")`, editor round trip lossless, `links` test passes, 23 source URLs return 200. Lint, typecheck and build not run: no application code changed.
- **Open:** category `ai-engineering` is a placeholder; FAQs are in the README, not the article body; no Go article exists to link to.

## Draft article: Python vs Go vs TypeScript (2026-11-03, owner request)

`content/blog/python-vs-go-vs-typescript.mdx`, `status: review`, written against roboshop-ai `c81e85a`, jithendar.com `f12f8cc`, moks `74a097d` and tools `387bd30`. Nothing published or committed. No application code changed.

- **Files:** the article; `docs/knowledge-sharing/python-vs-go-vs-typescript/` (README with SEO metadata, files used, validation and limitations; `verify_examples.py`).
- **Commands:** `verify_examples.py` passes (99 programs on CPython 3.11.9, Go 1.27.3 with `-race` and Node 26.13.0 match their `Output:` comments; 1 expected Go compile failure; pytest, `go test -race` and Vitest suites pass; `gofmt`/`go vet` clean; mypy `--strict`; `tsc` 6.0.3 and 7.0.2 strict with `erasableSyntaxOnly`; 10 project excerpts match their commits). RoboShop currency service `go test -race` 8/8. `npx vitest run`: 433 passed. Front matter validated against `articleFrontmatter`. Lint, typecheck and build not run: no application code changed.
- **Open:** category `ai-engineering` is a placeholder; Python examples not run on 3.12+; confirm Mermaid rendering is deployed (one diagram).

## Draft article: Python vs TypeScript (2026-11-03, owner request)

`content/blog/python-vs-typescript.mdx`, `status: review`, written against jithendar.com `dc249e8`, moks `ef6908a` and roboshop-ai `c81e85a`. Nothing published or committed. No application code changed.

- **Files:** the article; `public/images/python-vs-typescript/typescript-python-architecture.svg`; `docs/knowledge-sharing/python-vs-typescript/` (README with SEO metadata, files used, sources, validation and limitations; `verify_examples.py`).
- **Commands:** `verify_examples.py` passes (44 example groups run on CPython 3.11.9 and Node 26.13.0 and match their `Output:` comments; mypy; `tsc` 6.0.3 and 7.0.2, strict, with and without `noUncheckedIndexedAccess`; 9 project excerpts match their commits). `npx vitest run`: 428 passed, 1 `article-route` timeout under load that passes alone (8/8). Lint, typecheck and build not run: no application code changed.
- **Open:** category `ai-engineering` is a placeholder. Python examples were not run on 3.12+ (only 3.11 is installed here). `/python-practice` is linked as an absolute URL because the link checker does not know the route.

## Draft article: Learning TypeScript through jithendar.com (2026-11-03, owner request)

`content/blog/learning-typescript-real-project-jithendar-com.mdx`, `status: review`, written against this repository at `dc249e8`. Nothing published or committed. No application code changed.

- **Files:** the article, `docs/knowledge-sharing/typescript-tutorial/` (README with SEO metadata, files used, validation, gaps; `verify_article.py`).
- **Commands:** `verify_article.py` passes (77 blocks; 36 TS/TSX examples compiled with TypeScript 6.0.3). `npm test` 425 passed in 42 files, after one fix: the editor round trip first failed on a paragraph starting with inline `<p>` code. `npm run typecheck` passes; `npm run lint` is clean. `build` not run: no application code changed, and the MDX compile was checked directly.
- **Open:** category is a `devops-sre` placeholder (no web-development category exists). Six implementation gaps are listed in the package README, including deprecated `React.FormEvent` in 7 files and the link checker not knowing `/python-practice`.

## Python practice platform (2026-11-02, owner request)

`/python-practice`: role-based Python practice and interview preparation, plus a sandboxed code runner. Uncommitted. **Code execution is built but off**: mk4 has no gVisor runtime yet. Docs: `PYTHON_PRACTICE.md`, `PYTHON_PRACTICE_EXECUTOR.md`.

- **Owner decisions:** Postgres instead of the prompt's MongoDB; build the executor for gVisor and ship it switched off; treat prompt sections 1–14 as the full spec (the prompt was cut off in §14); deliver everything in one run.
- **Web (`www/`):** migration `0010_python_practice.sql` and schema; `lib/practice/*` (catalog, seeder, evaluator, submissions, sessions, progress, adaptive, daily, achievements, dashboard, profile/export, admin, settings, AI tutor); `/api/practice/*`; pages under `app/python-practice/`; admin under `app/admin/practice/`; components in `components/practice/`. Small edits: login `?mode=signup`, admin nav, audit severities, cache-bus kind, scheduler sweep, start-up seeding, `next.config.ts` no-store for `/api/practice`.
- **Content:** 20 roles, 57 topics, 100 original problems (`content/python-practice/`). Expected outputs come from running every reference solution through the real runner (`executor/tools/build_problems.py`), which also checked the hand-written expectations: 4 of mine were wrong and are fixed.
- **Executor (`executor/`):** FastAPI API, Redis queue, dispatcher (one gVisor pod per job), sandbox runner, Dockerfiles. Manifests in `k8s/practice-executor/` (separate from `deploy.sh`), NetworkPolicy egress added to `k8s/30-jithendar-com.yaml`, scripts `install-gvisor-mk4.sh`, `verify-practice-sandbox.sh`, `create-practice-executor-secrets.sh`, workflow `ci-practice-executor.yml`.
- **New dependencies:** `codemirror`, `@codemirror/{lang-python,state,view,commands,language}` (Monaco has no mobile support) and `@aws-sdk/client-bedrock-runtime` (Bedrock tutor; same SDK family as S3/SES).

**Commands run → result**
| Command | Result |
|---|---|
| `npm run lint` | pass (clean) |
| `npm run typecheck` | pass |
| `npm test` | pass: 42 files, 423 tests (21 new in `tests/practice.test.ts`) |
| `APP_ENV=production npm run build` | pass |
| `pytest` (executor, scratch venv, Python 3.11) | pass: 17 tests |
| `executor/tools/build_problems.py` | pass: 100 problems, 423 test cases |
| `next dev` smoke test as a guest | pages 200; `/dashboard` → 307 to `/login`; guest API calls → 401 `auth_required`; no solution code in problem HTML |
| `kubectl apply -k k8s/practice-executor --dry-run=server` | RuntimeClass and ValidatingAdmissionPolicy accepted. Namespaced objects not checked: their namespaces don't exist yet |
| Docker image builds (executor, sandbox) | **Not run.** The Docker daemon isn't running on this Mac; CI builds them |
| `install-gvisor-mk4.sh`, `verify-practice-sandbox.sh` | **Not run.** They change cluster nodes, which the owner runs |

**Open issues**
- Hidden tests and solutions of the seed problems are in this public repository: hidden in the product, not secret. Add private hidden tests in the admin where that matters.
- `catalog.generated.json` was generated with Python 3.11; CI regenerates it with 3.13 and fails if anything differs.
- The "practice time" metric is an estimate from activity gaps (definition shown on the dashboard).
- The header menu is admin-configured: add a "Python practice" link in Admin → Appearance.

**Manual configuration required (owner):** the six steps in `PYTHON_PRACTICE_EXECUTOR.md` → "Turning it on" (gVisor on every node, ECR repositories and CI push rights, apply manifests and secrets, verify, site secret, admin switch). The AI tutor needs a provider, model and key in Admin → Python practice → Settings.

## Draft article: FastAPI and FastMCP (2026-11-01, owner request)

`content/blog/fastapi-and-fastmcp-ai-projects.mdx`, `status: review`, four figures, written against `roboshop-ai` c81e85a and `moks` ab99cf7. Nothing published or committed. No application code changed.

- **Files:** the article, `docs/knowledge-sharing/fastapi-fastmcp/` (README, evidence map, editorial checklist, `verify_article.py`, `diagrams/`), `public/images/fastapi-fastmcp/`.
- **Commands:** `npm test` 401 passed; lint clean; `verify_article.py` passes. `typecheck` and `build` not run, because no TypeScript changed.
- **Open:** SVG and PNG files are rendered by `build_diagrams.py`, not exported by draw.io. Published-page discrepancies are listed in `editorial-checklist.md`.

## Draft project page: MOKS (2026-11-01, owner request)

`content/projects/moks.mdx`, `status: review`, checked against moks ab99cf7 and the EKS cluster. Not published or committed. Open items are in the page's `<Todo>`, including `usernamePassword.sh` tracked in the public moks repository and the missing LICENSE. The RoboShop series now uses the `:::figure` directive for captions.

## Draft series: RoboShop AI knowledge sharing (2026-11-01, owner request)

Four review drafts, nine figures and five editable draw.io files, written against `roboshop-ai` c81e85a. Nothing published or committed.

- **Files:** `content/blog/roboshop-ai-{architecture,gateway,mcp-server,shopping-agent}.mdx`, `docs/knowledge-sharing/roboshop-ai/` (README, evidence map, editorial review, `verify_series.py`, `diagrams/`), `public/images/roboshop-ai-series/`.
- **Commands:** `npm test` 399 passed; lint, typecheck and production build pass; `verify_series.py` passes. Details and the service test results are in section 3 of `docs/knowledge-sharing/roboshop-ai/editorial-review.md`.
- **Open:** SVG and PNG files are rendered by `build_diagrams.py`, not exported by draw.io, because the draw.io desktop download was refused by the session's permission policy. The `.drawio` files have not been opened in draw.io. No real model was called. Author decisions are listed in the editorial review.
- **Found:** a visual-editor bug where a paragraph starting "No. " becomes a list item. Not fixed.

## Article update: How We Implemented RAG and Skills in MOKS (2026-11-01, owner request)

**What changed**
- `content/blog/moks-rag-and-skills-design.mdx` rewritten against moks `9c150e9`. Same slug, `status: review`, not published. The live post is in Postgres, so the owner pastes this into the editor.
- Two Mermaid sources in `docs/diagrams/moks-rag-skills/`, rendered with mermaid-cli 11.4.2 to `public/images/moks/moks-rag-{knowledge-flow,skills-runtime}.svg`. The older SVGs stay because the live post uses them.
- `VERIFICATION.md`, `article_trace_test.py`, `trace-summary.txt` and `trace-probes.txt` in the same folder. `docs/CONTENT_AUDIT.md` row 7 marked drafted.

**Commands → result**: `vitest` 395 of 395 passed; article compiled and rendered through `compileMdx`. MOKS backend from a clean export: 835 passed, 3 failed (terminal chart tests), 4 skipped. Lint, typecheck and build not run (content and static assets only).

**Open**: four gaps listed in the article are unfixed in MOKS (citation existence only, freshness labels with no prompt rule, prompt truncation of passages, no knowledge effect in rule-based reports). No MOKS code changed.

## Content audit, Batch 1 (2026-11-01, owner request)

**What changed** (uncommitted, nothing published)
- `docs/CONTENT_AUDIT.md`: inventory, plan, SEO fields, redirects, open questions and validation.
- Rewrote `content/blog/deploy-roboshop-ai-amazon-eks.mdx` and `content/blog/roboshop-ai-microservices.mdx` (which absorbs `-architecture`), both `status: review`.
- Replaced `content/projects/jithendar-com.mdx` with `content/projects/nextjs-site-on-kubernetes.mdx`, matching the live slug.
- New diagrams `roboshop-ai-eks-services.svg` and `roboshop-ai-eks-delivery.svg`, with `.mmd` sources and two functions in `build_diagrams.py`.
- `tests/pages-media.test.ts`: title assertion follows the new article title.

**Commands → result**: `npm test` 394 passed / 1 failed (`article-route` future-post: fixture date 2026-11-01 has passed; unrelated, fails CI until moved); lint, typecheck and production build pass. Full table in `docs/CONTENT_AUDIT.md` section 10.

**Open**: live posts are in PostgreSQL, so approved drafts must be applied in the editor (audit section 6). Owner decisions are in audit section 7. Batches 2 and 3 wait for editorial review.

## Draft article: LangChain vs LangGraph for an SRE agent (2026-11-01, owner request)

**What changed**
- New `content/blog/langchain-vs-langgraph-sre-agent-moks.mdx` (analysis, `status: draft`; not published), written against moks commit `9c150e9`. The requested title changed because MOKS installs `langchain-core`, not `langchain`.
- Two Mermaid diagrams: sources in `docs/diagrams/moks-langgraph/*.mmd`, rendered with mermaid-cli 11.4.2 to `public/images/moks/moks-langgraph-*.svg`.
- `docs/diagrams/moks-langgraph/VERIFICATION.md`, plus the trace test and its output.

**Commands → result**: `vitest` 3 failed / 392 passed; the same 3 fail without this article (`article-route` future-post, `editor-workflow` deploy-roboshop-ai-amazon-eks, `pages-media` bundled posts). A fourth `article-route` test timed out once and passes alone. Lint, typecheck and build not run (content and static assets only).

**Manual steps**: review the `<Todo>`; publish `moks-rag-and-skills-design` first or remove the links to it; set `status`/`publishedAt`.

## Draft article: MOKS RAG and skills design (2026-10-31, owner request)

**What changed**
- New `content/blog/moks-rag-and-skills-design.mdx` (analysis, `status: review`; never published by this change), reviewed against moks commit `9b94516`. Includes the design-questions section the owner wants for interview preparation.
- Four diagrams in `public/images/moks/moks-*.svg`, generated by `docs/diagrams/moks-rag-skills/build_diagrams.py` (stdlib; reuses the RoboShop generator's helpers). This one has no Mermaid copies: the script is the editable source.

**Commands → result**

| Command | Result |
|---|---|
| moks backend `pytest` at `9b94516` (local PostgreSQL 17, Python 3.11) | 829 passed, 4 skipped |
| moks RAG and skills eval gates | all pass; recall@5 1.0 on 11 synthetic documents, keyword mode |
| `npm test` | pass (41 files, 394 tests) |
| `npm run lint` / `npm run typecheck` / `npm run build` | pass |
| Local preview (`CONTENT_PREVIEW=true`) | article 200 with the preview badge, 4 figures, 2 tables; SVGs served as `image/svg+xml`. Only warning: no local site-config database, so defaults were used |
| Diagram inspection | SVGs pass `xmllint`; each rendered with macOS Quick Look and checked for overlaps |

**Manual steps (owner)**
1. Review the `<Todo>`, update the proof section if Pinecone, a chat model or the lab have since run on mk4, add commentary, set `status`/`publishedAt`.

## Draft articles: RoboShop AI on Amazon EKS — system design + deployment guide (2026-10-30, owner request)

**What changed**
- New `content/blog/roboshop-ai-eks-system-design.mdx` (analysis) and `content/blog/deploy-roboshop-ai-amazon-eks.mdx` (tutorial), both `status: review` (visible only in `npm run preview`; never published by this change). Written against roboshop-ai commit `692e72d` plus its uncommitted `deploy/eks/` folder, which is the authoritative configuration; the articles link to it instead of copying files.
- Eight diagrams in `public/images/roboshop-eks/eks-*.svg`, copied from `roboshop-ai/deploy/eks/diagrams/svg/` (generated there by `build_diagrams.py`, stdlib; Mermaid sources beside it). 720 px wide, `<title>` + `<desc>` on each, alt text and captions in the articles.

**Commands → result**
| Command | Result |
|---|---|
| `npx vitest run tests/content.test.ts tests/links.test.ts tests/editor-workflow.test.ts` | pass (3 files, 41 tests) |
| `npm test` | pass (40 files, 383 tests) |
| `npm run lint` / `npm run typecheck` | pass |
| `npm run build` | pass |
| Local preview (`CONTENT_PREVIEW=true CONTENT_DIR=content next dev`) | both pages 200 with the preview badge; 8 figures render; SVGs served as `image/svg+xml` |
| Diagram inspection | each SVG rendered with macOS Quick Look and checked for overlaps/clipping; fixed several before copying |

**Manual steps (owner)**
1. Commit/push `roboshop-ai/deploy/eks`, then pin the `tree/master`/`blob/master` links in both articles to that commit.
2. The guide has not been run on AWS: deploy once, record region/date and fixes, then remove the "not yet run" wording.
3. The roboshop-ai licence is "all rights reserved": decide whether readers may deploy their own copy before publishing.
4. Review the `<Todo>` notes, add commentary, set `status`/`publishedAt`.

## Draft article: RoboShop AI microservices, benefits and trade-offs (2026-10-29, owner request)

**What changed**
- New draft `content/blog/roboshop-ai-microservices.mdx` (`status: draft`), written against roboshop-ai commit `8cded0b` (working tree had only doc/script changes). Complements, does not replace, the existing `roboshop-ai-microservices-architecture` draft, which still describes separate `frontend`/`nginx` workloads.
- Four diagrams in `public/images/roboshop-ai/roboshop-ai-{overview,ai-paths,checkout-events,observability}.svg`, generated by `docs/diagrams/roboshop-ai-microservices/build_diagrams.py` (stdlib only); matching editable Mermaid sources beside it. The overview is laid out at 560 px wide for phones.

**Commands**: Mermaid sources parsed and rendered with mermaid-cli 11.4.2; SVGs checked with `xmllint` and inspected in headless Chrome at full size and at a 358 px column; vitest 37 files / 361 tests pass (one editor-fidelity failure fixed by adding blank lines before lists). Lint, typecheck and build not run (content and static assets only).

**Manual steps**: review the `<Todo>`, add commentary, then set `status`/`publishedAt`. The two RabbitMQ reference URLs return 403 to scripted requests and were not fetch-verified.

## Tracing, logs, metrics and Grafana dashboards (2026-10-29, owner request)

**What changed**
- Tracing was already on (Jaeger lists `jithendar-com`); spans are now always recorded so request metrics can be derived from them.
- Metrics (`src/lib/metrics.ts`, no new dependency): per-route request rate/status/latency from Next.js server spans, process and event-loop metrics, email/comment counters, database gauges; served on cluster-internal port 9464.
- Logs: `event` slug, `errorType`/`errorCode`, `route` on request lines, matching the fields the cluster's Alloy pipeline keeps (it drops `msg`).
- Manifests (`k8s/` and `www/deploy/base`): metrics container port, NetworkPolicy rule for Prometheus only, headless Service, Role/RoleBinding for Alloy.
- `tools` repo (platform, synced by Argo CD): Alloy collects namespace `jithendar`; Prometheus job `jithendar-com` (DNS discovery) + 3 alerts; Grafana folder "Jithendar.com" with Overview and Logs dashboards; Loki trace-id links to Jaeger.
- Docs: `docs/OBSERVABILITY.md`.

**Commands**: lint pass; typecheck pass; vitest 37 files / 360 tests pass; production build pass; local `next start`: `/metrics` showed per-route counts after real requests; dashboard queries validated against live Prometheus/Loki (36/36 parse); kustomize renders + server dry-run for `k8s/`; Grafana chart rendered with new values.

**Manual steps**: deploy the site, then push `tools` (see docs/OBSERVABILITY.md → Rolling it out).

## Email provider choice: SMTP, Mailgun, Amazon SES (2026-10-29, owner request)

**What changed**
- Admin → Storage & email → Email: one selector (Disabled / SMTP / Mailgun / Amazon SES); only the selected provider's fields are shown and submitted; the others' settings are kept; no failover (`docs/EMAIL.md`).
- `src/lib/mail.ts`: versioned settings (old SES-only settings read as SES), per-provider validation with field errors, encrypted secrets never returned (empty field keeps the stored one), SES with the server's AWS credentials (SDK default chain) or stored keys incl. temporary keys + session token, Mailgun HTTP API (US/EU) without a new dependency, SMTP with TLS/STARTTLS only, reply-to, "configured" vs "tested", explicit test email to a typed address, secrets redacted from errors/logs/audit, `SMTP_URL` fallback only until an admin saves a choice (and only when it is a valid smtp(s) URL). All transactional email (verification, reset, contact) goes through it. System status reports the active provider without sending.
- Fixed during browser checks: React's automatic form reset after an action cleared typed values on validation errors and reset the provider select (next save turned email off); forms now submit without the reset. All missing-field errors are reported at once.

**Files**: `src/lib/mail.ts`, `src/lib/health.ts`, `src/app/admin/storage/{page,EmailSettings}.tsx`, `src/app/admin/storage/email-actions.ts`, `src/components/admin/ui.tsx`, `tests/mail.test.ts`, `docs/EMAIL.md`, `docs/DEPLOYMENT.md`, `.env.example`.

**Commands**: lint pass; typecheck pass; vitest 36 files / 355 tests pass; production build pass; browser checks (1440px, 390px) 10/10 pass.

**Manual steps**: choose and configure a provider in the admin, then Send test email. Provider-console and DNS steps: `docs/EMAIL.md`. No live provider was tested (no credentials).

## Sign-out, password toggles, discussions, social-login audit, article header (2026-10-29, owner request)

**What changed**
- Sign-out (`docs/AUTH.md`): one `signOutAndLeave()` for every control — server-side session deletion, private browser data cleared, full `replace()` to `/login?signedOut=1`. Mobile admin menu now has Sign out (the sidebar block is desktop-only). `SessionGuard` on admin/account layouts (bfcache reload, session ended elsewhere/expired → login). `no-store` on admin, admin API, comment API and login. Accurate "session expired" vs "not signed in". A race between the guard and sign-out (found in browser checks) is handled by `isSigningOut()`.
- `PasswordInput` with show/hide toggle on all password fields (login, sign-up, setup, admin secrets).
- Discussions (`docs/COMMENTS.md`): replies (2 visible levels), Markdown + preview with server-side sanitising, likes, reports, edit/delete, permalinks, sort + paging, moderation tabs/actions with audit, per-post open/locked/closed, approval and edit-window settings. Replaces `CommentForm`/old `approvedComments`.
- Article page: header spans the reading column plus the right column from `lg` (title 952px vs body 688px at 1440); standfirst stays at reading width; the cover image block is removed (cover still stored, edited, on cards, in Open Graph and Article JSON-LD). The now-unused "Cover image" Appearance toggle was removed (schema field kept).
- Social login audit: already complete (Google/GitHub, PKCE/state/nonce, lowest role, no implicit linking, explicit linking, error messages). No code changes; added tests for comment-anchor return URLs and off-site/protocol-relative refusal.
- Migration `0008_discussions.sql` (additive). New dev dependency `happy-dom@20.14.6` (DOM for the password toggle interaction tests only).

**Files**: `src/lib/{sign-out,comments,comment-markdown,comment-types,session,settings}.ts`, `src/components/{SessionGuard,AccountMenu,Comments,icons}.tsx`, `src/components/ui/PasswordInput.tsx`, `src/components/discussion/*`, `src/components/admin/{AdminNav,ui}.tsx`, `src/app/{account/SignOutButton,account/layout,account/settings/SessionControls,admin/layout,admin/comments/page,login/page,login/LoginForm,setup/SetupForm,admin/storage/page,admin/backups/page,admin/appearance/panels}.tsx`, `src/app/_actions/{comments,public}.ts`, `src/app/api/comments/[postId]/route.ts`, `src/lib/pages/article.tsx`, `src/lib/site-config/schema.ts`, `src/db/schema.ts`, `src/db/migrations/0008_discussions.sql`, `src/app/globals.css`, `next.config.ts`, tests `discussions`, `password-input`, `sign-out`, `social-auth` (+ sign-out/return URL cases), `article-route.test.tsx` (renamed from .ts; cover case), docs `AUTH.md`, `COMMENTS.md`.

**Commands**: lint pass; typecheck pass; vitest 35 files / 345 tests pass; production build pass; browser checks (Chrome, `next start`, 1440px and 390px) 45/45 pass.

**Manual steps**: OAuth clients still need creating (`docs/AUTH.md`); no other configuration. Review comment settings in Admin → Appearance → General → Features before publishing.

**Open**: no password-reset/change-password pages exist (reset emails point nowhere useful); social login not tested against real providers.

## Appearance & site settings (2026-10-29, owner request)

**What changed**
- Admin → Appearance & settings (`/admin/appearance`, admins only): General, Branding, Header, Navigation, Footer, Typography & colours, Homepage, Blog & articles, Media, SEO & integrations, Advanced, Revision history. Details and the full control list: `docs/APPEARANCE.md`.
- Typed, versioned `SiteConfig` (zod) with safe links, plain text, hex colours, bounded values, own-media images, contrast and navigation rules; legacy settings migrated; per-section fallbacks.
- Lifecycle: shared private draft with autosave and conflict detection → preview of the real pages (admin-only cookie token, no-store, noindex, phone/tablet/desktop) → atomic publish (transaction, revision, audit, cache bus) → history with restore; export/import of non-secret settings into the draft.
- Public site now reads the configuration: theme tokens/fonts via CSS variables, header (presets, inverse backgrounds, CTA, social, nested menus with keyboard submenus), dismissible announcement, footer, homepage section registry, listing/article presentation and page size, share links, date format/time zone, favicon/icons, configurable default share image.
- Maintenance mode in the proxy (503 + Retry-After, staff bypass, indexing untouched). Same-origin framing allowed for previews.
- Migration `0007_site_config.sql` (additive). No new dependencies. Old `/admin/settings` redirects.

**Files**: `src/lib/site-config/*`, `src/app/admin/appearance/*`, `src/app/api/admin/appearance/preview/route.ts`, `src/components/{SiteHeader,NavLinks,SiteFooter,Logo,AnnouncementBar,DismissAnnouncement,PreviewBanner,ShareLinks,CopyLink,ArticleList,CoverImage,TopicGrid}.tsx`, `src/components/sections/HomeSections.tsx`, `src/components/site/*`, `src/app/{layout,page,opengraph-image}.tsx`, `src/lib/{settings,dates,media}.ts`, `src/lib/pages/{article,listing,listings}.tsx|ts`, `src/lib/og/card.tsx`, `src/proxy.ts`, `next.config.ts`, `src/app/globals.css`, `src/db/schema.ts`, tests `site-config` (+ `indexing`, `seo-integrations`, `social-auth` adjusted), `docs/APPEARANCE.md`.

**Commands**: see the final report of this change (lint, typecheck, 32 test files, production build, browser flows and width audit).

**Manual steps**: none required; after deploying, review the draft in Admin → Appearance and publish when ready.

## Redesign + social sign-in, profiles and header account menu (2026-10-29, owner request)

**What changed**
- Design system (`docs/DESIGN_SYSTEM.md`): semantic colour tokens with one blue accent and a neutral grey scale, fluid type tokens, reading/page widths, radii, shadows, section rhythm; dark mode now follows the system *and* remembers an explicit choice (header toggle, footer System/Light/Dark) without a flash. Removed gradients, glass, grid backgrounds and the decorative hero mosaic; calmer category/type badges.
- Public pages: new header (accent underline for the current section, search, theme, account control far right; search/theme move into the mobile menu on phones), footer, homepage (text intro, one primary action, featured + recent, compact topics, projects only when published), article page (≈70-character column, TOC in the right margin ≥1280px, labelled code blocks, contained sources/corrections, separated ad slot), listings, static pages, author, search, 404 and a new runtime error page.
- Shared components: buttons/inputs/fields/alerts with sizes and states (16px inputs), pagination, tags, breadcrumbs, cards; ~40 files moved from duplicated light/dark class pairs to tokens.
- Admin: full-height sidebar shell, full-width header, accent current state, table/stat/header primitives, loading skeleton; editor action bar no longer slides under the sticky header; an expired session during save/autosave shows a message instead of navigating away (draft kept locally).
- Auth (`docs/AUTH.md`): Google + GitHub via Better Auth (PKCE, state, OIDC nonce, minimal scopes), buttons only when configured, readable callback errors, safe `next` handling, lowest role for every self-registration, no implicit account linking, explicit link/unlink with fresh-session rule and last-method protection, encrypted provider tokens, `/update-user` disabled.
- Accounts: `/account` (avatar, display name, bio, website, social links; server-validated allowlist) and `/account/settings` (email, sign-in methods, sign out / sign out everywhere); header account menu (keyboard, outside click, Escape, focus return, viewport-safe). Avatars re-encoded to 512px WebP without metadata, stored in R2 under `images/avatars/{user-id}/`, old uploads deleted on replace/remove. App rate limits for profile and avatar changes. `Cache-Control: private, no-store` on account and auth routes.
- Migration `0006_account_profile.sql` (additive, defaults). New direct dependency: `sharp@0.35.5` (already installed as Next's image engine; now declared because avatars use it directly).

**Files**: `src/app/globals.css`, `src/app/{layout,page,error,not-found}.tsx`, `src/app/account/**`, `src/app/login/**`, `src/app/admin/{layout,loading}.tsx`, admin pages (token pass), `src/app/media/avatars/[userId]/[file]/route.ts`, `src/components/{AccountMenu,UserAvatar,HideOnAdmin,SiteHeader,NavLinks,SiteFooter,Logo,Container,PageHeader,ArticleList,TopicGrid,CodeBlock,TableOfContents,Pagination,TagList,Breadcrumbs,AuthorCard,CoverImage,ContentTypeBadge,categoryStyle,icons}.tsx`, `src/components/theme/*`, `src/components/ui/form.tsx`, `src/components/admin/{ui,AdminNav}.tsx`, `src/lib/{auth,auth-providers,auth-errors,avatar,avatar-url,profile,rate-limit,safe-next,session,admin}.ts`, `src/lib/mdx/compile.ts`, `src/lib/pages/*.tsx`, `src/db/schema.ts`, `next.config.ts`, `deploy/base/networkpolicy.yaml` (comment only), `scripts/set-oauth-config.sh`, `.env.example`, `package.json`, tests `social-auth`, `account-helpers`, docs `AUTH.md`, `DESIGN_SYSTEM.md`.

**Commands**: see the final report of this change (lint, typecheck, 31 test files (278 tests), production build, browser checks at 320–1920px light/dark, account-menu keyboard flow, profile form, theme persistence).

**Manual steps**: create the Google and GitHub OAuth clients (`docs/AUTH.md`), `scripts/set-oauth-config.sh mk4`, restart; verify live sign-in and avatar upload with R2.

## Search engines, analytics, AdSense and the block editor (2026-10-29, owner request)

**What changed**
- SEO: SEO/social/noindex fields for posts and pages; image sitemap entries; noindex posts and pages left out of sitemaps; staging crawlable with `X-Robots-Tag: noindex` (was `Disallow: /`, which hides noindex); Google/Bing verification meta from runtime config; IndexNow with a Postgres job queue (retries, dedupe, never blocks publishing); HSTS and Permissions-Policy; `/search` rendered per request.
- GA4 (Consent Mode v2 defaults, manual de-duplicated page views, `article_engaged`, no PII, never on private routes) and AdSense (one tag, labelled reserved slot after articles, test mode outside production, `/ads.txt` verbatim, Google's certified CMP + "Privacy choices" link). Draft privacy and cookies pages bundled for owner review (not auto-published). Details: `docs/SEO_ANALYTICS_ADS.md`.
- Editor: visual block editor over canonical Markdown with protected shortcode blocks and a fidelity check, slash commands, searchable inserter, block move/duplicate/delete, code languages, figures/galleries, safe links; publish/schedule/update/unpublish; server autosave + recovery; optimistic concurrency; revisions with preview/restore; device previews; trash/restore/duplicate; posts and pages dashboards; media search/paging/drag-drop/paste, alt editing and usage warnings; server-side scheduler. Details: `docs/EDITOR.md`.
- Migration `0005_editor_seo.sql`: new columns (defaults keep existing behaviour), `revision` (baseline revision for all existing content), `autosave`, `job`. Additive only; rollback = deploy the previous image (it ignores the new columns/tables), but note it does not know about trash or scheduling: trashed posts would show again and scheduled posts would stay unpublished until rolled forward.
- Security: render-time filter for unsafe URL schemes (`lib/mdx/safe-urls.ts`), save-time link validation.

**Commands**: see the final report (lint, typecheck, 29 test files, build, HTTP checks, browser flows).

**Manual steps**: Search Console/Bing/GA4/AdSense/consent checklist in `docs/SEO_ANALYTICS_ADS.md`; `scripts/set-public-config.sh mk4`; review and publish the bundled privacy/cookies drafts (Admin → Pages); complete "Owner input needed" items.

## Responsive pages, R2 media, Gemini "Generate image" (2026-10-29, owner request)

**What changed**
- Media storage moved from S3 to Cloudflare R2 (S3 API): keys `jithendar/www/media/{type}/{yyyy}/{mm}/{id}.{ext}`; images, video, audio, PDF; presigned direct uploads with server-side verification (size, SHA-256, magic bytes); private files via 5-minute signed links; legacy S3 rows still served until migrated; resumable, verified, non-destructive S3 → R2 migration with dry run, manifest and rollback (Admin → Storage). Details: `docs/MEDIA.md`.
- "Generate image" beside the cover controls: Gemini Interactions API (model from `GEMINI_IMAGE_MODEL`), preview → Use as cover / Regenerate / Discard, alt text required, per-user hourly + concurrency and site-wide daily limits, timeout + cancel, temp storage with 1 h app cleanup and 1-day R2 lifecycle backstop; prompts never stored.
- Responsive: fixed page-level overflow on static pages (sidebar nav) and the contact form (Turnstile compact below 300 px); collapsible admin menu below `lg`; shared accessible dialog (full-screen on phones, focus trap, Escape); tables scroll in their own region; `::video`, `::audio`, `::embed` shortcodes in fixed-ratio frames; cover focal point; footer touch targets; `minmax(0,1fr)` grids.
- Image pipeline bounded: fixed widths/quality, 12 MB source cap, no redirects, 200 MB LRU disk cache; LCP images eager + high priority (Next 16 deprecates `priority`).
- Fixed: server-action uploads were capped at Next's 1 MB default (now 11 MB); local dev without `DATABASE_URL` crashed (PGlite bundled by Turbopack → now external).
- New dependency: `@aws-sdk/s3-request-presigner@3.1157.0` (Cloudflare's documented way to presign R2 URLs; same SDK version as `client-s3`). Gemini uses `fetch` (no SDK).

**Files**: `src/lib/{storage,storage-legacy,media,media-migration,gemini,image-generation,health,db-admin}.ts`, `src/lib/mdx/{shortcodes,tables,compile,html}.ts`, `src/app/media/[id]/[name]/route.ts`, `src/app/api/admin/{images,media-migration}/…`, `src/app/admin/{storage,media}/…`, `src/app/admin/_actions/shared.ts`, `src/components/admin/{Dialog,GenerateImageDialog,CoverImagePicker,MediaPicker,AdminNav}.tsx`, `src/components/{CoverImage,ContentImage,ContentMedia,Mdx,Turnstile,ContactForm,SiteFooter}.tsx`, `src/lib/pages/{article,page-view}.tsx`, `src/app/admin/layout.tsx`, `src/app/globals.css`, `src/db/{schema.ts,migrations/0004_r2_media.sql}`, `next.config.ts`, `deploy/base/{deployment,networkpolicy}.yaml`, `deploy/r2/{cors,lifecycle}.json`, `scripts/set-media-config.sh`, `.env.example`, `docs/{MEDIA,DEPLOYMENT}.md`, tests `media-storage`, `r2-config`, `image-generation`, `media-migration`, `responsive-content`.

**Commands**: see the final report of this change (lint, typecheck, tests, build, browser audit at 320–1920 px).

**Manual steps**: create the R2 bucket, token, CORS and lifecycle rules; `scripts/set-media-config.sh mk4`; choose `GEMINI_IMAGE_MODEL`; deploy; migrate legacy media if any (`docs/MEDIA.md`). Update the privacy policy to mention Gemini (editor-only) and YouTube/Vimeo embeds if used.

## CI deploys with kubectl, Argo CD removed (2026-10-27, owner request)

- **Why the live site did not change:** the owner ran `kubectl apply -k` from a checkout one commit behind `origin/master`. The local overlay pinned the old image (`dcdd3d7`), and CI had already pinned the new one (`d54da88`, `sha256:430f…`). The CI `deploy` job for that run was also waiting for an Argo CD app that had been deleted.
- **New deploy job:** loads `JITHENDAR_KUBECONFIG` (environment `production`), pins the digest built in the same run, then server dry-runs and applies `deploy/production`. It waits for `rollout status` (`rollout undo` on failure), waits for `/api/health` to report the commit, and runs the smoke test. The credential file is removed in an `always()` step.
- **CI identity:** `deploy/ci-access/rbac.yaml` (ServiceAccount, Role, RoleBinding; namespace `jithendar`; get/list/watch/create/update/patch on only the kinds in the overlay; read-only pods, events, replicasets; no delete; no Secrets). `scripts/ci-kubeconfig.sh` mints a 1-year token, refuses over-privileged or non-working credentials, and stores the GitHub secret.
- **Argo CD:** removed `argocd/jithendar-com.yaml` and its catalog entry, reverted the auto-sync exception in `scripts/argocd/validate.py`, updated `argocd/README.md`, and set `tests/test_argocd_catalog.py` to 25 apps. That test was already failing on `master` (26 expected, 25 present) after jithendar-com was commented out. During this change, a first edit accidentally commented out `jaeger.yaml`; caught by the validator count and fixed before reporting.
- **Checks:** actionlint, shellcheck, `validate.py` (25 apps, 79 resources), catalog tests 11 passed, RBAC server dry run passed.
- **Not done (blocked by the agent permission policy, owner to run):** `kubectl apply -f deploy/ci-access/rbac.yaml` and `scripts/ci-kubeconfig.sh mk4`. Until then the `deploy` job fails at "Load cluster credentials" with a clear message.

## Phases 3 + 4 — Transparency pages and content platform (2026-10-27, owner request: "implement complete website")

**Status:** complete locally. Not yet pushed; CI deploys on push. Phase 5 (n8n/OpenAI) and Phase 8 (monetisation scaffolding, observability) are not website features and were not started. Phase 7 (WordPress migration) is unnecessary; see AUD-008.

**Phase 3, transparency**
- `content/pages/`: about, contact, editorial-policy, corrections-policy, ai-use-policy, privacy-policy, terms. Rendered by `src/app/[page]`, editable as MDX, with `updatedAt` shown.
- Policies describe only the workflow that exists in this repo. Unverifiable facts (bio, contact email, legal entity, jurisdiction, log retention, licences, sponsorship rules, AI providers) are `<Todo>` blocks: visible in dev/preview, **render nothing in production**.
- Author profile: verified GitHub link (`github.com/mrjithendar`, name matches), bio TODO. "Open-source" wording avoided because the RoboShop AI repo has no licence.
- Article page: distinct badges for News / Analysis / Tutorial / Opinion / Curated summary / Project / Sponsored; byline → author page; published, updated, reading time; category link; sources; corrections log (links to the policy); curated and sponsored disclosures; tags.
- `docs/GOOGLE_NEWS_READINESS.md`.

**Phase 4, platform features**
- Category (`/category/<c>`), tag (`/tag/<t>`), collection and author listings with `/page/<n>` pagination (`/page/1` → 308 to base, out of range → 404). Taxonomy pages with < 3 items or no intro are `noindex, follow` and kept out of the sitemap; tag pages are always noindex. Category intros live in `src/config/taxonomy.ts`.
- Related reading: explicit `related` frontmatter first, then category (3) / related-category pair (1) / shared tag (2) scoring, deterministic tie-break, published only.
- Reading time; "On this page" TOC from h2/h3 (ids by rehype-slug, collected in the same compile); Shiki highlighting at render time (light/dark); copy button with an `aria-live` announcement.
- Search: `/search-index.json` (published only), lazy-loaded client search at `/search` (noindex).
- RSS 2.0: `/feed.xml` and `/category/<c>/feed.xml`, autodiscovery link in `<head>`.
- Broken-internal-link check (`src/lib/content/links.ts`), run by `npm test` against real content, so CI fails on a broken link.
- `npm run preview` (`CONTENT_PREVIEW=true`) shows `review` items locally with a badge; forced off when `APP_ENV=production` (tested).
- Site icon; redesigned header, footer (topics, policies, RSS) and homepage (news, articles, projects, topics, empty state).
- Two drafts for owner review, `status: review` (not public): `projects/roboshop-ai` (facts from the repo README only) and `blog/deploy-nextjs-kubernetes-argo-cd` (from this repo's real manifests and workflow).

**New dependencies:** `shiki` + `@shikijs/rehype` (build-time highlighting, no client JS), `rehype-slug` (heading ids), `hast-util-to-string` + `unist-util-visit` (TOC plugin; already transitive deps of MDX), `@types/hast`.

**Fixed along the way:** inline code was dark-on-dark in dark mode (typography plugin `lab()` fallback), now an explicit pill style; `/favicon.ico` 404 console error, now fixed with an icon; a `setState`-in-effect lint error in search, removed by dropping the `?q=` prefill.

**Commands run → result** (Node 26.8.2)
| Command | Result |
|---|---|
| `npm run lint` | Pass. 0 problems |
| `npm run typecheck` | Pass |
| `npm test` | Pass. 11 files, 88 tests |
| `APP_ENV=production npm run build` | Pass. No warnings |
| `kubectl kustomize deploy/production` | Pass |
| `shellcheck scripts/*.sh` | Pass |
| Production server + curl, fixture content | Pass. Status, single `<h1>`, canonical and robots correct on 19 routes; feeds valid; search index and sitemap published-only |
| Production server + curl, real content | Pass. 7 pages 200 and indexable; 0 `TODO(owner)` in HTML; review drafts 404 |
| Lighthouse 12.8.2, local `http://` | Home mobile 96/100/79/100 (perf/a11y/bp/seo), desktop 100/100/–/100; about mobile 96/100; blog 96–100 perf, a11y 100 (SEO 66 because the empty listing is noindex by design); article (staging preview) mobile 95, desktop 100, a11y 100 (SEO 66 because staging is noindex). Best-practices deductions are only HTTPS/HTTP2 audits from serving locally over http. Mobile LCP 2.7–2.9 s includes ~1.1 s of a local HTTPS-upgrade fallback; on HTTPS it would be about 1.6–1.8 s (estimate, not measured). These are lab scores, not field data |

**Open:** owner TODOs (see `GOOGLE_NEWS_READINESS.md`); AUD-018 (client-rendered 404 body on dynamic routes); no published content yet.

## Deployment to mk4 over HTTPS (2026-10-27, owner request; ahead of the Phase 6 plan)

**Status:** manifests, Dockerfile, CI and Argo app written and validated; ECR repo created. **Waiting on the owner to commit and push.**

**Update (owner request: "CI should build and deploy"):** CI now deploys end to end without cluster credentials. `publish` commits the image digest to `deploy/production`, Argo CD auto-syncs `jithendar-com` (no prune, no self-heal; allow-listed exception in `scripts/argocd/validate.py`), and `deploy` waits for `/api/health` to report the commit, then runs `scripts/smoke.sh`. This replaces the earlier one-off `kubectl apply` plan; the only manual cluster step is creating the Argo Application once. Checks: actionlint + shellcheck clean; `validate.py` 26 apps OK; catalog tests 11 passed; Argo app and digest-pinned overlay pass server dry run; site tests 67 passed.

**Changes**
- `src/app/api/health/route.ts` + test: probe endpoint.
- `Dockerfile`, `.dockerignore`: multi-stage, `node:26-alpine`, non-root UID 1000, standalone output.
- `deploy/base/*`, `deploy/production/*`: see `docs/DEPLOYMENT.md`.
- Outside the site folder (shared files): `argocd/jithendar-com.yaml`, an entry in `argocd/kustomization.yaml`, `.github/workflows/ci-jithendar-com.yml`.
- AWS: created ECR repository `jithendar-com` (immutable tags, scan on push, lifecycle keeps 30).

**Commands run → result**
| Command | Result |
|---|---|
| Read-only `kubectl get` on mk4 | Nodes arm64 ×4; `letsencrypt-prod` Ready; `/` unclaimed on jithendar.com; **Certificate `jithendar-com` missing** (AUD-003) |
| `kubectl kustomize deploy/production \| kubectl apply --dry-run=server` | Pass. All 11 objects accepted (incl. cert-manager and Traefik CRDs); nothing persisted |
| `python scripts/argocd/validate.py` | Pass. 26 Applications, 90 unique resources, no overlapping ownership |
| `pytest tests/test_argocd_catalog.py` | Pass. 11 tests |
| `npm run lint` / `typecheck` / `test` / `build` | Pass / pass / 66 tests pass / pass |
| `docker build` | **Not run.** No local Docker engine; owner chose GitHub Actions |
| Workflow run | **Not run.** Needs a push |

**Open**
- Whether the self-hosted runner's AWS identity can push to the new repository is unverified (it pushes `roboshop-*` today).
- `node:26-alpine` is pinned by tag, not digest (same as the RoboShop images).
- WordPress leftovers in `jithendar`: PVCs `wordpress-mysql` and `wordpress-wordpress`, and Secret `wordpress-credentials`. Untouched; delete only with owner approval.

## Phase 2 — Content model & SEO foundation (2026-10-27)

**Status:** complete. Not deployed (Phase 6). jithendar.com still returns 503.

**What changed**
- Scaffolded Next.js 16.4.3 (App Router, React 19.3, TS 5.9, Tailwind 4) with `output: "standalone"`. It has its own `package.json`, separate from the RoboShop root.
- Zod content schema, a loader that reports every error at once, and `getPublishedContent()` as the single read path. Collection ↔ contentType rules.
- Routes: `/`, `/blog`, `/news`, `/projects`, `/<collection>/<slug>`, `/authors/<slug>`, `/sitemap.xml`, `/news-sitemap.xml`, `/robots.txt`.
- Metadata: `%s | Jithendar.com` titles, per-page absolute canonicals (none at root level), Open Graph and Twitter cards, one `<h1>` per page (MDX `#` demoted to `<h2>`).
- Non-production: `noindex, nofollow` meta tag (build time, `APP_ENV`), `X-Robots-Tag` header and disallow-all `robots.txt` (request time, `APP_ENV` + host).
- JSON-LD builders (Person, Organization, WebSite, ProfilePage, NewsArticle/BlogPosting/CreativeWork, BreadcrumbList) with `<` escaping.
- `src/config/redirects.ts` (empty, one-hop tested) and `src/config/gone.ts`: 410 for the 21 hijacked WordPress URLs (AUD-002). The proxy does its own trailing-slash 308, so gone URLs answer 410 in one hop.
- Baseline headers: `nosniff`, `Referrer-Policy`, `X-Frame-Options: DENY`; `X-Powered-By` removed.

**New dependencies (justification)**
- `@mdx-js/mdx`: official MDX compiler, chosen over the less-maintained `next-mdx-remote`.
- `yaml`: frontmatter parser using the YAML 1.2 core schema, so timestamps stay strings with their offset. `gray-matter`/js-yaml would turn them into `Date` objects and lose the offset.
- `zod`: schema validation (required by the spec).
- Dev: `vitest` (TypeScript/TSX tests; the root's `node --test` would need extra tooling); `fast-xml-parser` (XML validity assertions); `@tailwindcss/typography` (article prose); `eslint-config-next`.
- `eslint` stays on 9.x (npm marks it deprecated). The plugins bundled with `eslint-config-next` 16.4.3 only accept ESLint ≤ 9. Revisit when they support 10.
- `typescript` 5.9.3 rather than the root's 7.0.2: `typescript-eslint` supports TS < 6.1 only.

**Files touched** (all under `sites/jithendar-com/`)
- Config: `package.json`, `package-lock.json`, `.nvmrc`, `.gitignore`, `.env.example`, `next.config.ts`, `tsconfig.json`, `postcss.config.mjs`, `eslint.config.mjs`, `vitest.config.ts`
- `src/config/{site,taxonomy,redirects,gone}.ts`, `src/proxy.ts`
- `src/lib/content/{schema,frontmatter,load,index}.ts`, `src/lib/seo/{canonical,jsonld,news-sitemap,sitemap,robots,xml}.ts`, `src/lib/dates.ts`, `src/lib/pages/{collection,article}.tsx`
- `src/components/{JsonLd,SiteHeader,SiteFooter,Mdx,ArticleList,Breadcrumbs}.tsx`
- `src/app/**` (layout, home, not-found, 3 collections × 2 routes, author, sitemap, news-sitemap, robots)
- `content/authors/jithendar-dharmapuri.mdx` (name only, `TODO(owner)` for the rest); empty `content/{blog,news,projects}/`
- `tests/*.test.ts` (8 files, 65 tests), `tests/fixtures/content/**` (9 articles covering every status and edge case)
- Docs: `README.md`, `docs/CONTENT_MODEL.md`; updated `AGENTS.md`, `docs/SEO_AUDIT.md`, `docs/IMPLEMENTATION_PLAN.md`

**Commands run → result** (Node 26.8.2)
| Command | Result |
|---|---|
| `npm install` | Pass. 505 packages. `unrs-resolver` postinstall not run (npm allowScripts); lint works without it |
| `npm run lint` | Pass. 0 problems |
| `npm run typecheck` (`next typegen && tsc --noEmit`) | Pass |
| `npm test` (vitest) | Pass. 8 files, 65 tests |
| `APP_ENV=production npm run build` | Pass. No warnings; standalone output holds `server.js`, `node_modules`, `content` only |
| Standalone server + curl, **fixture content** | Pass. Published article 200; draft/review/archived/future/wrong-collection 404; external canonical respected; single `<h1>`; JSON-LD dates match the page; sitemap excludes non-indexable URLs; news sitemap 48 h window (by real clock); 410s; 308 slash redirect relative, one hop; staging host → `X-Robots-Tag` + disallow-all robots |
| Standalone server + curl, **real content** | Pass. `/` 200 indexable; empty listings and author page `noindex, follow`; sitemap = homepage only; news sitemap valid and empty; CSS served; no server errors |
| Lighthouse | **Not run.** Phase 4 |
| Root `npm test` (RoboShop) | **Not run.** No RoboShop files changed |

**Note on the server check:** one intermediate run was answered by a stale server still bound to the port (`EADDRINUSE`). That run was discarded; results above come from fresh servers on the final builds.

**Open issues**
- Author bio, `jobTitle`, `sameAs` and the publication name: `TODO(owner)` (Phase 3).
- There is no published content yet, so the live site would be a homepage only. That's intentional: no fabricated posts.
- AUD-003 (shared TLS certificate) still unverified on the cluster.
- `www` → apex redirect must be recreated at ingress (Phase 6).

**Manual steps required (owner)**
1. Use Node 26: `export PATH=/opt/homebrew/bin:$PATH` (or reorder `PATH` in `~/.zshrc`).
2. Consider excluding `sites/jithendar-com/node_modules` and `.next` from Google Drive sync (AUD-016).
3. Phase 1 owner items 1, 2, 4 and 5 below are still open.

## Phase 1 — Audit & plan (2026-10-27)

**Status:** complete. Awaiting owner actions in IMPLEMENTATION_PLAN.md Phase 1.5.

**What changed**
- Stopped at first inspection: no Next.js repo existed, and the live site was a hijacked self-hosted WordPress. The owner removed WordPress (`argocd/wordpress.yaml` deleted, `argocd/kustomization.yaml` updated, both uncommitted) and confirmed its data is not needed.
- Created the site folder with standing rules and the audit/plan docs. No application code.

**Files touched**
- `sites/jithendar-com/AGENTS.md` — standing context and rules, adapted to verified state
- `sites/jithendar-com/docs/SEO_AUDIT.md` — findings AUD-001 to AUD-017
- `sites/jithendar-com/docs/IMPLEMENTATION_PLAN.md` — decisions D-1 to D-6, rescoped phases, risks
- `sites/jithendar-com/docs/PROGRESS.md` — this log

**Commands run → result**
| Command | Result |
|---|---|
| `curl` against public jithendar.com URLs (`/`, robots, sitemaps, feed, WP REST listings) | Ran. Evidence recorded in SEO_AUDIT.md |
| `openssl s_client` against jithendar.com:443 | Ran. Let's Encrypt cert for apex + www, valid until 2027-01-25 |
| `lint`, `typecheck`, `test`, `build` | **Not run.** No site code exists yet (Phase 2 scaffolds it) |
| Root `npm test` (RoboShop) | **Not run.** Out of scope; this phase changed no RoboShop code |
| `kubectl` against the cluster | **Not run.** AGENTS.md A3.3: agents do not touch the live cluster |

**Open issues:** AUD-002, AUD-003, AUD-004, AUD-005, AUD-007, AUD-010 to AUD-016.

**Manual steps required (owner)**
1. Check the shared TLS Certificate/Secret in namespace `jithendar` (AUD-003).
2. Check the workloads the hijacked pod could reach and rotate the credentials it could see (AUD-001).
3. Install Node ≥ 24 locally (AUD-015).
4. Confirm the publication name and host provider/spec (AUD-009).
5. Say whether an older WordPress.com export with real posts exists (AUD-008).
