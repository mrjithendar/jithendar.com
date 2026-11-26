# jithendar.com manifests for the mk4 minikube cluster

Everything jithendar.com runs on the mk4 cluster, in one flat folder. Exported from the live cluster on 2026-10-29
with cluster-generated fields removed, not deployed by Argo CD. The file name says which of two groups a manifest
belongs to; each group is applied on its own, and `scripts/manifests.sh <group>` prints it for `kubectl … -f -`.

| Group | Files | Applied by |
|---|---|---|
| `site` | `00-…` to `85-…`, listed in `kustomization.yaml` | CI (`deploy-kubernetes.yml`) on merge: all of it except the two token Secrets and the ClusterRole/ClusterRoleBinding in `85-`, which `scripts/setup-ci-applier.sh` and `setup-ci-deployer.sh` apply |
| `seo-agent` | `seo-agent-*.yaml` (SEO v4 agent service: internal API + MCP edge, and `seo-agent-60-dispatcher.yaml`: one CronJob that starts the flow schedules kept in the database every minute; the schedules are edited in Admin → CrewAI console → Schedules). Kong entities for `/mcp/*` are in `kong/seo-agent-mcp.deck.yaml` (decK, not kubectl) | a person the first time (`scripts/manifests.sh seo-agent \| kubectl apply -f -`), after `scripts/create-seo-agent-secrets.sh` and pgvector (moks-cms `services/www/docs/seo/MANUAL_SETUP.md` §13–15 and "v4"); then CI applies the application objects on merge (ConfigMap, Deployment, Services, NetworkPolicies) and restarts the agent when its ConfigMap changed. The CronJobs stay with a person |

## Site (`kustomization.yaml`)

| File | Resources |
|---|---|
| `00-namespace.yaml` | Namespace `jithendar` |
| `30-jithendar-com.yaml` | Deployment (no replica count: KEDA's, `35-autoscaling.yaml`), Service, Service `jithendar-com-internal` (SEO agent callbacks, port 9465, never routed publicly), PodDisruptionBudget, NetworkPolicy `jithendar-com`, NetworkPolicy `jithendar-com-cache-bus` (egress to the Valkey pods, pod port 6380 only) |
| `35-autoscaling.yaml` | KEDA ScaledObject `jithendar-com`: at least 2 pods, more on requests per second (Prometheus) or the web container's CPU; KEDA makes HPA `keda-hpa-jithendar-com` ("Autoscaling" below) |
| `60-istio-routing.yaml` | Delegate VirtualService `jithendar-com-site`: the default route of the jithendar.com routing table in the miniKube repo (`deploy/minikube/istio/edge`, which also does www → apex, HTTP → HTTPS and compression). Strips client trace headers |
| `70-observability.yaml` | Headless Service `jithendar-com-metrics` (Prometheus, port 9464) and Role/RoleBinding `alloy-logs`; see moks-cms `services/www/docs/OBSERVABILITY.md` |
| `80-ci-deployer.yaml` | ServiceAccount `github-ci-deployer`: CI may only set the image of, and restart, the site, the executor and the SEO agent (`scripts/setup-ci-deployer.sh`) |
| `85-ci-applier.yaml` | ServiceAccount `github-ci-applier`: `.github/workflows/deploy-kubernetes.yml` applies the site group, RBAC included, and may patch the Namespace `jithendar` (not Secrets, nothing else cluster-wide; read the file's header; `scripts/setup-ci-applier.sh`) |

The site's Grafana dashboards are not here: they live in
[mrjithendar/monitoring](https://github.com/mrjithendar/monitoring) (`dashboards/private/Jithendar.com/`, signed-in only),
which deploys them.

## Python practice (moved)

The practice executor (code runner, namespace `jithendar`), its sandboxes, the problems and their manifests moved to
[`moks-tech/practice-programming`](https://github.com/moks-tech/practice-programming) on 2026-11-16; its CI deploys
the executor. Two things stay here: the site's egress rule to `app=practice-executor-api` (`30-jithendar-com.yaml`)
and the init container `practice-catalog`, which copies that repository's `practice-catalog:latest` into
`/app/practice` (`PRACTICE_CATALOG_PATH`). The CI deployer (`80-ci-deployer.yaml`) may still roll the two executor
Deployments: practice-programming's CI uses the same token.

## Database (shared CloudNativePG cluster)

The site's database is `jithendar` on the shared cluster `postgres-db/postgres-cluster` (miniKube repo,
`minikube-infrastructure/postgres.tf`, `postgres_databases.jithendar`). Terraform writes Secret
`jithendar/postgres-db-credentials`; the site reads its `uri` (PgBouncer pooler, session mode) as `DATABASE_URL`.
It was copied there from the old `jithendar-postgres` StatefulSet on 2026-11-09 (`dbMigration.sh` in the workspace,
row counts verified). The site's own Adminer (`/db`) and `db.jithendar.com` are gone with it: use the cluster's
`/postgres` UI and `postgres.jithendar.com` (miniKube repo, `deploy/minikube/postgres/access`).

## Autoscaling (KEDA)

KEDA (miniKube repo, `minikube-infrastructure/keda.tf`, namespace `keda`) sets how many site pods run: ScaledObject
`jithendar-com` in `35-autoscaling.yaml`, from which KEDA makes and updates HPA `keda-hpa-jithendar-com`. Never fewer
than 2 pods. More when the requests per second per pod (Prometheus, the public Service `jithendar-com` only) or the
`web` container's CPU (Metrics Server) pass their thresholds; the HPA follows whichever asks for more. Scaling down
waits 300 s (the HPA's default). `30-jithendar-com.yaml` has no `replicas`: a count there would be applied over
KEDA's on every deploy. CI applies the ScaledObject (Role `github-ci-applier`, `scripts/ci-app-manifests.py`).

**The owner's numbers.** `maxReplicaCount`, the Prometheus `threshold` (requests per second one pod should take) and
the CPU `value` (percent of the web container's 250m request) are `SET-ME` until chosen; `fallback` and a slower
scale-down are optional, commented out in the file. While any is `SET-ME`, the deploy's `plan` job names each one and
stops (`scripts/ci-app-manifests.py`), so no deploy runs, not even a moks-cms release restart; and
`scripts/tests/test_autoscaling.py` fails. What bounds `maxReplicaCount`:

- each pod requests 250m CPU and 512Mi memory, and the topology spread (`DoNotSchedule`, one skew across the three
  workers) puts the third pod on whichever worker has none: that worker must have the room;
- each pod opens up to `DATABASE_POOL_MAX` (5) connections through PgBouncer in session mode (20 server connections per
  pooler pod, two pods; role `jithendar` limited to 50, the seo-agent included). Past that, requests queue for a
  connection.

**Once, before the first deploy without `replicas`.** `kubectl apply` (client-side) remembers the last applied
manifest in an annotation. Applying one without `replicas` when the annotation still has `replicas: 2` deletes the
field, and the Deployment drops to 1 pod until KEDA's HPA brings it back to 2. Rewrite the annotation from the new
manifest first, right before merging; if another deploy runs in between, do it again. Done on mk4 on 2026-11-26 (the
annotation has no `replicas`), so only needed again if a manifest with `replicas` is applied:

```sh
scripts/manifests.sh site | python3 -c 'import sys, yaml; print(yaml.safe_dump(next(d for d in yaml.safe_load_all(sys.stdin) if d and d["kind"] == "Deployment" and d["metadata"]["name"] == "jithendar-com")))' > /tmp/jithendar-com-deployment.yaml
kubectl -n jithendar apply set-last-applied -f /tmp/jithendar-com-deployment.yaml
kubectl -n jithendar get deployment jithendar-com -o jsonpath='{.metadata.annotations.kubectl\.kubernetes\.io/last-applied-configuration}' | python3 -c 'import json, sys; print("replicas" in json.load(sys.stdin)["spec"])'   # False
```

**Checking it**

```sh
kubectl -n jithendar get scaledobject jithendar-com        # READY True; ACTIVE True while a trigger is above its threshold
kubectl -n jithendar get hpa keda-hpa-jithendar-com        # both metrics with current values, MINPODS 2
kubectl -n jithendar describe scaledobject jithendar-com   # conditions and events (a Prometheus error shows here)
kubectl -n keda logs deploy/keda-operator -c keda-operator --tail=50
```

`READY False` with a Prometheus error: KEDA's operator could not query `prometheus.monitoring` (its sidecar, or
monitoring's AuthorizationPolicy in the miniKube repo). Pods `Pending` after a scale-up: no worker has the room the
topology spread allows.

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

The site runs one image of its own, `registry.jithendar.com/jithendar/moks-cms:latest`, the CMS named in
`30-jithendar-com.yaml`. moks-cms's CI builds it, and it serves any site. Articles live in Postgres and `/images/…`
in R2: `.github/workflows/content.yml` pushes them through the site's API, with no image and no restart. `site.json`
and `config/` are ConfigMap `jithendar-com-site`, generated by `kustomization.yaml` and mounted at `/app/site`; a
change to them is applied, and rolls the site, like any manifest. Every workload names `:latest` with
`imagePullPolicy: Always`, so a new release is a restart: moks-cms's `moks-cms-released` dispatch makes
`deploy-kubernetes.yml` apply the manifests and restart what was released (the CMS rolls with no downtime; the SEO
agent is one pod and is recreated).

Manifest changes are applied by `.github/workflows/deploy-kubernetes.yml` when their pull request is merged (server
dry run, diff, apply, restart, wait, smoke test). A merged pull request or a manual run restarts every Deployment it
applies in namespace `jithendar`, each only if it exists there (a missing one is skipped with a warning). To re-apply
everything and restart without a merge, which is what `./deploy.sh` did until it was removed on 2026-11-14:

```sh
gh workflow run deploy-kubernetes.yml --ref master     # or Actions → deploy to kubernetes → Run workflow
```

By hand, with the `mk4` kubeconfig, the same objects are `kubectl apply -k kubernetes`.

**Kube context.** Every script that changes the cluster (`scripts/create-*`, `set-*`, `setup-ci-*`) sources `scripts/lib/kube-context.sh`: it targets `KUBE_CONTEXT` if set, otherwise the
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
