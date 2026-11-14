# mk4 on k3s: shared figures

Figures of mk4, the k3s cluster on Hetzner Cloud (since 10 November 2026), used by several articles:

| Figure | Used in |
|---|---|
| `mk4-k3s-cluster` | CloudNativePG, Valkey, Kubernetes tools part 1, RoboShop AI architecture, the Next.js project page |
| `mk4-k3s-request-path` | Istio, Traefik (as today's path) |
| `mk4-k3s-ci-api` | GitHub Actions to the k3s API |

```bash
python3 sites/jithendar.com/docs/knowledge-sharing/mk4-k3s/diagrams/build_diagrams.py   # writes the .drawio files
bash sites/jithendar.com/docs/knowledge-sharing/mk4-k3s/diagrams/export.sh              # draw.io CLI → public/images/mk4-k3s/
```

Facts were read on 14 November 2026 from `hetzner-k3s.yaml` and `minikube-infrastructure/` in the kubernetes repository
and from read-only `kubectl` (nodes, storage classes, the gateway Service, the CI Role, pod placement in `postgres-db`
and `redis`). No IP addresses are drawn. Pod placement changes over time: re-read it before republishing.
