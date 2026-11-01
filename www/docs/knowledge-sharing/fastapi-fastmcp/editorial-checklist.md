# Editorial checklist

For the author, before publishing `content/blog/fastapi-and-fastmcp-ai-projects.mdx`. Nothing has been published, committed or pushed. The article has `status: review`.

## Where the code differs from the brief

| Brief assumed | Code shows | Effect |
| --- | --- | --- |
| Projects might use both packages together | No service uses both | The first paragraph says so |
| The MOKS SRE agent might use MCP | It has no MCP code | The article explains why it does not need it |
| The shopping agent might be an MCP client | It uses neither package and runs on Waitress | Listed as excluded, not treated as a project |
| FastAPI request validation throughout | True in MOKS. The gateway's `ChatRequest` is never applied by FastAPI | The article covers both |
| Tools use the FastMCP decorator | Hand-written `ToolSpec` plus a `Tool` subclass | The article says so |
| Resources and prompts | Not implemented | One sentence |

## Decisions and checks for you

- [ ] **"Why I chose them."** The repositories record no reasons. I wrote about what the design gives you, not your motives. Add your reasons where you want them.
- [ ] **Personal voice.** I removed anything that implied a personal reaction. The one past event, the sign-in 401, comes from a test docstring that says "observed live". Keep it only if you recall it that way.
- [ ] **Live state.** The article describes commits and manifests. I did not check whether `mcp-server`, `moks-api` or `moks-terminal` are running today.
- [ ] **`moks-terminal`.** `docs/LIMITATIONS.md` says the image was never built, and I quote that. My notes from 31 Oct say the gateway later ran on mk4, so that document may be out of date. Update the doc or the sentence.
- [ ] **SSE through the ingress.** Same document, same question: confirm it, then drop the caveat.
- [ ] **Three failing Helm tests in MOKS.** The article reports them. They concern terminal defaults, not FastAPI. Decide whether to fix them first.
- [ ] **Six gateway test errors.** They look like a `mongomock` fixture problem with an unpinned test dependency. Not diagnosed further. The service has no pinned test requirements.
- [ ] **Tracing on EKS.** `argocd-eks/apps/roboshop/roboshop-config-configmap.yaml` sets `OTEL_SDK_DISABLED: "true"` but `argocd-eks/apps/config/roboshop.env` says `false`. The article follows the ConfigMap. Confirm which one is applied.
- [ ] **Internal link.** `/blog/langchain-vs-langgraph-sre-agent-moks` is live, but its local MDX is still `status: draft`. The link works only because the live post is in the database.
- [ ] **Open each `.drawio` file once in draw.io.** See "Diagram exports" in `README.md`.

## Discrepancies in published pages

None of these were changed. Live pages are in the database, so edit them in the admin editor.

| Page | Says | Code shows | Suggested fix |
| --- | --- | --- | --- |
| `/projects/roboshop-ai`, `/blog/roboshop-ai-microservices-architecture` | `mcp-server`: "Diagnostics and Model Context Protocol tools" | Shopping and admin tools. `service_health` is the only diagnostic | "Shopping and admin tools over MCP" |
| `/blog/roboshop-ai-microservices-architecture` | "exposes 15 tools" | 15 defined, 11 registered by default, 8 for a customer | State the default |
| `/blog/roboshop-ai-gateway` | "FastAPI supplies the server" | Uvicorn is the server. FastAPI supplies the app, OpenAPI and middleware integration | Name Uvicorn |
| `/blog/roboshop-ai-gateway` | Implies the OpenAPI document describes the gateway | It has four paths, and `/docs` is on by default at the app | Add both facts |
| `/blog/roboshop-ai-mcp-server` | Input is checked "in addition to FastMCP's own" | The rejection I observed came from the service's validator. I could not confirm a FastMCP check ran first for this `Tool` subclass | Soften or test |
| `tools` `deploy/minikube/observability/opentelemetry/README.md` | "gateway FastAPI 0.156.3" | Pin is 0.159.1 | Update |
| Local `content/**/*.mdx` | `status: review` | Same slugs are live | Known drift, see `docs/CONTENT_AUDIT.md` |

Also noticed, outside this brief: `/projects/roboshop-ai` lists `frontend` and `nginx`, and the repository has one `services/web`.

## Findings that may be bugs

From reading code. None changed.

1. The gateway serves `/docs`, `/redoc` and `/openapi.json` with no setting to turn them off. Reachable in-cluster or by port-forward. NGINX does not route them.
2. `MCP_CONFIRMATION_KEY` is set in no manifest. It would be random per process, which matters only if admin writes are enabled.
3. The specification says servers must sanitize tool outputs. Product text reaches clients unmodified.
4. `mcp-server` has no inbound mesh AuthorizationPolicy, and NetworkPolicy enforcement on EKS is unconfirmed. Both were already raised in `../roboshop-ai/editorial-review.md`.

## Verification done

- `verify_article.py`: all 10 Python excerpts are verbatim runs of lines at the pinned commits, and every figure has an SVG, alt text and a parsing `.drawio` file.
- `xmllint` passed on every `.drawio` and SVG file. Each PNG was inspected by eye.
- `npm test` and `npm run lint` ran with the article present.
- **Not run:** `npm run typecheck` and `npm run build`, because no TypeScript changed. The service images were not built.
