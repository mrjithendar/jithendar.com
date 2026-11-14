# Verification note: langchain-vs-langgraph-sre-agent-moks

Checked 2026-11-01 against `mrjithendar/moks` commit `9c150e9` (`origin/master`). `backend/moks` had no uncommitted changes at that point.

## Dependency versions (installed from `backend/requirements.txt`, Python 3.11)

`langchain-core` 1.7.3, `langgraph` 1.2.19, `anthropic` 2.3.0, `pydantic` 2.14.2. Transitive: `langgraph-checkpoint` 4.3.1, `langgraph-prebuilt` 1.1.1, `langgraph-sdk` 0.4.11, `langsmith` 0.14.16, `langchain-protocol` 0.0.20. The `langchain` package is not installed (`import langchain` raises `ModuleNotFoundError`).

## Files inspected

- Graph and engine: `orchestrator/{graph,engine,prompts,report,worker}.py`
- Adapters: `llm/{lc,budget,providers}.py`, `tools/{lc,contracts,executor,builtin,phase2}.py`
- Entry and conversation: `api/investigations.py`, `conversations.py`, `scope.py`, `redaction.py`, `config.py`, `models.py`
- Skills and RAG: `skills/__init__.py`, `skills/builtin/crashloop-triage/SKILL.md`, `rag/service.py`
- Tests and data: `tests/test_investigation_graph.py`, `tests/conftest.py`, `evals/{fixture,runner}.py`, `evals/datasets/lab.yaml`, `lab/02-crashloop-config.yaml`
- Deployment: `deploy/helm/moks/{values,values-eks,values-minikube}.yaml`, `templates/{rbac,worker}.yaml`
- Docs: `ARCHITECTURE`, `LIMITATIONS`, `SECURITY`, `TESTING`
- Site: `docs/CONTENT_MODEL.md`, `src/lib/mdx/`, `tests/links.test.ts`, `content/blog/moks-rag-and-skills-design.mdx`

## What was run

| Check | Result |
| --- | --- |
| `tests/test_investigation_graph.py` | 13 passed |
| Full backend suite from a clean export of HEAD (PostgreSQL 17) | 832 passed, 3 failed, 4 skipped |
| The 3 backend failures | All in `tests/test_helm_render.py` (terminal chart). Not related to the investigation code. Not investigated further; that test file also has uncommitted edits |
| Trace runs (`article_trace_test.py`, output in `trace-summary.txt`) | 5 runs, real code, fixture cluster, scripted model |
| LangSmith env test, `StructuredTool` argument probes, `bind_tools`, recursion limit | Run against the pinned packages |
| Site `vitest` | 3 failed, 392 passed. The same 3 fail with this article removed. A fourth, a 30 s timeout in `article-route`, appeared once and passes alone |
| This article | Schema, links and editor round trip pass; compiled and rendered through `compileMdx` |
| Site lint, typecheck, build | Not run (content and static assets only) |

Framework claims come from the official pages in the article's `sources`. Those pages are not versioned, so anything version-sensitive was checked in the pinned packages. The recursion-limit default of 10,007 matches both the docs and the 1.2.19 source.

## Unresolved questions

1. Has a chat model answered a live request? `LIMITATIONS.md` says no, and it was last updated before commit `9c150e9` added Bedrock permissions. The live cluster and database were not queried, so the walkthrough stays labelled as scripted.
2. Is the LangChain docs' `create_agent` able to express the MOKS flow with middleware? Not tested. The article says so.
3. The article's "Gaps today" lists code issues found while writing (`self` argument, dropped `config` and `run_manager`, `Investigation.mode` never written). No MOKS code was changed.
4. Docs drift, not corrected: `LIMITATIONS.md` says 50 skills (51 exist), `ARCHITECTURE.md` says 17 tools (45 exist) and 16 tool calls (the chart sets 24). `moks-rag-and-skills-design.mdx` also says 16.
5. `graph.py`'s docstring says a stopped investigation is "taken over" by the reaper. `reap_stale` marks it failed.
