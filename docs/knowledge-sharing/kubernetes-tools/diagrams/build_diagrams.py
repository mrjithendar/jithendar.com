#!/usr/bin/env python3
"""Figures for the two-part Kubernetes tools series: editable .drawio files and matching SVGs.

Reuses the layout, palette and draw.io writer of the RoboShop AI series. Run from www/. The SVGs are rendered here,
not exported by draw.io: if a .drawio file is edited by hand, re-export it from draw.io over the SVG.
Versions are the latest stable releases on 2026-11-08; the mk4 figure follows a read-only inspection of the
cluster on the same day (tools d929c74, moks 3a02127, roboshop-ai 02a4478, jithendar.com a8b3390).
"""
import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[3] / "public" / "images" / "kubernetes-tools"
spec = importlib.util.spec_from_file_location("series_diagrams", HERE.parents[1] / "roboshop-ai" / "diagrams" / "build_diagrams.py")
series = importlib.util.module_from_spec(spec)
sys.modules["series_diagrams"] = series
spec.loader.exec_module(series)
Page = series.Page

COLS4 = (30, 245, 460, 675)  # x of four 195px-wide columns
COLS3 = (30, 315, 600)       # x of three 270px-wide columns


def at(node_x, node_w, x):
    """Relative anchor for an absolute x on a node edge."""
    return (x - node_x) / node_w


def ecosystem():
    p = Page("k8s-tools-ecosystem", "Ecosystem map", 900, 660,
             "The 15 Kubernetes tools in this series, grouped by the problem each one solves",
             "Five rows group the tools. Deliver: Helm 4.3, Kustomize 5.8, Argo CD 3.6 and Flux 2.10. Operate and observe: "
             "kubectl as the baseline, K9s 0.51, Lens from Mirantis and Prometheus 3.16. These two rows are Part 1. Scale: KEDA 2.21 "
             "and Karpenter 1.15, with the built-in HPA and Cluster Autoscaler as alternatives. Connect: Cilium 1.20, Istio 1.31 and "
             "Linkerd 2.20. Secure and recover: cert-manager 1.21, Kyverno 1.19 and Velero 1.18. These three rows are Part 2. "
             "Each box gives the CNCF status checked on 8 November 2026.")
    rows = [
        ("Deliver: package, configure and sync (Part 1)", [
            ("service", "Helm 4.3", "charts, values, releases", "CNCF graduated"),
            ("service", "Kustomize 5.8", "bases, overlays, patches", "Kubernetes SIG CLI project"),
            ("gateway", "Argo CD 3.6", "GitOps with a web UI", "CNCF graduated (Argo)"),
            ("gateway", "Flux 2.10", "GitOps as controllers + CRDs", "CNCF graduated"),
        ]),
        ("Operate and observe (Part 1)", [
            ("external", "kubectl", "the baseline every tool uses", "ships with Kubernetes"),
            ("browser", "K9s 0.51", "terminal UI over kubeconfig", "independent, Apache 2.0"),
            ("browser", "Lens (Mirantis)", "desktop IDE, freemium", "not a CNCF project"),
            ("store", "Prometheus 3.16", "metrics, PromQL, alert rules", "CNCF graduated"),
        ]),
        ("Scale (Part 2)", [
            ("agent", "KEDA 2.21", "event-driven pod scaling", "CNCF graduated"),
            ("agent", "Karpenter 1.15 (AWS)", "just-in-time nodes", "Kubernetes SIG Autoscaling"),
            ("external", "Built-in alternatives", "HPA (pods)", "Cluster Autoscaler 1.37"),
        ]),
        ("Connect (Part 2)", [
            ("mcp", "Cilium 1.20", "eBPF CNI, policy, Hubble", "CNCF graduated"),
            ("mcp", "Istio 1.31", "mesh: sidecar or ambient", "CNCF graduated"),
            ("mcp", "Linkerd 2.20", "lightweight mesh, Rust proxy", "OSS ships edge builds only"),
        ]),
        ("Secure and recover (Part 2)", [
            ("edge", "cert-manager 1.21", "issues and renews TLS", "CNCF graduated"),
            ("edge", "Kyverno 1.19", "policy as code, CEL", "CNCF graduated (2026)"),
            ("bus", "Velero 1.18", "backup, restore, migrate", "CNCF sandbox (2026)"),
        ]),
    ]
    y = 12
    for label, items in rows:
        p.zone(label, 15, y, 870, 112)
        cols = COLS4 if len(items) == 4 else COLS3
        w = 195 if len(items) == 4 else 270
        for i, (kind, title, *lines) in enumerate(items):
            p.node(f"n{y}-{i}", kind, cols[i], y + 28, w, 72, title, *lines)
        y += 124
    p.note(15, 632, "Versions: latest stable release on 8 Nov 2026. Same-row tools often compete; you rarely need all of a row.", size=12)
    return p


def gitops_flow():
    p = Page("k8s-tools-gitops-flow", "GitOps loop", 900, 640,
             "How Argo CD turns a Git commit into running workloads, and how drift is detected",
             "A GitHub repository holds Applications, Helm charts and Kustomize overlays; CI builds and pushes images and may "
             "commit a new tag. In namespace argocd, the repo-server clones Git and renders manifests with helm template or "
             "kustomize build. The application-controller compares the rendered manifests with live objects, reports Synced or "
             "OutOfSync and a health status, and applies changes through the Kubernetes API on a manual or automated sync. "
             "argocd-server serves the UI, API, CLI, SSO and RBAC. The ApplicationSet controller generates Applications from "
             "lists, Git directories or registered clusters. Changes made directly in the cluster, such as kubectl edit, are drift; "
             "selfHeal reverts fields that Git owns. Flux runs the same loop with source-, kustomize- and helm-controller and no "
             "built-in UI.")
    p.zone("Git: the desired state", 15, 12, 870, 104)
    p.zone("Argo CD, namespace argocd", 15, 132, 870, 206)
    p.zone("Kubernetes API", 15, 354, 870, 76)
    p.zone("Cluster", 15, 446, 870, 120)
    p.node("repo", "external", 30, 36, 400, 70, "GitHub repository", "Applications, charts/, overlays/",
           "every change is a reviewed commit")
    p.node("ci", "external", 470, 36, 400, 70, "CI pipeline", "builds and pushes the image",
           "may commit the new tag back to Git")
    p.node("repo-server", "gateway", 30, 156, 260, 92, "argocd-repo-server", "clones Git, runs helm template",
           "or kustomize build", "output: plain manifests")
    p.node("controller", "gateway", 320, 156, 260, 92, "application-controller", "diffs rendered vs live objects",
           "Synced / OutOfSync + health", "applies on sync: manual or auto")
    p.node("server", "gateway", 610, 156, 260, 92, "argocd-server", "UI, API and CLI endpoint",
           "SSO, projects, RBAC", "diff and sync history")
    p.node("appset", "agent", 30, 262, 260, 64, "ApplicationSet controller",
           "creates Applications from", "lists, Git dirs or clusters")
    p.node("api", "store", 30, 376, 840, 46, "kube-apiserver",
           "stores objects; admission webhooks (Kyverno, cert-manager, mesh injectors) run on every write")
    p.node("work", "service", 30, 470, 400, 80, "Workloads", "Deployments, Services, ConfigMaps",
           "what Git declares")
    p.node("drift", "reject", 470, 470, 400, 80, "Drift", "kubectl edit, scale, hot fixes",
           "selfHeal reverts fields Git owns", "HPA-owned replicas need ignoreDifferences")
    p.note(15, 580, "Flux runs the same loop as controllers: source-controller fetches, kustomize-controller and", size=12)
    p.note(15, 598, "helm-controller apply. Pick one controller per workload; two would fight over the same objects.", size=12)
    p.edge("repo", "repo-server", a_at=at(30, 400, 160), b_at=0.5, label="git fetch", dx=40, t=-0.55)
    p.edge("ci", "repo", a_side="l", b_side="r", label="tag commit", dy=-12, kind="dashed")
    p.edge("repo-server", "controller", a_side="r", b_side="l", a_at=0.4, b_at=0.4)
    p.edge("server", "controller", a_side="l", b_side="r", a_at=0.4, b_at=0.4, kind="dashed")
    p.edge("controller", "api", a_at=0.5, b_at=at(30, 840, 450), kind="write", label="apply", dx=30)
    p.edge("api", "work", a_at=at(30, 840, 230), b_at=0.5)
    p.edge("drift", "work", a_side="l", b_side="r", label="changes live state", dy=-12, kind="reject")
    return p


def prometheus_flow():
    p = Page("k8s-tools-prometheus-flow", "Prometheus data flow", 900, 640,
             "How Prometheus discovers, scrapes, stores and alerts on Kubernetes metrics",
             "Targets expose metrics over HTTP: the kubelet and cAdvisor for nodes and containers, applications on their "
             "own /metrics endpoint, and exporters such as kube-state-metrics for object state like restarts. "
             "kubernetes_sd_configs asks the API for nodes, pods or EndpointSlices and relabel rules pick the targets; "
             "the optional Prometheus Operator turns ServiceMonitor and PodMonitor objects into that scrape configuration. "
             "Prometheus pulls every target on its scrape interval, stores samples in its local TSDB, evaluates recording and "
             "alerting rules, and can remote_write to long-term storage. Alertmanager groups and routes alerts to people; Grafana "
             "queries PromQL for dashboards. Logs and traces travel through separate systems such as Loki and Jaeger.")
    p.zone("Targets: anything that serves /metrics", 15, 12, 870, 104)
    p.zone("Discovery", 15, 142, 870, 104)
    p.zone("Prometheus server", 15, 262, 870, 114)
    p.zone("Consumers", 15, 392, 870, 104)
    p.zone("Not metrics: separate pipelines", 15, 512, 870, 96)
    p.node("kubelet", "service", COLS3[0], 36, 270, 70, "kubelet and cAdvisor", "node and container metrics",
           "CPU, memory, filesystem")
    p.node("app", "service", COLS3[1], 36, 270, 70, "Applications", "their own /metrics endpoint",
           "HTTP rate, errors, latency")
    p.node("exporters", "service", COLS3[2], 36, 270, 70, "Exporters", "kube-state-metrics, node-exporter",
           "object state: restarts, replicas")
    p.node("sd", "gateway", 30, 166, 400, 70, "kubernetes_sd_configs", "roles: node, pod, endpointslice ...",
           "relabel_configs keep or drop targets")
    p.node("operator", "agent", 470, 166, 400, 70, "Prometheus Operator (optional)", "ServiceMonitor, PodMonitor, PrometheusRule",
           "generates scrape config and rule files")
    p.node("prom", "store", 30, 286, 840, 80, "Prometheus",
           "pulls each target every scrape_interval and writes samples to a local TSDB on a volume",
           "recording rules precompute expensive PromQL; alerting rules fire when an expression holds",
           "retention by time or size; remote_write ships samples to long-term storage")
    p.node("am", "bus", COLS3[0], 416, 270, 70, "Alertmanager", "group, inhibit, silence",
           "routes to Slack, PagerDuty, mail")
    p.node("grafana", "browser", COLS3[1], 416, 270, 70, "Grafana", "dashboards over PromQL",
           "also reads Loki and Jaeger")
    p.node("lts", "external", COLS3[2], 416, 270, 70, "Long-term storage", "Thanos, Mimir, managed services",
           "fed by remote_write")
    p.node("logs", "absent", 30, 536, 400, 62, "Logs: Loki, Elasticsearch", "what happened, line by line")
    p.node("traces", "absent", 470, 536, 400, 62, "Traces: Jaeger, Tempo", "where one request spent its time")
    for node, x in (("kubelet", 165), ("exporters", 735)):
        p.edge(node, "prom", a_at=0.5, b_at=at(30, 840, 450), via=[(x, 128), (450, 128)])
    p.edge("app", "prom", a_at=0.5, b_at=at(30, 840, 450), label="scrape (HTTP pull)", dx=70, t=-0.86)
    p.edge("operator", "sd", a_side="l", b_side="r", a_at=0.8, b_at=0.8, kind="dashed")
    p.edge("sd", "prom", a_at=at(30, 400, 230), b_at=at(30, 840, 230), label="target list", dx=48)
    p.edge("prom", "am", a_at=at(30, 840, 165), b_at=0.5, kind="async", label="alerts", dx=30)
    p.edge("grafana", "prom", a_side="t", b_side="b", b_at=at(30, 840, 450), label="PromQL", dx=32)
    p.edge("prom", "lts", a_at=at(30, 840, 735), b_at=0.5, kind="write", label="remote_write", dx=50)
    return p


def mk4_lab():
    p = Page("k8s-tools-mk4-lab", "mk4 lab today", 900, 780,
             "What runs on the mk4 Minikube lab on 8 November 2026, and what does not",
             "One Hetzner server with 16 vCPU and 32 GB RAM runs Docker and the Minikube profile mk4: eight nodes on Kubernetes "
             "v1.37.0 with the kindnet CNI, sharing the host's CPU and memory. Delivery: Argo CD v3.5.5 from Helm chart 10.10.5 "
             "with 35 live Applications synced by hand except Harbor; Helm charts and Kustomize directories as Argo sources; "
             "jithendar.com applied with kubectl apply -k. Edge and TLS: Traefik v3.7.14, cert-manager v1.20.4 with two Let's "
             "Encrypt ClusterIssuers and four Certificates, Harbor 2.15.4 as the registry. Observability: Prometheus v3.15.0 with "
             "hand-written scrape jobs and no Alertmanager or Operator, Grafana, Loki, Alloy, Jaeger and an OpenTelemetry "
             "Collector. Present but broken: Velero CRDs, an R2 storage location and a daily schedule with no Velero server since "
             "1 November, and 29 Applications for the deleted EKS cluster in status Unknown. Not installed: Flux, Karpenter, KEDA, "
             "Istio, Linkerd, Cilium, Kyverno and kube-state-metrics. kubectl and K9s run on a laptop with a kubeconfig from the "
             "tools repository.")
    p.node("laptop", "browser", 30, 12, 840, 46, "Laptop: kubectl and K9s",
           "kubeconfig from tools/deploy/minikube/kubeconfig.sh, context mk4")
    p.zone("Hetzner server: 16 vCPU, 32 GB RAM, Docker", 15, 90, 870, 680, "br")
    p.zone("Minikube profile mk4: 8 nodes, Kubernetes v1.37.0, kindnet CNI, hostPath storage", 30, 108, 840, 638)
    rows = [
        ("Delivery", [
            ("gateway", "Argo CD v3.5.5", "Helm chart 10.10.5", "35 live Applications", "manual sync, Harbor auto"),
            ("service", "Helm", "Argo sources: Grafana, Harbor,", "metrics-server, MOKS chart", "Traefik installed by hand"),
            ("service", "Kustomize", "RoboShop apps through Argo", "jithendar.com: apply -k", "from its kubernetes/ folder"),
        ]),
        ("Edge, TLS and registry", [
            ("edge", "Traefik v3.7.14", "the only way in from outside", "Ingress + Traefik CRDs", "HAProxy on the host in front"),
            ("edge", "cert-manager v1.20.4", "2 ClusterIssuers (ACME)", "4 Certificates, all Ready", "HTTP-01 through Traefik"),
            ("store", "Harbor 2.15.4", "registry.jithendar.com", "images pulled as :latest", "synced by Argo CD"),
        ]),
        ("Observability", [
            ("store", "Prometheus v3.15.0", "kubelet, cAdvisor, dns_sd jobs", "alert rules, no Alertmanager", "no Operator, no KSM"),
            ("service", "Grafana, Loki, Alloy", "dashboards and logs", "Alloy ships pod logs", "Grafana chart 14.0.1"),
            ("service", "Jaeger + OTel Collector", "traces from the site", "and MOKS", "in namespace observability"),
        ]),
        ("Present but not working", [
            ("reject", "Velero (no server)", "CRDs, R2 location, schedule", "last backup 1 Nov 2026", "7 requests never ran"),
            ("reject", "29 stale Applications", "roboshop-demo-* for EKS", "cluster deleted 2 Nov", "status Unknown"),
        ]),
    ]
    y = 140
    for label, items in rows:
        p.note(45, y - 2, label, size=12, bold=True)
        cols = COLS3 if len(items) == 3 else (45, 460)
        w = 240 if len(items) == 3 else 395
        for i, (kind, title, *lines) in enumerate(items):
            x = cols[i] + (15 if len(items) == 3 else 0)
            p.node(f"r{y}-{i}", kind, x, y + 16, w, 94, title, *lines)
        y += 128
    p.note(45, y - 2, "Not installed (Part 2 candidates)", size=12, bold=True)
    p.node("absent", "absent", 45, y + 16, 810, 64, "Flux, Karpenter, KEDA, Istio, Linkerd, Cilium, Kyverno, kube-state-metrics",
           "kindnet has no FQDN policy; Minikube volumes are hostPath, which Velero file backup does not support")
    p.edge("laptop", "r140-0", a_at=at(30, 840, 175), b_at=0.5, kind="dashed", label="kubeconfig", dx=40, t=-0.72)
    return p


def production():
    p = Page("k8s-tools-production", "Production architecture", 900, 780,
             "How the 15 tools fit one production platform: change path, request path and telemetry",
             "Three flows run through the platform. Change path, in amber: a commit in Git is rendered by Argo CD or Flux with "
             "Helm or Kustomize and applied to the Kubernetes API, where Kyverno admission policies accept, mutate or reject it. "
             "Request path, in grey: users reach a cloud load balancer, then an Ingress or Gateway API gateway whose TLS "
             "certificate cert-manager obtains from an ACME issuer, then pods. Inside the cluster Cilium provides the pod network, "
             "NetworkPolicy and Hubble flow logs, and an optional mesh, Istio or Linkerd, adds mutual TLS, retries and traffic "
             "splitting. KEDA feeds event metrics to an HPA; when new pods cannot be scheduled, Karpenter launches nodes from "
             "NodePools. Telemetry, dashed: Prometheus scrapes nodes, pods and mesh proxies and sends alerts to Alertmanager. "
             "Velero copies API objects and volume data to object storage. K9s and Lens are operator tools outside the request path.")
    p.zone("Change path", 15, 12, 870, 104)
    p.node("git", "external", 30, 36, 250, 70, "Git repository", "apps, charts, overlays",
           "policies and NodePools too")
    p.node("gitops", "gateway", 325, 36, 250, 70, "Argo CD or Flux", "renders Helm or Kustomize",
           "applies and reverts drift")
    p.node("api", "store", 620, 36, 250, 70, "kube-apiserver", "admission: Kyverno accepts,",
           "mutates or rejects each write")
    p.zone("Request path", 15, 132, 870, 104)
    p.node("users", "browser", 30, 156, 250, 70, "Users", "HTTPS")
    p.node("lb", "edge", 325, 156, 250, 70, "Cloud load balancer", "NLB on EKS, NodePort + proxy",
           "on a self-managed host")
    p.node("gw", "edge", 620, 156, 250, 70, "Ingress or Gateway API", "Istio, Traefik, Envoy Gateway",
           "TLS Secret from cert-manager")
    p.zone("Cluster data plane", 15, 252, 870, 254)
    p.node("pods", "service", 30, 276, 395, 98, "Workload pods", "mesh proxy per pod (sidecar) or per node",
           "(ambient ztunnel, Linkerd has sidecars only)", "mTLS, retries, canary weights")
    p.node("cilium", "mcp", 475, 276, 395, 98, "Cilium on every node", "eBPF pod network and Service load balancing",
           "NetworkPolicy and CiliumNetworkPolicy", "Hubble: who talked to whom")
    p.node("keda", "agent", 30, 394, 260, 98, "KEDA", "reads queue depth, lag,", "PromQL or cron", "feeds an HPA")
    p.node("hpa", "agent", 320, 394, 260, 98, "HorizontalPodAutoscaler", "sets replicas", "new pods may be Pending",
           "when nodes are full")
    p.node("karpenter", "agent", 610, 394, 260, 98, "Karpenter", "Pending pods → NodeClaim", "→ EC2 instance", "consolidates idle nodes")
    p.zone("Platform services", 15, 522, 870, 114)
    p.node("cm", "edge", 30, 546, 195, 80, "cert-manager", "ACME HTTP-01 / DNS-01", "renews before expiry")
    p.node("prom", "store", 245, 546, 195, 80, "Prometheus", "scrapes nodes, pods,", "mesh, KEDA, Karpenter")
    p.node("am", "bus", 460, 546, 195, 80, "Alertmanager", "routes alerts", "to on-call")
    p.node("velero", "bus", 675, 546, 195, 80, "Velero", "objects + volumes", "→ object storage")
    p.zone("Outside the cluster", 15, 652, 870, 116)
    p.node("acme", "external", 30, 676, 260, 80, "ACME CA", "Let's Encrypt", "issues certificates")
    p.node("s3", "external", 320, 676, 260, 80, "Object storage", "S3, R2, GCS", "backups land here")
    p.node("ops", "browser", 610, 676, 260, 80, "Operators", "kubectl, K9s, Lens", "read through RBAC")
    p.edge("git", "gitops", a_side="r", b_side="l", kind="write")
    p.edge("gitops", "api", a_side="r", b_side="l", kind="write", label="apply", dy=-12)
    p.edge("users", "lb", a_side="r", b_side="l")
    p.edge("lb", "gw", a_side="r", b_side="l")
    p.edge("gw", "pods", a_at=0.3, b_at=at(30, 395, 320), via=[(695, 250), (320, 250)])
    p.edge("keda", "hpa", a_side="r", b_side="l")
    p.edge("hpa", "karpenter", a_side="r", b_side="l", label="Pending", dy=-12)
    p.edge("prom", "am", a_side="r", b_side="l", kind="async")
    p.edge("cm", "acme", a_at=at(30, 195, 200), b_at=at(30, 260, 200), kind="dashed")
    p.edge("velero", "s3", a_at=0.5, b_at=at(320, 260, 520), via=[(772.5, 646), (520, 646)], kind="write")
    return p


def autoscaling():
    p = Page("k8s-tools-autoscaling-chain", "Autoscaling chain", 900, 540,
             "From a queue backlog to a new node: KEDA scales pods, Karpenter scales nodes",
             "Messages pile up in a RabbitMQ queue. The KEDA operator polls the queue through its scaler and, through the "
             "external metrics API served by keda-operator-metrics-apiserver, feeds an HPA named keda-hpa-<name> that it creates "
             "and owns. The HPA raises the Deployment's replicas between minReplicaCount and maxReplicaCount. If no node has room, "
             "the new pods stay Pending. Karpenter watches unschedulable pods, picks instance types allowed by a NodePool and its "
             "EC2NodeClass, creates a NodeClaim and launches an EC2 instance, which joins the cluster so the scheduler can bind "
             "the pods. When the queue drains, the HPA scales down after its stabilization window and Karpenter consolidates "
             "empty or underused nodes within the NodePool's disruption budgets.")
    p.zone("Pod scaling: KEDA and the HPA", 15, 12, 870, 160)
    p.node("queue", "bus", 30, 40, 195, 110, "RabbitMQ queue", "roboshop.shipping.orders", "backlog grows", "e.g. 120 messages")
    p.node("keda", "agent", 245, 40, 195, 110, "KEDA operator", "polls every 15 s", "metrics API server", "exposes the value")
    p.node("hpa", "agent", 460, 40, 195, 110, "HPA keda-hpa-*", "owned by KEDA", "target 20 per replica", "→ wants 6, max 4")
    p.node("deploy", "service", 675, 40, 195, 110, "Deployment", "replicas 1 → 4", "new pods created", "scheduler runs")
    p.zone("Node scaling: Karpenter", 15, 196, 870, 160)
    p.node("node", "external", 30, 224, 195, 110, "EC2 instance", "joins as a node", "scheduler binds", "the Pending pods")
    p.node("claim", "agent", 245, 224, 195, 110, "NodeClaim", "one per launch", "status shows", "launch errors")
    p.node("karpenter", "agent", 460, 224, 195, 110, "Karpenter", "batches Pending pods", "fits NodePool rules", "cheapest that fits")
    p.node("pending", "reject", 675, 224, 195, 110, "Pending pods", "no node has room", "FailedScheduling", "event on each pod")
    p.zone("Scale down", 15, 380, 870, 148)
    p.node("down1", "service", 30, 404, 400, 108, "Pods", "queue drains; the HPA waits out", "its scale-down stabilization window",
           "cooldownPeriod applies only to 1 → 0")
    p.node("down2", "agent", 470, 404, 400, 108, "Nodes", "Karpenter consolidates empty or", "underused nodes, one budget at a time",
           "PodDisruptionBudgets still apply")
    for a, b in (("queue", "keda"), ("keda", "hpa"), ("hpa", "deploy")):
        p.edge(a, b, a_side="r", b_side="l")
    p.edge("deploy", "pending", a_at=0.5, b_at=0.5)
    for a, b in (("pending", "karpenter"), ("karpenter", "claim"), ("claim", "node")):
        p.edge(a, b, a_side="l", b_side="r")
    return p


def service_mesh():
    p = Page("k8s-tools-service-mesh", "Service mesh planes", 900, 600,
             "Control plane and data plane in Istio sidecar mode, Istio ambient mode and Linkerd",
             "Istio's control plane, istiod, issues workload certificates and pushes routing and policy configuration to proxies "
             "over xDS. In sidecar mode every pod gets an Envoy container that handles mTLS and layer 7 routing. In ambient mode a "
             "ztunnel DaemonSet on each node handles mTLS and layer 4 policy for enrolled namespaces, and optional waypoint "
             "proxies, one Envoy Deployment per namespace or service account, add layer 7 features. Linkerd's control plane has "
             "destination, identity and proxy-injector components, and every meshed pod gets the Rust linkerd2-proxy sidecar. "
             "In all three, application traffic flows proxy to proxy, and the control plane is not in the request path.")
    p.zone("Control plane: certificates and configuration, not in the request path", 15, 12, 870, 120)
    p.node("istiod", "gateway", 30, 40, 545, 80, "istiod (Istio)", "CA: signs workload certificates (SPIFFE identities)",
           "xDS: pushes routes, AuthorizationPolicy, telemetry config", "watches Services, Gateway API and Istio CRDs")
    p.node("lcp", "gateway", 600, 40, 270, 80, "Linkerd control plane", "identity: issues certificates",
           "destination: endpoints, policy", "proxy-injector: adds sidecar")
    p.zone("Data plane: where requests flow", 15, 156, 870, 300, "br")
    p.note(30, 172, "Istio sidecar mode", size=13, bold=True)
    p.node("sa", "service", 30, 196, 250, 80, "Pod A", "app container", "+ Envoy sidecar (L4 + L7)")
    p.node("sb", "service", 30, 356, 250, 80, "Pod B", "app container", "+ Envoy sidecar (L4 + L7)")
    p.note(315, 172, "Istio ambient mode", size=13, bold=True)
    p.node("aa", "service", 315, 196, 120, 64, "Pod A", "app only")
    p.node("ab", "service", 455, 196, 120, 64, "Pod B", "app only")
    p.node("zt", "mcp", 315, 282, 260, 64, "ztunnel per node", "mTLS + L4 policy (Rust)")
    p.node("wp", "mcp", 315, 366, 260, 72, "waypoint (optional)", "Envoy per namespace or", "service account: L7 rules")
    p.note(600, 172, "Linkerd", size=13, bold=True)
    p.node("la", "service", 600, 196, 270, 80, "Pod A", "app container", "+ linkerd2-proxy (Rust)")
    p.node("lb", "service", 600, 356, 270, 80, "Pod B", "app container", "+ linkerd2-proxy (Rust)")
    p.zone("Telemetry", 15, 472, 870, 116)
    p.node("prom", "store", 30, 496, 400, 80, "Prometheus", "scrapes proxy metrics: request rate,", "errors, latency per service pair")
    p.node("trace", "store", 470, 496, 400, 80, "Tracing backend", "proxies emit spans; apps must forward", "trace headers to join them")
    p.edge("sa", "sb", label="mTLS", dx=26)
    p.edge("la", "lb", label="mTLS", dx=26)
    p.edge("aa", "zt", b_at=at(315, 260, 375))
    p.edge("zt", "wp", a_at=0.5, b_at=0.5, label="HBONE", dx=30)
    p.edge("zt", "ab", a_side="t", b_side="b", a_at=at(315, 260, 515), kind="dashed")
    p.edge("istiod", "sa", a_at=at(30, 545, 155), b_at=0.5, kind="dashed", label="xDS + certs", dx=46)
    p.edge("istiod", "zt", a_at=at(30, 545, 545), b_at=0.5, kind="dashed",
           via=[(545, 150), (590, 150), (590, 314)], b_side="r")
    p.edge("lcp", "la", kind="dashed")
    return p


def cert_manager():
    p = Page("k8s-tools-cert-manager-flow", "cert-manager issuance", 900, 600,
             "How cert-manager obtains and renews a Let's Encrypt certificate",
             "An Ingress or Gateway annotated with a ClusterIssuer, or a Certificate written by hand, starts the flow. "
             "cert-manager creates a private key Secret and a CertificateRequest. For an ACME issuer it creates an Order and one "
             "Challenge per DNS name. With HTTP-01 it starts a solver pod and a temporary route so Let's Encrypt can fetch a token "
             "from http://<domain>/.well-known/acme-challenge/; with DNS-01 it writes a TXT record at _acme-challenge.<domain> "
             "through a DNS provider API, which also supports wildcards. After validation Let's Encrypt signs the certificate and "
             "cert-manager stores it in a kubernetes.io/tls Secret that the ingress controller or gateway serves. By default "
             "renewal starts two thirds of the way through the certificate's lifetime and repeats the same flow.")
    p.zone("You declare", 15, 12, 870, 96)
    p.node("ing", "edge", 30, 36, 400, 62, "Ingress or Gateway", "annotation cert-manager.io/cluster-issuer",
           "cert-manager creates the Certificate")
    p.node("certdecl", "edge", 470, 36, 400, 62, "or write a Certificate yourself", "dnsNames, secretName, issuerRef")
    p.zone("cert-manager controllers", 15, 124, 870, 222)
    p.node("cert", "gateway", 30, 148, 260, 80, "Certificate", "desired: names, Secret,", "duration, renewBefore")
    p.node("cr", "gateway", 320, 148, 260, 80, "CertificateRequest", "a CSR signed by the", "new private key")
    p.node("order", "gateway", 610, 148, 260, 80, "Order (ACME)", "one per request", "lists the challenges")
    p.node("http01", "agent", 320, 248, 260, 86, "HTTP-01 Challenge", "solver pod + temporary route", "public port 80 must reach it")
    p.node("dns01", "agent", 610, 248, 260, 86, "DNS-01 Challenge", "TXT _acme-challenge.<name>", "needs DNS API token; wildcards")
    p.zone("Outside", 15, 362, 870, 100)
    p.node("le", "external", 470, 386, 400, 64, "Let's Encrypt (ACME)", "validates the challenge, signs the certificate")
    p.zone("Result", 15, 478, 870, 110)
    p.node("secret", "store", 30, 502, 400, 74, "Secret type kubernetes.io/tls", "tls.crt + tls.key, same name as", "secretName / certificateRefs")
    p.node("serve", "edge", 470, 502, 400, 74, "Ingress controller or gateway", "serves the new certificate;", "renewal at 2/3 of lifetime by default")
    p.edge("ing", "cert", a_at=at(30, 400, 160), b_at=0.5)
    p.edge("certdecl", "cert", a_at=at(470, 400, 520), b_at=0.8, via=[(520, 116), (238, 116)])
    p.edge("cert", "cr", a_side="r", b_side="l")
    p.edge("cr", "order", a_side="r", b_side="l")
    p.edge("order", "dns01", a_at=0.5, b_at=0.5)
    p.edge("order", "http01", a_at=0.2, b_at=0.5, via=[(662, 238), (450, 238)])
    p.edge("dns01", "le", a_at=0.5, b_at=at(470, 400, 740), kind="dashed")
    p.edge("http01", "le", a_at=0.5, b_at=at(470, 400, 520), via=[(450, 334), (450, 356), (520, 356)], kind="dashed")
    p.edge("le", "secret", a_side="l", b_side="t", b_at=0.7, via=[(310, 418)], kind="write", label="signed", dy=-12)
    p.edge("secret", "serve", a_side="r", b_side="l")
    p.edge("cert", "secret", a_at=0.3, b_at=at(30, 400, 108), kind="dashed", label="renew", dx=28, t=0.3)
    return p


FILES = {f.__name__: f for f in (ecosystem, gitops_flow, prometheus_flow, mk4_lab, production, autoscaling, service_mesh, cert_manager)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    built = []
    for make in FILES.values():
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
        (HERE / f"{page.figure}.drawio").write_bytes(ET.tostring(mxfile, encoding="utf-8", xml_declaration=False))
        (OUT / f"{page.figure}.svg").write_text(series.page_svg(page), encoding="utf-8")
        built.append((page.figure, page.w, page.h))
    (HERE / "figures.txt").write_text("".join(f"{f} {w} {h}\n" for f, w, h in built), encoding="utf-8")
    print(f"{len(built)} .drawio files and SVGs")


if __name__ == "__main__":
    main()
