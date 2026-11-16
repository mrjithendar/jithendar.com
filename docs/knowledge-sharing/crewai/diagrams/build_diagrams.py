#!/usr/bin/env python3
"""Figures for the two CrewAI articles: editable .drawio files and matching SVGs.

    python3 docs/knowledge-sharing/crewai/diagrams/build_diagrams.py        (from the repository root)

Reuses the layout, palette and draw.io writer of the RoboShop AI series. The SVGs are rendered here, not exported by
draw.io: if a .drawio file is edited by hand, re-export it from draw.io over the SVG. Every figure follows Git only,
read on 2026-11-16: mrjithendar/moks-sre at 28d9ba1 (the four moks-crewai-* figures), moks-tech/moks-cms at bb6a4ba and
this repository's kubernetes/ folder (the four seo-agent-* figures). No cluster was inspected.

verify() refuses a page whose boxes overlap, whose arrows run through a box or a zone label, or whose arrow labels
cover a box, on top of the label-fit checks the shared writer already makes.
"""
import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[3] / "public" / "images" / "crewai"
spec = importlib.util.spec_from_file_location("series_diagrams", HERE.parents[1] / "roboshop-ai" / "diagrams" / "build_diagrams.py")
series = importlib.util.module_from_spec(spec)
sys.modules["series_diagrams"] = series
spec.loader.exec_module(series)
Page = series.Page
ZONE_LABEL = 12 * 0.56  # px per character of a zone label (12 px, semi-bold), as the shared writer estimates it


def frame(p, label, x, y, w, h, label_x=None):
    """A zone. With label_x the label starts there instead of the corner, clear of the arrows that enter the zone."""
    if label_x is None:
        p.zone(label, x, y, w, h)
    else:
        p.zone("", x, y, w, h)
        p.note(label_x, y + 4, label, size=12, bold=True)


def at(p, node, x=None, y=None):
    """The fraction along a side of `node` that sits at page coordinate x (top/bottom) or y (left/right)."""
    n = p.nodes[node]
    return (x - n["x"]) / n["w"] if x is not None else (y - n["y"]) / n["h"]


def link(p, a, b, kind="sync", label="", a_side=None, b_side=None, a_at=0.5, b_at=0.5, via=None, seg=None, f=0.5, dx=0, dy=0):
    """An arrow from a to b. Sides default to the facing ones, and a bend is added where the anchors do not line up.
    The label sits on segment `seg` (the longest by default) at fraction f, moved by dx, dy."""
    na, nb = p.nodes[a], p.nodes[b]
    if a_side is None or b_side is None:
        if nb["y"] >= na["y"] + na["h"]:
            da, db = "b", "t"
        elif na["y"] >= nb["y"] + nb["h"]:
            da, db = "t", "b"
        elif nb["x"] >= na["x"] + na["w"]:
            da, db = "r", "l"
        else:
            da, db = "l", "r"
        a_side, b_side = a_side or da, b_side or db
    (x0, y0), (x1, y1) = p.port(a, a_side, a_at), p.port(b, b_side, b_at)
    if via is None:
        va, vb = a_side in "tb", b_side in "tb"
        if va and vb:
            via = [] if abs(x0 - x1) < 0.01 else [(x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)]
        elif not va and not vb:
            via = [] if abs(y0 - y1) < 0.01 else [((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)]
        else:
            via = [(x0, y1)] if va else [(x1, y0)]
    t = 0.0
    if label:
        points = [(x0, y0), *via, (x1, y1)]
        lengths = [abs(q[0] - r[0]) + abs(q[1] - r[1]) for q, r in zip(points, points[1:])]
        i = seg if seg is not None else max(range(len(lengths)), key=lengths.__getitem__)
        t = 2 * (sum(lengths[:i]) + lengths[i] * f) / sum(lengths) - 1
    p.edge(a, b, kind=kind, label=label, a_side=a_side, b_side=b_side, a_at=a_at, b_at=b_at, via=tuple(via), dx=dx, dy=dy, t=t)


def verify(p):
    bad = []
    nodes = list(p.nodes.values())
    for n in nodes:
        if n["x"] < 0 or n["y"] < 0 or n["x"] + n["w"] > p.w or n["y"] + n["h"] > p.h:
            bad.append(f"{n['id']} leaves the page")
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            if a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]:
                bad.append(f"{a['id']} overlaps {b['id']}")
    labels = [(z["label"], z["x"] + 8, z["y"] + 4) for z in p.zones if z["label"]] + [(t["text"], t["x"], t["y"]) for t in p.notes if t["bold"]]
    boxes = []
    for e in p.edges:
        for (x0, y0), (x1, y1) in zip(e["points"], e["points"][1:]):
            if abs(x0 - x1) > 0.01 and abs(y0 - y1) > 0.01:
                bad.append(f"{e['a']}->{e['b']}: a slanted segment")
            lo_x, hi_x, lo_y, hi_y = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
            if lo_x < 0 or lo_y < 0 or hi_x > p.w or hi_y > p.h:
                bad.append(f"{e['a']}->{e['b']} leaves the page")
            for n in nodes:
                if lo_x < n["x"] + n["w"] - 0.5 and hi_x > n["x"] + 0.5 and lo_y < n["y"] + n["h"] - 0.5 and hi_y > n["y"] + 0.5:
                    bad.append(f"{e['a']}->{e['b']} runs through {n['id']}")
            for text, lx, ly in labels:
                if lo_x < lx + len(text) * ZONE_LABEL + 4 and hi_x > lx - 4 and lo_y < ly + 18 and hi_y > ly:
                    bad.append(f"{e['a']}->{e['b']} crosses the zone label '{text}'")
        if e["label"]:
            x, y = series.label_point(e["points"], e["t"])
            w = series.text_width(e["label"], series.EDGE_SIZE) + 8
            box = (x + e["dx"] - w / 2, y + e["dy"] - 8.5, w, 17, e["label"])
            for n in nodes:
                if box[0] < n["x"] + n["w"] and n["x"] < box[0] + w and box[1] < n["y"] + n["h"] and n["y"] < box[1] + 17:
                    bad.append(f"label '{e['label']}' covers {n['id']}")
            for other in boxes:
                if box[0] < other[0] + other[2] and other[0] < box[0] + w and box[1] < other[1] + 17 and other[1] < box[1] + 17:
                    bad.append(f"labels '{e['label']}' and '{other[4]}' overlap")
            boxes.append(box)
    return [f"{p.figure}: {m}" for m in bad]


# ---- Article 1: CrewAI in MOKS (mrjithendar/moks-sre) ---------------------------------------------------------

def moks_request_path():
    p = Page("moks-crewai-request-path", "Request path", 900, 660,
             "How a CrewAI investigation travels through MOKS, next to the default LangGraph path",
             "Top to bottom. The Investigate page asks GET /investigate/config whether CrewAI is available and posts to "
             "POST /investigations/crewai, which answers 404 with the flag off and 503 with no CrewAI worker or no model. "
             "start_investigation checks permission and scope and queues a row whose first event carries a crewai block. "
             "In PostgreSQL sit the component_versions row the CrewAI worker keeps fresh, the evidence and audit rows, and "
             "the queue. Two kinds of worker claim from the queue with FOR UPDATE SKIP LOCKED: the CrewAI worker on the "
             "moks-crewai image takes only rows with a crewai block and runs the crew; the default worker takes the rest "
             "and runs the LangGraph graph. Both end in the same checks: validate_claims, verify_causes, the relevance "
             "check, the stored report and the reply in the conversation.")
    frame(p, "Browser", 15, 12, 870, 96)
    p.node("ui", "browser", 30, 38, 840, 58, "Investigate page",
           "the CrewAI form renders only when /investigate/config reports crewai.available = true")
    frame(p, "moks-api: default image, never imports crewai", 15, 124, 870, 134, label_x=575)
    p.node("cfg", "gateway", 30, 152, 250, 92, "GET /investigate/config", "crewai: enabled, available,", "reason, version, limits")
    p.node("route", "gateway", 325, 152, 250, 92, "POST /investigations/crewai", "flag off: 404", "no worker or no model: 503")
    p.node("start", "service", 620, 152, 250, 92, "start_investigation()", "permission + scope, rate limit", "queues the row")
    frame(p, "PostgreSQL", 15, 274, 870, 134)
    p.node("ver", "store", 30, 302, 250, 92, "component_versions", "component crewai + its version", "fresh for 5 minutes")
    p.node("evid", "store", 325, 302, 250, 92, "evidence + audit", "one row per tool call", "refs E1, E2, …")
    p.node("queue", "store", 620, 302, 250, 92, "investigations + events", "status queued", "seq-0 event carries crewai")
    frame(p, "Workers", 15, 436, 870, 134)
    p.node("crew", "agent", 30, 464, 545, 92, "moks-crewai: the CrewAI worker", "moks-crewai image, MOKS_WORKER_CLASSES=crewai",
           "runs crew_runner.run(): three agents in sequence")
    p.node("dflt", "external", 620, 464, 250, 92, "moks-worker: the default", "default image, class interactive", "runs graph.run() (LangGraph)")
    p.node("tail", "service", 30, 588, 840, 58, "The same tail for both paths",
           "validate_claims → verify_causes → relevance check → stored report → reply in the conversation (SSE)")
    link(p, "ui", "cfg", a_at=at(p, "ui", x=155))
    link(p, "ui", "route", a_at=at(p, "ui", x=450))
    link(p, "route", "start")
    link(p, "cfg", "ver", kind="dashed")
    link(p, "start", "queue", kind="write")
    link(p, "crew", "ver", kind="write", a_at=at(p, "crew", x=155), label="heartbeat", f=0.6, dx=44)
    link(p, "crew", "evid", kind="write", a_at=at(p, "crew", x=400), b_at=0.3, label="evidence", f=0.6, dx=40)
    link(p, "queue", "crew", a_at=0.3, b_at=at(p, "crew", x=520), via=[(695, 422), (520, 422)], label="crewai block", seg=1)
    link(p, "queue", "dflt", a_at=0.7, b_at=0.7, label="no block", f=0.4, dx=38)
    link(p, "crew", "tail", b_at=at(p, "tail", x=302.5))
    link(p, "dflt", "tail", b_at=at(p, "tail", x=745))
    return p


def moks_crew():
    p = Page("moks-crewai-crew", "The crew", 900, 640,
             "Three agents in sequence, with MOKS code between the model and the cluster and after the answer",
             "Top row: the CrewAI crew, a sequential process of three agents. The workload investigator has nine read-only "
             "tools for pods, events, logs, metrics and alerts. The change investigator has five for rollouts, configuration, "
             "Git commits and runbooks. The incident reviewer has only evidence_list and writes one JSON report. Second row: "
             "every tool call passes bind(), which fixes the namespace, workload and time window in code and refuses anything "
             "else, then the ToolExecutor, which checks RBAC and scope, applies the timeout, redacts and truncates, and "
             "audits. The result is stored as evidence and listed in the evidence registry with an excerpt. Third row: the "
             "live systems the tools read. Bottom row: the reviewer's JSON goes through validate(), which rejects invented "
             "citations, removes uncited claims and caps confidence, then through the checks every MOKS report passes, and "
             "is stored with a crewai block.")
    frame(p, "CrewAI crew: Process.sequential, max_iter 5, no delegation, memory, planning or cache", 15, 12, 870, 166)
    p.node("a1", "agent", 30, 40, 270, 124, "1. Workload investigator", "namespace_health, workload_status,", "workload_pods, describe_pod,",
           "recent_events, pod_logs, search_logs,", "pod_metrics, firing_alerts")
    p.node("a2", "agent", 315, 40, 270, 124, "2. Change investigator", "rollout_history, config_audit,", "recent_commits, deployed_commit,", "search_runbooks")
    p.node("a3", "agent", 600, 40, 270, 124, "3. Incident reviewer", "evidence_list only", "writes one JSON report", "cites ids, never quotes")
    frame(p, "MOKS code between the model and the cluster", 15, 206, 870, 134, label_x=245)
    p.node("bind", "gateway", 30, 234, 270, 92, "bind(): target fixed in code", "namespace, workload, time window", "another namespace or pod: refused")
    p.node("exec", "service", 315, 234, 270, 92, "ToolExecutor.run()", "RBAC + scope, timeout,", "redaction, truncation, audit")
    p.node("reg", "store", 600, 234, 270, 92, "Evidence registry", "E1, E2, … with excerpts", "cut from the stored rows")
    frame(p, "Live systems: 14 read-only tools on the allowlist", 15, 368, 870, 100)
    p.node("live", "external", 30, 396, 840, 58, "Kubernetes API · Loki · Prometheus · Git · knowledge base",
           "no exec, apply, patch, delete, scale or Secret read")
    frame(p, "After the crew: checks in code", 15, 496, 870, 132, label_x=245)
    p.node("v1", "gateway", 30, 524, 270, 92, "validate()", "invented citation: rejected", "uncited claim: removed", "confidence capped by evidence")
    p.node("v2", "service", 315, 524, 270, 92, "validate_claims + verify_causes", "the checks every MOKS", "LLM report passes")
    p.node("v3", "store", 600, 524, 270, 92, "Stored report", "facts, causes, missing evidence,", "next steps + a crewai block")
    link(p, "a1", "a2")
    link(p, "a2", "a3")
    link(p, "a1", "bind", label="tool call", dx=-40)
    link(p, "a2", "bind", a_at=0.3, b_at=at(p, "bind", x=230), via=[(396, 192), (230, 192)])
    link(p, "bind", "exec")
    link(p, "exec", "reg", kind="write")
    link(p, "reg", "a3", kind="dashed", label="evidence_list", dx=54)
    link(p, "exec", "live", kind="dashed")
    link(p, "a3", "v1", a_side="r", b_side="t", via=[(878, 102), (878, 482), (165, 482)], label="JSON answer", seg=2)
    link(p, "v1", "v2")
    link(p, "v2", "v3", kind="write")
    return p


def moks_thread_bridge():
    p = Page("moks-crewai-thread-bridge", "Thread bridge", 900, 500,
             "CrewAI runs its calls in a worker thread; the Bridge hands each one back to the event loop",
             "Left: the worker thread. An agent step builds the prompt and parses the Thought, Action and Observation text. "
             "MoksCrewLLM.call is CrewAI's BaseLLM with function calling off and cuts the reply at the Observation marker. "
             "MoksTool._run is a BaseTool with a pydantic argument schema. Right: the event loop, which owns the database "
             "session, the providers and the executor. crew.akickoff runs inside asyncio.timeout. Each model call crosses "
             "to budget.complete and each tool call crosses to ToolExecutor.run through Bridge.run, which schedules the "
             "coroutine on the loop and waits. Bottom: stopping. Bridge.close is called on cancel, timeout or a limit; the "
             "call in flight is cancelled on the loop and every later call raises CrewStopped, so the crew ends at its "
             "next step.")
    frame(p, "Worker thread: CrewAI's synchronous calls", 15, 12, 380, 330)
    p.node("t1", "agent", 30, 40, 350, 80, "Agent step", "CrewAI builds the prompt and parses", "Thought / Action / Observation")
    p.node("t2", "agent", 30, 144, 350, 80, "MoksCrewLLM.call()", "BaseLLM, function calling off", "cuts the reply at \\nObservation:")
    p.node("t3", "agent", 30, 248, 350, 80, "MoksTool._run()", "BaseTool with a pydantic args_schema", "returns: Evidence E7 … Cite it as E7.")
    frame(p, "Event loop: database session, providers, executor", 505, 12, 380, 330)
    p.node("l1", "service", 520, 40, 350, 80, "crew.akickoff()", "inside asyncio.timeout", "120 s by default")
    p.node("l2", "service", 520, 144, 350, 80, "budget.complete()", "the active chat LLM only", "reservations, daily limits, metering")
    p.node("l3", "service", 520, 248, 350, 80, "ToolExecutor.run()", "RBAC, scope, timeout, redaction", "Evidence row + audit record")
    frame(p, "Stopping: cancel, timeout or a limit", 15, 358, 870, 130)
    p.node("s1", "gateway", 30, 386, 270, 88, "Bridge.close(reason)", "called from the loop side", "the first reason wins")
    p.node("s2", "service", 315, 386, 270, 88, "The call in flight", "its future is cancelled", "on the event loop")
    p.node("s3", "reject", 600, 386, 270, 88, "Every later call", "raises CrewStopped at once:", "the crew ends at its next step")
    link(p, "l1", "t1", label="runs the crew")
    link(p, "t2", "l2", label="Bridge.run()")
    link(p, "t3", "l3", label="Bridge.run()")
    link(p, "t1", "t2", kind="dashed")
    link(p, "t2", "t3", kind="dashed")
    link(p, "s1", "s2")
    link(p, "s2", "s3")
    return p


def moks_build_deploy():
    p = Page("moks-crewai-build-deploy", "Build and deploy", 900, 560,
             "One commit, two images: only the CrewAI worker runs the image that carries crewai",
             "Top: GitHub Actions on a push to master. The check job runs the backend suite on the default pins and the "
             "crewai job runs it again on the CrewAI dependency set. release builds and pushes moks:latest. release-crewai "
             "needs both test jobs, builds the same commit with the build argument MOKS_CREWAI=true, proves crewai imports "
             "on a read-only root with no network, and pushes moks-crewai:latest. Both images go to the Harbor registry. "
             "deploy runs only when MK4_DEPLOY is true and asks Argo CD to sync and restart. In the cluster, the api, "
             "worker, executor and terminal Deployments run moks:latest; the Deployment moks-crewai runs "
             "moks-crewai:latest with MOKS_WORKER_CLASSES=crewai and is rendered by the Argo CD app moks-crewai only "
             "when crewai.enabled is true.")
    frame(p, "GitHub Actions: push to master", 15, 12, 870, 236)
    p.node("check", "service", 30, 40, 250, 80, "check", "backend suite on the default pins", "(pydantic 2.14.3)")
    p.node("crewai", "agent", 325, 40, 250, 80, "crewai", "the same suite on the CrewAI set", "crewai 1.15.36, pydantic < 2.13")
    p.node("rel", "service", 30, 150, 250, 84, "release", "docker build", "pushes moks:latest")
    p.node("relc", "agent", 325, 150, 250, 84, "release-crewai", "--build-arg MOKS_CREWAI=true", "import check: read-only, no network")
    p.node("dep", "gateway", 620, 150, 250, 84, "deploy", "only when MK4_DEPLOY is true", "Argo CD: sync, then restart")
    frame(p, "Harbor: registry.jithendar.com/jithendar", 15, 276, 870, 98, label_x=168)
    p.node("img1", "store", 30, 304, 250, 58, "moks:latest", "the default image")
    p.node("img2", "store", 325, 304, 250, 58, "moks-crewai:latest", "the same commit + 76 packages")
    frame(p, "mk4 cluster: namespace moks", 15, 402, 870, 146, label_x=168)
    p.node("d1", "external", 30, 430, 250, 92, "Every other Deployment", "api, worker, executor, terminal", "image moks:latest")
    p.node("d2", "agent", 325, 430, 250, 92, "Deployment moks-crewai", "image moks-crewai:latest", "MOKS_WORKER_CLASSES=crewai")
    p.node("argo", "gateway", 620, 430, 250, 92, "Argo CD app moks-crewai", "Helm resourceGroup crewai", "renders only if crewai.enabled")
    link(p, "check", "rel", a_at=0.3, b_at=0.3)
    link(p, "check", "relc", a_at=0.75, b_at=0.25, via=[(217.5, 135), (387.5, 135)])
    link(p, "crewai", "relc", a_at=0.7, b_at=0.7)
    link(p, "relc", "dep")
    link(p, "rel", "img1", kind="write")
    link(p, "relc", "img2", kind="write")
    link(p, "img1", "d1", kind="dashed")
    link(p, "img2", "d2", kind="dashed")
    link(p, "dep", "argo", label="sync + restart", f=0.143, dx=56)
    link(p, "argo", "d2", kind="write")
    return p


# ---- Article 2: CrewAI behind jithendar.com (moks-tech/moks-cms services/seo-agent) -----------------------------

def seo_kickoff():
    p = Page("seo-agent-crewai-kickoff", "One kickoff path", 900, 440,
             "Three triggers, one kickoff: how a flow run starts and where its work goes",
             "Top: three triggers. CronJobs named seo-flow-* run python -m app.trigger, the admin UI has Run now buttons "
             "and the review decision, and the admin MCP server has a kickoff_flow tool limited to an allowlist. All three "
             "call POST /flows/{name}/kickoff. Middle, inside the single seo-agent pod: FlowRunner.kickoff applies the "
             "start policy, validates the inputs against a strict model, creates the run row, takes the lock and starts a "
             "background task. The CrewAI Flow runs its start, listen and router methods, with data steps in plain Python. "
             "A Crew runs in a worker thread, sequentially, with read-only tools, a token cap and a wall clock. "
             "ClaudeCrewLLM, a CrewAI BaseLLM, sends each call through the budget guard to the Anthropic SDK. Bottom: "
             "PostgreSQL holds seo_flow_runs with the state after every step, the lock and the usage rows; the web app's "
             "callback API serves articles, validators and the draft API; the Anthropic API answers the model calls.")
    frame(p, "Triggers", 15, 12, 870, 110)
    p.node("cron", "external", 30, 40, 250, 68, "CronJobs seo-flow-*", "python -m app.trigger <flow>", "triggered_by = cron")
    p.node("admin", "browser", 325, 40, 250, 68, "Admin UI", "Run now, review decision", "manual or approval")
    p.node("mcp", "mcp", 620, 40, 250, 68, "Admin MCP: kickoff_flow", "allowlisted flows only", "triggered_by = mcp")
    frame(p, "seo-agent: one replica", 15, 150, 870, 136, label_x=690)
    p.node("runner", "gateway", 30, 178, 200, 94, "FlowRunner.kickoff()", "start policy, strict inputs,", "run row, lock, task")
    p.node("flow", "agent", 240, 178, 200, 94, "CrewAI Flow[State]", "@start @listen @router", "data steps in Python")
    p.node("crew", "agent", 450, 178, 200, 94, "Crew (worker thread)", "sequential, read-only tools,", "token cap + wall clock")
    p.node("llm", "model", 660, 178, 210, 94, "ClaudeCrewLLM", "a CrewAI BaseLLM over the", "budget guard + Anthropic SDK")
    frame(p, "Outside the pod", 15, 314, 870, 114)
    p.node("pg", "store", 30, 342, 410, 72, "PostgreSQL", "seo_flow_runs: state_json after every step, one active run", "per flow + target; advisory lock; seo_llm_usage")
    p.node("web", "edge", 450, 342, 200, 72, "Web app callback API", "articles, validators,", "the draft API")
    p.node("claude", "external", 660, 342, 210, 72, "Anthropic API", "Sonnet, Opus, Haiku", "per agent")
    link(p, "cron", "runner", a_at=at(p, "cron", x=100), b_at=at(p, "runner", x=100))
    link(p, "admin", "runner", b_at=at(p, "runner", x=170), via=[(450, 136), (170, 136)])
    link(p, "mcp", "runner", b_at=at(p, "runner", x=170), via=[(745, 136), (170, 136)], label="POST /flows/{name}/kickoff", seg=1, f=0.25)
    link(p, "runner", "flow")
    link(p, "flow", "crew")
    link(p, "crew", "llm")
    link(p, "runner", "pg", kind="write", a_at=at(p, "runner", x=190), b_at=at(p, "pg", x=190))
    link(p, "flow", "pg", kind="write", a_at=at(p, "flow", x=300), b_at=at(p, "pg", x=300))
    link(p, "flow", "web", a_at=at(p, "flow", x=400), b_at=at(p, "web", x=500), via=[(400, 300), (500, 300)])
    link(p, "crew", "web", kind="dashed", a_at=at(p, "crew", x=590), b_at=at(p, "web", x=590))
    link(p, "llm", "claude")
    return p


def seo_new_article_flow():
    p = Page("seo-agent-new-article-flow", "new_article_flow", 900, 512,
             "new_article_flow as CrewAI sees it: one start method, three listeners per outcome, two routers",
             "Top row: load_brief, the start method, reads the calendar brief from the web app. draft listens to it and to "
             "the router label to_retry; it runs the Editorial Crew and counts the attempt. The router after_draft "
             "returns to_paused when the budget stopped the crew, otherwise to_validate. Second row: validate_draft sends "
             "the document to the web app's validators. The router after_validate returns to_ok, to_retry (once) or "
             "to_fail. failed marks the draft generation_failed. Third row: save_draft is the flow's only write and "
             "ends with outcome draft_ready; paused marks the draft with the budget reason. Bottom: after every method "
             "PgFlowPersistence.save_state writes the state, the step name, tokens and cost into the run's row in "
             "seo_flow_runs.")
    frame(p, "NewArticleFlow(SeoFlow[NewArticleState])", 15, 12, 870, 400)
    p.node("lb", "service", 30, 40, 230, 80, "@start load_brief", "calendar brief from the web app")
    p.node("dr", "agent", 335, 40, 230, 80, "@listen draft", "Editorial Crew, attempts += 1", "BudgetExceeded: paused_budget")
    p.node("ad", "gateway", 640, 40, 230, 80, "@router after_draft", "to_paused or to_validate")
    p.node("fl", "reject", 30, 170, 230, 80, "@listen failed", "draft: generation_failed", "with the validator's errors")
    p.node("av", "gateway", 335, 170, 230, 80, "@router after_validate", "to_ok, to_retry or to_fail", "MAX_ATTEMPTS = 2")
    p.node("vd", "service", 640, 170, 230, 80, "@listen validate_draft", "the web app's validators", "errors: validator_feedback")
    p.node("sd", "store", 335, 300, 230, 80, "@listen save_draft", "the flow's only write", "outcome: draft_ready")
    p.node("ps", "reject", 640, 300, 230, 80, "@listen paused", "draft: generation_failed", "Paused: LLM budget reached")
    p.node("pg", "store", 30, 440, 840, 58, "After every method: PgFlowPersistence.save_state()",
           "writes state_json, current_step, tokens and cost_usd into the run's seo_flow_runs row (never SQLite)")
    link(p, "lb", "dr")
    link(p, "dr", "ad")
    link(p, "ad", "vd", label="to_validate", dx=-48)
    link(p, "vd", "av")
    link(p, "av", "dr", label="to_retry", dx=-38)
    link(p, "av", "fl", label="to_fail")
    link(p, "av", "sd", label="to_ok", dx=-30)
    link(p, "ad", "ps", a_side="r", b_side="r", via=[(878, 80), (878, 340)], label="to_paused", seg=1, f=0.75, dx=-40)
    return p


def seo_editorial_crew():
    p = Page("seo-agent-editorial-crew", "Editorial Crew", 900, 430,
             "The Editorial Crew: four agents write, and code assembles the draft",
             "Top row: four agents in sequence. The researcher runs on Sonnet with up to ten turns and holds vector_search, "
             "read_article and fetch_allowlisted_docs. The technical writer runs on Opus with up to six turns and holds "
             "read_article. The technical reviewer runs on Opus with up to eight turns and holds fetch_allowlisted_docs. "
             "The SEO editor runs on Sonnet with up to four turns, holds gsc_queries_for_topic and vector_search, and "
             "returns metadata only. Second row, in code: every URL a tool fetched is recorded; the body is the reviewer's "
             "corrected text; the editor's answer is parsed as the Pydantic model SeoMetadata. Bottom: NewArticleDraft is "
             "assembled from the body, the metadata, the code blocks extracted from the body and the fact-check flags, "
             "including one for each cited source the crew never fetched.")
    frame(p, "Editorial Crew: Process.sequential, one worker thread", 15, 12, 870, 160)
    p.node("rs", "agent", 30, 40, 195, 116, "Researcher", "Sonnet, up to 10 turns", "vector_search, read_article,", "fetch_allowlisted_docs")
    p.node("wr", "agent", 245, 40, 195, 116, "Technical writer", "Opus, up to 6 turns", "read_article", "writes the full MDX body")
    p.node("rv", "agent", 460, 40, 195, 116, "Technical reviewer", "Opus, up to 8 turns", "fetch_allowlisted_docs", "corrects, flags unsourced")
    p.node("se", "agent", 675, 40, 195, 116, "SEO editor", "Sonnet, up to 4 turns", "gsc_queries_for_topic,", "vector_search")
    frame(p, "Assembled in code, not by an agent", 15, 200, 870, 130, label_x=180)
    p.node("fetched", "store", 30, 228, 270, 88, "fetched[] (on_source hook)", "every URL a tool returned", "during this run")
    p.node("body", "service", 315, 228, 270, 88, "body_mdx", "the reviewer's corrected body:", "text before NEEDS_FACT_CHECK:")
    p.node("meta", "service", 600, 228, 270, 88, "SeoMetadata (Pydantic)", "title, slug, meta, outline,", "sources, links: never a body")
    p.node("draft", "store", 30, 358, 840, 58, "NewArticleDraft",
           "body + metadata + code blocks extracted from the body + fact-check flags (unsourced claims, sources never fetched)")
    link(p, "rs", "wr")
    link(p, "wr", "rv")
    link(p, "rv", "se")
    link(p, "rs", "fetched", kind="dashed", b_at=at(p, "fetched", x=127.5))
    link(p, "rv", "body", b_at=at(p, "body", x=557.5))
    link(p, "se", "meta", b_at=at(p, "meta", x=772.5))
    link(p, "fetched", "draft", kind="dashed", b_at=at(p, "draft", x=165))
    link(p, "body", "draft", kind="write", b_at=at(p, "draft", x=450))
    link(p, "meta", "draft", kind="write", b_at=at(p, "draft", x=735))
    return p


def seo_approval_gate():
    p = Page("seo-agent-approval-gate", "Approval gate", 900, 600,
             "The human gate: a drafting flow ends, and only a recorded approval can start publish_flow",
             "Four rows. Drafting: a crew writes a draft with read-only tools, save_draft sets the status "
             "ready_for_review, and the flow ends with its final state in seo_flow_runs; nothing waits in memory. Web "
             "app, hours or days later: a person accepts, rejects or edits each change, Approve runs a preflight and "
             "writes a row in seo_draft_approvals with the approver, the accepted change ids, a seven-day expiry and a "
             "single use. seo-agent: POST /review/{id}/decision is the only code that sets triggered_by to approval; "
             "check_kickoff answers 403 to publish_flow from cron, a manual kickoff, MCP or a child run; publish_flow "
             "applies the accepted changes. Web app again: cms_publish calls publishWithApproval, which re-checks and "
             "consumes the approval; verify_live tries three times; if it passes, the URL is submitted, reindexed and "
             "scheduled for measurement, and if it fails there is an alert with a one-click rollback and nothing is "
             "submitted.")
    frame(p, "Drafting: optimize_article_flow or new_article_flow", 15, 12, 870, 122, label_x=520)
    p.node("d1", "agent", 30, 40, 250, 80, "A crew writes a draft", "its agents hold read-only tools")
    p.node("d2", "service", 325, 40, 250, 80, "save_draft", "status ready_for_review")
    p.node("d3", "store", 620, 40, 250, 80, "The flow ends", "final state in seo_flow_runs")
    frame(p, "Web app: the review UI, hours or days later", 15, 162, 870, 122, label_x=300)
    p.node("r1", "browser", 30, 190, 250, 80, "A person reviews", "accept, reject or edit", "each change")
    p.node("r2", "edge", 325, 190, 250, 80, "Approve", "preflight, then a row in", "seo_draft_approvals")
    p.node("r3", "store", 620, 190, 250, 80, "The approval", "approver, accepted change ids,", "7-day expiry, single use")
    frame(p, "seo-agent", 15, 312, 870, 122, label_x=300)
    p.node("dec", "gateway", 30, 340, 250, 80, "POST /review/{id}/decision", "the only code that sets", "triggered_by = approval")
    p.node("pol", "gateway", 325, 340, 250, 80, "check_kickoff()", "publish_flow from cron, manual,", "MCP or a child run: 403")
    p.node("pub", "agent", 620, 340, 250, 80, "publish_flow", "apply_changes: the accepted", "change ids and edits")
    frame(p, "Web app again", 15, 462, 870, 122)
    p.node("end", "store", 30, 490, 250, 80, "After verification", "passed: submit, reindex, measure", "failed: alert + rollback offer")
    p.node("vl", "service", 325, 490, 250, 80, "verify_live", "3 attempts: 40 s, 30 s, 60 s")
    p.node("cp", "edge", 620, 490, 250, 80, "cms_publish", "publishWithApproval re-checks", "and consumes the approval")
    link(p, "d1", "d2")
    link(p, "d2", "d3", kind="write")
    link(p, "d3", "r1", kind="dashed", via=[(745, 148), (155, 148)], label="nothing waits in memory", seg=1)
    link(p, "r1", "r2")
    link(p, "r2", "r3", kind="write")
    link(p, "r3", "dec", via=[(745, 298), (155, 298)], label="decision: approve + approval_id", seg=1)
    link(p, "dec", "pol")
    link(p, "pol", "pub")
    link(p, "pub", "cp")
    link(p, "cp", "vl")
    link(p, "vl", "end")
    return p


FILES = (moks_request_path, moks_crew, moks_thread_bridge, moks_build_deploy,
         seo_kickoff, seo_new_article_flow, seo_editorial_crew, seo_approval_gate)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pages = [make() for make in FILES]
    problems = [m for page in pages for m in verify(page)]
    if problems:
        raise SystemExit("\n".join(problems))
    for page in pages:
        mxfile = ET.Element("mxfile", host="app.diagrams.net", agent="build_diagrams.py", version="24.7.17", type="device")
        mxfile.append(series.page_xml(page, 0))
        ET.indent(mxfile)
        (HERE / f"{page.figure}.drawio").write_bytes(ET.tostring(mxfile, encoding="utf-8", xml_declaration=False))
        (OUT / f"{page.figure}.svg").write_text(series.page_svg(page), encoding="utf-8")
    (HERE / "figures.txt").write_text("".join(f"{page.figure} {page.w} {page.h}\n" for page in pages), encoding="utf-8")
    print(f"{len(pages)} .drawio files and SVGs")


if __name__ == "__main__":
    main()
