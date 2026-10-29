# jithendar.com Kubernetes manifests

Everything jithendar.com runs on the mk4 cluster. Exported from the live cluster on 2026-10-29
with cluster-generated fields removed. Deployed with `kubectl apply -k k8s` (normally through
[`../deploy.sh`](../deploy.sh)), not Argo CD.

| File | Resources |
|---|---|
| `00-namespace.yaml` | Namespace `jithendar` |
| `10-postgres.yaml` | StatefulSet, Service, NetworkPolicy `jithendar-postgres` (10 Gi volume, pinned to node `mk4-m03`) |
| `20-redis.yaml` | Deployment, Service, NetworkPolicy `jithendar-redis` |
| `30-jithendar-com.yaml` | Deployment (2 replicas), Service, PodDisruptionBudget, NetworkPolicy `jithendar-com` |
| `40-middlewares.yaml` | Traefik middlewares `compress`, `https-redirect`, `www-redirect` |
| `45-jithendar-letsencrypt.yaml` | ClusterIssuers `letsencrypt-prod` and `letsencrypt-staging` (cluster-wide; formerly the `roboshop-letsencrypt` Argo CD app) |
| `50-certificate.yaml` | Certificate `jithendar-com` (apex + www) → Secret `jithendar-com-tls` |
| `55-tlsstore.yaml` | Traefik `TLSStore default`: `jithendar-com-tls` is the default certificate for every namespace, so `/argocd`, `/grafana`, `/prometheus` and `/roboshop` share it |
| `60-ingress.yaml` | Ingresses for `jithendar.com` and `www.jithendar.com` (HTTPS + HTTP redirect) |
| `70-observability.yaml` | Headless Service `jithendar-com-metrics` (Prometheus, port 9464) and Role/RoleBinding `alloy-logs`; see `www/docs/OBSERVABILITY.md` |
| `kustomization.yaml` | The list above plus the image digest pin |

## Before the first deploy

These Secrets must exist in `jithendar`; they are never committed. `scripts/create-secrets.sh mk4`
creates the first three.

- `jithendar-postgres` (key `password`), `jithendar-redis` (key `password`)
- `jithendar-com-env` (site configuration; its `DATABASE_URL`/`REDIS_URL` passwords match the two above)
- `ecr-pull` (image pull secret, refreshed by the `ecr-refresh` CronJob from the tools repository)

## Deploy

```sh
./deploy.sh          # the most recently pushed image
./deploy.sh <sha>    # a specific commit (also how you roll back)
```

It pins the image digest in `kustomization.yaml`, server dry-runs, applies, waits for the rollouts
(undoing the site's rollout if it fails) and runs `scripts/smoke.sh`. Commit `kustomization.yaml`
afterwards so Git records what is live.

To apply manifest changes without a new image, review and apply directly:

```sh
kubectl --context mk4 diff -k k8s
kubectl --context mk4 apply -k k8s
```

Never `kubectl apply -f k8s/`: it would try to apply `kustomization.yaml` itself and skip the digest pin.
