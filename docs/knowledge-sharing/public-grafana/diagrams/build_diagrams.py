#!/usr/bin/env python3
"""Figures for content/blog/public-grafana-read-only-dashboards-k3s-cloudflare.mdx (the public, read-only Grafana).

    python3 docs/knowledge-sharing/public-grafana/diagrams/build_diagrams.py   # writes the .drawio files
    bash docs/knowledge-sharing/public-grafana/diagrams/export.sh              # draw.io CLI → public/images/public-grafana/

If you edit a .drawio file by hand, run only export.sh afterwards. Running this script overwrites the edits.

Facts come from mrjithendar/k8s-deployments #30 and #31 (minikube-infrastructure/grafana.tf, istio/edge
templates/cloudflare-public.yaml, observability/grafana/values.yaml), mrjithendar/monitoring #1 and the read-only
checks on 24 November 2026 in ../evidence/checks.txt.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio_model import ARROWS, TEXT, Diagram  # noqa: E402

ARROWS["refused"] = ("#b91c1c", 1.5, "3 3", "Refused (403)")

HERE = Path(__file__).resolve().parent


def request_path():
    d = Diagram("public-grafana-request-path", 980, 520,
                "Who reaches the public Grafana, and what each layer checks")
    d.zone("z-out", "Internet", 20, 50, 205, 375, "plain")
    d.zone("z-cf", "Cloudflare (proxied DNS)", 240, 50, 220, 375, "plain")
    d.zone("z-mk4", "mk4: k3s on Hetzner, 4 arm64 nodes", 480, 50, 480, 375, "cluster")

    d.node("visitor", "client", 30, 85, 186, 76, "Visitor's browser", "passes the check once:",
           "cf_clearance cookie")
    d.node("script", "client", 30, 190, 186, 76, "Script or crawler", "can't solve the check:",
           "403, cf-mitigated")
    d.node("direct", "external", 30, 300, 186, 92, "Direct to the server", "Host: jithendar.com,",
           "skipping Cloudflare:", "403 at the gateway")

    d.node("rule", "security", 255, 85, 190, 124, "WAF custom rule", "host jithendar.com or www",
           "and path starts with", "/grafana", "action: Managed Challenge")
    d.node("cache", "network", 255, 250, 190, 76, "Cache", "Grafana sends no-store:",
           "BYPASS, never cached")

    d.node("lb", "network", 495, 85, 200, 60, "Hetzner load balancer", "PROXY protocol: real peer")
    d.node("gw", "security", 495, 175, 200, 124, "Istio ingress gateway", "cloudflare-public: /grafana",
           "only from Cloudflare's", "ranges (remoteIpBlocks)", "else 403")
    d.node("grafana", "compute", 725, 85, 220, 124, "Grafana 13.2", "anonymous: org Public,",
           "role Viewer", "Sign in: main org", "no Explore, no editing")
    d.node("prom", "data", 725, 240, 115, 76, "Prometheus", "both orgs", shape="db")
    d.node("loki", "data", 850, 240, 95, 76, "Loki", "both orgs", shape="db")
    d.node("jaeger", "data", 725, 335, 220, 76, "Jaeger", "main org only", shape="db")

    d.edge("visitor", "rule", exit=(1, 0.5), entry=(0, 0.3))
    d.edge("script", "rule", "403", kind="refused", exit=(1, 0.3), entry=(0, 0.75))
    d.edge("rule", "lb", "passed", exit=(1, 0.3), entry=(0, 0.5))
    d.edge("direct", "gw", "skips Cloudflare", kind="refused", exit=(1, 0.5), entry=(0, 0.85),
           via=((472, 346), (472, 280)))
    d.edge("lb", "gw", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("gw", "grafana", exit=(1, 0.3), entry=(0, 0.7))
    d.edge("grafana", "prom", exit=(0.23, 1), entry=(0.5, 0))
    d.edge("grafana", "loki", exit=(0.77, 1), entry=(0.5, 0))

    d.text("note", 20, 435, 940, 40, "<b>Live on 24 November 2026:</b> the org Public holds 16 dashboards (the landing "
           "page, 9 Platform, 6 MOKS); the 7 Jithendar.com dashboards stay in the main org. A Viewer may query every "
           "data source of its org, not only the dashboards' queries, so the org decides what is public.", color=TEXT)
    d.legend(487, labels={"client": "Callers", "external": "Bypass attempt", "security": "Checks",
                          "network": "Edge", "compute": "Grafana", "data": "Data sources"})
    return d


def dashboards_as_code():
    d = Diagram("public-grafana-dashboards-as-code", 980, 520,
                "How a dashboard in Git becomes a dashboard in Grafana, in the right org and folder")
    d.zone("z-gh", "GitHub: mrjithendar/monitoring", 20, 50, 300, 375, "plain")
    d.zone("z-ns", "Namespace grafana-dashboards", 340, 50, 250, 375, "cluster")
    d.zone("z-pod", "Grafana pod (namespace monitoring)", 610, 50, 350, 375, "cluster")

    d.node("repo", "data", 35, 85, 270, 108, "dashboards/ (uid = file name)", "public/live-infrastructure.json",
           "public/Platform (9), MOKS (6)", "private/Jithendar.com (7)", "inactive/RoboShop: not deployed",
           align="left")
    d.node("check", "ops", 35, 215, 270, 76, "check.yml (every pull request)", "uids, grid, data sources per org,",
           "links; tests with k8s-deployments", align="left")
    d.node("deploy", "ops", 35, 310, 270, 92, "deploy.yml (push to main)", "as github-dashboards-deployer:",
           "apply one ConfigMap per dashboard,", "delete those removed from Git", align="left")

    d.node("cms", "data", 355, 85, 220, 124, "ConfigMap dashboard-<uid>", "label grafana_dashboard=1",
           "annotation grafana_folder:", "public/Platform or", "private/Jithendar.com", align="left")
    d.node("sa", "security", 355, 240, 220, 76, "Deploy ServiceAccount", "github-dashboards-deployer:",
           "ConfigMaps here, nothing else", align="left")
    d.node("role", "security", 355, 335, 220, 76, "Role grafana-sidecar", "Grafana may get, list and",
           "watch ConfigMaps here only", align="left")

    d.node("sidecar", "compute", 625, 85, 320, 76, "k8s-sidecar (watches)", "writes /tmp/dashboards/",
           "<annotation>/<uid>.json")
    d.node("ppub", "service", 625, 195, 155, 92, "provider public", "…/public, folders", "from directories",
           "org Public")
    d.node("ppriv", "service", 790, 195, 155, 92, "provider private", "…/private, folders", "from directories",
           "main org")
    d.node("opub", "client", 625, 315, 155, 92, "Org Public", "anyone, read-only", "Platform, MOKS,",
           "landing page")
    d.node("opriv", "client", 790, 315, 155, 92, "Main org", "signed in only", "Jithendar.com")

    d.edge("repo", "check", "pull request", kind="control", exit=(0.25, 1), entry=(0.25, 0))
    d.edge("check", "deploy", "merge", kind="control", exit=(0.25, 1), entry=(0.25, 0))
    d.edge("deploy", "cms", kind="control", exit=(1, 0.3), entry=(0, 0.75), via=((330, 338), (330, 178)))
    d.edge("sidecar", "cms", "watch", exit=(0, 0.5), entry=(1, 0.3))
    d.edge("sidecar", "ppub", "files", exit=(0.25, 1), entry=(0.5, 0))
    d.edge("sidecar", "ppriv", exit=(0.77, 1), entry=(0.5, 0))
    d.edge("ppub", "opub", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("ppriv", "opriv", exit=(0.5, 1), entry=(0.5, 0))

    d.text("note", 20, 435, 940, 40, "<b>No restart:</b> the providers poll every 30 seconds, so a merged change shows "
           "within a minute. The Grafana chart's own RBAC is off: with a sidecar enabled, its ClusterRole would let "
           "Grafana read every Secret and ConfigMap in the cluster.", color=TEXT)
    d.legend(487, labels={"data": "Dashboards", "ops": "Workflows", "security": "Access", "compute": "Loader",
                          "service": "File providers", "client": "Grafana orgs"})
    return d


FIGURES = [request_path, dashboards_as_code]

if __name__ == "__main__":
    names = []
    for build in FIGURES:
        d = build()
        (HERE / f"{d.name}.drawio").write_text(d.xml() + "\n")
        names.append(d.name)
        print(f"wrote {d.name}.drawio ({d.w}x{d.h})")
    (HERE / "figures.txt").write_text("\n".join(names) + "\n")
