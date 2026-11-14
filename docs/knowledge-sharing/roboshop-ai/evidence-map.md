# Evidence map

Component → source files → verified behaviour → article. Paths are relative to `roboshop-ai` at commit `c81e85a1fd9d3552c69d4490be17ccf61d29437b` unless they name `tools` or a live check. A1 to A4 are the articles in series order.

How each row was verified:

- **Code:** read directly at that commit.
- **Run:** executed in this review with pinned dependencies.
- **Live:** read-only check against the EKS cluster or public site on 2026-11-01.
- **Doc:** taken from a repository document, not independently confirmed.

## Application

| Component | Source | Verified behaviour | How | Article |
| --- | --- | --- | --- | --- |
| Routing to services | `services/web/nginx/snippets/routes.conf` | `/api/*` to gateway, `/moks/*` to moks, `/api/chat` is 403, `/metrics` is 404 | Code | A1, A2 |
| Ingress | `tools/deploy/eks/manifests/ingress/roboshop-virtualservice.yaml` | `/roboshop/` prefix stripped; no public route to `mcp-server` | Code | A1, A3 |
| Catalogue read | `services/ai-gateway/server.py` `Gateway.products`, `services/catalogue-service/routes.mjs` | Gateway overlays ledger stock on catalogue data | Code | A1 |
| Cart write | `services/ai-gateway/store.py` `update`, `sync_cart`; `services/cart-service/server.py` `REPLACE` | Absolute quantity; stock and pending-payment checks; Lua revision check; ledger re-seeds Redis | Code | A1 |
| Guest cart | `store.py` `session`; `server.py` `Gateway.session` | Cookie `rs_session`, 604800 s; guest cart moves to account | Code | A1 |
| Authentication | `services/user-service/accounts.py`, `server.py`; `services/ai-gateway/user_client.py` | scrypt, stored SHA-256 digest, 8 h, cookie `rs_auth`, fails closed | Code | A1, A2 |
| Roles | `services/ai-gateway/auth.py` `require_role` | customer, admin, superadmin | Code | A1 |
| Checkout | `server.py` `checkout`, `reconcile`; `services/ai-gateway/README.md` state table | `creating`, `payment_review`, `payment_pending`, `paid` | Code, Doc | A1 |
| Verification | `server.py` `/api/payments/verify`; `services/payment-service/README.md` | HMAC plus capture fetch | Code, Doc | A1 |
| Order events | `services/ai-gateway/events.py` `OrderPublisher` | Quorum queues, publisher confirms, 2 s retry loop, `order.paid`, `order.test-paid` | Code | A1 |
| Shipping consumer | `services/shipping-service/.../OrderEvents.java` | Consumes `roboshop.shipping.orders`, `order.paid` only | Code | A1 |
| Kafka copy | `services/kafka-bridge/README.md`, `events.py` | Separate queue, not on checkout path | Code, Doc | A1 |
| Ledger | `services/ai-gateway/lifecycle.py`, `store.py`, `ai-gateway-deployment.yaml` | JSON default, `replicas: 1`, `Recreate`; `COMMERCE_BACKEND` absent from EKS config | Code | A1, A2 |
| Redis config | `argocd-eks/apps/roboshop/roboshop-config-configmap.yaml` | `allkeys-lru`, no persistence | Code | A1 |
| Readiness | `services/ai-gateway/readiness.py` | MongoDB, catalogue, users, ledger, cart; no AI | Code, Live | A1, A2 |

## AI gateway

| Component | Source | Verified behaviour | How | Article |
| --- | --- | --- | --- | --- |
| No model SDK | `services/ai-gateway/requirements.txt` | fastapi, uvicorn, pymongo, pika, dnspython, psycopg, Pillow | Code | A2 |
| Transport | `asgi_app.py` `dispatch` | 64 KiB, 10 s body, 8 slots, 23 s deadline, error mapping, `X-Request-ID` | Code | A2 |
| Chat route | `server.py` `/api/chat` | Order of checks; 2 `chat_slots`; 18 s; 429 versus 503; stock re-applied; turn saved | Code | A2, A4 |
| Contracts | `api_models.py` | `extra='forbid'`, strict, 1 to 1000 chars | Code | A2 |
| LLM config | `llm.py`, `lib/llm_config.py` | Compare-and-set revision, audit, field allowlist, IP-literal Ollama, failover shape | Code | A2 |
| Rate limit | `server.py` `limit`, `client_address.py`, `ai-gateway-deployment.yaml` | 300 and 10 per minute per peer. `TRUST_PROXY=true`, `TRUSTED_PROXY_CIDRS` unset in repo, tools and manifests | Code | A2 |
| Retries | `lib/runtime.py` `_retry_read` | One retry, reads only, transient only | Code | A2 |
| Logging | `lib/runtime.py` `log_event`, `LOG_FIELDS` | Field allowlist; HMAC identity with `TELEMETRY_ID_KEY` | Code | A2 |
| Streaming | `services/ai-gateway/README.md`, `moks/ollama_provider.py`, `moks/bedrock_provider.py` | None. `stream: False`, `converse` | Code | A2, A4 |

## MCP server

| Component | Source | Verified behaviour | How | Article |
| --- | --- | --- | --- | --- |
| Versions | `services/mcp-server/requirements.txt` | fastmcp 4.1.3, mcp 2.3.0 | Run | A3 |
| Protocol revision | `demo` client against real server | Client negotiated `2026-07-28` | Run | A3 |
| Tool catalogue | `gateway_tools.py` `TOOLS` | 15 specs; 8, 9 or 11 by role; 4 admin writes off | Code, Run | A3 |
| Resources and prompts | Client calls | `list_resources`, `list_resource_templates`, `list_prompts` all empty | Run | A3 |
| Transport guards | `server.py` `http_options`; `otel_bridge.py` `HTTPTracing` | 401, 401, 421, 403, 413 observed | Run | A3 |
| Validation | `gateway_tools.py` `validate`; `server.py` `GatewayTool.run` | `"2"` refused for an integer | Run | A3 |
| Error shape | `server.py` `_error` | `not_found` structure observed | Run | A3 |
| Session forwarding | `server.py` `ShopSessionVerifier`; `gateway_client.py` | No cache; only allowed headers | Code | A3 |
| Confirmation | `confirmation.py` | HMAC state, digest, 120 s, nonce, per-process store | Code | A3 |
| Search path | `gateway_tools.py` `_search_request`; `catalogue-service/routes.mjs` | `strategy: catalogue-keyword-ranking` | Code | A3 |
| Tests and demo | `services/mcp-server/tests`, `demo/demo.py` | 20 passed; demo output as described | Run | A3 |
| Deployment | `mcp-server-deployment.yaml`, `mcp-server-network-policy.yaml`, `argocd-eks/apps/mesh` | 1 replica, hardening, policy present, no `mcp-client` label on a workload, no inbound AuthorizationPolicy | Code, Live | A3 |

## Shopping agent

| Component | Source | Verified behaviour | How | Article |
| --- | --- | --- | --- | --- |
| Graph | `services/moks/agent.py` | Three nodes, linear, no conditional edges, `recursion_limit: 8` | Code, Run | A4 |
| Prompt | `agent.py` `INSTRUCTIONS` | Version `moks-instructions-2` | Code | A4 |
| No tools | `bedrock_provider.py`, `ollama_provider.py`, `widget.js` | No `toolConfig`, no tools field, no cart calls | Code | A4 |
| Retrieval | `lib/catalogue.py` | Keyword rules, hard filters, `notStated` | Code, Run | A4 |
| Follow-ups | `conversation.py`, `agent.py` `refine` | Deterministic references and refinement | Code, Run | A4 |
| History | `services/ai-gateway/chat_history.py` | 40 kept, last 2 sent, 1000 chars | Code | A4 |
| Card validation | `agent.py` `select_cards` | Invented SKU dropped | Run | A4 |
| Routing | `routing.py` | Guard before attempts; eligible codes; one fallback; breaker 3 failures, 30 s | Code | A2, A4 |
| Provider limits | `providers.py`, `deadlines.py`, `server.py` | 600 tokens, 16 s, 12 s, 2 slots | Code | A2, A4 |
| Privacy | `generation_telemetry.py`, `lib/runtime.py` | Content capture only for `synthetic-only` plus evaluation traffic | Code | A4 |
| Conversation trace | `services/moks` with stub provider, public catalogue | Table in A4 | Run, with stub model | A4 |
| Tests | `services/moks/tests` | 65 passed | Run | A4 |

## Live state, 2026-11-01

| Check | Result |
| --- | --- |
| `kubectl get deploy,sts -n roboshop-ai` on `roboshop-demo` | 14 workloads, all ready, no `moks` |
| `GET /roboshop/moks/widget.js`, `/moks/available` | 502 from NGINX |
| `GET /roboshop/`, `/roboshop/ready` | 200, all dependencies ready |
| `GET /roboshop/api/status` | `assistantMode: ai` |
| `GET /roboshop/api/products` | 32 products, all `collection: demo`, INR, `sale` |
| PeerAuthentication | `PERMISSIVE` |
| AuthorizationPolicies | 14 applied; `istio.io/dry-run` set in `apps/mesh/kustomization.yaml` |
| Pod containers | All 14 pods have `istio-proxy` |
| NetworkPolicies | `kafka-internal`, `mcp-server-clients` |
| Argo CD | `roboshop-demo-*` commerce apps Synced and Healthy; no `roboshop-demo-moks` Application |

## Documentation that conflicts with code

The articles use verified behaviour in every case.

| Document says | Verified behaviour | Handling |
| --- | --- | --- |
| Moks README: "It reads the catalogue snapshot through the gateway" | `moks/server.py` fetches `CATALOGUE_URL` directly. The MCP README describes it correctly | A1 and A4 use the code |
| Moks README: fallback "each attempt is capped at six seconds" | Six applies with failover on, otherwise 12 (`routing.py`) | A2 and A4 give both |
| `llm-providers.md`: "Please connect an LLM to get AI recommendations." | Gateway returns "Please connect an LLM to get results." The Moks copy of `llm_config.py` still has the older text | A2 and A4 use the gateway text |
| `argocd-eks/README.md`: sidecar turned off for data services | All 14 pods have `istio-proxy`, and the mesh comment says data stores included | Figure 5 uses live state |
| Root README and existing site article: twenty robots | Live API returns 32 demo products | A4 says 32, dated |
| Root README: `evaluation*/` directories | None exist at this commit | A4 says so |
| `tests/load/VERIFICATION.md`: "Agent evaluations: 6 passed" (2026-10-23) | Source not found in the current tree | A4 flags it as unconfirmed |
| Root and service READMEs link to `tools/.../roboshop/...` | `tools` has no `roboshop/` directory now. Content moved to `tools/deploy` and `docs/` | Articles do not use those links |
| MCP README deployment section: `argocd/mcp-server.yaml`, `scripts/deploy/deploy-minikube.sh` | Application is `argocd-eks/mcp-server.yaml`; imperative scripts retired | A3 omits those commands |
| Gateway README: "Port 3000 serves the storefront" | On EKS `web` serves it. `static` runs only if `FRONTEND_DIST` is set | A1 uses `web` |

## External sources checked

| Topic | Source | Result |
| --- | --- | --- |
| MCP 2026-07-28 | [Key changes](https://modelcontextprotocol.io/specification/2026-07-28/changelog) | Stateless, `initialize` removed, Multi Round-Trip Requests |
| MCP authorization | [Authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization) | Optional; "MUST NOT accept or transit any other tokens" |
| Streamable HTTP | [Transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http) | JSON or SSE per request; Origin validation required |
| FastMCP | [HTTP deployment](https://gofastmcp.com/deployment/http) | `stateless_http`, `host_origin_protection`, `allowed_hosts`. The page does not mention `json_response` |
| LangGraph | [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) | Nodes, edges, `recursion_limit` default 10,007 since 1.1.4 |
| Bedrock | [Converse](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html) | `guardrail_intervened`, `content_filtered`, usage fields |
| Ollama | [API](https://github.com/ollama/ollama/blob/main/docs/api.md) | `stream` defaults to true; `prompt_eval_count`, `eval_count` |
| EKS NetworkPolicy | [AWS docs](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html) | Requires VPC CNI support; enforcement on this cluster not confirmed |
