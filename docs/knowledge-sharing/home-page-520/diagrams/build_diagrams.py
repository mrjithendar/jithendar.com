#!/usr/bin/env python3
"""Figures for content/blog/cloudflare-520-home-page-postmortem-jithendar-com.mdx (the 23 November 2026 incident).

    python3 docs/knowledge-sharing/home-page-520/diagrams/build_diagrams.py   # writes the .drawio files
    bash docs/knowledge-sharing/home-page-520/diagrams/export.sh              # draw.io CLI → public/images/home-page-520/

If you edit a .drawio file by hand, run only export.sh afterwards. Running this script overwrites the edits.

Every time and number here comes from ../evidence (Kubernetes events, ReplicaSets, managed fields, GitHub Actions
run and job times, the site's request log, and the curl checks). Times are UTC.
"""
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio_model import ARROWS, FONT, TEXT, Diagram  # noqa: E402

# Arrow kinds for this article only (the shared writer stays unchanged).
ARROWS["check"] = ("#0f766e", 1.5, "8 4", "What a check tested")
ARROWS["next"] = ("#0f766e", 1.5, "8 4", "Next question")
ARROWS["leads"] = ("#475569", 1.5, None, "Answer and what it means")
ARROWS["fixes"] = ("#0f766e", 1.5, "8 4", "Addressed by")

HERE = Path(__file__).resolve().parent


def path():
    d = Diagram("home-page-520-path", 960, 600, "Where the request for jithendar.com/ failed, and what each check showed")
    d.zone("z-you", "Visitor", 20, 50, 150, 150, "plain")
    d.zone("z-cf", "Cloudflare (Singapore edge)", 190, 50, 230, 150, "risk")
    d.zone("z-mk4", "mk4 cluster (k3s), namespace jithendar", 440, 50, 500, 150, "cluster")

    d.node("browser", "client", 32, 85, 126, 96, "Browser", "GET /", "520, 502 or", "no answer")
    d.node("cf", "network", 202, 85, 206, 96, "Cloudflare cache", "rule: cache HTML by URL", "key / : broken", "every other key: fine")
    d.node("gw", "network", 452, 85, 150, 96, "Istio gateway", "TLS, routes,", "compression")
    d.node("proxy", "compute", 622, 85, 130, 96, "istio-proxy", "sidecar", "in each pod")
    d.node("web", "service", 772, 85, 156, 96, "web: Next.js", "ISR page cache,", "2 pods, warm-up", "of 91 pages")
    d.edge("browser", "cf", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("cf", "gw", "fetch", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("gw", "proxy", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("proxy", "web", exit=(1, 0.5), entry=(0, 0.5))
    d.marker(1, 404, 89)

    y, h = 250, 132
    d.node("c-cf", "security", 20, y, 290, h, "1. Through Cloudflare", "GET /  →  520, 502 or time-out",
           "HEAD /  →  200 (not cached)", "GET /?a=1 and GET /?  →  200", "GET /blog, /privacy-policy  →  200",
           "after the purge: GET /  →  200, HIT", align="left")
    d.node("c-gw", "security", 335, y, 290, h, "2. At the origin, no Cloudflare", "curl --resolve to the gateway",
           "GET /  →  200, 174 KB, about 1 s", "IPv4 and IPv6; HTTP/1.1 and HTTP/2",
           "identity, gzip, br and zstd: 200", align="left")
    d.node("c-pod", "security", 650, y, 290, h, "3. At the pod", "port-forward: GET /  →  200 in 1.3 s",
           "request log: Cloudflare's tagged", "GET / answered 200 in 3 ms, while", "the client got no answer at all",
           "warm-up after a start: 52 to 54 s", align="left")
    d.edge("c-cf", "cf", "tests", exit=(0.65, 0), entry=(0.5, 1), kind="check")
    d.edge("c-gw", "gw", "tests", exit=(0.5, 0), entry=(0.5, 1), kind="check")
    d.edge("c-pod", "web", "tests", exit=(0.75, 0), entry=(0.5, 1), kind="check")

    d.node("fix", "ops", 20, 420, 920, 56, "Fix: purge https://jithendar.com/ from Cloudflare's cache (Admin → Cache)",
           "No code, pod or gateway change. The same URL answered 200 within a minute and was cached again.")
    d.text("note", 20, 488, 920, 40, "<b>Only one cache key was broken.</b> The pod, the gateway and the page itself were fine; "
           "the same page under another key (a query string, or a HEAD request, which Cloudflare does not cache) worked "
           "throughout.", color=TEXT)
    d.legend(540, failure=True, labels={"client": "Visitor", "network": "Edge and gateway", "compute": "Sidecar",
                                         "service": "Site", "security": "Check and result", "ops": "Fix"})
    return d


# Timeline -------------------------------------------------------------------------------------
T0, X0, PX_PER_MIN = 15, 130, 14.6  # 08:15 at x=130


def tx(hhmmss):
    h, m, s = (int(p) for p in hhmmss.split(":"))
    return round(X0 + ((h - 8) * 60 + m - T0 + s / 60) * PX_PER_MIN)


EVENTS = [  # number, time label, lane, x time, text
    (1, "08:19:58", "chg", "08:19:58", "moks-cms #192 merged: the Reader Revenue Manager code"),
    (2, "08:20–08:28", "chg", "08:24:14", "moks-cms builds and pushes the new :latest image (08:20:01–08:28:28)"),
    (3, "08:21:08", "chg", "08:21:08", "jithendar.com #17 merged: one key in site.json"),
    (4, "08:21:56", "pod", "08:21:56", "deploy: new ConfigMap, then a restart at 08:22:01, still on the old image; smoke test passes"),
    (5, "08:29:36", "chg", "08:29:36", "deploy re-run by hand to pick up the image; restart at 08:30:11; smoke test passes 08:30:53"),
    (6, "08:30:24", "pod", "08:30:40", "new pods: startup, liveness and readiness probes time out (08:30:24–08:30:59)"),
    (7, "08:39:39", "cf", "08:39:39", "first failed GET / through Cloudflare; /blog answers 200"),
    (8, "08:41:31", "pod", "08:41:31", "both pods deleted; the new pods warm up for 52–54 s and fail probes meanwhile"),
    (9, "08:53:44", "cf", "08:53:44", "Cloudflare's 520 page in the browser"),
    (10, "08:54:21", "cf", "08:54:21", "a tagged GET / through Cloudflare reaches a pod: 200 in 3 ms; the client gets nothing"),
    (11, "09:02–09:06", "cf", "09:04:25", "purges from Admin → Cache (site caches and Cloudflare)"),
    (12, "09:07:21", "cf", "09:07:21", "GET / through Cloudflare: 200, then served from Cloudflare's cache (HIT)"),
]


def event_dot(d, id, n, cx, cy, fill):
    style = "ellipse;" + d.style(html=1, fillColor=fill, strokeColor="#ffffff", strokeWidth=2, fontColor="#ffffff",
                                 fontStyle=1, fontFamily=FONT, fontSize=11, align="center", verticalAlign="middle")
    d._add(id, str(n), style, cx - 11, cy - 11, 22, 22)


def timeline():
    d = Diagram("home-page-520-timeline", 960, 760, "23 November 2026 (UTC): what changed, what the pods did, and what visitors got")
    lanes = {"chg": (60, "Changes and deploys"), "pod": (140, "Pods"), "cf": (220, "GET / through Cloudflare")}
    lane_h = 64
    for key, (y, label) in lanes.items():
        d.rect(f"lane-{key}", X0 - 10, y, tx("09:10:00") - X0 + 20, lane_h, "#f8fafc", "#e2e8f0")
        d.text(f"lane-{key}-t", 20, y + 8, 100, 48, f"<b>{escape(label)}</b>", color=TEXT)

    # bars
    yc = lanes["chg"][0]
    d.rect("b-build", tx("08:20:01"), yc + 40, tx("08:28:28") - tx("08:20:01"), 10, "#bfdbfe", "#1d4ed8")
    yp = lanes["pod"][0]
    d.rect("b-probe1", tx("08:30:24"), yp + 40, max(tx("08:30:59") - tx("08:30:24"), 6), 10, "#fecaca", "#b91c1c")
    d.rect("b-warm", tx("08:41:40"), yp + 40, tx("08:42:35") - tx("08:41:40"), 10, "#fecaca", "#b91c1c")
    d.rect("b-roll1", tx("08:21:56"), yp + 40, max(tx("08:22:01") - tx("08:21:56"), 6), 10, "#e2e8f0", "#64748b")
    d.rect("b-roll2", tx("08:30:11"), yp + 40, 4, 10, "#e2e8f0", "#64748b")
    yf = lanes["cf"][0]
    d.rect("b-unknown", tx("08:22:01"), yf + 40, tx("08:39:39") - tx("08:22:01"), 10, "#f1f5f9", "#94a3b8")
    d.rect("b-down", tx("08:39:39"), yf + 40, tx("09:07:21") - tx("08:39:39"), 10, "#fca5a5", "#b91c1c")
    d.rect("b-purge", tx("09:02:43"), yf + 52, tx("09:06:07") - tx("09:02:43"), 6, "#99f6e4", "#0f766e")
    d.rect("b-up", tx("09:07:21"), yf + 40, tx("09:10:00") - tx("09:07:21"), 10, "#bbf7d0", "#047857")
    d.text("t-unknown", tx("08:22:01") + 4, yf + 22, 230, 16, "not checked (Cloudflare analytics: to do)", size=11)
    d.text("t-down", tx("08:39:39") + 4, yf + 22, 260, 16, "<b>fails: 520, 502 or no answer (≥ 28 min)</b>", size=11, color="#b91c1c")

    # event dots, staggered so neighbours do not overlap
    colours = {"chg": "#1d4ed8", "pod": "#475569", "cf": "#b91c1c"}
    last_x = {}
    for n, _, lane, at, _ in EVENTS:
        y = lanes[lane][0] + 18
        x = tx(at)
        if lane in last_x and x - last_x[lane] < 26:
            x = last_x[lane] + 26
        last_x[lane] = x
        fill = "#047857" if n == 12 else colours[lane]
        event_dot(d, f"ev{n}", n, x, y, fill)

    # axis
    ya = 300
    d.rect("axis", X0, ya, tx("09:10:00") - X0, 2, "#64748b")
    for m in range(0, 56, 5):
        x = round(X0 + m * PX_PER_MIN)
        hh, mm = divmod(8 * 60 + T0 + m, 60)
        d.rect(f"tick{m}", x - 1, ya - 4, 2, 10, "#64748b")
        d.text(f"tickt{m}", x - 20, ya + 8, 40, 16, f"{hh:02d}:{mm:02d}", size=11, align="center")

    # numbered list
    yl = 345
    d.text("list-h", 20, yl, 920, 18, "<b>Events</b> (times from Kubernetes events, ReplicaSets, GitHub Actions and the site's request log)", color=TEXT)
    for i, (n, when, lane, _, what) in enumerate(EVENTS):
        y = yl + 26 + i * 26
        fill = "#047857" if n == 12 else colours[lane]
        event_dot(d, f"evl{n}", n, 31, y + 9, fill)
        d.text(f"lw{n}", 52, y, 100, 18, f"<b>{escape(when)}</b>", color=TEXT)
        d.text(f"lt{n}", 150, y, 790, 18, escape(what), color=TEXT)
    yk = yl + 26 + len(EVENTS) * 26 + 8
    keys = [("#1d4ed8", "Changes and deploys"), ("#475569", "Pods"), ("#b91c1c", "Through Cloudflare"),
            ("#bfdbfe", "Image build"), ("#fecaca", "Probes timing out"), ("#99f6e4", "Purges"), ("#bbf7d0", "Working again")]
    x = 20
    for i, (fill, label) in enumerate(keys):
        width = 28 + round(len(label) * 6.6)
        if x + width > 940:
            x, yk = 20, yk + 24
        d.rect(f"k{i}", x, yk + 2, 22, 14, fill, "#64748b")
        d.text(f"kt{i}", x + 28, yk, width - 28, 18, escape(label))
        x += width + 18
    d.h = yk + 30
    return d


def narrowing():
    d = Diagram("home-page-520-narrowing", 960, 640, "Narrowing it down: five questions, each answered with one command")
    rows = [
        ("Is the whole site down?", "No: /blog and /privacy-policy", "answer 200 through Cloudflare", "not an outage of the site"),
        ("Does a pod serve / ?", "Yes: port-forward to the pod,", "200, 174 KB in 1.3 s", "the app and ISR cache are fine"),
        ("Does the origin serve / ?", "Yes: curl --resolve past Cloudflare,", "200 on IPv4, IPv6, h1, h2, any encoding", "Istio and TLS are fine"),
        ("Is it the page or the URL?", "The URL: /?a=1, /? and HEAD /", "all work through Cloudflare", "only the key / is affected"),
        ("Does Cloudflare's GET / arrive?", "Yes: a tagged request got 200", "from the pod in 3 ms", "the answer stops at Cloudflare"),
    ]
    y0, rh, gap = 50, 70, 16
    for i, (q, a1, a2, so) in enumerate(rows):
        y = y0 + i * (rh + gap)
        d.node(f"q{i}", "client", 20, y, 290, rh, f"{i + 1}. {q}")
        d.node(f"a{i}", "security", 340, y, 320, rh, a1, a2, align="left")
        d.node(f"s{i}", "service", 700, y, 240, rh, "So:", so, align="left")
        d.edge(f"q{i}", f"a{i}", exit=(1, 0.5), entry=(0, 0.5), kind="leads")
        d.edge(f"a{i}", f"s{i}", exit=(1, 0.5), entry=(0, 0.5), kind="leads")
        if i:
            d.edge(f"q{i - 1}", f"q{i}", exit=(0.5, 1), entry=(0.5, 0), kind="next")
    y = y0 + len(rows) * (rh + gap) + 6
    d.node("cause", "network", 20, y, 430, 70, "Cloudflare's entry for https://jithendar.com/", "is broken; the origin is not")
    d.node("fix", "ops", 500, y, 440, 70, "Purge that URL (Admin → Cache)", "09:07:21: GET / answers 200, then HIT")
    d.edge(f"q{len(rows) - 1}", "cause", exit=(0.5, 1), entry=(0.2, 0), kind="next")
    d.edge("cause", "fix", exit=(1, 0.5), entry=(0, 0.5), kind="leads")
    d.marker(1, 438, y + 12)
    d.legend(y + 100, failure=True, labels={"client": "Question", "security": "Command and result", "service": "Conclusion",
                                             "network": "Cause", "ops": "Fix"})
    return d


def followups():
    d = Diagram("home-page-520-followups", 960, 600, "What let a deploy break one URL for half an hour, and the follow-ups")
    d.zone("z-l", "What let it happen", 20, 50, 440, 470, "risk")
    d.zone("z-r", "Follow-up (all open)", 500, 50, 440, 470, "plain")
    rows = [
        (("Three rollouts in nine minutes", "two merges 70 s apart; the image came", "6 min after the config change"),
         ("Deploy once per change set", "merge the site config after the image is", "pushed, or let the deploy wait for it")),
        (("Probes fail during warm-up", "52 to 54 s rendering 91 pages; startup,", "liveness and readiness time out"),
         ("Keep warm-up off the probe path", "a startup probe that allows the warm-up;", "ready only when warm-up has finished")),
        (("The smoke test skips Cloudflare", "port-forward to one pod: it passed at", "08:22:43 and 08:30:53"),
         ("Smoke-test through Cloudflare", "GET / and a few key URLs on the public", "host after every deploy")),
        (("Nothing watches the public URL", "I found it by opening the site;", "the start time is still unknown"),
         ("An outside check with an alert", "probe / and /blog through Cloudflare;", "alert on 5xx or no answer")),
        (("Cloudflare caches HTML by URL", "one bad entry breaks that URL for", "everyone; deploys never purge"),
         ("Purge Cloudflare after a deploy", "the site has the token and the purge", "code; call it when a rollout ends")),
    ]
    y0, rh, gap = 80, 74, 12
    for i, (left, right) in enumerate(rows):
        y = y0 + i * (rh + gap)
        d.node(f"f{i}", "security", 35, y, 410, rh, *left, align="left")
        d.node(f"a{i}", "ops", 515, y, 410, rh, *right, align="left")
        d.edge(f"f{i}", f"a{i}", exit=(1, 0.5), entry=(0, 0.5), kind="fixes")
    d.legend(540, labels={"security": "Contributing factor", "ops": "Follow-up"})
    return d


def main():
    for build in (path, timeline, narrowing, followups):
        d = build()
        (HERE / f"{d.name}.drawio").write_text(d.xml() + "\n")
        print(f"wrote {d.name}.drawio ({d.w}x{d.h})")


if __name__ == "__main__":
    main()
