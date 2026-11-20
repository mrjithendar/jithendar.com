# Argo CD on mk4: evidence and review notes

Draft (status `review`, written 2026-11-20): `content/blog/argocd-gitops-deploy-k3s-app-of-apps.mdx`, how MOKS and
RoboShop are deployed to mk4 through Argo CD (AppProjects, the MOKS app of apps, one chart split by `resourceGroup`,
the RoboShop flat catalog, sync policy, Secrets, the `:latest` restart gap, incidents).

## Sources

Every code block was matched line by line against these commits (a script compared each quoted line with the file;
`...` marks cuts):

| Repository | Commit | Files |
|---|---|---|
| `moks-tech/kubernetes` | `b74771b` | `minikube-infrastructure/argocd.tf`, `deploy/minikube/argocd/values.yaml`, `deploy/minikube/applications/`, `scripts/argocd/deploy.py` |
| `mrjithendar/moks-sre` | `7e09449` | `deploy/argocd/project-root.yaml`, `deploy/argocd/hetzner/`, `deploy/helm/moks/templates/_helpers.tpl`, `templates/api.yaml`, `scripts/deploy-hetzner.sh`, `scripts/setup-argocd-ci.sh`, `.github/workflows/ci.yml`, `docs/ARGOCD_APP_SPLIT.md` |
| `mrjithendar/roboshop-ai` | `6f3a341` | `argocd-k3s/` (README, project, postgres) |

Pull requests and commits cited: moks-sre #40, #56, #67, #75, #77, #85, #90, #91, `4c94afe` (auto-sync, 8 Nov);
kubernetes `f514eaf` (8 Nov), `5a8ec33` (10 Nov), `8f5eb06`, `fe3efdd`, `6f93d92`, `1f76443` (19 Nov); roboshop-ai
`6f3a341` (11 Nov).

Read-only checks on mk4, 2026-11-20 about 13:45 UTC (`kubectl`, `helm`, current context):

- Argo CD pods: server, repo-server, application-controller (StatefulSet), applicationset-controller, all
  `quay.io/argoproj/argocd:v3.5.5`, 2/2 with sidecars. Helm release `argocd`, chart `argo-cd-10.10.5`, revisions 1-2 on
  2026-11-10 (13:40, 15:00 IST), 3-6 on 2026-11-19 at 12:27, 12:41, 12:48, 13:05 UTC (match the four cache commits).
- `argocd-cm`: `timeout.reconciliation` 120s, jitter 60s, anonymous off. `argocd-cmd-params-cm`: `redis.db` 7,
  `redis.server` valkey-master.redis:6379, rootpath/basehref `/argocd`, `server.insecure` true.
- 26 Applications: 9 MOKS (`moks-root` + 8 children, project `moks`/`moks-root`, destination `moks-sre`), 17 RoboShop
  (project `roboshop`). AppProjects live: `default`, `moks`, `moks-root`, `roboshop` (`mk-platform` not applied).
  Tracked resources: moks 68, roboshop 42, moks-root 8 (Applications). Per child: foundation 18, executor 26, reranker
  10, terminal 8, api 3, worker/crewai/routing 1 each.
- 25 Synced/Healthy; `moks-foundation` OutOfSync: PeerAuthentication `moks-opensearch-edge` and
  `moks-opensearch-dashboards-edge` in `moks-sre`, `requiresPruning: true`.
- `moks-root` and `moks-routing` last `operationState`: Error at 09:42:41 UTC, "repository contains out-of-bounds
  symlinks. file: frontend/node_modules".
- Live projects `moks` and `moks-root` list two source repos (`moks-sre.git` and the old `moks.git`); Git lists one.
- Children created 2026-11-10T11:58:25Z (7), `moks-routing` 2026-11-19T12:39:10Z; RoboShop apps 2026-11-11T13:19Z.
- MOKS images `registry.jithendar.com/jithendar/moks*:latest`, pull Always; RoboShop app images `:latest` Always, data
  stores pinned. Namespace `moks` no longer exists.
- moks-sre repository variables: only `AWS_ROLE_ARN` (no `MK4_DEPLOY`), no `ARGOCD_AUTH_TOKEN` secret: the CI deploy
  job is skipped.
- `/argocd/` answers 200; `/argocd/api/version` returns `cache-control: no-store, no-transform`,
  `cf-cache-status: DYNAMIC`.
- Chart 10.10.5 `helm show values`: the `applicationSet` section has no `enabled` key.

Not re-verified from a log: the 16-19 November InvalidSpecError after the repository rename comes from the
2026-11-19 session notes (and moks-sre#56's description); the live projects still listing the old URL is consistent
with it. The "new chart, old image" after moks-sre#67 also comes from session notes (2026-11-20).

Argo CD documentation checked on 2026-11-20: auto-sync interval ("defaults to 120s with added jitter of 60s for a
maximum period of 3 minutes"), sync options `Prune=false` / `Delete=false` / `managedNamespaceMetadata`, and
"Out-of-bounds symlinks now blocked at fetch" (upgrading 2.4 to 2.5). All reference URLs answered 200.

## Figures

`diagrams/build_diagrams.py` writes the editable `.drawio` files; `diagrams/export.sh` has the draw.io desktop CLI
export them to `public/images/argocd-mk4/` (SVG for the article, 2x PNG for the featured image). From the repository
root:

```bash
python3 docs/knowledge-sharing/argocd-mk4/diagrams/build_diagrams.py
bash docs/knowledge-sharing/argocd-mk4/diagrams/export.sh
```

`drawio_model.py` is a copy of the bge-m3 one. After editing a `.drawio` file by hand, run only `export.sh`.

| Figure | Used in |
|---|---|
| `argocd-mk4-who-deploys-what` | featured image and "What runs where" |
| `argocd-mk4-app-of-apps` | Step 4 |
| `argocd-mk4-deploy-loop` | Step 8 |
| `argocd-mk4-timeline` | "What went wrong" |

## To do before publishing

| Item | Status |
|---|---|
| Delete the two leftover PeerAuthentications (or keep them as the article's live example) | not done; the article says so |
| Run `scripts/setup-argocd-ci.sh` to switch the MOKS CI deploy job on, then rewrite Step 8's callout | not done; the article says so |
| Fix the stale "Manual sync" comments in moks-sre `deploy/argocd/hetzner/` and `applicationSet.enabled` in kubernetes `values.yaml` | not done; the article describes both as found |
| Decide whether "What went wrong" may name these incidents and PR numbers publicly | `<Todo>` in the article |

## Not run

`scripts/check-content.sh` needs Docker, which was not running. The body was compiled with `@mdx-js/mdx` 3.1.1 plus
`remark-gfm` 4.0.1 and `remark-directive` 4.0.0 (the versions in moks-cms `package.json`), and the frontmatter limits,
related refs and image paths were checked against moks-cms `src/lib/content/schema.ts`. `content.yml` runs the full
check on push and stops before sending anything if the article is invalid.
