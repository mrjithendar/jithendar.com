#!/usr/bin/env python3
"""Figures for content/blog/keda-autoscaling-requests-per-second-jithendar-com.mdx (KEDA scales the site's CMS).

    python3 docs/knowledge-sharing/keda-autoscaling/diagrams/build_diagrams.py   # writes the .drawio files
    bash docs/knowledge-sharing/keda-autoscaling/diagrams/export.sh              # draw.io CLI → public/images/keda-autoscaling/

If you edit a .drawio file by hand, run only export.sh afterwards. Running this script overwrites the edits.

Every number here comes from ../evidence: prometheus.txt (7 days of Prometheus data to 26 November 2026) and
live-state.txt (read-only kubectl on mk4 the same day).
"""
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio_model import ARROWS, FONT, KINDS, TEXT, Diagram  # noqa: E402

# Arrow kinds for this article only (the shared writer stays unchanged).
ARROWS["scrape"] = ("#b45309", 1.5, "2 3", "Scrape or read a metric")
ARROWS["answer"] = ("#64748b", 1.5, "4 3", "Answer")
ARROWS["scale"] = ("#0f766e", 2, "8 4", "Create, watch or scale")

HERE = Path(__file__).resolve().parent
GRID = "#e2e8f0"
AXIS = "#64748b"


def label(d, id, x, y, w, h, html, size=12, color=TEXT, align="left"):
    d.text(id, x, y, w, h, html, size=size, color=color, align=align)


def step_dot(d, id, n, cx, cy, fill="#0f766e"):
    style = "ellipse;" + d.style(html=1, fillColor=fill, strokeColor="#ffffff", strokeWidth=2, fontColor="#ffffff",
                                 fontStyle=1, fontFamily=FONT, fontSize=11, align="center", verticalAlign="middle")
    d._add(id, str(n), style, cx - 10, cy - 10, 20, 20)


# 1. Overview (also the cover) -------------------------------------------------------------------
def overview():
    d = Diagram("keda-autoscaling-overview", 960, 780, "How jithendar.com scales: requests and CPU in, pods out")
    d.zone("z-out", "Outside mk4", 20, 50, 330, 150, "plain")
    d.zone("z-site", "mk4 · namespace jithendar", 370, 50, 570, 150, "cluster")
    d.node("browser", "client", 32, 88, 130, 96, "Visitor", "a browser", "or a crawler")
    d.node("cf", "network", 178, 88, 160, 96, "Cloudflare", "caches HTML by URL;", "a cache hit never", "reaches the pods")
    d.node("gw", "network", 382, 88, 130, 96, "Istio gateway", "TLS and routes")
    d.node("svc", "network", 528, 88, 150, 96, "jithendar-com", "the public Service", "(not -internal)")
    d.node("pods", "service", 694, 88, 234, 96, "Pods: 2 to 8", "web (Next.js, moks-cms)", "istio-proxy counts each",
           "request it receives")
    d.edge("browser", "cf", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("cf", "gw", "miss", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("gw", "svc", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("svc", "pods", exit=(1, 0.5), entry=(0, 0.5))

    d.node("prom", "data", 540, 246, 210, 100, "Prometheus", "istio_requests_total,", "scraped every 30 s",
           "namespace monitoring", shape="db")
    d.node("ms", "compute", 776, 246, 164, 100, "metrics-server", "CPU per container,", "from the kubelets")
    d.edge("pods", "prom", "scrape", kind="scrape", exit=(0.25, 1), entry=(0.75, 0))
    d.edge("pods", "ms", kind="scrape", exit=(0.85, 1), entry=(0.5, 0))

    label(d, "rule", 20, 236, 270, 120,
          "<b>The rule, every 15 seconds</b><br>pods = the larger of<br>· requests per second ÷ 5, rounded up<br>"
          "· pods × CPU % ÷ 200, rounded up<br>never fewer than 2, never more than 8.<br>"
          "Up at once; down only after 5 minutes.")

    d.node("so", "ops", 20, 410, 170, 104, "ScaledObject", "jithendar-com", "min 2, max 8", "requests: 5 per pod",
           "cpu: 200 % of 250m")
    d.zone("z-keda", "namespace keda (KEDA 2.21.1)", 230, 386, 230, 324, "cluster", valign="bottom")
    d.node("op", "ops", 250, 410, 180, 104, "keda-operator", "runs the prometheus", "scaler; mTLS through",
           "its own sidecar")
    d.node("mapi", "ops", 250, 566, 180, 104, "KEDA metrics API", "external.metrics.k8s.io", "for the HPAs", "(no sidecar)")
    d.node("hpa", "ops", 530, 566, 210, 104, "HPA", "keda-hpa-jithendar-com", "asks both metrics, takes", "the larger, keeps 2 to 8")
    d.node("dep", "service", 790, 566, 150, 104, "Deployment", "jithendar-com", "replicas set", "by the HPA")

    d.edge("so", "op", "watches", kind="scale", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("op", "prom", "PromQL, mTLS", kind="sync", both=True, exit=(0.5, 0), entry=(0, 0.5), via=((340, 296),))
    d.edge("op", "hpa", "creates and updates", kind="scale", exit=(1, 0.5), entry=(0.3, 0), via=((593, 462),))
    d.edge("hpa", "mapi", "s0-prometheus", kind="sync", exit=(0, 0.5), entry=(1, 0.5))
    d.edge("mapi", "op", "gRPC :9666", kind="sync", exit=(0.5, 0), entry=(0.5, 1))
    d.edge("hpa", "ms", "metrics.k8s.io", kind="sync", exit=(0.8, 0), entry=(0.5, 1), via=((698, 500), (858, 500)))
    d.edge("hpa", "dep", "scale", kind="scale", exit=(1, 0.5), entry=(0, 0.5))
    d.legend(730, labels={"client": "Visitor", "network": "Edge and routing", "service": "The site",
                          "data": "Metrics store", "compute": "Cluster add-on", "ops": "Scaling"})
    return d


# 2. One HPA sync as a sequence --------------------------------------------------------------------
def loop():
    d = Diagram("keda-autoscaling-loop", 960, 760, "One HPA sync, every 15 seconds: where each number comes from")
    parts = [  # id, centre x, kind, title, line
        ("hpa", 90, "ops", "HPA controller", "in k3s"),
        ("api", 248, "network", "kube-apiserver", "APIServices"),
        ("mapi", 406, "ops", "KEDA metrics", "API, no sidecar"),
        ("op", 564, "ops", "keda-operator", "and its sidecar"),
        ("prom", 722, "data", "Prometheus", "monitoring"),
        ("ms", 870, "compute", "metrics-server", "kube-system"),
    ]
    xs = {}
    for id, cx, kind, title, line in parts:
        w = 140
        d.node(id, kind, cx - w // 2, 50, w, 56, title, line)
        d.rect(f"life-{id}", cx - 1, 106, 2, 404, "#cbd5e1")
        xs[id] = cx

    def msg(n, a, b, y, text, kind="sync"):
        xa, xb = xs[a], xs[b]
        pad = 4 if xb > xa else -4
        d.line(xa + pad, y, xb - pad, y, text, kind=kind)
        step_dot(d, f"s{n}", n, xa + (14 if xb > xa else -14), y - 14, fill="#475569" if kind != "answer" else "#94a3b8")

    msg(1, "hpa", "api", 140, "s0-prometheus?")
    msg(2, "api", "mapi", 180, "external.metrics")
    msg(3, "mapi", "op", 220, "gRPC :9666")
    msg(4, "op", "prom", 260, "PromQL, mTLS")
    msg(5, "prom", "op", 300, "1.4 req/s", kind="answer")
    msg(6, "op", "hpa", 340, "total 1.4 (not per pod)", kind="answer")
    msg(7, "hpa", "api", 390, "cpu of web?")
    msg(8, "api", "ms", 430, "metrics.k8s.io")
    msg(9, "ms", "hpa", 470, "51m a pod: 20 % of 250m", kind="answer")

    d.node("decide", "ops", 20, 530, 440, 136, "10 · The HPA decides", "requests: 1.4 ÷ 5 = 0.28 → 1 pod",
           "cpu: 2 pods × 20 % ÷ 200 % = 0.2 → 1 pod", "larger of the two: 1; below the minimum → 2",
           "2 pods already run: nothing to change", align="left")
    label(d, "notes", 484, 530, 456, 150,
          "<b>Who calls whom</b><br>"
          "The API server calls KEDA's metrics API directly, so that pod has no Istio sidecar. "
          "It reads each value from the operator over gRPC, with KEDA's own TLS, on port 9666 (PERMISSIVE). "
          "The operator queries Prometheus through its sidecar: Prometheus accepts mTLS only, and namespace keda "
          "is one of its allowed callers. KEDA answers with the query's total; the HPA divides it by the pods. "
          "CPU never passes through KEDA.")
    d.legend(700, labels={"ops": "Scaling", "network": "Kubernetes API", "data": "Metrics store",
                          "compute": "Cluster add-on"})
    return d


# 3. CPU evidence: why requests lead ---------------------------------------------------------------
def bars(d, prefix, x, y, rows, scale, colors, value_fmt="{}"):
    """Horizontal bars: rows of (label, value); the label sits above its bar."""
    for i, (text, value) in enumerate(rows):
        yy = y + i * 52
        label(d, f"{prefix}-l{i}", x, yy, 380, 18, escape(text), color=TEXT)
        length = max(3, round(value * scale))
        d.rect(f"{prefix}-b{i}", x, yy + 22, length, 18, colors[i], "none")
        label(d, f"{prefix}-v{i}", x + length + 8, yy + 22, 80, 18, f"<b>{escape(value_fmt.format(value))}</b>", color=TEXT)


def cpu_evidence():
    d = Diagram("keda-autoscaling-cpu-evidence", 960, 510,
                "Why requests lead and CPU only backs them up (7 days to 26 November 2026)")
    d.zone("z-a", "Minutes a pod used more than 0.4 cores", 20, 50, 450, 210, "plain")
    bars(d, "a", 40, 90, [("in its first 10 minutes after starting", 129), ("in the rest of its life", 4)],
         2.6, ["#1d4ed8", "#94a3b8"])
    label(d, "a-note", 40, 200, 410, 50, "A new pod warms its page cache first. 88 different pods ran in these "
          "7 days: deploys, releases and node work all restart them.")

    d.zone("z-b", "Minutes the site's average CPU was above a target", 490, 50, 450, 260, "plain")
    bars(d, "b", 510, 90, [("above 80 % of the 250m request", 79), ("above 100 %", 73), ("above 150 %", 50),
                           ("above 200 %: the target we chose", 28)],
         3.6, ["#93c5fd", "#93c5fd", "#93c5fd", "#0f766e"])

    d.zone("z-c", "Requests per second, the whole site", 20, 280, 450, 150, "plain")
    rows = [("now", 0.9), ("p99 over the week", 1.47), ("peak over the week", 4.79)]
    for i, (text, v) in enumerate(rows):
        yy = 316 + i * 34
        label(d, f"c-l{i}", 40, yy, 150, 18, escape(text), color=TEXT)
        d.rect(f"c-b{i}", 190, yy, max(3, round(v * 50)), 18, "#047857", "none")
        label(d, f"c-v{i}", 190 + round(v * 50) + 8, yy, 60, 18, f"<b>{v:g}</b>", color=TEXT)

    d.node("take", "ops", 490, 330, 450, 100, "What it means", "CPU jumps when a pod starts; requests don't.",
           "So requests per second decide, and CPU at 200 %", "only adds pods for unusually heavy requests.",
           align="left")
    label(d, "foot", 20, 450, 920, 60,
          "<b>From Prometheus on mk4</b> (evidence/prometheus.txt): the web container's CPU from cAdvisor, matched to each "
          "pod's start time, and istio_requests_total for the public Service. At the busiest minute, with 4.8 requests "
          "per second for the whole site, the busiest pod used 0.26 cores.", color=TEXT)
    return d


# 4. Pods for a given load ----------------------------------------------------------------------------
def steps():
    d = Diagram("keda-autoscaling-steps", 960, 560, "Pods for a given load: requests per second ÷ 5, never below 2 or above 8")
    X0, X1, Y0 = 100, 910, 440          # chart origin and right edge
    PXR = (X1 - X0) / 45                # px per request per second
    PXP = 44                            # px per pod

    def x(r):
        return round(X0 + r * PXR)

    def y(p):
        return round(Y0 - p * PXP)

    for p in range(0, 9):
        d.rect(f"gy{p}", X0, y(p), X1 - X0, 1, GRID)
        label(d, f"ty{p}", X0 - 40, y(p) - 9, 30, 18, str(p), color=AXIS, align="right")
    for r in range(0, 46, 5):
        d.rect(f"gx{r}", x(r), y(8), 1, Y0 - y(8), GRID)
        label(d, f"tx{r}", x(r) - 20, Y0 + 8, 40, 18, str(r), color=AXIS, align="center")
    d.rect("axis-x", X0, Y0, X1 - X0, 2, AXIS)
    d.rect("axis-y", X0, y(8), 2, Y0 - y(8), AXIS)
    label(d, "ax-x", X0, Y0 + 30, 600, 18, "requests per second for the whole site (public Service, 2-minute rate)",
          color=TEXT)
    label(d, "ax-y", 20, y(8) - 30, 200, 18, "<b>pods</b>", color=TEXT)

    # the step function: ceil(R / 5), within 2..8
    segments = [(0, 10, 2)] + [(5 * (n - 1), 5 * n, n) for n in range(3, 8)] + [(35, 45, 8)]
    for i, (a, b, n) in enumerate(segments):
        d.rect(f"st{i}", x(a), y(n) - 2, x(b) - x(a), 5, "#0f766e")
        if i:
            prev = segments[i - 1][2]
            d.rect(f"sv{i}", x(a) - 1, y(n), 3, y(prev) - y(n), "#0f766e")

    # where the site is
    for id, r, text in (("now", 0.9, "now: 0.9"), ("peak", 4.79, "7-day peak: 4.8")):
        d.rect(f"m-{id}", x(r), y(8), 2, Y0 - y(8), "#be123c")
    label(d, "m-now-t", x(0.9) + 6, y(8) + 4, 70, 18, "<b>now 0.9</b>", color="#be123c")
    label(d, "m-peak-t", x(4.79) + 6, y(8) + 24, 140, 18, "<b>7-day peak 4.8</b>", color="#be123c")

    label(d, "n-min", x(5.4), y(2) + 8, 230, 36, "minimum 2: two nodes, and more than<br>the disruption budget's 1",
          color=TEXT)
    label(d, "n-max", x(35.5), y(8) + 8, 160, 36, "maximum 8: the database<br>connection ceiling", color=TEXT)
    label(d, "n-third", x(10.5), y(3) + 8, 260, 36, "3rd pod at about 11 req/s: the HPA<br>ignores changes within 10 %",
          color=TEXT)
    label(d, "n-cpu", x(13.5), y(8) + 8, 290, 54,
          "<b>CPU at 200 %</b> is about 9 req/s of typical requests on one pod (0.5 cores). It adds pods only when "
          "requests get heavier than usual.", color=TEXT)
    label(d, "foot", 20, 506, 920, 40, "Illustration of the HPA's rule with the ScaledObject's numbers; the site has not "
          "needed a third pod yet. Scaling up happens at the next sync; scaling down waits 5 minutes.", color=SUB)
    return d


SUB = "#334155"


# 5. Placement and the database ---------------------------------------------------------------------
def worker(d, id, x, y, name, used, alloc, pods, note=None):
    w, h = 214, 236
    fill, stroke, _ = KINDS["compute"]
    d.rect(f"{id}-box", x, y, w, h, fill, stroke)
    label(d, f"{id}-t", x + 12, y + 10, w - 24, 18, f"<b>{escape(name)}</b>", size=13, color=TEXT)
    label(d, f"{id}-m", x + 12, y + 34, w - 24, 18, "memory requested", color=SUB)
    d.rect(f"{id}-bar", x + 12, y + 56, w - 24, 14, "#ffffff", "#94a3b8")
    pct = used / alloc
    d.rect(f"{id}-fill", x + 12, y + 56, round((w - 24) * pct), 14, "#b91c1c" if pct > 0.9 else "#60a5fa")
    # whole percent rounded down, as kubectl describe node prints it
    label(d, f"{id}-v", x + 12, y + 76, w - 24, 18, f"{used} of {alloc} Mi ({int(pct * 100)} %)", color=TEXT)
    for i, (title, line, kind) in enumerate(pods):
        d.node(f"{id}-p{i}", kind, x + 12, y + 108 + i * 72, w - 24, 60, title, line)
    if note:
        label(d, f"{id}-n", x + 12, y + 108 + len(pods) * 72, w - 24, 50, note, color=TEXT)
    return d


def placement():
    d = Diagram("keda-autoscaling-placement", 960, 560, "Where a third pod would go, and why it would wait (26 November 2026)")
    d.zone("z-w", "mk4 workers: the spread domains (maxSkew 1, DoNotSchedule)", 20, 50, 700, 290, "cluster")
    worker(d, "w1", 32, 86, "worker1", 5774, 7729, [("pod 1", "jithendar-com", "service")])
    worker(d, "w2", 258, 86, "worker2", 5988, 7729, [("pod 2", "jithendar-com", "service")])
    worker(d, "w3", 484, 86, "worker3", 7240, 7729, [("pod 3: Pending", "needs 512Mi, 489 free", "optional")],
           note="The only node it may use: 1 / 1 / 0 pods allows no other place.")
    d.marker(1, 690, 206)
    d.node("m1", "optional", 740, 86, 200, 110, "master1", "tainted, so not a", "spread domain", "(nodeTaintsPolicy",
           "Honor)")
    d.node("db", "data", 740, 210, 200, 130, "PgBouncer", "session mode", "2 poolers × 20 = 40", "8 pods × 5 = 40",
           "so at most 8 pods", shape="db")
    label(d, "why", 20, 358, 920, 80,
          "<b>Why pod 3 would wait.</b> The Deployment spreads its pods so that no node has more than one pod more than "
          "another, and a pod that can't keep to that stays Pending (DoNotSchedule). With one pod on worker1 and one on "
          "worker2, a third may only start on worker3, and worker3 has 489Mi of memory requests left against the 512Mi "
          "a pod asks for. Until someone frees about 25Mi there, or relaxes the rule to ScheduleAnyway, the HPA can ask "
          "for 3 pods and the site keeps running 2.", color=TEXT)
    label(d, "why-db", 20, 440, 920, 40,
          "<b>Why 8 is the ceiling.</b> Each pod opens up to 5 database connections (DATABASE_POOL_MAX), and PgBouncer in "
          "session mode holds one server connection per client: 8 pods use all 40.", color=TEXT)
    d.legend(500, failure=True, labels={"service": "Running pod", "optional": "Pending pod or excluded node",
                                         "data": "Database pool"})
    return d


# 6. From a pull request to an HPA ----------------------------------------------------------------------
def pipeline():
    d = Diagram("keda-autoscaling-pipeline", 960, 720, "From a pull request to an HPA: what checks the ScaledObject on the way")
    d.node("pr", "client", 20, 60, 160, 100, "Pull request", "kubernetes/", "35-autoscaling.yaml")
    d.node("check", "ops", 200, 60, 230, 100, "check · scripts", "test_autoscaling.py: wiring,", "max ≥ min, numbers;",
           "skipped while SET-ME", align="left")
    d.node("plan", "ops", 450, 60, 250, 100, "deploy · plan", "kustomize, then", "ci-app-manifests.py: allow-list;",
           "SET-ME → left out, warning", align="left")
    d.node("merge", "client", 720, 60, 220, 100, "Merged to master", "the deploy job starts", "(also: manual run,",
           "moks-cms release)")
    d.edge("pr", "check", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("check", "plan", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("plan", "merge", exit=(1, 0.5), entry=(0, 0.5))
    d.marker(2, 690, 64)

    d.zone("z-dep", "deploy job, as ServiceAccount jithendar/github-ci-applier", 20, 200, 920, 130, "cluster", corner="right")
    steps_ = [("dry", "Server dry run", "API + webhooks"), ("diff", "kubectl diff", "shows changes"),
              ("apply", "kubectl apply", "site, seo-agent"), ("restart", "rollout restart", "and wait"),
              ("smoke", "Smoke test", "port-forward"), ("crew", "crewconfig", "restore")]
    for i, (id, title, line) in enumerate(steps_):
        d.node(id, "ops", 32 + i * 151, 236, 140, 76, title, line)
        if i:
            d.edge(steps_[i - 1][0], id, exit=(1, 0.5), entry=(0, 0.5))
    d.edge("merge", "dry", exit=(0.5, 1), entry=(0.5, 0), via=((830, 184), (102, 184)))
    d.marker(1, 168, 240)

    d.node("role", "security", 20, 380, 300, 110, "Role github-ci-applier", "what the deploy job may do:",
           "scaledobjects: create, patch, update", "HPAs: get, list, watch only", "TriggerAuthentication: none",
           align="left")
    d.node("so", "ops", 334, 380, 140, 110, "ScaledObject", "jithendar-com", "on mk4")
    d.node("op", "ops", 532, 380, 180, 110, "keda-operator", "validates it, then", "creates the HPA")
    d.node("hpa", "ops", 760, 380, 180, 110, "HPA", "keda-hpa-jithendar-com", "scales the", "Deployment")
    d.edge("apply", "so", "creates", kind="scale", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("so", "op", kind="scale", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("op", "hpa", kind="scale", exit=(1, 0.5), entry=(0, 0.5))

    label(d, "n1", 20, 520, 920, 54,
          "<b>1 · 26 November, 08:33 UTC.</b> The pull request that added the ScaledObject was merged with three values "
          "still SET-ME. The server dry run refused it (spec.maxReplicaCount must be of type integer), so every deploy "
          "failed before it changed anything, moks-cms release restarts included. The site kept its 2 pods.", color=TEXT)
    label(d, "n2", 20, 580, 920, 54,
          "<b>2 · After #25 the plan step named each SET-ME and stopped</b>, so the failure showed on the pull request "
          "itself. Since #26 it leaves a ScaledObject with any SET-ME out, with one warning per value, and deploys the "
          "rest; a SET-ME in any other kind still stops the run.", color=TEXT)
    d.legend(650, failure=True, labels={"client": "Pull request and merge", "ops": "Checks, deploy and scaling",
                                         "security": "What CI may do"})
    return d


def main():
    names = []
    for build in (overview, loop, cpu_evidence, steps, placement, pipeline):
        d = build()
        (HERE / f"{d.name}.drawio").write_text(d.xml() + "\n")
        names.append(d.name)
        print(f"wrote {d.name}.drawio ({d.w}x{d.h})")
    (HERE / "figures.txt").write_text("\n".join(names) + "\n")


if __name__ == "__main__":
    main()
