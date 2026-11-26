# KEDA autoscaling for jithendar.com (26 November 2026): evidence and figures

Draft (status `review`, written 2026-11-26): `content/blog/keda-autoscaling-requests-per-second-jithendar-com.mdx`, how
the site's CMS scales with KEDA on requests per second, with CPU as a backstop, and how its numbers were chosen.

## Sources

| Source | What it gave |
|---|---|
| This repository | `kubernetes/35-autoscaling.yaml` (values from commit 83c02c3), `30-jithendar-com.yaml`, `85-ci-applier.yaml`, `scripts/ci-app-manifests.py`, `scripts/tests/test_autoscaling.py`; pull requests #23 to #26 and their workflow runs |
| mrjithendar/k8s-deployments #33 | KEDA 2.21.1: `minikube-infrastructure/keda.tf`, `deploy/minikube/keda/values.yaml` and its README (mesh split, port 9666) |
| Prometheus on mk4 (read-only, port-forward) | 7 days of request rates and CPU, the CPU cost per request, and where the CPU peaks come from: `evidence/prometheus.txt` |
| kubectl on mk4 (read-only) | the ScaledObject and the HPA KEDA made from it, the external metric's raw value, node memory requests, the spread rule: `evidence/live-state.txt` |
| KEDA, Kubernetes and Istio docs | listed under `sources` in the article |

Nothing in the evidence identifies a visitor: no client addresses, no origin IP addresses, no Cloudflare IDs.

## Not known yet (Todo items in the article)

1. **The first real scale-up.** On 26 November the site had never needed more than 2 pods. When it happens, add the HPA's
   events to "Checking it".
2. **Room for a third pod.** worker3 had 489Mi of memory requests free against the 512Mi a site pod asks for, and the
   spread rule (`maxSkew 1`, `DoNotSchedule`) sends pod 3 there. Update the section and `placement()` once that changes.
3. **The pipeline apply.** The ScaledObject went live at 09:13 UTC outside the deploy workflow. Confirm the next merged
   pull request that touches `kubernetes/` applies it cleanly.
4. **Grafana.** KEDA's operator metrics and kube-state-metrics are not scraped; an autoscaling panel needs both.

## Figures

Built with `diagrams/build_diagrams.py` (standard library only, using the shared `drawio_model.py` writer), then
exported with `diagrams/export.sh` (draw.io desktop CLI, light theme) to `public/images/keda-autoscaling/`:

| Figure | Shows |
|---|---|
| `keda-autoscaling-overview` | the request path, the two metric paths and the scaling loop; the cover image |
| `keda-autoscaling-loop` | one 15-second HPA sync as a sequence, with example values |
| `keda-autoscaling-cpu-evidence` | why requests lead: CPU peaks at pod start, the site's request rates |
| `keda-autoscaling-steps` | pods for a given request rate, with today's rate and the week's peak |
| `keda-autoscaling-placement` | where a third pod would go and why it would wait; the database ceiling |
| `keda-autoscaling-pipeline` | from a pull request to the HPA, and the two failure points of 26 November |

```bash
python3 docs/knowledge-sharing/keda-autoscaling/diagrams/build_diagrams.py
DRAWIO=/Applications/draw.io.app/Contents/MacOS/draw.io bash docs/knowledge-sharing/keda-autoscaling/diagrams/export.sh
```

If you edit a `.drawio` file by hand, run only `export.sh` afterwards. Running the build script overwrites the edits.
