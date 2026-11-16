# jithendar.com manifests for the mk4 minikube cluster

Everything jithendar.com runs on the mk4 cluster, in one flat folder. Exported from the live cluster on 2026-10-29
with cluster-generated fields removed, not deployed by Argo CD. The file name says which of two groups a manifest
belongs to; each group is applied on its own, and `scripts/manifests.sh <group>` prints it for `kubectl … -f -`.

| Group | Files | Applied by |
|---|---|---|
| `site` | `00-…` to `85-…`, listed in `kustomization.yaml` | CI (`deploy-kubernetes.yml`) on merge: all of it except the two token Secrets and the ClusterRole/ClusterRoleBinding in `85-`, which `scripts/setup-ci-applier.sh` and `setup-ci-deployer.sh` apply |
| `practice-executor` | `practice-executor-*.yaml` | a person, once, after gVisor is verified; then CI (application objects) |
| `seo-agent` | `seo-agent-*.yaml` (SEO v4 agent service: internal API + MCP edge, flow-trigger CronJobs, including `seo-agent-62-promotion-triggers.yaml` for the two promotion flows). Kong entities for `/mcp/*` are in `kong/seo-agent-mcp.deck.yaml` (decK, not kubectl) | a person the first time (`scripts/manifests.sh seo-agent \| kubectl apply -f -`), after `scripts/create-seo-agent-secrets.sh` and pgvector (moks-cms `services/www/docs/seo/MANUAL_SETUP.md` §13–15 and "v4"); then CI applies the application objects on merge (ConfigMap, Deployment, Services, NetworkPolicies) and restarts the agent when its ConfigMap changed. The CronJobs stay with a person |

## Site (`kustomization.yaml`)

| File | Resources |
|---|---|
| `00-namespace.yaml` | Namespace `jithendar` |
| `30-jithendar-com.yaml` | Deployment (2 replicas), Service, Service `jithendar-com-internal` (SEO agent callbacks, port 9465, never routed publicly), PodDisruptionBudget, NetworkPolicy `jithendar-com`, NetworkPolicy `jithendar-com-cache-bus` (egress to the Valkey pods, pod port 6380 only) |
| `60-istio-routing.yaml` | Delegate VirtualService `jithendar-com-site`: the default route of the jithendar.com routing table in the miniKube repo (`deploy/minikube/istio/edge`, which also does www → apex, HTTP → HTTPS and compression). Strips client trace headers |
| `70-observability.yaml` | Headless Service `jithendar-com-metrics` (Prometheus, port 9464) and Role/RoleBinding `alloy-logs`; see moks-cms `services/www/docs/OBSERVABILITY.md` |
| `80-ci-deployer.yaml` | ServiceAccount `github-ci-deployer`: CI may only set the image of, and restart, the site, the executor and the SEO agent (`scripts/setup-ci-deployer.sh`) |
| `85-ci-applier.yaml` | ServiceAccount `github-ci-applier`: `.github/workflows/deploy-kubernetes.yml` applies the site group, RBAC included, and may patch the Namespace `jithendar` (not Secrets, nothing else cluster-wide; read the file's header; `scripts/setup-ci-applier.sh`) |

The Grafana dashboards are not cluster manifests here: they live in [`../grafana/`](../grafana/README.md) and
reach Grafana through Argo CD.

## Python practice executor (`practice-executor-*.yaml`)

Code runner in namespace `jithendar`, next to the site (moks-cms `services/www/docs/PYTHON_PRACTICE_EXECUTOR.md`). Not in
`kustomization.yaml` on purpose, so its RBAC, quota, RuntimeClass and admission policies are never applied by CI. Apply it by hand, only after gVisor is
installed (`scripts/install-gvisor-mk4.sh`), then prove isolation with `scripts/verify-practice-sandbox.sh`:

```sh
scripts/manifests.sh practice-executor | kubectl apply -f -
```

| File | Resources |
|---|---|
| `practice-executor-05-runtimeclass.yaml` | RuntimeClass `gvisor-nonet` (runsc, no network) |
| `practice-executor-10-rbac.yaml` | ServiceAccounts `practice-dispatcher`, `practice-api`, `practice-sandbox`; Role/RoleBinding for the dispatcher |
| `practice-executor-15-admission.yaml` | ValidatingAdmissionPolicies that pin down sandbox pods |
| `practice-executor-20-quota.yaml` | ResourceQuota for all sandboxes together |
| `practice-executor-40-executor.yaml` | ConfigMap, API and dispatcher Deployments, Service `practice-executor` |
| `practice-executor-50-networkpolicies.yaml` | Allowed traffic |

moks-cms's CI (`ci-practice-executor.yml`) pushes `:pr-<number>` and `:latest`; the manifests name the tag both
Deployments run (`deploy-kubernetes.yml` moves it when moks-cms announces a release, and applies the application
objects); sandbox pods keep using `practice-sandbox:latest`.

## Database (shared CloudNativePG cluster)

The site's database is `jithendar` on the shared cluster `postgres-db/postgres-cluster` (miniKube repo,
`minikube-infrastructure/postgres.tf`, `postgres_databases.jithendar`). Terraform writes Secret
`jithendar/postgres-db-credentials`; the site reads its `uri` (PgBouncer pooler, session mode) as `DATABASE_URL`.
It was copied there from the old `jithendar-postgres` StatefulSet on 2026-11-09 (`dbMigration.sh` in the workspace,
row counts verified). The site's own Adminer (`/db`) and `db.jithendar.com` are gone with it: use the cluster's
`/postgres` UI and `postgres.jithendar.com` (miniKube repo, `deploy/minikube/postgres/access`).

## Traefik (gone)

Traefik was uninstalled on 2026-11-09; the Istio gateway in the miniKube repo (`deploy/minikube/istio`) is the only
edge, with its own wildcard certificate (DNS-01). The old HTTP-01 ClusterIssuers `letsencrypt-prod`/`-staging`, the
Certificates `jithendar-com` and `db-jithendar-com`, Traefik's TLSStore, IngressRouteTCP, TLSOption and MiddlewareTCP
were deleted from mk4 the same day, and nothing here admits the `traefik` namespace any more. The namespace is STRICT
mTLS with no plain-text port: Prometheus scrapes `:9464` over mTLS through its own sidecar.

## Before the first deploy

These Secrets must exist in `jithendar`; they are never committed. `KUBE_CONTEXT=mk4 scripts/create-secrets.sh`
creates `jithendar-com-env`; Terraform in the miniKube repository writes the database and Redis ones.

- `jithendar-com-env` (site configuration)
- `postgres-db-credentials` (key `uri`, read as `DATABASE_URL`): the shared CloudNativePG cluster in namespace
  `postgres-db`, written by Terraform in the miniKube repository (`minikube-infrastructure/postgres.tf`)
- `redis-practice-credentials` (key `uri`, read as `EXECUTOR_REDIS_URL` by the practice executor): the shared Valkey
  in namespace `redis`, written by Terraform in the miniKube repository (`minikube-infrastructure/redis.tf`,
  `redis_tenants.practice`). The site itself has no `REDIS_URL` (removed 2026-11-09)
- `redis-site-cachebus-credentials` (key `uri`, read as `CACHE_BUS_REDIS_URL` by the site, through an explicit `env`
  entry, never `envFrom`): the site's cache bus, PUBLISH/SUBSCRIBE only on the shared Valkey (ACL user `site-cachebus`,
  `redis_tenants.site-cachebus`). Optional: the site starts without it and keeps TTL-only caches. Apply order:
  1. miniKube repo: add the tenant (moks-cms `services/www/docs/redis-site-cachebus.md`), `terraform apply`;
  2. check the Secret appeared: `kubectl -n jithendar get secret redis-site-cachebus-credentials`;
  3. run the `deploy to kubernetes` workflow by hand (or
     `kubectl -n jithendar rollout restart deployment/jithendar-com`: env is read at pod start);
  4. the ACL check in that document, then Admin → System status shows "cache bus: connected".
- `harbor-pull` (pull secret for `registry.jithendar.com`, used by the site, the practice executor and sandbox pods;
  written by the tools repository's `deploy/minikube/harbor/registry.py pull-secrets`)

## Deploy

The site runs two images. `registry.jithendar.com/jithendar/moks-cms:<tag>` is the CMS, the tag named in
`30-jithendar-com.yaml`. moks-cms's CI builds it, and it serves any site. `jithendar-com-content:latest` holds this
site's articles, images, `site.json` and `config/`: its init container copies them into the pod, and the CMS reads them
at run time. A content change ships with `.github/workflows/content.yml` (build, push, restart). A new CMS release is a
new tag in the manifests: moks-cms's `moks-cms-released` dispatch makes `deploy-kubernetes.yml` commit it and apply it,
or change it by hand in a pull request. A manifest that names `:latest` keeps the image a workload already runs
(`scripts/keep-live-images.py`); a tag is applied as written.

Manifest changes are applied by `.github/workflows/deploy-kubernetes.yml` when their pull request is merged (server
dry run, diff, apply, wait, smoke test). To re-apply everything and restart the site without a merge, which is what
`./deploy.sh` did until it was removed on 2026-11-14:

```sh
gh workflow run deploy-kubernetes.yml --ref master     # or Actions → deploy to kubernetes → Run workflow
```

By hand, with the `mk4` kubeconfig, the same objects are `kubectl apply -k kubernetes`.

**Kube context.** Every script that changes the cluster (`scripts/create-*`, `set-*`, `setup-ci-*`,
`verify-practice-sandbox.sh`) sources `scripts/lib/kube-context.sh`: it targets `KUBE_CONTEXT` if set, otherwise the
current kubectl context, refuses a context that doesn't exist, prints the context and its API server, and passes
`--context` to every kubectl call so the whole run stays on one cluster. Without `KUBE_CONTEXT` it asks for confirmation
when run from a terminal (`YES=1` skips the question; CI and pipes never prompt). `scripts/manifests.sh` only prints,
so it has no guard; the `kubectl` you pipe it into uses your current context.
Tests: `bash scripts/tests/kube-context.test.sh` and `python3 -m unittest discover -s scripts/tests -p 'test_*.py'`
(stub kubectl, no cluster).

Server dry-runs, applies the `site` group, restarts the site (on the image it runs), waits for the rollouts and runs
`scripts/smoke.sh`.

To apply manifest changes without a new image, review and apply one group directly:

```sh
scripts/manifests.sh site | kubectl diff -f -
scripts/manifests.sh site | kubectl apply -f -
```

(`kubectl apply -k kubernetes` is the same as the `site` group.) Never `kubectl apply -f kubernetes/`: it would apply
every group at once and try to apply `kustomization.yaml` itself.

A pull request merged into `master` that changes `kubernetes/` also runs `.github/workflows/deploy-kubernetes.yml`, which applies the
application objects of all three groups as `github-ci-applier` (moks-cms `services/www/docs/DEPLOYMENT.md`).
