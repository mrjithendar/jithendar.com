#!/usr/bin/env python3
"""Figures for the Traefik on Minikube article: editable .drawio files and matching SVGs.

Reuses the layout, palette and draw.io writer of the RoboShop AI series. Run from www/. The SVGs are rendered here,
not exported by draw.io: if a .drawio file is edited by hand, re-export it from draw.io over the SVG.
Labels follow the read-only inspection of mk4 on 2026-11-05 (tools 8413177, jithendar.com ba3e851, moks 9220dc7).
"""
import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[3] / "public" / "images" / "traefik-minikube"
spec = importlib.util.spec_from_file_location("series_diagrams", HERE.parents[1] / "roboshop-ai" / "diagrams" / "build_diagrams.py")
series = importlib.util.module_from_spec(spec)
sys.modules["series_diagrams"] = series
spec.loader.exec_module(series)
Page = series.Page


def request_path():
    p = Page("traefik-minikube-request-path", "Request path", 900, 720,
             "External request path from a browser to applications on the mk4 Minikube cluster",
             "A browser resolves jithendar.com through Cloudflare DNS in DNS-only mode, so the address is the Hetzner host itself. "
             "On the host, an HAProxy container forwards TCP ports 80 and 443 to the Minikube node's NodePorts 30080 and 30443 and "
             "adds a PROXY protocol v2 header. The NodePort Service sends traffic to the single Traefik v3.7.14 pod, where TLS ends "
             "with the Let's Encrypt certificate from the default TLSStore. Traefik matches host and path rules from Ingress and "
             "Traefik CRD objects and forwards plain HTTP to Services in the jithendar, moks, monitoring and argocd namespaces. "
             "Calls between pods, such as the site to the practice executor, use cluster DNS and do not pass through Traefik.")
    p.zone("Internet", 15, 12, 870, 100)
    p.zone("Hetzner host (Linux, Docker)", 15, 124, 870, 100, "br")
    p.zone("Minikube cluster mk4: 5 nodes on Docker network 192.168.49.0/24", 15, 236, 870, 470, "br")
    p.zone("namespace traefik", 30, 256, 840, 204)
    p.node("browser", "browser", 30, 36, 220, 64, "Browser", "https://jithendar.com/...", "or curl --resolve for tests")
    p.node("dns", "external", 300, 36, 300, 64, "Cloudflare DNS, DNS only", "A records: apex, www, db", "point at the host, no CDN proxy")
    p.node("haproxy", "edge", 30, 148, 840, 64,
           "HAProxy 3.2 container from expose-ingress.sh: TCP mode, holds no certificates",
           "host :80 → mk4 node :30080 and host :443 → mk4 node :30443",
           "adds a PROXY protocol v2 header, so Traefik sees the visitor's address instead of the node's")
    p.node("nodeport", "service", 45, 280, 810, 46, "Service traefik, type NodePort",
           "80 → nodePort 30080 → pod :8000 (web)    443 → nodePort 30443 → pod :8443 (websecure)")
    p.node("traefik", "gateway", 45, 348, 810, 96, "Traefik v3.7.14 from Helm chart 42.0.0, 1 replica",
           "entryPoints web and websecure trust the PROXY header from 192.168.49.0/24 only",
           "TLS ends here: default TLSStore → Secret jithendar-com-tls (Let's Encrypt via cert-manager HTTP-01)",
           "providers: kubernetesingress (IngressClass traefik) and kubernetescrd, all namespaces; no Gateway API",
           "middlewares: redirects, compress, basicAuth, ipAllowList, headers; upstream connections are plain HTTP")
    p.node("jithendar", "service", 45, 490, 195, 96, "ns jithendar", "/ → jithendar-com:80", "/db → jithendar-db-ui:80",
           "db.jithendar.com (TCP, SNI)", "→ jithendar-postgres:5432")
    p.node("moks", "service", 250, 490, 195, 96, "ns moks", "/moks → moks-api:8080", "/moks/api/terminal",
           "→ moks-terminal:8080", "/opensearch* IngressRoutes")
    p.node("monitoring", "service", 455, 490, 195, 96, "ns monitoring", "/grafana → grafana:80", "/prometheus → :9090, auth",
           "/loki/api/v1/push, auth", "Loki read: router disabled")
    p.node("argocd", "service", 660, 490, 195, 96, "ns argocd", "/argocd → argocd-server:80", "Argo CD serves /argocd",
           "itself, no prefix strip", "HTTP → HTTPS middleware")
    p.node("exec", "absent", 45, 616, 195, 64, "practice-executor-api", "no Ingress: called by", "the site pods in-cluster")
    p.note(270, 640, "Pod-to-pod calls use Service DNS names and never pass through Traefik.", size=12)
    p.edge("browser", "dns", a_side="r", b_side="l", label="1. lookup", dy=-10)
    p.edge("browser", "haproxy", a_at=0.5, b_at=(140 - 30) / 840, label="2. TCP 80/443", dx=50)
    p.edge("haproxy", "nodeport", b_at=0.5)
    p.edge("nodeport", "traefik")
    for i, (target, x) in enumerate((("jithendar", 142.5), ("moks", 347.5), ("monitoring", 552.5), ("argocd", 757.5))):
        p.edge("traefik", target, a_at=(x - 45) / 810, label="Host + path match" if i == 0 else "", dx=62)
    p.edge("jithendar", "exec", kind="dashed")
    return p


def config_flow():
    p = Page("traefik-minikube-config-flow", "Configuration flow", 900, 590,
             "How routing configuration reaches Traefik on mk4",
             "Three GitHub repositories hold the configuration. A person installs Traefik itself with Helm through bootstrap.py "
             "or deploy-traefik.sh, and the same bootstrap applies Argo CD's own Ingress with kubectl apply -k. Argo CD, synced "
             "manually with deploy.py, applies the Grafana, Prometheus, Loki and MOKS routes. GitHub Actions with the "
             "github-ci-applier ServiceAccount, and the owner's deploy.sh, apply the jithendar.com routes, TLSStore and "
             "certificates. Everything lands in the Kubernetes API. Helm values become Traefik's static configuration, which "
             "needs a pod restart to change; Traefik's providers watch Ingress and CRD objects and apply them as dynamic "
             "configuration without a restart. Invalid references are logged and the affected router is skipped.")
    p.zone("Git repositories on GitHub", 15, 12, 870, 108)
    p.zone("Who applies it", 15, 140, 870, 116)
    p.zone("Kubernetes API", 15, 268, 870, 78)
    p.zone("namespace traefik", 15, 358, 870, 222, "br")
    p.node("tools", "external", 30, 36, 270, 76, "tools", "deploy/minikube/traefik/values.yaml",
           "argocd/ Ingress + Middleware", "observability/ Ingress + auth")
    p.node("moksrepo", "external", 315, 36, 270, 76, "moks", "deploy/helm/moks chart",
           "templates/ingress.yaml", "Ingress, IngressRoute, Middleware")
    p.node("siterepo", "external", 600, 36, 270, 76, "jithendar.com", "minikube/40–60: Ingress, Middleware",
           "TLSStore, Certificate, issuers", "db-access: IngressRouteTCP")
    p.node("helm", "edge", 30, 164, 200, 80, "Helm, by a person", "bootstrap.py or", "deploy-traefik.sh",
           "chart 42.0.0 → Deployment")
    p.node("kubectl", "edge", 245, 164, 200, 80, "kubectl apply -k", "deploy/minikube/argocd", "run by bootstrap.py",
           "Argo CD's own Ingress")
    p.node("argo", "edge", 460, 164, 200, 80, "Argo CD on mk4", "manual sync with deploy.py", "grafana, prometheus, loki",
           "moks-routing (moks repo)")
    p.node("ci", "edge", 675, 164, 200, 80, "CI and deploy.sh", "deploy-minikube.yml", "SA github-ci-applier",
           "deploy.sh: TLSStore, RBAC")
    p.node("api", "store", 30, 292, 845, 46, "Kubernetes API server (mk4)",
           "Deployment args (static) · Ingress, Middleware, TLSStore, TLSOption, IngressRouteTCP (dynamic) · Secrets, EndpointSlices")
    p.node("static", "gateway", 30, 382, 400, 80, "Static configuration", "CLI arguments rendered from Helm values",
           "entryPoints, providers, PROXY protocol, metrics", "a change means a new pod")
    p.node("dynamic", "gateway", 475, 382, 400, 80, "Dynamic configuration", "providers list and watch the API",
           "routers, services, middlewares, TLS", "applied live, no restart")
    p.node("runtime", "service", 30, 490, 845, 64, "Traefik pod (v3.7.14)",
           "a router whose middleware or Secret is missing is logged and skipped,",
           "e.g. Loki read routes while Secret monitoring/loki-read-auth does not exist")
    p.edge("tools", "helm", a_at=(130 - 30) / 270)
    p.edge("tools", "kubectl", a_at=(192 - 30) / 270, via=[(192, 130), (345, 130)])
    p.edge("tools", "argo", a_at=(286.5 - 30) / 270, b_at=0.3, via=[(286.5, 122), (520, 122)], kind="dashed")
    p.edge("moksrepo", "argo", a_at=(560 - 315) / 270, kind="dashed", label="Argo pulls", dx=40)
    p.edge("siterepo", "ci", a_at=(775 - 600) / 270)
    for node, x in (("helm", 130), ("kubectl", 345), ("argo", 560), ("ci", 775)):
        p.edge(node, "api", b_at=(x - 30) / 845, kind="write")
    p.edge("api", "static", a_at=(230 - 30) / 845)
    p.edge("api", "dynamic", a_at=(675 - 30) / 845, label="list/watch", dx=40)
    p.edge("static", "runtime", b_at=(230 - 30) / 845)
    p.edge("dynamic", "runtime", b_at=(675 - 30) / 845)
    return p


FILES = {"traefik-minikube-request-path": request_path, "traefik-minikube-config-flow": config_flow}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    built = []
    for name, make in FILES.items():
        page = make()
        for e in page.edges:
            for x, y in e["points"]:
                if not (0 <= x <= page.w and 0 <= y <= page.h):
                    raise SystemExit(f"{page.figure}: edge {e['id']} leaves the page")
        for n in page.nodes.values():
            if n["x"] < 0 or n["y"] < 0 or n["x"] + n["w"] > page.w or n["y"] + n["h"] > page.h:
                raise SystemExit(f"{page.figure}: {n['id']} leaves the page")
        mxfile = ET.Element("mxfile", host="app.diagrams.net", agent="build_diagrams.py", version="24.7.17", type="device")
        mxfile.append(series.page_xml(page, 0))
        ET.indent(mxfile)
        (HERE / f"{name}.drawio").write_bytes(ET.tostring(mxfile, encoding="utf-8", xml_declaration=False))
        (OUT / f"{page.figure}.svg").write_text(series.page_svg(page), encoding="utf-8")
        built.append((page.figure, page.w, page.h))
    (HERE / "figures.txt").write_text("".join(f"{f} {w} {h}\n" for f, w, h in built), encoding="utf-8")
    print(f"{len(built)} .drawio files and SVGs")


if __name__ == "__main__":
    main()
