# Verification note: moks-rag-and-skills-design (2026-11-01 update)

Checked against `mrjithendar/moks` commit `9c150e9` (`master`). `backend/moks` and the docs read here had no uncommitted changes. This updates the live post in place: URL and slug are unchanged, and `status` stays `review`.

## Files inspected

- RAG: `rag/{service,ingest,chunking,backends,access,secrets}.py`, `api/knowledge.py`, `tools/phase2.py` (`kb_search`), `models.py`, `migrations/versions/0002_phases_2_4.py`, `jobs.py`, `orchestrator/worker.py`, `redaction.py`, `connectors/git.py`
- Skills: `skills/{__init__,registry,validate,readiness}.py`, `skills/builtin/crashloop-triage/SKILL.md`, all 51 skill files (by script)
- Runtime: `orchestrator/{engine,graph,prompts,report}.py`, `tools/{executor,contracts,builtin}.py`, `diagnosis/{detectors,logs,config_audit}.py`, `connectors/kubernetes.py`, `actions/service.py`
- Evaluation: `evals/{gates,runner,fixture}.py`, `evals/datasets/{rag,skills,lab}.yaml`, test names in `tests/test_{rag,rag_governance,rag_index,skills,skill_registry,eval_gates}.py`
- Deployment: `deploy/helm/moks/{values,values-eks,values-minikube}.yaml`
- Docs, treated as claims: `KNOWLEDGE`, `SKILLS`, `LIMITATIONS`, `SECURITY`, `TESTING`
- Site: `docs/CONTENT_MODEL.md`, `docs/CONTENT_AUDIT.md`, `src/lib/content/schema.ts`, the live page at `/blog/moks-rag-and-skills-design`

## Versions

Installed from `backend/requirements.txt` on Python 3.11: `langgraph` 1.2.19, `langchain-core` 1.7.3, `pydantic` 2.14.2, `fastapi` 0.162.0, `SQLAlchemy` 2.1.6, `anthropic` 2.3.0. PostgreSQL 17.11 locally, matching the chart's `postgres:17.11-alpine`. Chart references, not run: `pgvector/pgvector:0.8.7-pg17`, OpenSearch 3.9.0, Pinecone API `2026-07`. Site: Next 16.4.3, Node 26.8.2, mermaid-cli 11.4.2.

## Checks

| Check | Result |
| --- | --- |
| Backend suite, clean export of the whole repository at HEAD | 835 passed, 3 failed, 4 skipped |
| The 3 failures | All in `tests/test_helm_render.py` (web terminal chart). Not related to RAG or skills. Not investigated further |
| First run, exporting only `backend/` without PostgreSQL tools on PATH | 42 failed. Caused by that setup (missing `deploy/` files, no `pg_dump`). Superseded by the run above |
| `article_trace_test.py`: rules, no-knowledge, scripted-model, probes, gates, lab | 6 passed. Output in `trace-summary.txt` and `trace-probes.txt` |
| RAG gates | All pass, keyword mode, 11 synthetic documents |
| Skills gates | All pass, 51 skills, 9 declared cases |
| Lab dataset, rules mode | 1.0 on 6 cases |
| Site `vitest` | 395 of 395 passed |
| Article compiled and rendered through `compileMdx` | Passed, no raw directives left |
| Mermaid | Parsed and rendered, `xmllint` clean, inspected as PNG |
| Site lint, typecheck, build | Not run (content and static assets only) |
| Live page and internal link targets | GET returned 200. Internal link used: `/blog/roboshop-ai-microservices` |

**What the trace is.** Real ingestion, search, graph, skills, executor and validation. The cluster is `FixtureKubernetes`, the runbooks are synthetic, and the model is absent or scripted by hand. It proves plumbing and validator behaviour, not model quality. To re-run: copy `article_trace_test.py` into `backend/tests/`, set `TRACE_OUT` and `MOKS_TEST_DATABASE_URL`, then run it from `backend/`. The truncation measurement (2 and 3 passage bodies seen at 1,400 characters each) came from a short script that pads a real `kb_search` hit and calls `prompts.untrusted` at both limits. It is not in the harness.

## Official sources

Checked on 2026-11-01: PostgreSQL 17 text search, pgvector README, Kubernetes pod lifecycle and debugging pages, OWASP LLM01, Azure RAG overview. Pinecone's and LangGraph's documentation were not rechecked, and the article makes no claim that relies on them.

- OpenSearch's docs are `latest`, not pinned to 3.9.0. Only the general filtered k-NN behaviour was relied on.
- The RRF paper's PDF could not be fetched (redirect loop), so the citation points to the Google Research record and the article does not say the paper chose k=60. It says only that MOKS uses 60.

## Unresolved

1. **Live state not queried.** No cluster, database or provider was touched. "No chat model has answered a live request" comes from `LIMITATIONS.md`. Which knowledge sources exist on EKS, and how many documents, is unknown.
2. **First person.** The body says "I ran" and "I traced" for checks performed for this draft. Confirm you are comfortable with that, or rerun them. The title's "We" was requested. The body uses "I" because MOKS is a personal project.
3. **The exec bug** in "Lessons" comes from project notes, not from a document read at this commit.
4. **Gaps listed in the article are unfixed.** No MOKS code was changed.
5. **The Q&A section was removed** on the audit's advice. It remains in Git history (`6bc2304`), and project notes say it doubled as interview preparation.
6. **The old SVGs stay** (`moks-trust-model`, `moks-rag-ingestion`, `moks-rag-retrieval`, `moks-skills-lifecycle`) because the live post uses them. They can go once the update is live.

## Docs drift found, not corrected

- `LIMITATIONS.md`: says 50 skills (51 exist); says the runner does not read skill `evaluation` entries (`gates.run_skills` does); says GitHub sync reads at most 3,000 files (sync is now batched, and 3,000 is the per-document chunk cap).
- `SKILLS.md`: says a custom skill with a built-in's name replaces it (it needs `overrides_builtin` plus policy); lists 13 of 51 skills; says processes follow a generation "within about 30 seconds" (`REFRESH_SECONDS` is 5, and the end-to-end delay was not measured, so the article gives no figure).
- `skills/__init__.py`: mentions `evals/skills.py`, which does not exist (it is `gates.py`).
- `_rerank` docstring: "not enough to bury a clear match". The -0.03 penalty took a superseded passage to -0.01387.
- `service.identifiers("CrashLoopBackOff")` returns `rashLoopBackOff`, because the pattern has no leading boundary. Harmless today, because it is an `ILIKE` substring match.
- `rules_report` labels `kb_search` facts `(cluster)`, because the tool has no namespace argument.
