# GitHub Actions runners on mk4: evidence and review notes

Draft (status `review`, written 2026-11-21): `content/blog/github-actions-runners-k3s-arc-terraform.mdx`, how the
organization mrjithendar's workflows run on mk4 (ARC 0.15.1 from Terraform, the GitHub App, the NetworkPolicy, the
`mk4-runner` image, the privileged dind sidecar) and the issues hit on 21 November 2026.

## Sources

Every snippet was matched against these commits (comments trimmed and elisions marked `...`):

| Repository | Commit | Files |
|---|---|---|
| `mrjithendar/k8s-deployments` | `381b585` | `minikube-infrastructure/runners.tf`, `_variables.tf`, `vars/mk4.tfvars`, `tests/releases.tftest.hcl`, `deploy/minikube/runners/` (`values.yaml`, `controller.yaml`, `image/Dockerfile`, `README.md`), `deploy/minikube/gatekeeper/constraints/values.yaml`, `.github/workflows/create-mk-infrastructure.yml`, `build-runner-image.yml`, `gh-app.sh` (IDs replaced in the article) |
| `mrjithendar/k8s-deployments` | `a9cd274` (PR #24), `c64ca5d`, `18b905c`, `c06ac72` | the commits the timeline names; PR #24's description for the OIDC subject |
| `mrjithendar/aws-infra` | `master` on 2026-11-21 | `runner/README.md` (the 29 October host runners) |
| `mrjithendar/moks-sre-agent` | `8e54ac4` | the `terminal` matrix diff |
| the ten organization repositories | `c64ca5d` and siblings | the `runs-on: mk4` move (perl one-liner) |

## Workflow runs (2026-11-21, UTC)

| Run | Repository | What it shows |
|---|---|---|
| 44869812890 | k8s-deployments | first deploy after PR #24: "Not set: TF_VAR_github_runners_app_*" |
| 44874590419, 44875758550, 44877072503 | k8s-deployments | deploys on mk4 pods stopping at "AWS credentials": OIDC not authorized |
| 44874905707 | jithendar.com (private) | content.yml on 58ef3f7: attempt 1 06:18 `mk4-runner-wb4p4` git-lfs missing; attempt 2 06:38 `mk4-runner-pmp4w` docker socket missing; attempt 3 06:55:28–06:56:12 `mk4-runner-z2k2l` success |
| 44874602150 | moks-sre-agent | `services:` jobs: "Exit code 1 returned from process: file name '/usr/bin/docker', arguments 'version ...'" |
| 44874582769 | aws-vpc | checkov container action: "Docker pull failed with exit code 1" |
| 44878347711 | moks-cms (private) | manual `ci-repo.yml` after dind: hygiene 07:02:39–07:02:54 success (`docker run` promtool, shellcheck) |
| 44878350354 | roboshop-ai-app | manual `showcase-checks.yml` after dind: "Initialize containers" (mongo:8.0) success; unittest step failed (1 failure, 2 errors of 140), the workflow's first run |
| 44877072494 | k8s-deployments | Build runner image on c06ac72: tag check fails, two `image:` lines matched |

Tally: jobs of runs created after 05:30 in the ten repositories with `runner_name` `mk4-*`: 29 (7 success, 22
failure), counted at about 07:05.

## Read-only checks on mk4 and GitHub (2026-11-21, about 06:15 to 07:10 UTC, current kube context)

- `helm -n runners-system history arc`: revision 1 at 06:01:50 (chart gha-runner-scale-set-controller-0.15.1).
  `helm -n runners history arc-runners`: 06:02:23 install, 06:35:19 and 06:47:56 upgrades (shown in IST by Helm).
- Pods: `arc-gha-rs-controller-788ffdb87-5jh2n` and `mk4-cd7f7986-listener` Running on w3; AutoscalingRunnerSet `mk4`
  Running, no min or max; the live template uses `mk4-runner:2.338.2-48743dc57f6a` with init containers
  `init-dind-externals` and `dind`. Namespace labels: `runners` privileged, `runners-system` baseline.
- Nodes m1, w1–w3 all arm64, k3s v1.37.2+k3s1.
- `gh api orgs/mrjithendar/actions/runner-groups`: Default, visibility all, `allows_public_repositories` false →
  set to true at about 06:14. Fork PR approval policy `first_time_contributors`; private-repo fork workflows off.
- `ghcr.io/mrjithendar/mk4-runner:2.338.2-48743dc57f6a`: anonymous manifest request answers 200 (public package).
- Five repositories public (k8s-deployments, moks-sre-agent, aws-infra, aws-vpc, roboshop-ai-app), five private.

## Figures

`diagrams/build_diagrams.py` writes the editable `.drawio` files; `diagrams/export.sh` has the draw.io desktop CLI
(32.6.10) export them to `public/images/mk4-github-runners/` (SVG for the article, 2x PNG for the featured image).
Run both from the repository root:

```bash
python3 docs/knowledge-sharing/mk4-github-runners/diagrams/build_diagrams.py
DRAWIO=/Applications/draw.io.app/Contents/MacOS/draw.io bash docs/knowledge-sharing/mk4-github-runners/diagrams/export.sh
```

`drawio_model.py` is a copy of the argocd-k3s-hetzner one. After editing a `.drawio` file by hand, run only
`export.sh`. No IP addresses are drawn except the private ranges the NetworkPolicy refuses.

| Figure | Used in |
|---|---|
| `mk4-runners-architecture` | featured image and "The architecture" |
| `mk4-runners-job-lifecycle` | "How one job runs" |
| `mk4-runners-terraform` | "The Terraform: runners.tf" |
| `mk4-runners-timeline` | "Issues we hit, and how we fixed them" |

## To do before publishing

| Item | Where in the article |
|---|---|
| Fork PR approval policy is `first_time_contributors` while public repos may use privileged runners: change it, or untick public repos, before publishing | "Security", `<Todo>` |
| Build runner image tag check (two `image:` lines) | issue 9, "Still open", timeline row "open" |
| OIDC trust for k8s-deployments and aws-infra | issue 3, "Still open" |
| practice-programming executor tests not re-run on the new image | "Still open" |
| Runner limits unset | "Still open" |
