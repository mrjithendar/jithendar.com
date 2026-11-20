# MOKS CI/CD article: evidence and review notes

Draft (status `review`, written 2026-11-20): `content/blog/moks-sre-github-actions-ci-cd-pipeline.mdx`. It replaces
an earlier draft that was written from a screenshot of the Actions page; that draft still listed `opensearch-image`
and guessed at the `needs` graph.

## Sources

| What | Where |
|---|---|
| Workflow | `mrjithendar/moks-sre` `.github/workflows/ci.yml` at `cd2f58f` (master on 2026-11-20; the file last changed in `7e09449`, #91) |
| Release and rollback | `docs/RELEASES.md` at `cd2f58f` |
| Argo CD role and sync policy | `deploy/argocd/hetzner/project.yaml`, `deploy/argocd/hetzner/apps/*.yaml` (auto-sync, selfHeal, no prune) |
| Model locks | `reranker/model.lock.json` (ms-marco-MiniLM-L6-v2 @ 233902d), `reranker/embedder.lock.json` (bge-base-en-v1.5 @ a5beb1e) |
| Job timings | GitHub Actions API, `repos/mrjithendar/moks-sre/actions/runs/<id>/jobs`: the 22 completed (success or failure) push runs on master, 2026-11-16 to 2026-11-20, in `job-timings-2026-11-16-to-20.tsv` |
| Failure causes | `gh run view --job <id> --log-failed` for each red job |
| Repository settings | `gh variable list` (only `AWS_ROLE_ARN`; no `MK4_DEPLOY`), `branches/master/protection` (404 "Branch not protected"), `rulesets` (empty), all on 2026-11-20 |

Derived numbers (14 green runs): wall clock median 622.5 s (538-756), runner time median 2,222 s (2,049-2,551),
check median 476 s (374-633), crewai 422 s (340-577), release-crewai 119 s (114-127). crewai finished after check in
runs 176, 227, 251, 253 and 255. image, e2e and terminal ended by 219 s at the latest; check never ended before 377 s.
Run 279 (the timeline figure): check 3-576 s, backend tests step 463 s, release jobs from 581 s, last job 708 s,
runner time 2,220 s. Runs 214-220 (19 Nov burst) were cancelled 11-16 s after queueing and never started a job.

The 19 November chart/image race (figure `moks-ci-chart-image-race`): run times are from the API (#221 release done
11:03:31 UTC, #67 merged 11:31:22, run 225 release done 11:40:11). The pod restart at 11:33 on image
`0.1.0+5b1e709` and the "pgvector is not installed" failure come from the 2026-11-20 session notes, not re-read from
cluster logs for this article.

## Figures

`diagrams/build_diagrams.py` writes the editable `.drawio` files; `diagrams/export.sh` has the draw.io desktop CLI
export them to `public/images/moks-ci-pipeline/` (SVG for the article, 2x PNG for the featured image). From the
repository root:

```bash
python3 docs/knowledge-sharing/moks-ci-pipeline/diagrams/build_diagrams.py
DRAWIO=/Applications/draw.io.app/Contents/MacOS/draw.io bash docs/knowledge-sharing/moks-ci-pipeline/diagrams/export.sh
```

`drawio_model.py` is a copy of the bge-m3 one plus three arrow kinds (`needs`, `after`, `push`). After editing a
`.drawio` file by hand, run only `export.sh`.

| Figure | Shows |
|---|---|
| `moks-ci-job-graph` | the 12 jobs, their `needs`, median times (featured image and body) |
| `moks-ci-run-timeline` | run 279 job by job, critical path |
| `moks-ci-release-deploy` | release steps, Harbor, the (skipped) deploy job, mk4 today |
| `moks-ci-chart-image-race` | 19 November: chart synced before its image was pushed |

## Before publishing

| Item | Status |
|---|---|
| The article says "I merged eight Dependabot pull requests within 82 seconds" (runs 214-221) | confirm the wording |
| The 11:33 restart and the image it ran come from session notes | re-check if you have the pod events or logs |
| Run 257's CVE finding cleared in the next run with no change under `deploy/terminal`; the article says "most likely" Trivy's database changed | inference, labelled as such |
| If `MK4_DEPLOY`, branch protection or the `needs` lines change before publishing, update "Deploy", "What I'd change next" and the job-graph figure | open |

## Not run

`scripts/check-content.sh` needs Docker, which was not running; `content.yml` runs it on the push and stops before
sending anything if the article is invalid. The body was compiled with `@mdx-js/mdx` 3.1.1, `remark-gfm` 4.0.1 and
`remark-directive` 4.0.0 (moks-cms's pinned versions), and frontmatter lengths, related refs, image paths and
in-page anchors were checked against `moks-cms/src/lib/content/schema.ts`.
