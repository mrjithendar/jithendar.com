#!/usr/bin/env python3
"""Figures for "Istio Service Mesh on Minikube: Features, Setup and Troubleshooting".

    python3 sites/jithendar.com/docs/knowledge-sharing/istio-minikube/diagrams/build_diagrams.py   (from www/)
    bash sites/jithendar.com/docs/knowledge-sharing/istio-minikube/diagrams/export.sh

The first command writes one editable .drawio file per figure beside this script; the second has the draw.io desktop
CLI export each to public/images/istio-minikube/<name>.svg and .png. After editing a .drawio file by hand, run only
export.sh, or this script overwrites the edits.

The mk4 figures were checked against the miniKube repository (deploy/minikube/istio) and the live cluster on
9 November 2026.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio_model import Diagram  # noqa: E402

HERE = Path(__file__).resolve().parent


def architecture():
    d = Diagram("istio-architecture", 860, 600, "Istio in sidecar mode: control plane, data plane and gateways")
    d.node("client", "client", 35, 60, 200, 56, "Client", "browser or API caller")
    d.zone("z-cluster", "Kubernetes cluster", 20, 136, 820, 380, "cluster")
    d.zone("z-cp", "istio-system", 35, 166, 260, 140)
    d.node("istiod", "ops", 50, 196, 230, 96, "istiod", "watches Services and Istio CRDs", "pushes Envoy config (xDS)",
           "CA + injection webhook")
    d.node("igw", "network", 330, 166, 230, 70, "Ingress gateway", "standalone Envoy, north-south", "Gateway + VirtualService")
    d.zone("z-app", "App namespace, istio-injection=enabled", 310, 256, 515, 132, corner="right")
    d.node("podA", "service", 325, 290, 220, 78, "Pod: productpage", "app container", "+ istio-proxy (Envoy)")
    d.node("podB", "service", 590, 290, 220, 78, "Pod: reviews", "app container", "+ istio-proxy (Envoy)")
    d.node("cni", "compute", 35, 326, 260, 62, "istio-cni (DaemonSet)", "sets up traffic redirection per pod,", "no NET_ADMIN init container")
    d.node("egw", "optional", 590, 420, 220, 62, "Egress gateway", "optional single exit")
    d.node("ext", "external", 325, 420, 220, 62, "External API", "outside the mesh")
    d.edge("client", "igw", exit=(1, 0.5), entry=(0.5, 0), via=[(445, 88)], label="HTTPS")
    d.edge("igw", "podA", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("podA", "podB", exit=(1, 0.5), entry=(0, 0.5), label="mTLS")
    d.edge("podB", "egw", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("egw", "ext", exit=(0, 0.5), entry=(1, 0.5))
    d.edge("istiod", "igw", exit=(1, 0.2), entry=(0, 0.5), kind="control")
    d.edge("istiod", "podA", exit=(1, 0.8), entry=(0, 0.5), kind="control")
    d.text("facts", 20, 526, 820, 46, "Solid lines are requests: every hop between Envoys is mutual TLS with a short-lived certificate "
           "per service account (SPIFFE identity), while the app speaks plain HTTP. Dashed teal lines are xDS configuration "
           "and certificates from istiod. If istiod is down, proxies keep their last configuration, but no new pod can start "
           "in an injected namespace.", size=11)
    d.legend(578)
    return d


def mk4_edge():
    d = Diagram("mk4-istio-edge", 960, 880, "mk4: the Istio ingress gateway is the only way in (9 November 2026)")
    d.node("visitor", "client", 35, 56, 300, 56, "Visitor", "browser, docker, psql")
    d.node("dns", "external", 420, 56, 300, 56, "Cloudflare DNS", "DNS only, no proxying")
    d.zone("z-host", "Hetzner host (one server)", 20, 132, 920, 96, corner="right")
    d.node("haproxy", "network", 35, 160, 360, 56, "HAProxy :80 / :443", "TCP only, adds PROXY protocol v2")
    d.node("nodeport", "network", 520, 160, 405, 56, "NodePort 31080 / 31443", "Service istio-ingressgateway")
    d.zone("z-gw", "namespace istio-ingress", 20, 248, 660, 250, "cluster")
    d.node("gw", "network", 35, 278, 325, 206, "istio-ingressgateway x2", "PDB minAvailable 1, two nodes",
           "1. PROXY header required", "2. TLS: wildcard certificate", "3. basic auth by path prefix",
           "4. DENY: read-only, IP allowlists", "5. X-Forwarded-For = real IP", "6. compression, access log",
           align="left")
    d.node("hosts", "security", 400, 278, 265, 92, "Own hostnames (SNI)", "registry. → harbor routes",
           "db. → TLS ends here, then TCP", "with ALPN postgresql")
    d.node("root", "security", 400, 392, 265, 92, "Root VirtualService", "Gateway public: jithendar.com",
           "one route per path prefix", "site last; www → apex")
    d.node("harbor", "data", 700, 278, 225, 50, "harbor", "registry.jithendar.com")
    d.node("pg", "data", 700, 342, 225, 50, "jithendar-postgres", "db.jithendar.com:443")
    d.zone("z-apps", "Meshed namespaces: STRICT mTLS from the gateway to every pod", 20, 518, 920, 250, "cluster")
    apps = [("site", "jithendar", "site, the default", "and /db (Adminer)"), ("moks", "moks", "/moks", "/opensearch*"),
            ("rs", "roboshop-ai", "/roboshop", "web, NGINX"), ("mon", "monitoring", "/grafana", "/prometheus /loki"),
            ("argo", "argocd", "/argocd", "Argo CD server"), ("kiali", "istio-system", "/kiali", "Kiali, meshed")]
    for i, (key, ns, a, b) in enumerate(apps):
        d.node(key, "service", 35 + (i % 3) * 300, 556 + (i // 3) * 104, 285, 86, ns, f"delegate: {a}", b)
    d.text("note", 20, 780, 920, 32, "Every hop below the gateway is mTLS between Envoy sidecars. Sources: miniKube "
           "deploy/minikube/istio and the live mk4 cluster.", size=11)
    d.edge("visitor", "dns", exit=(1, 0.5), entry=(0, 0.5), label="lookup")
    d.edge("visitor", "haproxy", exit=(0.5, 1), entry=(0.5, 0), label="80 / 443")
    d.edge("haproxy", "nodeport", exit=(1, 0.5), entry=(0, 0.5), label="PROXY v2")
    d.edge("nodeport", "gw", exit=(0.1, 1), entry=(0.5, 0), via=[(560.5, 240), (197.5, 240)])
    d.edge("gw", "hosts", exit=(1, 0.22), entry=(0, 0.5))
    d.edge("gw", "root", exit=(1, 0.77), entry=(0, 0.5))
    d.edge("hosts", "harbor", exit=(1, 0.24), entry=(0, 0.5))
    d.edge("hosts", "pg", exit=(1, 0.93), entry=(0, 0.5))
    d.edge("root", "z-apps", exit=(0.5, 1), entry=((532.5 - 20) / 920, 0), label="one delegate per prefix")
    d.legend(828)
    return d


def mk4_security():
    d = Diagram("mk4-mesh-security", 900, 760, "mk4: who may call whom inside the mesh (9 November 2026)")
    d.zone("z-default", "istio-system/default PeerAuthentication: STRICT for every namespace", 20, 48, 860, 84, "risk")
    d.text("default", 35, 76, 830, 60, "A meshed pod accepts only mutual TLS. Plain-text exceptions left: harbor registry :5000 "
           "(harbor-core keeps the public Host header, so its sidecar passes the call through as plain TCP) and "
           "moks-opensearch :9200 (removed by the next moks sync).", size=12)
    d.zone("z-callers", "Callers (mTLS identities)", 20, 164, 300, 410)
    callers = [("c-gw", "network", "istio-ingress", "the public gateway"), ("c-mon", "ops", "monitoring", "Prometheus, Grafana"),
               ("c-kiali", "ops", "istio-system", "Kiali (meshed by pod label)"), ("c-moks", "ai", "moks", "connectors: metrics, logs"),
               ("c-apps", "service", "jithendar, roboshop-ai", "OTLP traces")]
    for i, (key, kind, title, sub) in enumerate(callers):
        d.node(key, kind, 35, 194 + i * 74, 270, 60, title, sub)
    d.zone("z-callees", "allow-known-callers (ALLOW, dry run)", 360, 164, 520, 410, "cluster")
    callees = [("t-app", "jithendar · moks · roboshop-ai", "own pods + istio-ingress + monitoring"),
               ("t-plat", "argocd · harbor", "own pods + istio-ingress + monitoring"),
               ("t-cm", "cert-manager", "own pods + monitoring"),
               ("t-mon", "monitoring", "own + istio-ingress, istio-system, moks"),
               ("t-obs", "observability", "own + monitoring, jithendar, moks, roboshop-ai")]
    for i, (key, title, sub) in enumerate(callees):
        d.node(key, "security", 375, 194 + i * 74, 490, 60, title, sub)
    d.edge("c-gw", "t-app", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("c-gw", "t-plat", exit=(1, 0.75), entry=(0, 0.5), via=[(352, 239), (352, 298)])
    d.edge("c-mon", "t-mon", exit=(1, 0.5), entry=(0, 0.3), via=[(328, 298), (328, 434)])
    d.edge("c-kiali", "t-mon", exit=(1, 0.5), entry=(0, 0.7), via=[(336, 372), (336, 458)])
    d.edge("c-moks", "t-obs", exit=(1, 0.5), entry=(0, 0.3), via=[(344, 446), (344, 508)])
    d.edge("c-apps", "t-obs", exit=(1, 0.5), entry=(0, 0.7))
    d.zone("z-out", "Outside the mesh on purpose", 20, 594, 860, 84)
    d.node("o1", "optional", 35, 620, 270, 48, "moks sandboxes", "terminals, diagnostics, lab")
    d.node("o2", "optional", 320, 620, 270, 48, "cert-manager webhook", "called by the API server")
    d.node("o3", "optional", 605, 620, 260, 48, "istiod, istio-cni", "and kube-system")
    d.text("note", 20, 684, 860, 30, "Dry run: Envoy counts what each policy would refuse (rbac shadow_denied) and lets it through. "
           "Every namespace's own pods are always allowed. NetworkPolicies still apply underneath.", size=11)
    d.legend(722, labels={"security": "Policy", "optional": "Not meshed"})
    return d


FIGURES = [architecture, mk4_edge, mk4_security]


def main():
    names = []
    for make in FIGURES:
        d = make()
        (HERE / f"{d.name}.drawio").write_text(d.xml(), encoding="utf-8")
        names.append(d.name)
    (HERE / "figures.txt").write_text("\n".join(names) + "\n", encoding="utf-8")
    print(f"{len(names)} .drawio files: {', '.join(names)}")


if __name__ == "__main__":
    main()
