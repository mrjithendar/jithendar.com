# Let's Encrypt articles: evidence and review notes

Drafts (status `draft`, written 2026-11-14):

- `content/blog/lets-encrypt-ssl-explained-acme-challenges-renewal.mdx` (Part 1, concepts)
- `content/blog/lets-encrypt-k3s-cert-manager-automatic-renewal.mdx` (Part 2, the mk4 k3s setup)

Part 2 was written from Git only: `mrjithendar/minikube` at `13be756`. **The cluster was not inspected.** Every row
below marked "not checked" needs a look at mk4 before the article is published.

## Figures

`diagrams/build_diagrams.py` writes the editable `.drawio` files here and the SVGs in `public/images/lets-encrypt/`.
`diagrams/render_png.sh` renders 2x PNGs with `rsvg-convert` (not headless Chrome, unlike the other series). Run both
from `www/`. The SVGs are rendered by the script (shared writer in `../roboshop-ai/diagrams`), not exported by draw.io:
after editing a `.drawio` file by hand, export it from draw.io over the SVG.

| Figure | Used in |
|---|---|
| `lets-encrypt-acme-flow` | Part 1 (featured image and body) |
| `lets-encrypt-challenge-types` | Part 1 |
| `lets-encrypt-k3s-architecture` | Part 2 (featured image and body) |
| `lets-encrypt-k3s-renewal` | Part 2 |

## Declared in Git vs verified live (Part 2)

| Claim | Git (minikube 13be756) | Live |
|---|---|---|
| mk4 is k3s on Hetzner Cloud since 2026-11-10, hetzner-k3s | `minikube-infrastructure/_versions.tf` | not checked |
| 1 control plane without workloads, 2 workers cax21 (4 vCPU, 8 GB) | `deploy/minikube/harbor/README.md`, `redis/values.yaml` | not checked |
| Hetzner load balancer `mk4-edge`, 80/443, PROXY protocol | `deploy/minikube/istio/ingressgateway.yaml` | not checked; `istio/edge/values.yaml` header still describes the host HAProxy |
| Istio ingress gateway, 2 replicas, Gateway `public`, `credentialName` | `istio/ingressgateway.yaml`, `istio/edge/` | not checked |
| cert-manager chart v1.20.4, OCI, Terraform Helm release | `minikube-infrastructure/cert-manager.tf`, `cert-manager/values.yaml` | not checked |
| DoH self-check values and the port 53 timeout | comment in `cert-manager/values.yaml` | not checked |
| ClusterIssuers `letsencrypt-dns`, `letsencrypt-dns-staging` (DNS-01, Cloudflare) | `cert-manager/issuers/` | not checked |
| Certificates `istio-ingress/jithendar-com`, `jithendar/jithendar-com-wildcard` | `istio/edge/values.yaml`, `cert-manager/issuers/values.yaml` | not checked |
| Token Secret missing on 2026-11-08 | `minikube-infrastructure/README.md`, "Wildcard certificate" | — |
| `prometheus.enabled: false` (no cert-manager metrics) | `cert-manager/values.yaml` | not checked |

General cert-manager behaviour (renewal at 2/3 of the lifetime, `rotationPolicy: Always` since v1.18, backoff 1 h to
32 h, ARI behind `ACMEUseARI` in 1.21) comes from cert-manager's documentation and release notes, not from mk4.

## Not run

`npm test` (content and link validation) was not run: the session had no `node_modules` and no package installs.
Frontmatter lengths and required keys were checked by hand against `src/lib/content/schema.ts`.
