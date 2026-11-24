# Public, read-only Grafana (24 November 2026): evidence and review notes

Draft (status `review`, written 2026-11-24): `content/blog/public-grafana-read-only-dashboards-k3s-cloudflare.mdx`,
about the Grafana at https://jithendar.com/grafana/ that anyone can open after Cloudflare's human check, and the
repository its dashboards are deployed from.

## Sources

| Source | What it gave |
|---|---|
| mrjithendar/k8s-deployments #30, #31 (master) | `minikube-infrastructure/grafana.tf` (anonymous org, data sources, providers, namespace, RBAC), `deploy/minikube/istio/edge/templates/cloudflare-public.yaml`, `deploy/minikube/observability/grafana/values.yaml` (sidecar), `docs/grafana-public.md` |
| mrjithendar/monitoring #1 (main) | `dashboards/`, `scripts/` (dashboards.py, check_dashboards.py, render_configmaps.py, audit_live.py), `.github/workflows/deploy.yml` |
| mk4 and the public internet, read-only | `evidence/checks.txt` |
| Grafana and Cloudflare docs | the article's `sources` |
| Screenshots | headless Chrome against Grafana through a port-forward, signed out (what an anonymous visitor sees): `public/images/public-grafana/public-grafana-landing.png`, `public-grafana-istio-mesh.png`, cropped |

## Not checked or not decided yet (Todo items in the article)

1. **Inspect for anonymous visitors.** Grafana's panel menu offers Inspect to every role, but the headless screenshots
   could not open the drawer from a URL. Open a panel's Inspect → Query in a private window before publishing.
2. **Loki in the public org** (owner's choice, 24 November). Any visitor who passes the check can query every
   namespace's logs, the site's request logs included. Decide whether the article and the privacy page say so, or
   whether to drop client addresses from the logs (Alloy) or remove Loki from the public org.
3. **Metrics and Logs Drilldown.** The anonymous role has `plugins.app:access`, and this Grafana has the Drilldown
   apps installed. Check in a private window whether a visitor can open them (they would make browsing the logs
   very easy).
4. **The Cloudflare rule.** The article shows the runbook's expression; confirm the deployed rule matches.
5. **Link previews.** Crawlers cannot pass the Managed Challenge, so a shared link previews as Cloudflare's page or a
   generic "Grafana". See k8s-deployments `docs/grafana-public.md`, "Linking to it".

## Figures

```bash
python3 docs/knowledge-sharing/public-grafana/diagrams/build_diagrams.py
DRAWIO=/Applications/draw.io.app/Contents/MacOS/draw.io bash docs/knowledge-sharing/public-grafana/diagrams/export.sh
```

`drawio_model.py` is the shared writer (copied from `../lancedb-r2`). Edit `build_diagrams.py`, never the exported
SVG or PNG. The two screenshots are not built: retake them with headless Chrome (`--window-size=1600,1250`, URL
parameter `kiosk` for the landing page) against a port-forward, then crop to the page body.
