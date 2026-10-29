# jithendar.com Kubernetes manifests

Plain YAML exported from the running mk4 cluster (namespace `jithendar`) on 2026-10-29, with
cluster-generated fields removed. `kubectl diff -f k8s/` against the cluster showed no differences.

| File | Resources |
|---|---|
| `00-namespace.yaml` | Namespace `jithendar` |
| `10-postgres.yaml` | StatefulSet, Service, NetworkPolicy `jithendar-postgres` (10 Gi volume from the StatefulSet) |
| `20-redis.yaml` | Deployment, Service, NetworkPolicy `jithendar-redis` |
| `30-jithendar-com.yaml` | Deployment (2 replicas), Service, PodDisruptionBudget, NetworkPolicy `jithendar-com` |
| `40-middlewares.yaml` | Traefik middlewares `compress`, `https-redirect`, `www-redirect` |
| `50-certificate.yaml` | cert-manager Certificate `jithendar-com` (ClusterIssuer `letsencrypt-prod`) |
| `60-ingress.yaml` | Ingresses for `jithendar.com` and `www.jithendar.com` (HTTPS + HTTP redirect) |

## Before applying

Secrets are not in this folder and must never be committed. These must exist in `jithendar`:

- `jithendar-postgres` (key `password`), `jithendar-redis` (key `password`)
- `jithendar-com-env` (site configuration; its `DATABASE_URL`/`REDIS_URL` passwords must match the two above)
- `ecr-pull` (image pull secret, refreshed by the `roboshop-ai/ecr-refresh` CronJob)

## Apply

```sh
kubectl --context mk4 apply -f k8s/ --dry-run=server   # validate first
kubectl --context mk4 apply -f k8s/                    # files apply in name order
kubectl --context mk4 -n jithendar rollout status statefulset/jithendar-postgres
kubectl --context mk4 -n jithendar rollout status deployment/jithendar-redis
kubectl --context mk4 -n jithendar rollout status deployment/jithendar-com
www/scripts/smoke.sh https://jithendar.com
```

## Releasing a new version

The site image is pinned by digest in `30-jithendar-com.yaml` (`image: …/jithendar-com@sha256:…`). To
release, replace that digest with the one CI printed for the new commit, then apply. `./deploy.sh` does the
same automatically for the Kustomize manifests in `www/deploy/production` (same resources), including the
ECR lookup, rollout waits and smoke test. Keep the two in step, or use only one of them.
