# Traefik on Minikube article: evidence and review notes

Draft: `content/blog/traefik-minikube-architecture-implementation.mdx` (status `review`, 2026-11-05).
Inspected: tools `8413177`, jithendar.com `ba3e851`, moks `9220dc7`, plus read-only `kubectl --context mk4`,
`helm` and `curl` on 2026-11-05. Nothing was changed in the cluster.

## SEO

- Title: Traefik on Minikube: Architecture, Features, and Implementation Across My Applications
- SEO title (48 chars): Traefik on Minikube: Real Architecture and Setup
- Meta description (157 chars): How Traefik v3.7 runs on a self-hosted Minikube cluster: Helm install, NodePort and HAProxy exposure, TLS, middlewares, app onboarding and troubleshooting.
- Slug: `traefik-minikube-architecture-implementation`

## Figures

`diagrams/build_diagrams.py` writes the editable `.drawio` files here and the SVGs in
`public/images/traefik-minikube/`. `diagrams/render_png.sh` renders 2x PNGs with headless Chrome. Run both from `www/`.
The SVGs are rendered by the script (shared writer in `../roboshop-ai/diagrams`), not exported by draw.io.

## Declared in Git vs verified live

| Claim | Git | Live |
|---|---|---|
| Chart 42.0.0, Traefik v3.7.14, ns traefik, 1 replica | tools `scripts/argocd/bootstrap.py`, `deploy/minikube/traefik/values.yaml` | `helm history`, Deployment image |
| Providers kubernetesingress (class traefik) + kubernetescrd, no namespace filter, no Gateway API | values.yaml | pod args; no `gateway.networking.k8s.io` CRDs |
| NodePort 30080/30443, PROXY protocol trusted from 192.168.49.0/24 | values.yaml | Service, pod args |
| HAProxy 3.2 TCP forwarder with send-proxy-v2 | `deploy/minikube/expose-ingress.sh` | indirect: allowlisted `/db/` returns 200 from the listed address; host container not inspected |
| DNS-only Cloudflare A records to Hetzner | — | `dig` (Cloudflare NS, Hetzner IP via whois) |
| Default TLSStore → jithendar-com-tls, LE cert apex + www | jithendar.com `minikube/50-certificate.yaml`, `55-tlsstore.yaml` | `openssl s_client`, expiry 2027-01-25 |
| Routes and middlewares (inventory table) | jithendar.com `minikube/`, tools `deploy/minikube/{argocd,observability}`, moks `deploy/helm/moks/templates/ingress.yaml` | `kubectl get ingress,ingressroute*,middleware* -A`, curl status codes |
| Argo apps manual sync | tools `deploy/minikube/applications`, moks `deploy/argocd/minikube` | `spec.syncPolicy.automated` empty |
| Metrics exposed but not scraped | tools `observability/prometheus/values.yaml` (no traefik job) | pod args `--metrics.prometheus`, pod annotations |
| loki-read routers skipped | tools `observability/loki/loki-read-*.yaml` | Traefik log `secret 'monitoring/loki-read-auth' not found`; curl 404 |

Redacted from the article: the host's public IP, the owner's allowlisted home IP, the AWS account ID in `bootstrap.py`.

## Implementation gaps (also listed at the end of the article)

1. Secret `monitoring/loki-read-auth` missing → four Loki read routers skipped.
2. Helm revision 2 `failed` (context canceled) while the Deployment runs its args; `bootstrap.py` refuses non-`deployed` releases.
3. Grafana/Prometheus/Loki Ingresses have no `router.entrypoints`; routers attach to the internal `metrics` entryPoint too.
4. Traefik metrics not scraped; access logs and tracing off.
5. No NetworkPolicy or PDB in `traefik`; one replica; one host.
6. `deploy/minikube/traefik/README.md` says Vultr (host is Hetzner) and links a missing `docs/operations/scripts.md`.
7. JFrog and Vault Ingresses declared, not deployed.
8. Unused `hub.traefik.io` CRDs from the chart.

## Before publishing

- Re-run the inventory commands: the loki-read Secret or the Helm state may have been fixed.
- Kubectl on the Mac is 1.30 against a 1.37 server (outside the supported skew); the read-only commands worked.
