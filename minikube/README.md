# jithendar.com manifests for the mk4 minikube cluster

Everything jithendar.com runs on the mk4 cluster, in one flat folder. Exported from the live cluster on 2026-10-29
with cluster-generated fields removed, not deployed by Argo CD. The file name says which of three groups a manifest
belongs to; each group is applied on its own, and `scripts/manifests.sh <group>` prints it for `kubectl … -f -`.

| Group | Files | Applied by |
|---|---|---|
| `site` | `00-…` to `85-…`, listed in `kustomization.yaml` | `./deploy.sh` (all of it); CI applies the application objects |
| `practice-executor` | `practice-executor-*.yaml` | a person, once, after gVisor is verified; then CI (application objects) |
| `db-access` | `db-access-*.yaml` | CI, once its Role allows TCP routes (`DB_ACCESS.md`) |

## Site (`kustomization.yaml`)

| File | Resources |
|---|---|
| `00-namespace.yaml` | Namespace `jithendar` |
| `10-postgres.yaml` | StatefulSet, Service, NetworkPolicy `jithendar-postgres` (10 Gi volume, pinned to node `mk4-m03`) |
| `20-redis.yaml` | Deployment, Service, NetworkPolicy `jithendar-redis` |
| `30-jithendar-com.yaml` | Deployment (2 replicas), Service, PodDisruptionBudget, NetworkPolicy `jithendar-com` |
| `40-middlewares.yaml` | Traefik middlewares `compress`, `https-redirect`, `www-redirect`, `strip-trace-headers` |
| `45-jithendar-letsencrypt.yaml` | ClusterIssuers `letsencrypt-prod` and `letsencrypt-staging` (cluster-wide; formerly the `roboshop-letsencrypt` Argo CD app) |
| `50-certificate.yaml` | Certificate `jithendar-com` (apex + www) → Secret `jithendar-com-tls` |
| `55-tlsstore.yaml` | Traefik `TLSStore default`: `jithendar-com-tls` is the default certificate for every namespace, so `/argocd`, `/grafana`, `/prometheus` and `/roboshop` share it |
| `60-ingress.yaml` | Ingresses for `jithendar.com` and `www.jithendar.com` (HTTPS + HTTP redirect) |
| `70-observability.yaml` | Headless Service `jithendar-com-metrics` (Prometheus, port 9464) and Role/RoleBinding `alloy-logs`; see `www/docs/OBSERVABILITY.md` |
| `80-ci-deployer.yaml` | ServiceAccount `github-ci-deployer`: CI may only restart the site and the executor (`scripts/setup-ci-deployer.sh`) |
| `85-ci-applier.yaml` | ServiceAccount `github-ci-applier`: `.github/workflows/deploy-minikube.yml` applies the application objects (not RBAC, Secrets or anything cluster-wide; `scripts/setup-ci-applier.sh`) |

The Grafana dashboards are not cluster manifests here: they live in [`../grafana/`](../grafana/README.md) and
reach Grafana through Argo CD.

## Python practice executor (`practice-executor-*.yaml`)

Code runner in namespace `jithendar`, next to the site (`www/docs/PYTHON_PRACTICE_EXECUTOR.md`). Not in
`kustomization.yaml` on purpose, so `./deploy.sh` never applies it. Apply it by hand, only after gVisor is
installed (`scripts/install-gvisor-mk4.sh`), then prove isolation with `scripts/verify-practice-sandbox.sh`:

```sh
scripts/manifests.sh practice-executor | kubectl --context mk4 apply -f -
```

| File | Resources |
|---|---|
| `practice-executor-05-runtimeclass.yaml` | RuntimeClass `gvisor-nonet` (runsc, no network) |
| `practice-executor-10-rbac.yaml` | ServiceAccounts `practice-dispatcher`, `practice-api`, `practice-sandbox`; Role/RoleBinding for the dispatcher |
| `practice-executor-15-admission.yaml` | ValidatingAdmissionPolicies that pin down sandbox pods |
| `practice-executor-20-quota.yaml` | ResourceQuota for all sandboxes together |
| `practice-executor-30-redis.yaml` | The executor's own Redis queue |
| `practice-executor-40-executor.yaml` | ConfigMap, API and dispatcher Deployments, Service `practice-executor` |
| `practice-executor-50-networkpolicies.yaml` | Allowed traffic |

Images are always `:latest`. CI (`ci-practice-executor.yml`, job `deploy`) pushes `:latest` and restarts both
Deployments on every release once repository variable `PRACTICE_EXECUTOR_DEPLOY` is `true`.

## Database access (`db-access-*.yaml`)

Adminer at `https://jithendar.com/db/` and PostgreSQL at `db.jithendar.com:443`, both limited to two client IPs.
Read [`DB_ACCESS.md`](DB_ACCESS.md) first: the order matters.

| File | Resources |
|---|---|
| `db-access-10-allowlist.yaml` | The allowed client addresses (HTTP and TCP middlewares; edit both lists together) |
| `db-access-20-adminer.yaml` | Adminer (`jithendar-db-ui`): Deployment, Service, NetworkPolicy, middlewares, Ingress |
| `db-access-30-postgres-tls.yaml` | Certificate, TLSOption and IngressRouteTCP for `db.jithendar.com`, NetworkPolicy `jithendar-postgres-remote` |

## Before the first deploy

These Secrets must exist in `jithendar`; they are never committed. `scripts/create-secrets.sh mk4`
creates the first three.

- `jithendar-postgres` (key `password`), `jithendar-redis` (key `password`)
- `jithendar-com-env` (site configuration; its `DATABASE_URL`/`REDIS_URL` passwords match the two above)
- `ecr-pull` (image pull secret, refreshed by the `ecr-refresh` CronJob from the tools repository)

## Deploy

The site always runs `jithendar-com:latest` with `imagePullPolicy: Always`. CI pushes `:latest` and restarts
the Deployment on every push to `master`, so new code needs nothing here.

```sh
./deploy.sh
```

Server dry-runs, applies the `site` group, restarts the site so it pulls `:latest`, waits for the rollouts and runs
`scripts/smoke.sh`.

To apply manifest changes without a new image, review and apply one group directly:

```sh
scripts/manifests.sh site | kubectl --context mk4 diff -f -
scripts/manifests.sh site | kubectl --context mk4 apply -f -
```

(`kubectl apply -k minikube` is the same as the `site` group.) Never `kubectl apply -f minikube/`: it would apply
every group at once and try to apply `kustomization.yaml` itself.

A push to `master` that changes `minikube/` also runs `.github/workflows/deploy-minikube.yml`, which applies the
application objects of all three groups as `github-ci-applier` (`www/docs/DEPLOYMENT.md`).
