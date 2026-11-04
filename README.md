# jithendar.com

Personal website and tech blog covering DevOps, cloud infrastructure, Kubernetes and AI engineering.
Built with Next.js, MDX, PostgreSQL, Cloudflare R2 and Kubernetes.

| Path | Contents |
|---|---|
| [`www/`](www/README.md) | The Next.js site: source, content, tests, Dockerfiles and [docs](www/docs/) |
| [`minikube/`](minikube/README.md) | Every manifest the site runs on the mk4 minikube cluster, in one flat folder: the site (`kustomization.yaml`), the Python practice executor (`practice-executor-*.yaml`) and database access (`db-access-*.yaml`); `scripts/manifests.sh <group>` prints one group |
| [`grafana/`](grafana/README.md) | Grafana dashboards for the site (metrics, logs and traces), loaded by Argo CD's `grafana` app |
| `deploy.sh` | Apply the site manifests and restart the site on `jithendar-com:latest` |
| `scripts/` | `create-secrets.sh` (first-time Secrets), `set-*-config.sh` (update site settings), `smoke.sh` (post-deploy checks) |
| [`runner/`](runner/README.md) | Self-hosted GitHub Actions runners (retired for CI: builds run on GitHub-hosted runners) |
| `.github/workflows/` | CI: checks pull requests; on `master`, builds and pushes the image to ECR (`infra.yml` applies `infra/`) |
| `infra/` | Terraform: ECR repositories and the CI's AWS role ([infra/README.md](infra/README.md)) |

## Release

Push to `master`. CI tests, builds, pushes `jithendar-com:latest` (and `:<commit-sha>` for history) to ECR and
restarts the site, which always runs `:latest` with `imagePullPolicy: Always`. That is the whole release.

Run `./deploy.sh` only after changing `minikube/` (it applies the manifests and restarts the site). It needs
`kubectl` with the `mk4` context. First-time setup,
Secrets, routing and rollback: [www/docs/DEPLOYMENT.md](www/docs/DEPLOYMENT.md).

## Local development

See [www/README.md](www/README.md).

## License

Copyright (c) 2026 Jithendar Dharmapuri. All rights reserved. This is proprietary software; no use, copying, modification or distribution is permitted without written permission. See [LICENSE](LICENSE).
