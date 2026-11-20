# Argo CD install article: evidence and review notes

Draft (status `review`, written 2026-11-20): `content/blog/argocd-k3s-hetzner-terraform-helm.mdx`, how Argo CD itself
is installed on mk4 (hetzner-k3s, Terraform `helm_release`, the argo-cd chart and every value, Valkey, the `/argocd`
route and the Cloudflare fixes). Companion: `content/blog/argocd-gitops-deploy-k3s-app-of-apps.mdx` (deploying
applications through Argo CD; figures in `../argocd-mk4`). The two link to each other.

## Sources

Every snippet was matched against these commits (comments trimmed and elisions marked `...`):

| Repository | Commit | Files |
|---|---|---|
| `moks-tech/kubernetes` | `b74771b` | `hetzner-k3s.yaml`, `minikube-infrastructure/argocd.tf`, `redis.tf`, `_versions.tf`, `_variables.tf`, `vars/mk4.tfvars`, `deploy/minikube/argocd/values.yaml` + `README.md`, `deploy/minikube/istio/edge/values.yaml`, `deploy/minikube/istio/ingressgateway.yaml`, `deploy/minikube/istio/mesh/values.yaml`, `deploy/minikube/applications/`, `.github/workflows/create-mk-infrastructure.yml`, `check-mk-infrastructure.yml` |
| `moks-tech/kubernetes` | `5a8ec33`, `8f5eb06`, `fe3efdd`, `6f93d92`, `1f76443` | the commits that changed Argo CD (messages quoted in the Cloudflare table) |
| `mrjithendar/moks-sre` | `cd2f58f` | `deploy/argocd/hetzner/root.yaml`, `apps/*.yaml`, `deploy/argocd/project-root.yaml` |
| `mrjithendar/roboshop-ai` | `d33b00d` | `argocd-k3s/` (README, `project.yaml`, `web.yaml`) |
| argo-cd chart | 10.10.5 | `helm pull argo-cd --repo https://argoproj.github.io/argo-helm --version 10.10.5`; defaults read from its `values.yaml` (4,951 lines); `helm template` with our values: 33,555 lines, 30,890 in the 3 CRDs; `templates/argocd-applicationset/deployment.yaml` has no condition |

Read-only checks on mk4 (2026-11-20, about 13:30 to 14:00 UTC, current kube context):

- `helm -n argocd history argocd`: 6 revisions, chart argo-cd-10.10.5, app v3.5.5; `helm get values --revision 1`
  has the chart's Redis (with resources) and no `externalRedis`/`extraObjects`; revision 2 has Valkey, the
  VirtualService, the NetworkPolicy and `global.podAnnotations.checksum/redis`.
- Workflow runs (`gh run list --workflow create-mk-infrastructure.yml`): 8f5eb06 12:26:32, fe3efdd 12:40:26,
  6f93d92 12:47:59, 1f76443 13:05:18 UTC on 2026-11-19, all `success`, each under a minute before its Helm revision.
  The two runs on 2026-11-10 failed, so revisions 1 and 2 were applied by hand. `MINIKUBE_TERRAFORM_APPLY` = `true`.
- Pods: 4, all `2/2` (sidecars are native: init containers with `restartPolicy: Always`, 20m/64Mi requests,
  2/256Mi limits). `kubectl top --containers`: controller 298Mi, server 102Mi, repo-server 56Mi, appset 44Mi,
  sidecars 45+38+42+41 Mi. ApplicationSet controller has no resources. No PVCs in `argocd`.
- Secrets: no `argocd.argoproj.io/secret-type` (no repository credentials); `argocd-redis` present but not referenced
  by the rendered release; `argocd-initial-admin-secret` present.
- Applications: 26, all `automated` + `selfHeal` + `prune: false`, annotation `Prune=false,Delete=false`,
  `FailOnSharedResource` + `PruneLast` (RoboShop also `CreateNamespace`), no finalizers; `moks-foundation` OutOfSync
  at the time. AppProjects: `default`, `moks`, `moks-root`, `roboshop` (no `mk-platform`).
- Nodes m1 (control-plane, etcd), w1 to w3, k3s v1.37.2+k3s1, arm64. kube-system has hcloud CCM v1.33.0 and CSI
  v2.21.2; StorageClass `hcloud-volumes` is the default. Gateway Service: LoadBalancer, 80:31080, 443:31443.

The localStorage `theme` story is from the 2026-11-19 investigation (moks-cms "keep the reader's theme under
site-theme", merged 13:14 UTC); moks-cms is private, so the article does not link it.

## Figures

`diagrams/build_diagrams.py` writes the editable `.drawio` files; `diagrams/export.sh` has the draw.io desktop CLI
(32.6.10) export them to `public/images/argocd-k3s-hetzner/` (SVG for the article, 2x PNG for the featured image).
Run both from the repository root:

```bash
python3 docs/knowledge-sharing/argocd-k3s-hetzner/diagrams/build_diagrams.py
bash docs/knowledge-sharing/argocd-k3s-hetzner/diagrams/export.sh
```

`drawio_model.py` is a copy of the bge-m3 one. After editing a `.drawio` file by hand, run only `export.sh`.
No IP addresses are drawn.

| Figure | Used in |
|---|---|
| `argocd-install-layers` | featured image and "Three layers, three tools" |
| `argocd-helm-values` | Step 4 |
| `argocd-components` | Step 6 |
| `argocd-request-path` | Step 7 |

## To do before publishing

| Item | Status |
|---|---|
| "Loose ends": fix them first (delete `applicationSet.enabled` or set `applicationSet.replicas: 0`; delete Secret `argocd-redis`; apply or remove `mk-platform`), or keep them public | `<Todo>` in the article |
| "What's next" says `/argocd` is not behind Cloudflare Access yet (edge `access.enabled: false`, `cloudflare_access` commented out in mk4.tfvars) | keep or drop |
| Re-read pod memory and the Application count if publishing much later | numbers are from 2026-11-20 |
| `minikube-infrastructure/_versions.tf` still says the root is "Run by a person"; CI applies it on merge | repository comment, not the article |

## Not run

`scripts/check-content.sh` needs Docker, which was not available; `content.yml` runs it on the push and stops before
sending anything if an article is invalid. The body was compiled with `@mdx-js/mdx` 3.1.1, `remark-gfm` 4.0.1 and
`remark-directive` 4.0.0 (moks-cms's versions), and frontmatter lengths, related refs and image paths were checked.
