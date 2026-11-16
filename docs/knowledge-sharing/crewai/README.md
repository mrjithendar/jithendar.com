# CrewAI articles: evidence and review notes

Drafts (status `draft`, written 2026-11-16):

- `content/blog/crewai-moks-sre-agent-kubernetes-investigation-crew.mdx`: CrewAI in MOKS, the SRE agent
- `content/blog/crewai-flows-crews-jithendar-com-seo-agent.mdx`: CrewAI Flows and Crews behind this site

Both were written from Git only. **Nothing was run and no cluster was inspected.** Every snippet in the two
articles was matched against these commits (whitespace aside):

| Article | Repository | Commit |
|---|---|---|
| MOKS | `mrjithendar/moks-sre` (public) | `28d9ba1` |
| jithendar.com | `moks-tech/moks-cms` (private), `services/seo-agent` and `services/www/docs/seo` | `bb6a4ba` |
| jithendar.com | this repository, `kubernetes/seo-agent-*.yaml` | `0e26db8` |

## Figures

`diagrams/build_diagrams.py` writes the editable `.drawio` files here and the SVGs in `public/images/crewai/`.
`diagrams/render_png.sh` renders 2x PNGs with `rsvg-convert`. Run both from the repository root. The SVGs are rendered
by the script (shared writer in `../roboshop-ai/diagrams`), not exported by draw.io: after editing a `.drawio` file by
hand, export it from draw.io over the SVG.

| Figure | Used in |
|---|---|
| `moks-crewai-request-path` | MOKS article |
| `moks-crewai-crew` | MOKS article (featured image and body) |
| `moks-crewai-thread-bridge` | MOKS article |
| `moks-crewai-build-deploy` | MOKS article |
| `seo-agent-crewai-kickoff` | jithendar.com article (featured image and body) |
| `seo-agent-new-article-flow` | jithendar.com article |
| `seo-agent-editorial-crew` | jithendar.com article |
| `seo-agent-approval-gate` | jithendar.com article |

## To confirm before publishing

| Claim | Where it comes from | Status |
|---|---|---|
| No real model has run the MOKS crew; no smoke test on mk4 | `moks-sre/docs/crewai-investigation.md`, "What is still unverified" | Repository's own statement. Update the article if a real run exists |
| The CrewAI image is pushed to Harbor | `moks-sre/.github/workflows/ci.yml`, job `release-crewai` | The design note still says ECR. The article follows `ci.yml` |
| crewai 1.15.36 brings 76 extra packages; telemetry endpoint and port; memory, knowledge and planning call their own providers | `moks-sre/docs/crewai-investigation.md` section 3 | Not re-measured here |
| CrewAI's telemetry switches and the `BaseLLM` extension point | docs.crewai.com (telemetry, custom LLM), read on 2026-11-16 | Checked against the current docs, not the 1.15.36 copy |
| seo-agent pins crewai 1.15.34 | `moks-cms/services/seo-agent/pyproject.toml` | `FLOWS.md` and `DECISIONS.md` D-54 still say 1.15.30 |
| The five CrewAI behaviours (auto memory, `@persist()` SQLite, router labels, inherited methods, `validate`) | `moks-cms/services/www/docs/seo/DECISIONS.md` D-54, and the code that handles each | Found on 1.15.30. Not re-tested on 1.15.34 |
| Production crew limits: 300,000 tokens, 1,200 s, turns 4/10/6/8, flow limit 2,700 s | `kubernetes/seo-agent-40-seo-agent.yaml` | Declared in Git. "How I built jithendar.com" still quotes 150k tokens and 600 s |
| 177 to 161 locked packages when LangGraph and LangChain were removed | `DECISIONS.md` D-54 | As recorded at the v4 switch |
| Ten SEO CronJobs, two promotion, three news | `kubernetes/seo-agent-60/61/62-*.yaml` | Counted in Git |

## Not run

The content check (`scripts/check-content.sh`) needs Docker and the registry, so it did not run in the writing session;
`content.yml` runs it on the push. Frontmatter limits, related refs, internal links, image paths and sizes were checked
by hand against `moks-cms/services/www/src/lib/content/schema.ts` and `links.ts`.
