# Evidence table: FastAPI and FastMCP

Checked 2026-11-01. Paths are relative to each repository.

| Repository | Commit | Note |
| --- | --- | --- |
| `roboshop-ai` | `c81e85a` | On `origin/master`; clean working tree |
| `moks` | `ab99cf7` | On `origin/master`. Tested from a clean export, because the working tree has 4 uncommitted files (`api/admin.py`, `api/finops.py`, `tools/phase2.py`, `Insights.tsx`) |
| `tools` | `fa11817` | Searched only: documentation mentions, no code uses either package |
| `jithendar.com` | `98df2f3` | Searched only: Next.js, no Python service |

## Verified use

| Project | Component | Framework/package | Source files | Verified purpose |
| --- | --- | --- | --- | --- |
| RoboShop AI | `ai-gateway` | `fastapi==0.159.1`, `uvicorn==0.54.0` | `services/ai-gateway/requirements.txt`, `asgi_app.py`, `server.py` (entry point), `api_models.py`, `lifecycle.py`, `readiness.py`, `tests/test_fastapi.py` | ASGI shell and lifespan around `Gateway.handle`. Five registered routes, all pointing at `dispatch`; four paths in OpenAPI |
| RoboShop AI | `mcp-server` | `fastmcp==4.1.3`, `mcp==2.3.0`, `mcp-types==2.3.0`, `uvicorn==0.54.0`. Import is `from fastmcp import FastMCP`, the standalone package | `services/mcp-server/requirements.txt`, `server.py`, `gateway_tools.py`, `gateway_client.py`, `confirmation.py`, `otel_bridge.py`, `tests/test_fastmcp.py`, `demo/demo.py` | MCP server for external clients. 15 tools defined, 11 registered by default. stdio and stateless Streamable HTTP. Tools only |
| MOKS | `moks-api` | `fastapi==0.162.0`, `uvicorn[standard]==0.54.0`, `pydantic==2.14.2` | `backend/requirements.txt`, `backend/moks/main.py`, `backend/moks/cli.py`, `backend/moks/api/*.py`, `backend/moks/auth/deps.py`, `backend/moks/db.py`, `backend/tests/test_routing_auth.py` | Portal API, auth, SSE, SPA hosting. 20 routers, 142 paths, 161 operations |
| MOKS | `moks-terminal` | Same as above, `WebSocket` | `backend/moks/terminal/app.py`, `backend/moks/terminal/api.py`, `deploy/helm/moks/templates/terminal.yaml`, `values.yaml` (`terminal.enabled: false`) | Optional terminal gateway, separate process, no OpenAPI endpoints |

## Checked and excluded

| Project | Component | What it uses | Evidence |
| --- | --- | --- | --- |
| RoboShop AI | `moks` shopping assistant | Waitress (WSGI), LangGraph. Neither package, and no MCP | `services/moks/requirements.txt`, `server.py:105-110`, `services/mcp-server/README.md` |
| RoboShop AI | `cart-service`, `user-service`, `kafka-bridge` | Python without either package | No matches in imports or requirements |
| RoboShop AI | `catalogue-service`, `payment-service` | Node.js | `package.json` |
| RoboShop AI | `currency-service` | Go | `go.mod` |
| RoboShop AI | `shipping-service` | Java | Published service table; not re-read |
| RoboShop AI | Any in-cluster MCP client | None. Only the NetworkPolicy file contains the `roboshop.ai/mcp-client` label | `git grep` across YAML |
| MOKS | Any MCP component | None. `git grep -i '\bmcp\b|fastmcp'` over the repository returned nothing. Importing the app loads neither `fastmcp` nor `mcp` | Search and import probe |
| MOKS | Tool layer | In-process Pydantic tools behind `ToolExecutor` | `backend/moks/tools/contracts.py`, `executor.py` |
| Next.js site | Whole project | TypeScript | `www/package.json` |

## Package relationship

| Fact | Evidence |
| --- | --- |
| `fastmcp` 4.1.3 depends on `fastmcp-slim`, which requires `mcp>=2.2.0,<3.0.0` | Installed package metadata |
| `mcp/server/fastmcp.py` exists in SDK 2.3.0, but importing it raises `ModuleNotFoundError` naming `MCPServer` | Import in a scratch environment. `find_spec` alone reports it as present, so do not rely on it |
| FastAPI is absent from the `mcp-server` environment | `importlib` check |
| Client and server negotiated protocol `2026-07-28` | `client.protocol_version` against the real server |

## Behaviour observed

Probes used the real ASGI apps at the pinned versions, with a synthetic or mocked backend. Nothing here came from a live deployment.

| Probe | Result |
| --- | --- |
| Tools over HTTP as customer, admin, superadmin | 8, 9, 11 |
| Tools over stdio, default | 11, unfiltered |
| `update_cart` with `quantity: "2"` | `isError`, `invalid_argument`; gateway saw `/api/auth/me` only |
| `update_cart` with an extra field | Same |
| `update_cart` with unknown SKU | `not_found`, `detail: Product not found.`, `retryable: false` |
| Hidden tool as customer over HTTP | `Unknown tool: 'admin_list_users'` |
| `/mcp` with no bearer; unknown Host | 401; 421 |
| Gateway `POST /api/chat`, bad body, no service token | 403, for all four bad bodies tried |
| Gateway `POST /api/chat`, bad body, service token | 400, generic message. Never 422 |
| Gateway `/docs`, `/redoc`, `/openapi.json` | 200 at the app. NGINX `routes.conf` proxies only `/api/` |
| MOKS `POST /moks/api/investigations`, bad body, no session | 401: the auth dependency raises before body errors are returned |
| Same, with `get_auth` and `get_db` overridden | 422 listing `question` and `namespace` |
| `CreateIn(question="x", namespace="BAD!")` | Two validation errors |

## Test runs

Python 3.11.9, pinned requirements, in a scratch folder. The images use Python 3.14 (RoboShop) and 3.12 (MOKS), so these are not image runs.

| Suite | Result | Note |
| --- | --- | --- |
| `mcp-server` | 20 passed | Also runs during the image build |
| `ai-gateway` | 35 passed, 6 errors, of 41 | All 6 are in `test_admin_console` setup: `BulkWriteError` under `mongomock` 4.3.0, which is not pinned. `test_fastapi`, `test_chat_history` and `test_user_service_contract` passed, 28 tests |
| MOKS backend | 835 passed, 3 failed, 4 skipped | Temporary PostgreSQL 17. Failures are all in `test_helm_render.py`: `test_terminals_are_off_by_default`, `test_a_tag_or_no_profile_is_refused`, `test_the_terminal_namespace_is_restricted_and_closed_by_default` |
| Site `npm test` and lint | 401 passed, lint clean | With the new article in place |

## Website pages reviewed

Live, 2026-11-01: `/projects`, `/projects/moks`, `/projects/roboshop-ai`, `/blog`, `/blog/roboshop-ai-mcp-server`, `/blog/roboshop-ai-gateway`. Local MDX for the rest was searched.
