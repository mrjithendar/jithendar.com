#!/usr/bin/env python3
"""Figures for content/blog/kubernetes-node-out-of-memory-postmortem-mk4.mdx (the 28 November 2026 incident).

    python3 docs/knowledge-sharing/worker1-oom/diagrams/build_diagrams.py   # writes the .drawio files
    bash docs/knowledge-sharing/worker1-oom/diagrams/export.sh              # draw.io CLI → public/images/worker1-oom/

If you edit a .drawio file by hand, run only export.sh afterwards. Running this script overwrites the edits.

Every time and number comes from ../evidence (Kubernetes events, Prometheus samples, kubelet configz, the site's
log). Times are UTC.
"""
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio_model import ARROWS, FONT, TEXT, Diagram  # noqa: E402

ARROWS["leads"] = ("#475569", 1.5, None, "Leads to")
ARROWS["fixes"] = ("#0f766e", 1.5, "8 4", "Addressed by")
ARROWS["next"] = ("#475569", 1.5, None, "Next step")

HERE = Path(__file__).resolve().parent
RED, RED_FILL, AMBER, AMBER_FILL, BLUE, BLUE_FILL = "#b91c1c", "#fecaca", "#b45309", "#fde68a", "#1d4ed8", "#bfdbfe"
GREY, GREY_FILL, GREEN, GREEN_FILL = "#64748b", "#e2e8f0", "#047857", "#bbf7d0"


# 1. Memory: what the scheduler counted and what the node had ---------------------------------------
GIB_MAX, BX0, BW = 8.5, 250, 560  # scale 0..8.5 GiB over 560 px from x=250


def gx(gib):
    return round(BX0 + gib / GIB_MAX * BW)


def segment(d, id, start, size, fill, stroke, y, h, label=""):
    d.rect(id, gx(start), y, gx(start + size) - gx(start), h, fill, stroke)
    if label:
        d.text(id + "-t", gx(start) + 6, y + 9, gx(start + size) - gx(start) - 10, 18, f"<b>{escape(label)}</b>", color=TEXT, size=11)


def memory():
    d = Diagram("worker1-oom-memory", 960, 560, "worker1 at 11:10:23 UTC: the scheduler said the second LiteLLM pod fits. The node had no room for it.")
    cap = 7.55
    # scale
    ya = 96
    d.rect("axis", gx(0), ya, gx(GIB_MAX) - gx(0), 2, GREY)
    for g in range(0, 9):
        d.rect(f"tick{g}", gx(g) - 1, ya - 4, 2, 10, GREY)
        d.text(f"tick{g}-t", gx(g) - 20, ya - 26, 40, 16, f"{g} GiB", size=11, align="center")
    d.text("axis-t", 20, ya - 12, 220, 18, "<b>Memory on worker1</b>", color=TEXT)

    # bar 1: requests
    y1, h = 130, 36
    d.text("b1-t", 20, y1 + 2, 220, 34, "<b>What the scheduler counts</b><br>memory requests", color=TEXT)
    segment(d, "r-other", 0, 5.28, GREY_FILL, GREY, y1, h, "other pods 5.28 (10:25)")
    segment(d, "r-l1", 5.28, 1.0, BLUE_FILL, BLUE, y1, h, "LiteLLM 1")
    segment(d, "r-l2", 6.28, 1.0, AMBER_FILL, AMBER, y1, h, "LiteLLM 2")
    d.text("r-sum", gx(7.55) + 10, y1 + 9, 150, 18, "7.28 GiB: fits", color=GREEN, size=11)

    # bar 2: working set
    y2 = 200
    d.text("b2-t", 20, y2 + 2, 220, 34, "<b>What the node had in use</b><br>working set (cAdvisor)", color=TEXT)
    segment(d, "w-other", 0, 5.86, GREY_FILL, GREY, y2, h, "everything else 5.86")
    segment(d, "w-l1", 5.86, 1.02, BLUE_FILL, BLUE, y2, h, "LiteLLM 1")
    segment(d, "w-l2", 6.88, 1.05, RED_FILL, RED, y2, h, "LiteLLM 2")
    d.text("w-sum", gx(7.93) + 10, y2 + 2, 165, 34, "about 7.9 GiB:<br>0.4 GiB more than exists", color=RED, size=11)

    # capacity line
    d.rect("cap", gx(cap) - 1, ya + 6, 3, y2 + h + 18 - ya - 6, RED)
    d.text("cap-t", gx(cap) - 170, y2 + h + 26, 340, 34,
           "<b>7.55 GiB: the machine's memory, and also its allocatable memory</b> (nothing reserved for the OS, kubelet or k3s)",
           color=RED, size=11, align="center")
    d.marker(1, gx(cap), y2 - 16)

    # notes
    y3 = 330
    d.node("n1", "data", 20, y3, 295, 104, "Measured at 11:10:15", "worker1 working set 6.88 GiB (91%),", "LiteLLM 1 alone 1.02 GiB.",
           "LiteLLM 2 started at 11:10:24; it was", "never scraped, so 1.05 GiB is LiteLLM 1's.", align="left")
    d.node("n2", "security", 333, y3, 295, 104, "No memory eviction on the kubelet", "evictionHard: disk thresholds only.",
           "With no memory.available threshold,", "the kubelet never evicts for memory:", "the node thrashed instead.", align="left")
    d.node("n3", "compute", 646, y3, 294, 104, "Why worker1, twice", "The scheduler ranks nodes by requests.",
           "worker1 had the most unrequested", "memory (69% requested at 10:25), and", "was already the most used (80%).", align="left")
    d.legend(470, labels={"data": "Measurement", "security": "Missing guardrail", "compute": "Scheduler"}, failure=True)
    return d


# 2. Timeline ---------------------------------------------------------------------------------------
T0_MIN, X0, PX = 10 * 60 + 54, 150, 24.5  # 10:54 at x=150; 24.5 px per minute → 11:27 at x≈958 (page 980)


def tx(hhmmss):
    parts = [int(p) for p in hhmmss.split(":")]
    h, m, s = (parts + [0])[:3]
    return round(X0 + (h * 60 + m - T0_MIN + s / 60) * PX)


EVENTS = [  # number, lane, time, text (the article's timeline table repeats these)
    (1, "me", "10:55:43", "moks-rag #14 merged: LiteLLM with PostgreSQL, request 1 GiB, limit 2 GiB"),
    (2, "node", "10:56:19", "LiteLLM 1 scheduled on worker1; waits for a Secret key until 11:06:22"),
    (3, "me", "11:06:22", "Secret keys added; LiteLLM 1 starts at 11:06:36 and is ready by 11:07:33"),
    (4, "me", "11:10:23", "kubectl rollout restart deploy/litellm: LiteLLM 2 scheduled on worker1"),
    (5, "node", "11:10:33", "probes on worker1 start timing out; last heartbeat was 11:10:22"),
    (6, "svc", "11:11:16", "Harbor core restarted: it lost Valkey (valkey-0 is on worker1); image pulls fail from 11:18"),
    (7, "node", "11:13:11", "worker1 NotReady"),
    (8, "node", "11:18:11", "taint eviction: pods on worker1 marked for deletion; replacements Pending"),
    (9, "node", "11:20:54", "kernel OOM killer kills docling-serve on worker1"),
    (10, "node", "11:21:05", "worker1 Ready"),
    (11, "svc", "11:23:52", "Harbor core starts cleanly once Valkey is back (valkey-0 recreated 11:22:03)"),
    (12, "svc", "11:25:47", "every pod in the cluster Running again"),
]


def event_dot(d, id, n, cx, cy, fill):
    style = "ellipse;" + d.style(html=1, fillColor=fill, strokeColor="#ffffff", strokeWidth=2, fontColor="#ffffff",
                                 fontStyle=1, fontFamily=FONT, fontSize=11, align="center", verticalAlign="middle")
    d._add(id, str(n), style, cx - 11, cy - 11, 22, 22)


def timeline():
    d = Diagram("worker1-oom-timeline", 980, 790, "28 November 2026 (UTC): what I did, what worker1 did, and what everyone else saw")
    lanes = {"me": (52, "What I did"), "node": (128, "worker1"), "svc": (204, "Other services"), "site": (280, "Visitors")}
    lane_h = 64
    for key, (y, label) in lanes.items():
        d.rect(f"lane-{key}", X0 - 10, y, tx("11:27") - X0 + 14, lane_h, "#f8fafc", "#e2e8f0")
        d.text(f"lane-{key}-t", 20, y + 8, 120, 48, f"<b>{escape(label)}</b>", color=TEXT)

    yn = lanes["node"][0]
    d.rect("b-wait", tx("10:56:19"), yn + 40, tx("11:06:22") - tx("10:56:19"), 10, GREY_FILL, GREY)
    d.text("t-wait", tx("10:56:19") + 4, yn + 22, 200, 16, "LiteLLM 1 waits for its Secret", size=11)
    d.rect("b-hot", tx("11:06:36"), yn + 40, tx("11:10:23") - tx("11:06:36"), 10, AMBER_FILL, AMBER)
    d.rect("b-sick", tx("11:10:23"), yn + 40, tx("11:21:05") - tx("11:10:23"), 10, RED_FILL, RED)
    d.text("t-sick", tx("11:10:23") + 4, yn + 52, 270, 14, "<b>thrashing, then NotReady: 10 min 42 s</b>", size=11, color=RED)
    d.rect("b-ok", tx("11:21:05"), yn + 40, tx("11:27") - tx("11:21:05"), 10, GREEN_FILL, GREEN)

    ys = lanes["svc"][0]
    d.rect("b-harbor", tx("11:11:16"), ys + 40, tx("11:23:52") - tx("11:11:16"), 10, RED_FILL, RED)
    d.text("t-harbor", tx("11:11:16") + 4, ys + 52, 330, 14, "Harbor down: pulls from registry.jithendar.com fail", size=11, color=RED)
    d.rect("b-all", tx("11:23:52"), ys + 40, tx("11:25:47") - tx("11:23:52"), 10, AMBER_FILL, AMBER)

    yv = lanes["site"][0]
    d.rect("b-site", X0, yv + 22, tx("11:27") - X0, 10, GREEN_FILL, GREEN)
    d.text("t-site", X0 + 4, yv + 4, 520, 14, "jithendar.com: 215 × 200, 4 × 404, no errors in the site's log (11:10–11:22)", size=11, color=GREEN)
    d.rect("b-admin", tx("11:10:33"), yv + 44, tx("11:21:30") - tx("11:10:33"), 10, RED_FILL, RED)
    d.text("t-admin", tx("11:10:33") - 330, yv + 42, 320, 14, "/llm, /chat, /argocd, /grafana, docling: down", size=11, color=RED, align="right")

    colours = {"me": BLUE, "node": "#475569", "svc": RED}
    last_x = {}
    for n, lane, at, _ in EVENTS:
        y = lanes[lane][0] + 18 if lane != "me" else lanes[lane][0] + 32
        x = tx(at)
        if lane in last_x and x - last_x[lane] < 26:
            x = last_x[lane] + 26
        last_x[lane] = x
        fill = GREEN if n in (10, 12) else (AMBER if n == 4 else colours[lane])
        event_dot(d, f"ev{n}", n, x, y, fill)

    ya = 358
    d.rect("axis", X0, ya, tx("11:27") - X0, 2, GREY)
    for hh, mm in ((10, 55), (11, 0), (11, 5), (11, 10), (11, 15), (11, 20), (11, 25)):
        x = tx(f"{hh}:{mm:02d}")
        d.rect(f"tick{hh}{mm}", x - 1, ya - 4, 2, 10, GREY)
        d.text(f"tick{hh}{mm}-t", x - 20, ya + 8, 40, 16, f"{hh}:{mm:02d}", size=11, align="center")

    y = 400
    for n, lane, at, text in EVENTS:
        fill = GREEN if n in (10, 12) else (AMBER if n == 4 else colours[lane])
        event_dot(d, f"lst{n}", n, 31, y + 9, fill)
        d.text(f"lst{n}-t", 50, y, 900, 18, f"<b>{at}</b>  {escape(text)}", color=TEXT)
        y += 26
    d.text("note", 20, y + 6, 940, 34, "Event 4 is the trigger. The first LiteLLM pod (event 3) had already taken worker1 to 91% of its memory; "
           "the restart put a second one next to it.", color=TEXT)
    return d


# 3. Recovery ---------------------------------------------------------------------------------------
STEPS = [
    ("1. Notice", "11:20", "k9s could not stream logs:", "502 from worker1's kubelet;", "get nodes: worker1 NotReady"),
    ("2. Size the damage", "11:21", "site 200: its pods elsewhere", "gateway: 2nd replica worker3", "list what runs on worker1"),
    ("3. Do no more harm", "from 11:21", "no restarts, no pod deletes,", "no rollouts: a restart is", "how this started"),
    ("4. Look from outside", "11:21", "conditions Unknown since", "11:10:22; CPU 3.9 of 4 cores", "read the event stream"),
    ("5. Node comes back", "11:20:54", "kernel kills docling-serve;", "kubelet Ready at 11:21:05,", "stops the evicted pods"),
    ("6. Dependents recover", "11:22 to 11:25", "valkey-0 recreated 11:22:03", "Harbor core up at 11:23:52", "image pulls work again"),
    ("7. Confirm the cause", "11:25 to 11:45", "SystemOOM event, no reboot", "ReplicaSet at 11:10:23", "memory samples, configz"),
]


def recovery():
    d = Diagram("worker1-oom-recovery", 960, 470, "How worker1 and the services on it recovered, step by step")
    w, h, gap = 210, 112, 26
    pos = []
    for i, (title, when, *lines) in enumerate(STEPS):
        row, col = divmod(i, 4)
        x = 20 + col * (w + gap)
        y = 56 + row * (h + 70)
        kind = "ops" if i in (2,) else ("compute" if i in (4, 5) else "security")
        d.node(f"s{i}", kind, x, y, w, h, title, when, *lines, align="left")
        pos.append((x, y))
    for i in range(len(STEPS) - 1):
        if i == 3:
            d.edge("s3", "s4", kind="next", exit=(0.5, 1), entry=(0.5, 0), via=((pos[3][0] + w / 2, pos[3][1] + h + 35), (pos[4][0] + w / 2, pos[3][1] + h + 35)))
        else:
            d.edge(f"s{i}", f"s{i+1}", kind="next", exit=(1, 0.5), entry=(0, 0.5))
    d.node("plan-b", "optional", 20 + 3 * (w + gap), 56 + h + 70, w, h, "If it had stayed down", "next step:",
           "reboot it from the Hetzner", "console (no shell access", "was used)", align="left")
    d.text("note", 20, 56 + 2 * h + 70 + 24, 920, 40, "<b>The node recovered on its own:</b> the kernel's OOM killer freed memory at 11:20:54 and the "
           "kubelet reported Ready eleven seconds later. My part was to stop making it worse and to check each layer as it came back.", color=TEXT)
    d.legend(56 + 2 * h + 70 + 76, labels={"security": "Check", "ops": "Decision", "compute": "Recovery", "optional": "Fallback, not needed"})
    return d


# 4. Causes and follow-ups -------------------------------------------------------------------------
CAUSES = [
    ("c1", "Restart during a rollout", "a second LiteLLM pod while the", "first one was still settling"),
    ("c2", "Requests below real use", "worker1: 69% requested, 80% used;", "the scheduler sees requests only"),
    ("c3", "No memory guardrail", "no memory eviction threshold,", "nothing reserved for the system"),
    ("c4", "Nobody was told", "no node or memory alert, no", "Alertmanager; Prometheus was on worker1"),
    ("c5", "Single points on one node", "Valkey primary path, Prometheus,", "Open WebUI's volume on worker1"),
]
FIXES = [
    ("f1", "Wait, then look, then restart", "rollout status first; kubectl top", "nodes; one change at a time"),
    ("f2", "Requests that match reality", "compare working set with requests;", "raise the ones that lie"),
    ("f3", "Reserve memory, evict early", "system-reserved, kube-reserved and", "memory.available on every node"),
    ("f4", "Alerts that reach me", "NotReady and node memory rules;", "Alertmanager; watch from outside"),
    ("f5", "Spread what others depend on", "anti-affinity and placement for", "Valkey, Prometheus, Open WebUI"),
]


def followups():
    d = Diagram("worker1-oom-followups", 960, 640, "What let one restart take a node down, and what I am changing")
    d.text("hc", 20, 46, 400, 18, "<b>What let it happen</b>", color=TEXT)
    d.text("hf", 540, 46, 400, 18, "<b>Follow-up</b>", color=TEXT)
    y = 72
    for (cid, ct, *cl), (fid, ft, *fl) in zip(CAUSES, FIXES):
        d.node(cid, "security", 20, y, 380, 84, ct, *cl, align="left")
        d.node(fid, "ops", 540, y, 400, 84, ft, *fl, align="left")
        d.edge(cid, fid, kind="fixes", exit=(1, 0.5), entry=(0, 0.5))
        y += 100
    d.legend(y + 6, labels={"security": "Cause", "ops": "Follow-up (open)"})
    return d


def main():
    for build in (memory, timeline, recovery, followups):
        d = build()
        (HERE / f"{d.name}.drawio").write_text(d.xml())
        print("wrote", d.name)


if __name__ == "__main__":
    main()
