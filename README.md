# jithendar.com

Personal website and tech blog covering DevOps, cloud infrastructure, Kubernetes and AI engineering.
Built with Next.js, MDX, PostgreSQL, Cloudflare R2 and Kubernetes.

| Path | Contents |
|---|---|
| [`www/`](www/README.md) | The Next.js site: source, content, tests, Dockerfiles and [docs](www/docs/) |
| [`k8s/`](k8s/README.md) | Every manifest the site runs on the mk4 cluster, including the Let's Encrypt issuers and the shared TLS certificate |
| `deploy.sh` | Deploy a CI-built image to the cluster |
| `scripts/` | `create-secrets.sh` (first-time Secrets), `set-*-config.sh` (update site settings), `smoke.sh` (post-deploy checks), `set-image.sh` (used by `deploy.sh`) |
| [`runner/`](runner/README.md) | Self-hosted GitHub Actions runners for this repository |
| `.github/workflows/` | CI: checks pull requests; on `master`, builds and pushes the image to ECR |

## Release

1. Push to `master`. CI tests, builds and pushes `jithendar-com:<commit-sha>` to ECR. It has no cluster access.
2. Deploy from an up-to-date checkout, then commit the updated `k8s/kustomization.yaml`:

   ```bash
   ./deploy.sh          # the most recently pushed image
   ./deploy.sh <sha>    # a specific commit (also how you roll back)
   ```

Needs `kubectl` with the `mk4` context and AWS credentials that can read ECR. First-time setup,
Secrets, routing and rollback: [www/docs/DEPLOYMENT.md](www/docs/DEPLOYMENT.md).

## Local development

See [www/README.md](www/README.md).
