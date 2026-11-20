#!/usr/bin/env python3
"""Figures for content/blog/argocd-k3s-hetzner-terraform-helm.mdx (Argo CD on mk4, the k3s cluster on Hetzner).

    python3 docs/knowledge-sharing/argocd-k3s-hetzner/diagrams/build_diagrams.py   # writes the .drawio files
    bash docs/knowledge-sharing/argocd-k3s-hetzner/diagrams/export.sh              # draw.io CLI → public/images/argocd-k3s-hetzner/

After editing a .drawio file by hand, run only export.sh, or this script overwrites the edits.

Sources (20 November 2026): moks-tech/kubernetes b74771b (hetzner-k3s.yaml, minikube-infrastructure/argocd.tf,
redis.tf, istio.tf, deploy/minikube/argocd/values.yaml, deploy/minikube/istio/edge/values.yaml,
deploy/minikube/istio/ingressgateway.yaml), the argo-cd chart 10.10.5 rendered with those values, mrjithendar/moks-sre
cd2f58f (deploy/argocd/), mrjithendar/roboshop-ai d33b00d (argocd-k3s/), and read-only kubectl and helm on mk4.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio_model import Diagram  # noqa: E402

HERE = Path(__file__).resolve().parent
NOTE = 11


def install_layers():
    d = Diagram("argocd-install-layers", 960, 600, "Argo CD on mk4: three layers, three tools, one direction")
    xs = (40, 270, 500, 730)
    w = 190

    d.zone("z1", "1 · Servers and k3s: hetzner-k3s create --config hetzner-k3s.yaml", 20, 50, 920, 150, "plain")
    d.node("cli", "ops", xs[0], 85, w, 95, "hetzner-k3s", "servers, private network,", "firewall rules, k3s,",
           "Hetzner CCM and CSI driver")
    d.node("m1", "compute", xs[1], 85, w, 95, "m1 · cax11", "control plane + etcd", "k3s v1.37.2+k3s1",
           "one master, no API LB")
    d.node("w", "compute", xs[2], 85, w, 95, "w1, w2, w3 · cax21", "4 arm64 vCPU, 8 GiB each",
           "flannel over 10.0.0.0/16", "Falkenstein (fsn1)")
    d.node("hc", "external", xs[3], 85, w, 95, "Hetzner Cloud", "volumes: hcloud-volumes", "LBs for LoadBalancer",
           "Services")
    d.edge("cli", "m1", kind="control", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("m1", "w", kind="control", exit=(1, 0.5), entry=(0, 0.5))

    d.zone("z2", "2 · Add-ons: terraform apply -var-file=vars/mk4.tfvars (minikube-infrastructure/, state in S3)",
           20, 220, 920, 170, "cluster")
    d.node("tf", "ops", xs[0], 255, w, 95, "Terraform", "helm, kubernetes providers", "one root, one state file",
           "CI applies on merge")
    d.node("istio", "network", xs[1], 255, w, 95, "istiod + istio-edge", "sidecars, STRICT mTLS", "Gateway + certificate",
           "routing table: /argocd")
    d.node("valkey", "data", xs[2], 255, w, 95, "Valkey", "namespace redis, Sentinel", "ACL user argocd, db 7",
           shape="db")
    d.node("argocd", "ops", xs[3], 255, w, 95, "helm_release argocd", "chart argo-cd 10.10.5", "Argo CD v3.5.5",
           "values.yaml + checksum")
    d.edge("tf", "istio", kind="control", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("istio", "valkey", kind="control", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("valkey", "argocd", kind="control", exit=(1, 0.5), entry=(0, 0.5))
    d.text("dep", 40, 360, 880, 20, "Left to right is the apply order: argocd depends_on istiod, istio-edge, valkey, "
           "redis-access and its Secret. None of them is an Argo CD Application.", size=NOTE)

    d.zone("z3", "3 · Applications: Argo CD syncs them from Git (automated, selfHeal, never prune)", 20, 410, 920, 150,
           "plain")
    d.node("gh", "external", xs[0], 445, w, 95, "GitHub (public)", "mrjithendar/moks-sre", "mrjithendar/roboshop-ai",
           "HTTPS, no credentials")
    d.node("root", "ops", xs[1], 445, w, 95, "moks-root", "app of apps: writes the", "deploy/argocd/hetzner/apps",
           "Applications, nothing else")
    d.node("moks", "service", xs[2], 445, w, 95, "8 MOKS Applications", "one Helm chart, split", "by resourceGroup",
           "namespace moks-sre")
    d.node("robo", "service", xs[3], 445, w, 95, "17 RoboShop apps", "one per service or layer", "project roboshop",
           "namespace roboshop-ai")
    d.edge("gh", "root", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("root", "moks", kind="control", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("argocd", "robo", "syncs all 26", kind="control", exit=(0.5, 1), entry=(0.5, 0))
    d.text("not", 20, 568, 920, 18, "Not in Argo CD: the jithendar.com site (GitHub Actions, kubectl apply) and every "
           "add-on in layer 2, Argo CD included.", size=NOTE)
    d.legend(596, labels={"ops": "Installer or controller", "external": "Outside the cluster"})
    return d


def request_path():
    d = Diagram("argocd-request-path", 960, 560, "https://jithendar.com/argocd: from the browser to argocd-server")
    d.node("you", "client", 20, 60, 160, 100, "Browser or CLI", "jithendar.com/argocd", "argocd --grpc-web")
    d.node("cf", "network", 210, 60, 220, 100, "Cloudflare (proxied)", "caches by URL alone,", "ignores cookies and Accept",
           "Rocket Loader rewrites HTML")
    d.node("lb", "network", 460, 60, 200, 100, "Hetzner LB11 mk4-edge", "TCP 80/443, PROXY protocol",
           "to NodePorts 31080/31443")
    d.node("gw", "network", 690, 60, 250, 100, "istio-ingressgateway", "TLS: *.jithendar.com (DNS-01)",
           "routing table, first match wins", "/argocd → delegate argocd/argocd")
    d.edge("you", "cf", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("cf", "lb", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("lb", "gw", exit=(1, 0.5), entry=(0, 0.5))

    d.zone("z-ns", "namespace argocd · VirtualService argocd (extraObjects)", 20, 205, 920, 270, "cluster")
    d.text("why", 40, 240, 270, 200,
           "<b>Why two routes</b><br>Argo CD sends no Cache-Control on API GETs. A page request that does not "
           "accept text/html (curl, a probe) gets the file as built, with &lt;base href=\"/\"&gt;, or a 404. "
           "Cloudflare cached all of these by URL and served them to every browser.", size=NOTE)
    d.node("api", "network", 330, 240, 290, 95, "argocd-api: /argocd/api/", "response: cache-control",
           "no-store, no-transform", "commits fe3efdd, 1f76443")
    d.node("ui", "network", 640, 240, 290, 95, "argocd: everything else", "request: accept: text/html",
           "response: adds no-transform", "8f5eb06, 6f93d92, 1f76443")
    d.node("srv", "service", 330, 360, 600, 95, "argocd-server :80", "plain HTTP inside the mesh (server.insecure)",
           "serves under /argocd itself (rootpath, basehref): never strip the prefix",
           "UI, REST API and gRPC-web")
    d.edge("gw", "api", "/argocd/api/*", exit=(0.1, 1), entry=(0.5, 0), via=[(715, 185), (475, 185)])
    d.edge("gw", "ui", "/argocd/*", exit=(0.38, 1), entry=(0.5, 0))
    d.edge("api", "srv", exit=(0.5, 1), entry=(0.2417, 0))
    d.edge("ui", "srv", exit=(0.5, 1), entry=(0.7583, 0))

    d.text("fixes", 20, 485, 920, 36,
           "<b>Fixed on 19 November 2026, Helm revisions 3 to 6:</b> a cached /argocd/ with the wrong base (blank page), "
           "a cached signed-out userinfo (login loop) and a signed-in /api/v1/clusters served to anyone, a curl's cached "
           "404 for /argocd/applications, and Rocket Loader holding back main.js (blank page).", size=NOTE)
    d.legend(532, labels={"service": "Argo CD", "network": "Network and routing"})
    return d


def helm_values():
    d = Diagram("argocd-helm-values", 960, 920,"deploy/minikube/argocd/values.yaml: what each block makes the argo-cd chart render")
    d.text("hl", 20, 44, 420, 18, "<b>Values (values.yaml, plus one block from Terraform)</b>", color="#0f172a")
    d.text("hr", 520, 44, 420, 18, "<b>Rendered by chart 10.10.5 (Argo CD v3.5.5)</b>", color="#0f172a")
    rows = (
        (("ops", "configs.cm", "url: https://jithendar.com/argocd",
          "admin.enabled: true · users.anonymous.enabled: false"),
         ("data", "ConfigMap argocd-cm", "the external URL (links, SSO callbacks), the local", "admin user on, anonymous off")),
        (("ops", "configs.params", "server.insecure: true · server.rootpath: /argocd",
          "server.basehref: /argocd · redis.db: \"7\""),
         ("data", "ConfigMap argocd-cmd-params-cm", "read by every component as env vars; the chart adds",
          "redis.server = valkey-master.redis...:6379")),
        (("ops", "configs.rbac", "policy.default: ''", "(no default role for signed-in users)"),
         ("data", "ConfigMap argocd-rbac-cm", "a user without a role gets nothing;",
          "admin is role:admin built in")),
        (("ops", "server · controller · repoServer", "replicas: 1 each; Service ClusterIP; no Ingress",
          "requests 50m/128Mi, 100m/256Mi, 100m/256Mi"),
         ("compute", "argocd-server, -repo-server (Deployments)", "argocd-application-controller (StatefulSet)",
          "limits 500m/512Mi, 1/1Gi, 1/1Gi")),
        (("ops", "redis / redis-ha: enabled: false", "externalRedis: valkey-master.redis.svc...:6379",
          "existingSecret: argocd-redis-valkey"),
         ("optional", "No Redis pod", "REDIS_USERNAME and REDIS_PASSWORD from the",
          "Secret Terraform writes (argocd.tf)")),
        (("ops", "dex · notifications: enabled: false", "no SSO connector, no notification", "controller"),
         ("optional", "Not rendered", "no argocd-dex-server, no", "argocd-notifications-controller")),
        (("ops", "applicationSet: enabled: false", "this chart has no such switch", "(the key is ignored)"),
         ("compute", "argocd-applicationset-controller", "rendered anyway, and running", "(no ApplicationSet exists)")),
        (("ops", "extraObjects", "rendered as they are, released with the", "chart: one helm upgrade for everything"),
         ("network", "VirtualService argocd", "the /argocd delegate (two routes)", "NetworkPolicy istio-sidecars")),
        (("ops", "Terraform: global.podAnnotations", "checksum/redis = sha1(the Valkey password)",
          "a new password changes it"),
         ("compute", "Every pod rolls", "when the password changes, so no pod keeps", "a password Valkey no longer accepts")),
        (("ops", "Chart defaults we keep", "crds.install, crds.keep: true",
          "global.networkPolicy.create: true"),
         ("security", "3 CRDs + 3 NetworkPolicies", "CRDs keep on uninstall (resource-policy)",
          "ingress policies: server, repo-server, controller")),
    )
    y = 72
    for i, ((lk, lt, *ll), (rk, rt, *rl)) in enumerate(rows):
        d.node(f"v{i}", lk, 20, y, 420, 70, lt, *ll, align="left")
        d.node(f"r{i}", rk, 520, y, 420, 70, rt, *rl, align="left")
        d.edge(f"v{i}", f"r{i}", exit=(1, 0.5), entry=(0, 0.5))
        y += 80
    d.text("merge", 20, y + 4, 920, 34,
           "Merge order: the chart's 4,951-line values.yaml, then our file, then Terraform's yamlencode() block. Rendered: "
           "33,555 lines, 30,890 of them the three CRDs. Inspect with helm show values and helm template.", size=NOTE)
    d.legend(y + 50, labels={"ops": "Values we set", "data": "ConfigMaps", "compute": "Workloads",
                             "optional": "Not rendered", "network": "Routing objects", "security": "Policy and CRDs"})
    return d


def components():
    d = Diagram("argocd-components", 960, 560, "Inside namespace argocd: four pods, a shared cache, Git and the API")
    d.zone("z-ns", "namespace argocd · istio-injection=enabled (pods 2/2)", 230, 50, 500, 395,
           "cluster")
    d.node("you", "client", 20, 80, 180, 88, "You", "browser at /argocd", "argocd CLI (gRPC-web)")
    d.node("gh", "external", 20, 230, 180, 88, "GitHub", "moks-sre, roboshop-ai", "public HTTPS,", "no repo credentials")
    d.node("srv", "service", 250, 80, 220, 88, "argocd-server", "UI, REST and gRPC API", "login, RBAC, sessions",
           "about 102 Mi in use")
    d.node("repo", "ops", 250, 230, 220, 88, "argocd-repo-server", "git fetch, then helm template", "or kustomize build",
           "about 56 Mi in use")
    d.node("ctrl", "ops", 490, 80, 220, 88, "application-controller", "StatefulSet, one replica",
           "desired (Git) vs live (API)", "about 298 Mi in use")
    d.node("aset", "optional", 490, 230, 220, 88, "applicationset-controller", "running, but no", "ApplicationSet exists",
           "about 44 Mi in use")
    d.node("pol", "security", 250, 350, 460, 75, "NetworkPolicies (ingress)", "chart: server, repo-server, controller",
           "ours: monitoring → sidecar ports 15020, 15090")
    d.node("vk", "data", 760, 60, 180, 110, "Valkey", "valkey-master.redis", "ACL user argocd", "database 7 only",
           "mTLS (STRICT)", shape="db")
    d.node("api", "compute", 760, 230, 180, 88, "Kubernetes API", "Applications (CRDs)", "live objects",
           "apply on sync")
    d.node("apps", "service", 760, 350, 180, 75, "Workloads", "ns moks-sre (8 apps)", "ns roboshop-ai (17)")
    d.edge("you", "srv", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("srv", "repo", "manifests", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("repo", "gh", "git fetch", exit=(0, 0.5), entry=(1, 0.5))
    d.edge("ctrl", "repo", "render", exit=(0.1, 1), entry=(0.77, 0), via=[(512, 200), (419, 200)])
    d.edge("ctrl", "vk", "cache", exit=(1, 0.3), entry=(0, 0.42))
    d.edge("ctrl", "api", "watch, sync", exit=(1, 0.8), entry=(0, 0.3), via=[(735, 150), (735, 256)])
    d.edge("api", "apps", exit=(0.5, 1), entry=(0.5, 0))
    d.text("cache", 20, 455, 920, 34,
           "server, repo-server and controller all cache in Valkey (manifests, app state, sessions); every key has a TTL, so "
           "Valkey may evict it and Argo CD recomputes it. In use on 20 November 2026: about 500 Mi for Argo CD, "
           "plus about 166 Mi for four sidecars.", size=NOTE)
    d.legend(505, labels={"service": "Argo CD API", "ops": "Argo CD controllers", "optional": "Running, unused",
                          "security": "Policy", "external": "Outside the cluster"})
    return d


FIGURES = (install_layers, request_path, helm_values, components)

if __name__ == "__main__":
    names = []
    for make in FIGURES:
        d = make()
        (HERE / f"{d.name}.drawio").write_text(d.xml() + "\n")
        names.append(d.name)
        print(f"{d.name}.drawio  {d.w}x{d.h}")
    (HERE / "figures.txt").write_text("\n".join(names) + "\n")
