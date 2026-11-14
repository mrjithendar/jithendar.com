"""Figures of mk4, the k3s cluster on Hetzner Cloud, shared by the articles that describe it.

    python3 sites/jithendar.com/docs/knowledge-sharing/mk4-k3s/diagrams/build_diagrams.py
    bash sites/jithendar.com/docs/knowledge-sharing/mk4-k3s/diagrams/export.sh

writes one .drawio file per figure here (figures.txt lists them), and export.sh uses the draw.io desktop CLI to
export each to public/images/mk4-k3s/<name>.svg and .png. drawio_model.py is a copy of the istio-minikube one.

Facts were checked on 14 November 2026 against hetzner-k3s.yaml and minikube-infrastructure/ in the kubernetes
repository and read-only kubectl on the live cluster (nodes, storage classes, the gateway Service, the CI Role, pod
placement in postgres-db and redis). No IP addresses are drawn.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio_model import Diagram  # noqa: E402

HERE = Path(__file__).resolve().parent


def cluster():
    d = Diagram("mk4-k3s-cluster", 960, 870, "mk4: k3s on Hetzner Cloud, Falkenstein (14 November 2026)")
    d.node("visitor", "client", 35, 56, 270, 56, "Visitors", "browser, docker, psql")
    d.node("dns", "external", 345, 56, 270, 56, "Cloudflare DNS", "jithendar.com, DNS only")
    d.node("gha", "external", 655, 56, 270, 56, "GitHub Actions", "releases and manifest applies")
    d.zone("z-hc", "Hetzner Cloud, location fsn1 (dc14)", 20, 132, 920, 546, valign="bottom")
    d.node("lb", "network", 35, 162, 400, 64, "Load balancer mk4-edge (LB11)", "80 / 443 to the gateway's NodePorts",
           "PROXY protocol, IPv4 and IPv6")
    d.node("fw", "security", 525, 162, 400, 64, "Cloud firewall (from hetzner-k3s)", "SSH and API 6443 allowed",
           "from 0.0.0.0/0 (to tighten)")
    d.zone("z-net", "Private network 10.0.0.0/16, flannel, k3s v1.37.2+k3s1, Ubuntu 24.04, arm64", 35, 246, 890, 400,
           "cluster")
    d.node("master", "compute", 50, 278, 860, 64, "jithendar-master1: cax11, 2 vCPU, 4 GB, 40 GB disk",
           "k3s server and API :6443; taint CriticalAddonsOnly, so no workloads; no API load balancer, no HA")
    workers = [
        ("w1", "worker1", ["valkey-0", "PgBouncer, pgAdmin", "Grafana"]),
        ("w2", "worker2", ["postgres-cluster-1 (primary)", "valkey-1, PgBouncer", "Harbor registry, Loki"]),
        ("w3", "worker3", ["postgres-cluster-2 (replica)", "", ""]),
    ]
    for i, (key, name, pods) in enumerate(workers):
        x = 50 + i * 290
        d.node(key, "compute", x, 362, 280, 56, f"jithendar-pool-workers-{name}", "cax21: 4 vCPU, 8 GB, 80 GB disk")
        lines = [p for p in pods if p]
        d.node(f"{key}-pods", "data", x, 432, 280, 26 + 18 * len(lines), "Stateful pods", *lines)
    d.node("lp", "data", 50, 530, 425, 100, "StorageClass local-path", "a folder on the node's own disk",
           "volume pinned to that node (Retain)", "Postgres, Valkey, Harbor, Loki,", "Prometheus, Grafana")
    d.node("hv", "data", 485, 530, 425, 100, "StorageClass hcloud-volumes (default)", "Hetzner Cloud block volume (CSI)",
           "attached to the pod's node (Delete)", "RoboShop's stateful services")
    d.node("tf", "ops", 20, 696, 450, 72, "Terraform: minikube-infrastructure/", "add-ons as Helm releases: Istio,",
           "cert-manager, CloudNativePG, Valkey, Harbor ...")
    d.node("hk", "ops", 490, 696, 450, 72, "hetzner-k3s.yaml", "servers, network, firewall, k3s version;",
           "cluster autoscaler off")
    d.text("note", 20, 780, 920, 32, "Placement of stateful pods as read on 14 November 2026: the scheduler may move "
           "stateless pods; local-path volumes keep their pods on the same worker. Sources: kubernetes repository and "
           "kubectl.", size=11)
    d.edge("visitor", "dns", exit=(1, 0.5), entry=(0, 0.5), label="lookup")
    d.edge("visitor", "lb", exit=(0.5, 1), entry=(0.33, 0), label="80 / 443")
    d.edge("gha", "fw", exit=(0.5, 1), entry=(0.67, 0), label="6443")
    d.edge("lb", "z-net", exit=(0.5, 1), entry=((235 - 35) / 890, 0), label="private IPs")
    d.edge("fw", "master", exit=(0.5, 1), entry=((725 - 50) / 860, 0))
    d.legend(824)
    return d


def request_path():
    d = Diagram("mk4-k3s-request-path", 960, 640, "mk4 on k3s: how a request reaches an application")
    d.node("visitor", "client", 35, 56, 280, 56, "Visitor", "browser, docker, psql")
    d.node("dns", "external", 360, 56, 280, 56, "Cloudflare DNS", "no proxying")
    d.node("lb", "network", 35, 150, 380, 72, "Hetzner load balancer mk4-edge", "LB11, created by the cloud controller",
           "for the gateway's LoadBalancer Service")
    d.node("np", "network", 545, 150, 380, 72, "NodePorts 31080 / 31443", "on the nodes' private addresses",
           "PROXY protocol header on every connection")
    d.zone("z-gw", "namespace istio-ingress", 20, 246, 920, 140, "cluster")
    d.node("gw", "network", 35, 276, 440, 96, "istio-ingressgateway", "requires the PROXY header (client address)",
           "TLS with the wildcard certificate", "logins and IP allowlists by path")
    d.node("root", "security", 505, 276, 420, 96, "Gateway public + root VirtualService", "one route per path prefix",
           "own hostnames by SNI (registry. ...)", "the site last; www to the apex")
    d.zone("z-apps", "Meshed namespaces: STRICT mTLS from the gateway to every pod", 20, 406, 920, 132, "cluster")
    apps = [("site", "jithendar", "the site"), ("moks", "moks", "/moks"), ("rs", "roboshop-ai", "/roboshop"),
            ("mon", "monitoring", "/grafana ...")]
    for i, (key, ns, path) in enumerate(apps):
        d.node(key, "service", 35 + i * 226, 440, 214, 72, ns, path)
    d.text("note", 20, 548, 920, 32, "Since 10 November 2026. On Minikube (until then) HAProxy on the one server "
           "forwarded 80 and 443 to the same NodePorts. Source: deploy/minikube/istio in the kubernetes repository.",
           size=11)
    d.edge("visitor", "dns", exit=(1, 0.5), entry=(0, 0.5), label="lookup")
    d.edge("visitor", "lb", exit=(0.5, 1), entry=(0.33, 0), label="80 / 443")
    d.edge("lb", "np", exit=(1, 0.5), entry=(0, 0.5), label="TCP + PROXY")
    d.edge("np", "gw", exit=(0.5, 1), entry=(0.5, 0), via=[(735, 236), (255, 236)])
    d.edge("gw", "root", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("root", "z-apps", exit=(0.5, 1), entry=((715 - 20) / 920, 0), label="delegates")
    d.legend(592)
    return d


def ci_api():
    d = Diagram("mk4-k3s-ci-api", 960, 620, "GitHub Actions to the k3s API on mk4")
    d.node("runner", "client", 35, 56, 380, 96, "GitHub-hosted runner, release job", "kubeconfig built at run time from",
           "MK4_API_SERVER, MK4_CA_DATA (variables)", "and MK4_CI_TOKEN (secret)")
    d.node("fw", "security", 545, 56, 380, 96, "Hetzner Cloud firewall", "allowed_networks.api: 0.0.0.0/0",
           "runners have no fixed addresses", "")
    d.zone("z-m", "jithendar-master1 (control plane)", 20, 176, 920, 150, "cluster")
    d.node("api", "network", 35, 208, 380, 104, "k3s API server :6443", "TLS: k3s-server-ca, SANs = node name",
           "and addresses (not jithendar.com)", "CI connects by IP and verifies the CA")
    d.node("auth", "security", 545, 208, 380, 104, "Token to identity, then RBAC", "github-ci-deployer: patch 4 Deployments",
           "github-ci-applier: apply app objects", "no Secrets, no create pods")
    d.zone("z-ns", "namespace jithendar (on the workers)", 20, 346, 920, 140, "cluster")
    d.node("rollout", "ops", 35, 378, 380, 92, "scripts/ci-rollout.py", "kubectl set image ... :pr-<n>",
           "jithendar-com, practice-executor, seo-agent", "")
    d.node("apply", "ops", 545, 378, 380, 92, "deploy-kubernetes.yml", "applies kubernetes/ on merge",
           "keeps each Deployment's running image", "")
    d.text("note", 20, 500, 920, 48, "Tokens are long-lived ServiceAccount token Secrets, issued on 10 November 2026 "
           "when the k3s cluster was set up. The kubeconfig exists only during one step (umask 077, deleted by a trap). "
           "Sources: .github/ in moks-cms, hetzner-k3s.yaml, the live API certificate and Role.", size=11)
    d.edge("runner", "fw", exit=(1, 0.5), entry=(0, 0.5), label="HTTPS 6443")
    d.edge("fw", "api", exit=(0.5, 1), entry=(0.5, 0), via=[(735, 166), (225, 166)])
    d.edge("api", "auth", exit=(1, 0.5), entry=(0, 0.5), label="bearer token")
    d.edge("auth", "rollout", exit=(0.25, 1), entry=(0.75, 0), via=[(640, 336), (320, 336)], kind="control")
    d.edge("auth", "apply", exit=(0.75, 1), entry=(0.75, 0), kind="control")
    d.legend(568)
    return d


FIGURES = [cluster, request_path, ci_api]


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
