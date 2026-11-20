#!/usr/bin/env python3
"""Figures for content/blog/argocd-gitops-deploy-k3s-app-of-apps.mdx (how we deploy to mk4 with Argo CD).

    python3 docs/knowledge-sharing/argocd-mk4/diagrams/build_diagrams.py   # writes the .drawio files
    bash docs/knowledge-sharing/argocd-mk4/diagrams/export.sh              # draw.io CLI → public/images/argocd-mk4/

After editing a .drawio file by hand, run only export.sh, or this script overwrites the edits.

Sources (20 November 2026): moks-tech/kubernetes b74771b (minikube-infrastructure/argocd.tf,
deploy/minikube/argocd/values.yaml, deploy/minikube/applications), mrjithendar/moks-sre 7e09449 (deploy/argocd/,
deploy/helm/moks/templates/_helpers.tpl, scripts/deploy-hetzner.sh, .github/workflows/ci.yml),
mrjithendar/roboshop-ai 6f3a341 (argocd-k3s/), and read-only kubectl and helm on mk4 at about 13:45 UTC.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio_model import Diagram  # noqa: E402

HERE = Path(__file__).resolve().parent
NOTE = 11


def who_deploys_what():
    d = Diagram("argocd-mk4-who-deploys-what", 960, 620, "Who deploys what on mk4: Terraform, Argo CD and one kubectl job")
    repos = (
        ("r-kube", 20, "moks-tech/kubernetes", "minikube-infrastructure/*.tf", "deploy/minikube/argocd"),
        ("r-moks", 255, "mrjithendar/moks-sre", "chart: deploy/helm/moks", "apps: deploy/argocd/hetzner"),
        ("r-robo", 490, "mrjithendar/roboshop-ai", "manifests: services/*", "apps: argocd-k3s/"),
        ("r-site", 725, "moks-tech/jithendar.com", "kubernetes/ manifests", "deploy-kubernetes.yml"),
    )
    for id, x, title, *lines in repos:
        d.node(id, "external", x, 55, 215, 72, title, *lines)
    d.node("tf", "ops", 20, 180, 215, 90, "Terraform", "CI applies on merge", "Helm releases: Istio, Valkey,",
           "CNPG, Harbor, Argo CD ...")
    d.node("argo", "ops", 255, 180, 450, 90, "Argo CD v3.5.5 · namespace argocd", "26 Applications in 3 projects",
           "automated sync + selfHeal, never prune", "polls Git: 120 s + up to 60 s jitter")
    d.node("gha", "ops", 725, 180, 215, 90, "GitHub Actions", "kubectl apply, then", "rollout restart",
           "no Argo CD Application")
    d.edge("r-kube", "tf", exit=(0.5, 1), entry=(0.5, 0), kind="control")
    d.edge("r-moks", "argo", "reads master", exit=(0.5, 1), entry=(0.238, 0))
    d.edge("r-robo", "argo", "reads master", exit=(0.5, 1), entry=(0.76, 0))
    d.edge("r-site", "gha", exit=(0.5, 1), entry=(0.5, 0), kind="control")
    d.edge("tf", "argo", exit=(1, 0.5), entry=(0, 0.5), kind="control")
    d.zone("z-mk4", "mk4 · k3s v1.37 on Hetzner · m1 (cax11) + w1 to w3 (cax21), all arm64", 20, 305, 920, 180, "cluster", valign="bottom")
    d.node("plat", "compute", 40, 345, 200, 106, "Platform namespaces", "istio-system, monitoring", "redis, postgres-db",
           "harbor, embeddings", "argocd")
    d.node("moks", "service", 270, 345, 200, 106, "moks-sre", "9 Applications", "68 tracked resources",
           "1 Helm chart, 8 groups")
    d.node("robo", "service", 500, 345, 200, 106, "roboshop-ai", "17 Applications", "42 tracked resources",
           "kustomize + patches")
    d.node("site", "service", 730, 345, 190, 106, "jithendar", "the site (moks-cms)", "seo-agent", "applied by CI")
    d.edge("tf", "plat", "helm_release", exit=(0.5, 1), entry=(0.5, 0), kind="control")
    d.edge("argo", "moks", "sync", exit=(0.256, 1), entry=(0.5, 0), kind="control")
    d.edge("argo", "robo", "sync", exit=(0.767, 1), entry=(0.5, 0), kind="control")
    d.edge("gha", "site", exit=(0.5, 1), entry=(0.5, 0), kind="control")
    d.text("live", 20, 500, 920, 40,
           "<b>Live, 20 November 2026 at about 13:45 UTC:</b> 25 of 26 Applications Synced and Healthy. moks-foundation "
           "is OutOfSync because two PeerAuthentications left over from the OpenSearch removal are waiting for a prune "
           "that, by design, never comes.", size=12)
    d.legend(555, labels={"external": "Git repository", "ops": "Deployer", "compute": "Platform (Terraform)",
                          "service": "Applications"})
    return d


def app_of_apps():
    d = Diagram("argocd-mk4-app-of-apps", 960, 660, "Two catalog shapes: an app of apps for MOKS, a flat list for RoboShop")
    d.zone("z-moks", "MOKS: app of apps (mrjithendar/moks-sre)", 20, 50, 560, 545, "cluster")
    d.node("script", "ops", 40, 85, 250, 90, "scripts/deploy-hetzner.sh", "preflight: Argo CD, CNPG, Secrets",
           "kubectl apply: 2 projects + root", "waits for Synced/Healthy")
    d.node("root", "ops", 310, 85, 250, 90, "moks-root (project moks-root)", "reads deploy/argocd/hetzner/apps",
           "may only write Applications", "into namespace argocd")
    d.edge("script", "root", exit=(1, 0.5), entry=(0, 0.5), kind="control")
    d.zone("z-kids", "apps/: 8 children named moks-<group>", 40, 200, 520, 160, "plain")
    d.edge("root", "z-kids", "writes", exit=(0.5, 1), entry=(0.76, 0), kind="control")
    kids = (("foundation", 18), ("api", 3), ("worker", 1), ("crewai", 1), ("executor", 26), ("terminal", 8),
            ("routing", 1), ("reranker", 10))
    for i, (name, n) in enumerate(kids):
        x, y = 55 + (i % 4) * 125, 228 + (i // 4) * 65
        d.node(f"k-{name}", "service", x, y, 115, 56, name, f"{n} resource{'s' if n != 1 else ''}")
    d.node("spec", "service", 40, 385, 520, 106, "Every child has the same source", "chart deploy/helm/moks, values-hetzner.yaml",
           "releaseName moks, parameter resourceGroup=<group>", "destination: namespace moks-sre",
           "only foundation: CreateNamespace + namespace labels", align="left")
    d.edge("z-kids", "spec", "renders one group each", exit=(0.5, 1), entry=(0.5, 0), kind="control")
    d.node("opt", "optional", 40, 510, 520, 70, "optional/: not read by the root", "database, migrate, backup render nothing on mk4",
           "move a file into apps/ to turn it on", align="left")
    d.zone("z-robo", "RoboShop: flat catalog (roboshop-ai)", 600, 50, 340, 545, "cluster")
    d.node("apply", "ops", 620, 85, 300, 72, "kubectl apply -k argocd-k3s", "no parent Application", "applied by hand")
    d.node("proj", "security", 620, 180, 300, 74, "AppProject roboshop", "1 repository, 1 namespace", "Secrets denied")
    d.node("apps", "service", 620, 280, 300, 150, "17 Applications, roboshop-<app>", "web, user, cart, catalogue, payment,",
           "shipping, currency, ai-gateway,", "mcp-server, kafka-bridge, moks,", "mongodb, postgres, rabbitmq,",
           "roboshop-config, mesh, routing", "42 resources tracked")
    d.node("patch", "data", 620, 455, 300, 106, "Kustomize patches in the spec", "volumes: gp3-encrypted to", "hcloud-volumes (5 apps)",
           "origin and Turnstile host:", "jithendar.com")
    d.edge("apply", "proj", exit=(0.5, 1), entry=(0.5, 0), kind="control")
    d.edge("proj", "apps", "admits", exit=(0.5, 1), entry=(0.5, 0), kind="control")
    d.edge("apps", "patch", exit=(0.5, 1), entry=(0.5, 0), kind="control")
    d.text("both", 20, 605, 920, 20, "<b>Both:</b> automated sync with selfHeal, prune off, Prune=false,Delete=false on every "
           "Application, no finalizer, source branch master.", size=12)
    d.legend(632, labels={"ops": "Bootstrap or root", "service": "Application", "security": "AppProject",
                          "data": "Patch", "optional": "Present but off"})
    return d


def deploy_loop():
    d = Diagram("argocd-mk4-deploy-loop", 960, 540, "Two kinds of change: Git changes sync themselves, :latest images do not")
    d.zone("z-git", "A chart or manifest changes in Git", 20, 50, 920, 140, "cluster")
    xs = (35, 220, 405, 590, 775)
    chain = (
        ("a1", "external", "PR merged", "to master"),
        ("a2", "ops", "Argo CD notices", "polls every 120 s", "+ up to 60 s jitter"),
        ("a3", "ops", "Render", "helm template or", "kustomize build"),
        ("a4", "ops", "Diff", "live vs rendered:", "OutOfSync"),
        ("a5", "compute", "Applied", "selfHeal, no prune", "Synced + Healthy"),
    )
    for x, (id, kind, title, *lines) in zip(xs, chain):
        d.node(id, kind, x, 85, 160, 80, title, *lines)
    for a, b in zip(("a1", "a2", "a3", "a4"), ("a2", "a3", "a4", "a5")):
        d.edge(a, b, exit=(1, 0.5), entry=(0, 0.5), kind="control")
    d.zone("z-img", "New code under the same image tag (:latest)", 20, 210, 920, 215, "risk")
    d.node("b1", "external", 35, 280, 160, 80, "CI release", "builds the image,", "pushes :latest")
    d.node("b2", "data", 220, 275, 160, 90, "Harbor", "new digest,", "same tag", shape="db")
    d.node("b3", "optional", 405, 280, 160, 80, "Git unchanged", "Argo CD sees", "nothing to sync")
    d.node("b4", "optional", 590, 240, 160, 88, "CI deploy job", "app sync + restart", "action, role moks/ci", "off: MK4_DEPLOY unset")
    d.node("b5", "ops", 590, 340, 160, 72, "Restart by hand", "today: kubectl", "rollout restart")
    d.node("b6", "compute", 775, 280, 160, 80, "New pods", "pull Always,", "roll one by one")
    d.edge("b1", "b2", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("b2", "b3", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("b3", "b4", exit=(1, 0.3), entry=(0, 0.5), kind="control")
    d.edge("b3", "b5", exit=(1, 0.7), entry=(0, 0.5), kind="control")
    d.edge("b4", "b6", exit=(1, 0.5), entry=(0, 0.3), kind="control")
    d.edge("b5", "b6", exit=(1, 0.5), entry=(0, 0.7), kind="control")
    d.text("trap", 20, 440, 920, 40,
           "<b>The trap:</b> a chart change syncs on its own, an image change does not. Merge both without a restart and the "
           "cluster runs the new chart with the old code.", size=12)
    d.legend(495, labels={"external": "GitHub", "ops": "Argo CD or operator", "compute": "Cluster",
                          "data": "Registry", "optional": "No action or switched off"})
    return d


def timeline():
    d = Diagram("argocd-mk4-timeline", 960, 470, "Argo CD on mk4, 8 to 20 November 2026: what changed and what broke")
    xs = (20, 255, 490, 725)
    row1 = (
        ("t1", "ops", "8 Nov", "kubernetes: deploy.py,", "catalog checks and tests", "moks-sre and kubernetes:", "auto-sync switched on"),
        ("t2", "ops", "10 Nov", "Argo CD becomes a", "Terraform release, cache", "on Valkey db 7; moks-root", "+ 7 children created"),
        ("t3", "ops", "11 Nov", "RoboShop catalog", "argocd-k3s: 17 apps", "applied with kubectl,", "volumes on hcloud"),
        ("t4", "security", "16 to 19 Nov", "repository renamed;", "hand-applied projects", "lacked the new URL:", "InvalidSpecError"),
    )
    row2 = (
        ("t5", "ops", "19 Nov", "4 Cloudflare cache fixes", "= Helm revisions 3 to 6", "(12:27 to 13:05 UTC);", "child moks-routing added"),
        ("t6", "ops", "20 Nov, 05:55 UTC", "MOKS moves to", "namespace moks-sre", "(#75, then #77)", "one sync per child"),
        ("t7", "security", "20 Nov, 09:10 UTC", "committed symlink", "frontend/node_modules:", "every MOKS app fails", "to render until #90"),
        ("t8", "security", "20 Nov, 10:27 UTC", "#91 drops OpenSearch:", "2 PeerAuthentications", "stay, OutOfSync, since", "nothing prunes them"),
    )
    for y, row in ((60, row1), (225, row2)):
        for x, (id, kind, title, *lines) in zip(xs, row):
            d.node(id, kind, x, y, 215, 106, title, *lines)
    for a, b in (("t1", "t2"), ("t2", "t3"), ("t3", "t4"), ("t5", "t6"), ("t6", "t7"), ("t7", "t8")):
        d.edge(a, b, exit=(1, 0.5), entry=(0, 0.5), kind="control")
    d.edge("t4", "t5", exit=(0.5, 1), entry=(0.5, 0), via=[(832, 196), (127, 196)], kind="control")
    d.text("note", 20, 350, 920, 40, "Sources: commit times in moks-tech/kubernetes, mrjithendar/moks-sre and roboshop-ai; "
           "Application creation times, sync history and Helm release history read from mk4 on 20 November.", size=NOTE)
    d.arrows_used.clear()  # the arrows only mean "then"
    d.legend(400, labels={"ops": "Change shipped", "security": "Incident or drift"})
    return d


FIGURES = (who_deploys_what, app_of_apps, deploy_loop, timeline)

if __name__ == "__main__":
    names = []
    for build in FIGURES:
        diagram = build()
        (HERE / f"{diagram.name}.drawio").write_text(diagram.xml() + "\n")
        names.append(diagram.name)
        print(f"wrote {diagram.name}.drawio ({diagram.w}x{diagram.h})")
    (HERE / "figures.txt").write_text("\n".join(names) + "\n")
