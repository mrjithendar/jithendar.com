# "Deploy Moks CMS" series: evidence and review notes

Drafts (status `draft`, written 2026-11-14, owner request):

- `content/blog/deploy-moks-cms-linux-server-ec2-docker.mdx` (Part 1: one Linux server, EC2 as the example)
- `content/blog/deploy-moks-cms-kubernetes-k3s.mdx` (Part 2: k3s)
- `content/blog/deploy-moks-cms-amazon-eks.mdx` (Part 3: Amazon EKS)

Renamed the same day at the owner's request: the product is **Moks CMS**, the AI/ML-powered CMS, and jithendar.com is
the site deployed with it. Kubernetes and AWS resource names in the guides are `moks-cms` (database and user `moks`).

**None of the three was run end to end.** They were written from the repository and are guides for readers, not a
record of how jithendar.com runs (it runs Moks CMS on k3s, mk4; Part 2's "How production differs" lists the gaps). Each article
starts with a `<Todo>` listing what to run or confirm before publishing.

## Figures

`diagrams/build_diagrams.py` writes the editable `.drawio` files here and the SVGs in
`public/images/deploy-moks-cms/` (shared writer in `../roboshop-ai/diagrams`). `diagrams/render_png.sh` renders
2x PNGs with headless Chrome. Run both from `www/`. After editing a `.drawio` file by hand, export it from draw.io over
the SVG.

| Figure | Used in |
|---|---|
| `deploy-server-architecture` | Part 1 (featured image and body) |
| `deploy-server-release` | Part 1 |
| `deploy-k8s-architecture` | Part 2 (featured image and body) |
| `deploy-k8s-rollout` | Part 2 |
| `deploy-eks-architecture` | Part 3 (featured image and body) |
| `deploy-eks-delivery` | Part 3 |

## Facts taken from the repository

| Claim in the articles | Source |
|---|---|
| Three-stage Dockerfile, node:26-alpine, user 1000, port 3000, `GIT_SHA` build arg | `services/www/Dockerfile` |
| Standalone output carries `content/` and the SQL migrations | `next.config.ts` (`outputFileTracingIncludes`) |
| Required variables and their failure messages | `src/lib/auth.ts`, `src/lib/secrets.ts`, `src/db/index.ts`, `src/app/setup/actions.ts` |
| Migrations on start under an advisory lock | `src/instrumentation.ts`, `src/db/migrate.ts` |
| `/api/health` does not touch the database and reports `GIT_SHA` | `src/app/api/health/route.ts` |
| Rate limiter trusts the right-most `X-Forwarded-For` hop | `src/app/api/ask/route.ts` (`clientAddress`) |
| `sslmode` read from `DATABASE_URL`; pool of 5 (`DATABASE_POOL_MAX`) | `src/db/index.ts`, postgres.js 4.1.0 |
| Probes, security context, resources, preStop, PDB, spread | `kubernetes/30-jithendar-com.yaml` |
| Only `PRODUCTION_HOST` is indexable | `src/config/site.ts` (`isIndexableHost`) |
| Cache bus over Redis pub/sub, sessions in Postgres | `docs/DEPLOYMENT.md`, `src/lib/cache-bus.ts` |
| GitHub OIDC role for ECR pushes | `infra/ci-role.tf` |
| Action versions (checkout v7, configure-aws-credentials v6) | `.github/workflows/` |
| cert-manager chart v1.20.4 (OCI) | the Let's Encrypt Part 2 article |
| EKS 1.36 on t4g.large in this account | the RoboShop AI EKS article (checked 2026-11-01) |

## Not from the repository (confirm before publishing)

- Prices (us-east-1, on-demand): t4g.medium $0.0336/h, t4g.large $0.0672/h, EKS $0.10/h, NAT gateway $0.045/h,
  ALB $0.0225/h, RDS db.t4g.small $0.032/h, public IPv4 $0.005/h, gp3 $0.08/GB (EBS) and $0.115/GB (RDS).
- PostgreSQL 18 Docker image volume path (`/var/lib/postgresql`).
- k3s ServiceLB preserving the client address with `externalTrafficPolicy: Local`; the Traefik chart value names.
- CloudNativePG Secret `<cluster>-app` key `uri`, Services `-rw/-ro/-r`, operator status port 8000.
- eksctl `podIdentityAssociations` with `wellKnownPolicies`, the `metrics-server` EKS add-on, External Secrets
  `external-secrets.io/v1`.

## Naming to settle before publishing

- "Moks CMS" is not used anywhere else on the site yet: `how-i-built-jithendar-com` and the code (`site.name`,
  `appName: "Jithendar.com"` in Better Auth, the repository name) still call it jithendar.com.
- The existing project `projects/moks` is MOKS, the AI SRE investigation portal. Readers may assume the two are the
  same product; consider a sentence or a project page for Moks CMS.
