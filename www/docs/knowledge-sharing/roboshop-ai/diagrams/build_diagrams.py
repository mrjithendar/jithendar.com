#!/usr/bin/env python3
"""Build the RoboShop AI series diagrams (standard library only).

    python3 docs/knowledge-sharing/roboshop-ai/diagrams/build_diagrams.py   (from www/)

One layout model produces both outputs, so they cannot drift apart:

  docs/knowledge-sharing/roboshop-ai/diagrams/<name>.drawio   editable, multi-page draw.io files
  public/images/roboshop-ai-series/<figure>.svg               rendered here, for the articles

The SVGs are NOT draw.io exports: this script renders them from the model. If a .drawio file is
edited by hand in draw.io, re-export that page from draw.io over the matching SVG.
PNGs are screenshots of those SVGs; see render_png.sh beside this file.

Every label is checked against its box, and every edge against known cell ids. The build fails
rather than writing a diagram with text that does not fit.
"""
import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[3] / "public" / "images" / "roboshop-ai-series"
FONT = "Inter, 'Segoe UI', system-ui, -apple-system, Helvetica, Arial, sans-serif"
TITLE_SIZE, LINE_SIZE, EDGE_SIZE = 14, 12, 12

KINDS = {  # fill, stroke, title colour
    "browser": ("#f8fafc", "#334155", "#0f172a"),
    "edge": ("#eef2ff", "#4338ca", "#1e1b4b"),
    "gateway": ("#eff6ff", "#1d4ed8", "#1e3a8a"),
    "agent": ("#f5f3ff", "#6d28d9", "#2e1065"),
    "mcp": ("#f0fdfa", "#0f766e", "#134e4a"),
    "service": ("#ecfdf5", "#047857", "#064e3b"),
    "model": ("#fdf2f8", "#be185d", "#500724"),
    "store": ("#fffbeb", "#b45309", "#451a03"),
    "bus": ("#fff1f2", "#be123c", "#4c0519"),
    "external": ("#f1f5f9", "#64748b", "#0f172a"),
    "reject": ("#fef2f2", "#b91c1c", "#7f1d1d"),
    "absent": ("#ffffff", "#94a3b8", "#475569"),
}
ARROWS = {  # stroke, width, dash
    "sync": ("#475569", 1.6, None),
    "write": ("#b45309", 2.2, None),
    "async": ("#be123c", 2.2, None),
    "reject": ("#b91c1c", 1.4, "5 4"),
    "dashed": ("#64748b", 1.4, "6 4"),
    "life": ("#cbd5e1", 1.2, "4 4"),
}


def text_width(text, size, bold=False):
    return len(text) * size * (0.56 if bold else 0.52)


class Page:
    def __init__(self, figure, name, width, height, title, desc):
        self.figure, self.name, self.w, self.h, self.title, self.desc = figure, name, width, height, title, desc
        self.zones, self.nodes, self.edges, self.notes = [], {}, [], []

    def zone(self, label, x, y, w, h, corner="tl"):
        self.zones.append(dict(id=f"z{len(self.zones)}", label=label, x=x, y=y, w=w, h=h, corner=corner))

    def node(self, id, kind, x, y, w, h, title, *lines):
        for line in (title, *lines):
            bold = line == title
            size = TITLE_SIZE if bold else LINE_SIZE
            if text_width(line, size, bold) > w - 8:
                raise SystemExit(f"{self.figure}/{id}: '{line}' is too wide for a {w}px box")
        if (len(lines) + 1) * 17 + 6 > h:
            raise SystemExit(f"{self.figure}/{id}: too many lines for a {h}px box")
        self.nodes[id] = dict(id=id, kind=kind, x=x, y=y, w=w, h=h, title=title, lines=lines)

    def note(self, x, y, text, size=12, color="#475569", bold=False):
        self.notes.append(dict(id=f"t{len(self.notes)}", x=x, y=y, text=text, size=size, color=color, bold=bold))

    def port(self, id, side, at=0.5):
        n = self.nodes[id]
        return {"t": (n["x"] + n["w"] * at, n["y"]), "b": (n["x"] + n["w"] * at, n["y"] + n["h"]),
                "l": (n["x"], n["y"] + n["h"] * at), "r": (n["x"] + n["w"], n["y"] + n["h"] * at)}[side]

    def edge(self, a, b, kind="sync", label="", a_side="b", b_side="t", a_at=0.5, b_at=0.5, via=(), dx=0, dy=0, t=0.0, both=False):
        """Connect two nodes. t is draw.io's relative label position (-1 start, 0 middle, 1 end)."""
        points = [self.port(a, a_side, a_at), *via, self.port(b, b_side, b_at)]
        self.edges.append(dict(id=f"e{len(self.edges)}", a=a, b=b, kind=kind, label=label, a_side=a_side, b_side=b_side,
                               a_at=a_at, b_at=b_at, via=via, points=points, dx=dx, dy=dy, t=t, both=both))


def anchor(side, at):
    return {"t": (at, 0), "b": (at, 1), "l": (0, at), "r": (1, at)}[side]


def label_point(points, t):
    lengths = [abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(points, points[1:])]
    remaining = sum(lengths) * (t + 1) / 2
    for (a, b), length in zip(zip(points, points[1:]), lengths):
        if remaining <= length and length:
            f = remaining / length
            return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
        remaining -= length
    return points[-1]


def drawio_style(parts):
    return ";".join(f"{k}={v}" for k, v in parts.items()) + ";"


def page_xml(page, index):
    diagram = ET.Element("diagram", id=f"{page.figure}-{index}", name=page.name)
    model = ET.SubElement(diagram, "mxGraphModel", dx="800", dy="800", grid="0", gridSize="10", guides="1", tooltips="1", connect="1",
                          arrows="1", fold="1", page="1", pageScale="1", pageWidth=str(page.w), pageHeight=str(page.h),
                          background="#ffffff", math="0", shadow="0")
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")

    def geometry(cell, x, y, w, h):
        ET.SubElement(cell, "mxGeometry", {"x": str(x), "y": str(y), "width": str(w), "height": str(h), "as": "geometry"})

    for zone in page.zones:
        style = dict(rounded=1, arcSize=2, dashed=1, dashPattern="6 4", fillColor="none", strokeColor="#94a3b8", align="left" if zone["corner"] == "tl" else "right",
                     verticalAlign="top" if zone["corner"] == "tl" else "bottom", spacingLeft=8, spacingRight=8, spacingTop=4, spacingBottom=4, fontFamily="Helvetica", fontSize=LINE_SIZE, fontColor="#475569",
                     fontStyle=1, whiteSpace="wrap", html=0)
        geometry(ET.SubElement(root, "mxCell", id=zone["id"], value=zone["label"], style=drawio_style(style), vertex="1", parent="1"),
                 zone["x"], zone["y"], zone["w"], zone["h"])
    for n in page.nodes.values():
        fill, stroke, colour = KINDS[n["kind"]]
        if n.get("life"):
            fill, stroke = "#cbd5e1", "#cbd5e1"
        style = dict(rounded=1, arcSize=8, whiteSpace="wrap", html=0, fillColor=fill, strokeColor=stroke, fontColor=colour,
                     fontFamily="Helvetica", fontSize=LINE_SIZE, align="center", verticalAlign="middle")
        if n["kind"] == "absent":
            style["dashed"] = 1
        geometry(ET.SubElement(root, "mxCell", id=n["id"], value="\n".join((n["title"], *n["lines"])), style=drawio_style(style),
                               vertex="1", parent="1"), n["x"], n["y"], n["w"], n["h"])
    for note in page.notes:
        style = dict(text=1, html=0, align="left", verticalAlign="top", resizable=1, fontFamily="Helvetica", fontSize=note["size"],
                     fontColor=note["color"], fontStyle=1 if note["bold"] else 0, whiteSpace="nowrap")
        lines = note["text"].split("\n")
        geometry(ET.SubElement(root, "mxCell", id=note["id"], value=note["text"], style=drawio_style(style), vertex="1", parent="1"),
                 note["x"], note["y"], max(len(line) for line in lines) * note["size"] * 0.56, len(lines) * (note["size"] + 5))
    for e in page.edges:
        stroke, width, dash = ARROWS[e["kind"]]
        ex, ey = anchor(e["a_side"], e["a_at"])
        nx, ny = anchor(e["b_side"], e["b_at"])
        style = dict(edgeStyle="none", rounded=0, html=0, strokeColor=stroke, strokeWidth=width, fontFamily="Helvetica", fontSize=EDGE_SIZE,
                     fontColor="#0f172a", labelBackgroundColor="#ffffff", endArrow="none" if e["kind"] == "life" else "block",
                     endFill=1, exitX=ex, exitY=ey, exitDx=0, exitDy=0, entryX=nx, entryY=ny, entryDx=0, entryDy=0)
        if e["both"]:
            style.update(startArrow="block", startFill=1)
        if dash:
            style.update(dashed=1, dashPattern=dash)
        cell = ET.SubElement(root, "mxCell", id=e["id"], value=e["label"], style=drawio_style(style), edge="1", parent="1", source=e["a"], target=e["b"])
        geo = ET.SubElement(cell, "mxGeometry", {"x": str(e["t"]), "y": "0", "relative": "1", "as": "geometry"})
        if e["dx"] or e["dy"]:
            ET.SubElement(geo, "mxPoint", {"x": str(e["dx"]), "y": str(e["dy"]), "as": "offset"})
        if e["via"]:
            points = ET.SubElement(geo, "Array", {"as": "points"})
            for x, y in e["via"]:
                ET.SubElement(points, "mxPoint", x=str(x), y=str(y))
    return diagram


def page_svg(page):
    uid = page.figure
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {page.w} {page.h}" width="{page.w}" height="{page.h}" role="img" '
           f'aria-labelledby="{uid}-title {uid}-desc" font-family="{FONT}">',
           f'<title id="{uid}-title">{escape(page.title)}</title>', f'<desc id="{uid}-desc">{escape(page.desc)}</desc>',
           f'<rect width="{page.w}" height="{page.h}" fill="#ffffff"/>', "<defs>"]
    for kind, (stroke, _, _) in ARROWS.items():
        out.append(f'<marker id="{uid}-{kind}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                   f'<path d="M0 0L10 5L0 10z" fill="{stroke}"/></marker>')
    out.append("</defs>")
    for z in page.zones:
        out.append(f'<rect x="{z["x"]}" y="{z["y"]}" width="{z["w"]}" height="{z["h"]}" rx="8" fill="none" stroke="#94a3b8" stroke-dasharray="6 4"/>')
        tl = z["corner"] == "tl"
        tx, ty, ta = (z["x"] + 8, z["y"] + 16, "start") if tl else (z["x"] + z["w"] - 8, z["y"] + z["h"] - 7, "end")
        out.append(f'<text x="{tx}" y="{ty}" text-anchor="{ta}" font-size="{LINE_SIZE}" font-weight="600" fill="#475569">{escape(z["label"])}</text>')
    for n in page.nodes.values():
        if n.get("life"):
            x = n["x"] + 0.5
            out.append(f'<line x1="{x}" y1="{n["y"]}" x2="{x}" y2="{n["y"] + n["h"]}" stroke="#cbd5e1" stroke-width="1.2" stroke-dasharray="4 4"/>')
    for e in page.edges:
        stroke, width, dash = ARROWS[e["kind"]]
        points = " ".join(f"{x},{y}" for x, y in e["points"])
        marker = "" if e["kind"] == "life" else f' marker-end="url(#{uid}-{e["kind"]})"'
        start = f' marker-start="url(#{uid}-{e["kind"]})"' if e["both"] else ""
        dashes = f' stroke-dasharray="{dash}"' if dash else ""
        out.append(f'<polyline points="{points}" fill="none" stroke="{stroke}" stroke-width="{width}"{dashes}{marker}{start}/>')
    for n in page.nodes.values():
        if n.get("life"):
            continue
        fill, stroke, colour = KINDS[n["kind"]]
        dashes = ' stroke-dasharray="6 4"' if n["kind"] == "absent" else ""
        out.append(f'<rect x="{n["x"]}" y="{n["y"]}" width="{n["w"]}" height="{n["h"]}" rx="7" fill="{fill}" stroke="{stroke}" stroke-width="1.4"{dashes}/>')
        rows = [(n["title"], TITLE_SIZE, 600, colour)] + [(line, LINE_SIZE, 400, "#334155") for line in n["lines"]]
        total = sum(size + 4 for _, size, _, _ in rows) - 4
        y = n["y"] + (n["h"] - total) / 2
        for line, size, weight, fill_text in rows:
            y += size
            out.append(f'<text x="{n["x"] + n["w"] / 2}" y="{y:.1f}" text-anchor="middle" font-size="{size}" font-weight="{weight}" fill="{fill_text}">{escape(line)}</text>')
            y += 4
    for e in page.edges:
        if not e["label"]:
            continue
        x, y = label_point(e["points"], e["t"])
        x, y = x + e["dx"], y + e["dy"]
        lines = e["label"].split("\n")
        width = max(text_width(line, EDGE_SIZE) for line in lines) + 8
        height = len(lines) * 15 + 2
        out.append(f'<rect x="{x - width / 2:.1f}" y="{y - height / 2:.1f}" width="{width:.1f}" height="{height}" fill="#ffffff" opacity="0.92"/>')
        for i, line in enumerate(lines):
            out.append(f'<text x="{x:.1f}" y="{y - height / 2 + 12 + i * 15:.1f}" text-anchor="middle" font-size="{EDGE_SIZE}" fill="#0f172a">{escape(line)}</text>')
    for note in page.notes:
        for i, line in enumerate(note["text"].split("\n")):
            weight = ' font-weight="600"' if note["bold"] else ""
            out.append(f'<text x="{note["x"]}" y="{note["y"] + note["size"] + i * (note["size"] + 5)}" font-size="{note["size"]}"{weight} fill="{note["color"]}">{escape(line)}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


# Layout ---------------------------------------------------------------------------------------

def logical():
    p = Page("roboshop-ai-architecture-logical", "Logical architecture", 620, 800, "RoboShop AI logical architecture",
             "A browser uses web, which proxies API calls to ai-gateway and assistant calls to moks. moks and ai-gateway call each other over "
             "private routes; moks reads catalogue-service and calls Amazon Bedrock or Ollama. An optional MCP client reaches the private mcp-server, "
             "which forwards the caller's session to ai-gateway. ai-gateway calls user, catalogue, cart, payment and shipping services and owns the "
             "order ledger. Paid orders flow through RabbitMQ to shipping-service and kafka-bridge, then Kafka.")
    p.zone("Outside the cluster", 15, 12, 590, 96)
    p.zone("Namespace roboshop-ai: application tier", 15, 120, 590, 262)
    p.zone("Domain services", 15, 394, 590, 150)
    p.zone("Data and messaging", 15, 556, 590, 232)
    p.node("browser", "browser", 30, 36, 170, 60, "Browser", "storefront, Moks widget")
    p.node("models", "model", 225, 36, 170, 60, "Model provider", "Bedrock or Ollama")
    p.node("client", "external", 420, 36, 170, 60, "MCP client", "not in the cluster today")
    p.node("web", "edge", 30, 150, 170, 62, "web", "NGINX, static storefront")
    p.node("moks", "agent", 225, 150, 170, 62, "moks", "widget + LangGraph")
    p.node("mcp", "mcp", 420, 150, 170, 62, "mcp-server", "FastMCP, private")
    p.node("gateway", "gateway", 30, 300, 520, 66, "ai-gateway", "public API, authorization, LLM settings, chat history, order ledger")
    p.node("user", "service", 30, 418, 170, 52, "user-service", "accounts, sessions")
    p.node("cart", "service", 225, 418, 170, 52, "cart-service", "carts")
    p.node("catalogue", "service", 420, 418, 170, 52, "catalogue-service", "products, ranking")
    p.node("payment", "service", 30, 482, 170, 52, "payment-service", "Razorpay orders")
    p.node("shipping", "service", 225, 482, 170, 52, "shipping-service", "quotes, shipments")
    p.node("currency", "service", 420, 482, 170, 52, "currency-service", "ECB reference rates")
    p.node("mongo", "store", 30, 582, 170, 52, "MongoDB", "products, users, chats")
    p.node("redis", "store", 225, 582, 170, 52, "Redis", "cart contents")
    p.node("postgres", "store", 420, 582, 170, 52, "PostgreSQL", "shipping data")
    p.node("ledger", "store", 30, 648, 170, 52, "Order ledger", "JSON on a volume")
    p.node("rabbit", "bus", 225, 648, 170, 52, "RabbitMQ", "roboshop.orders")
    p.node("bridge", "service", 420, 648, 170, 52, "kafka-bridge", "analytics copy")
    p.node("kafka", "bus", 420, 722, 170, 52, "Kafka", "order topics")
    p.edge("browser", "web", label="HTTPS", dy=-14)
    p.edge("web", "moks", a_side="r", b_side="l", label="/moks/*", dy=-11)
    p.edge("web", "gateway", label="/api/*", b_at=0.163, dx=-22)
    p.edge("moks", "models", a_side="t", b_side="b", label="Converse\nor /api/chat")
    p.edge("moks", "gateway", kind="sync", label="/api/chat\n/internal/llm/config", a_at=0.3, b_at=0.473, dx=-58)
    p.edge("gateway", "moks", kind="sync", a_side="t", b_side="b", a_at=0.604, b_at=0.7, label="/internal/chat", dx=46)
    p.edge("client", "mcp", kind="dashed", label="POST /mcp")
    p.edge("mcp", "gateway", label="caller's session", b_at=0.881, a_at=0.4, dx=0, dy=26)
    p.edge("moks", "catalogue", kind="dashed", a_side="b", b_side="t", a_at=0.92, b_at=0.9, via=[(382, 232), (573, 232), (573, 400)], label="GET /api/products", t=-0.3, dx=36, dy=10)
    p.edge("gateway", "user", a_at=0.244, b_at=0.75)
    p.edge("gateway", "cart", a_at=0.538, b_at=0.5, label="HTTP to each service", dx=72, dy=-8)
    p.edge("ledger", "rabbit", a_side="r", b_side="l", kind="async", label="outbox", dy=-11)
    p.edge("rabbit", "bridge", a_side="r", b_side="l", kind="async", label="queue", dy=-11)
    p.edge("rabbit", "shipping", a_side="t", b_side="b", kind="async", via=[(310, 642), (408, 642), (408, 540), (310, 540)])
    p.edge("bridge", "kafka", kind="async")
    p.note(30, 722, "Solid: request path\nDashed: read or private path\nRed: asynchronous event", 12)
    p.note(225, 722, "Each store has one owner.\nThe article lists who\nowns which.", 12)
    return p


def deployment():
    p = Page("roboshop-ai-architecture-deployment", "Deployment on EKS", 620, 804, "RoboShop AI deployment on Amazon EKS",
             "Argo CD on the mk4 cluster syncs manifests from Git to the roboshop-demo EKS cluster and images come from ECR. Internet traffic passes "
             "a Network Load Balancer to the Istio ingress gateway, which ends TLS, strips /roboshop and routes to web. In roboshop-ai every pod has a "
             "sidecar, with PERMISSIVE mTLS and authorization policies in dry-run. mcp-server is running with no public route. The moks Deployment "
             "was not present on 1 November 2026. OpenTelemetry export is disabled and Prometheus and Kiali run for mesh metrics.")
    p.zone("Outside the cluster", 15, 12, 590, 92)
    p.zone("AWS: EKS cluster roboshop-demo", 15, 116, 590, 676)
    p.zone("Namespace istio-ingress", 30, 232, 560, 84)
    p.zone("Namespace roboshop-ai: every pod has an Envoy sidecar", 30, 328, 560, 352, "br")
    p.node("git", "external", 30, 36, 170, 56, "GitHub + ECR", "manifests, images")
    p.node("argo", "edge", 225, 36, 170, 56, "Argo CD on mk4", "manual sync, no prune")
    p.node("user", "browser", 420, 36, 170, 56, "Browser", "eks.jithendar.com")
    p.node("nlb", "edge", 420, 150, 170, 62, "NLB", "Network Load Balancer")
    p.node("istio", "edge", 180, 256, 410, 50, "Istio ingress gateway", "ends TLS, strips /roboshop")
    p.node("web", "edge", 45, 352, 170, 60, "web", "1 replica")
    p.node("gateway", "gateway", 225, 352, 170, 60, "ai-gateway", "1 replica, Recreate")
    p.node("moks", "absent", 405, 352, 170, 60, "moks", "no Deployment on 1 Nov")
    p.node("services", "service", 45, 426, 350, 60, "user, catalogue, cart, payment,", "shipping, currency: 1 replica each")
    p.node("mcp", "mcp", 405, 426, 170, 60, "mcp-server", "ClusterIP, no route")
    p.node("stores", "store", 45, 500, 530, 60, "StatefulSets: mongodb, rabbitmq, kafka", "Deployments: redis, shipping-db (PostgreSQL)")
    p.node("mesh", "external", 45, 574, 530, 78, "Mesh policy", "PeerAuthentication: PERMISSIVE", "AuthorizationPolicies present with istio.io/dry-run: true")
    p.node("obs", "external", 30, 694, 270, 84, "Metrics", "prometheus-agent, Kiali", "/metrics on each service")
    p.node("otel", "absent", 320, 694, 270, 84, "Traces", "OTEL_SDK_DISABLED=true", "no collector on this cluster")
    p.edge("git", "argo", a_side="r", b_side="l", label="sync", dy=-11)
    p.edge("user", "nlb", label="HTTPS 443")
    p.edge("nlb", "istio", label="TCP", b_at=0.8)
    p.edge("istio", "web", a_side="b", b_side="t", a_at=0.049, b_at=0.912)
    p.edge("web", "gateway", a_side="r", b_side="l")
    p.edge("web", "moks", kind="dashed", a_side="t", b_side="t", a_at=0.3, via=[(96, 338), (490, 338)], label="502 until deployed", t=0.1, dy=-8)
    p.edge("gateway", "services", b_at=0.757)
    p.edge("mcp", "gateway", a_side="t", b_side="b", kind="dashed", a_at=0.05, b_at=0.95, via=[(413.5, 419), (386.5, 419)])
    p.edge("argo", "istio", kind="dashed", a_at=0.5, b_at=0.2805, a_side="b", b_side="t", label="syncs every app")
    return p


def lifelines(page, names, top, bottom, x0=30, gap=None, w=None):
    gap = gap or (page.w - 2 * x0 - (w or 130)) / (len(names) - 1)
    w = w or 130
    for i, (id, kind, title, sub) in enumerate(names):
        x = x0 + gap * i
        lines = (sub,) if sub else ()
        page.node(id, kind, round(x), top, w, 50, title, *lines)
    return {id: round(x0 + gap * i + w / 2) for i, (id, _, _, _) in enumerate(names)}


class Sequence:
    """Lifelines as thin cells so draw.io edges stay attached when a message is moved."""
    def __init__(self, page, names, top=16, bottom=None, w=130):
        self.page = page
        self.x = lifelines(page, names, top, bottom, w=w)
        self.y0 = top + 50
        self.bottom = bottom or page.h - 16
        self.count = 0
        self.ids = names
        for id, _, _, _ in names:
            x = self.x[id]
            page.nodes[id + "-life"] = dict(id=id + "-life", kind="absent", life=True, x=x - 0.5, y=self.y0, w=1, h=self.bottom - self.y0, title="", lines=())

    def message(self, y, a, b, label, kind="sync", number=True):
        if number:
            self.count += 1
            label = f"{self.count}. {label}"
        p = self.page
        ids = f"{a}-life", f"{b}-life"
        ya = (y - self.y0) / (self.bottom - self.y0)
        right = self.x[b] > self.x[a]
        lines = label.split("\n")
        width = max(text_width(line, EDGE_SIZE) for line in lines) + 8
        mid = (self.x[a] + self.x[b]) / 2
        dx = 0
        if mid - width / 2 < 6:
            dx = 6 - (mid - width / 2)
        if mid + width / 2 > p.w - 6:
            dx = p.w - 6 - (mid + width / 2)
        p.edge(ids[0], ids[1], kind=kind, label=label, a_side="r" if right else "l", b_side="l" if right else "r", a_at=ya, b_at=ya,
               dx=dx, dy=-5 - 8 * len(lines))

    def self_note(self, y, a, label, h=44, w=196, kind="gateway"):
        id = f"note{len(self.page.nodes)}"
        lines = label.split("\n")
        x = self.x[a] - w / 2
        x = max(8, min(x, self.page.w - w - 8))
        self.page.node(id, kind, round(x), y, w, h, lines[0], *lines[1:])


def seq_browse():
    p = Page("roboshop-sequence-browse-cart", "Browse and cart", 620, 560, "Traditional shopping request: browse and add to cart",
             "The browser requests products through web. ai-gateway reads catalogue-service, overlays live stock from its ledger and returns the list. "
             "Adding to the cart posts the SKU and quantity; ai-gateway checks the session, stock and pending payments, then writes to cart-service, "
             "which stores the cart in Redis, and commits the revision in its ledger.")
    s = Sequence(p, [("b", "browser", "Browser", ""), ("w", "edge", "web", "NGINX"), ("g", "gateway", "ai-gateway", ""), ("d", "service", "services", "")], bottom=540)
    s.message(96, "b", "w", "GET /api/products")
    s.message(128, "w", "g", "proxy, 35 s read limit")
    s.message(160, "g", "d", "catalogue-service\nGET /api/products")
    s.message(204, "d", "g", "products", kind="dashed")
    s.self_note(214, "g", "Overlay live stock\nreservations, sales", 46, 180)
    s.message(292, "g", "b", "products with instock", kind="dashed")
    s.message(340, "b", "g", "POST /api/cart {sku, quantity}", kind="write")
    s.self_note(350, "g", "Authorize and check\nstock, pending payment", 46, 180)
    s.message(444, "g", "d", "cart-service\nreplace(revision)", kind="write")
    s.message(476, "d", "g", "new revision, Redis Lua", kind="dashed")
    s.message(520, "g", "b", "cart: gateway-computed totals", kind="dashed")
    return p


def seq_checkout():
    p = Page("roboshop-sequence-checkout", "Checkout to order", 620, 640, "Checkout, payment and order events",
             "The signed-in browser posts an order with an idempotency key. ai-gateway reserves stock in its ledger, then asks payment-service to create a "
             "Razorpay order and returns public checkout options. After payment the browser sends the signature for verification; payment-service verifies "
             "it and fetches the capture. ai-gateway marks the order paid and its outbox publishes to RabbitMQ for shipping-service and kafka-bridge. A signed "
             "webhook gives Razorpay a separate route to the same result.")
    s = Sequence(p, [("b", "browser", "Browser", "signed in"), ("g", "gateway", "ai-gateway", "ledger"), ("p", "service", "payment-service", ""), ("r", "external", "Razorpay", "")], bottom=500)
    s.message(112, "b", "g", "POST /api/payments/orders\nIdempotency-Key", kind="write")
    s.self_note(120, "g", "reserve_payment\nstate: creating", 46, 170)
    s.message(190, "g", "p", "orders: amount from server", kind="write")
    s.message(224, "p", "r", "create order", kind="write")
    s.message(262, "p", "g", "provider order ID", kind="dashed")
    s.message(304, "g", "b", "state: payment_pending\npublic checkout options", kind="dashed")
    s.message(346, "b", "r", "hosted Razorpay Checkout")
    s.message(384, "b", "g", "POST /api/payments/verify", kind="write")
    s.message(420, "g", "p", "verify signature, fetch capture")
    s.message(452, "r", "g", "signed webhook, alternative route", kind="dashed")
    s.self_note(462, "g", "mark_paid\npaid, outbox event", 46, 180)
    p.zone("After the response: at-least-once delivery", 15, 524, 590, 104)
    p.node("rabbit", "bus", 30, 552, 170, 60, "RabbitMQ", "roboshop.orders")
    p.node("ship", "service", 225, 552, 170, 60, "shipping-service", "PostgreSQL request")
    p.node("bridge", "service", 420, 552, 170, 60, "kafka-bridge", "then Kafka")
    p.edge("rabbit", "ship", kind="async", a_side="r", b_side="l", label="order.paid", dy=-11)
    p.edge("rabbit", "bridge", kind="async", a_side="b", b_side="b", via=[(115, 622), (505, 622)], label="roboshop.kafka.orders", dy=-1)
    return p


def seq_chat():
    p = Page("roboshop-sequence-assistant", "AI-assisted request", 620, 620, "AI-assisted shopping request",
             "The widget posts a message to moks through web. moks checks the Origin and session, then calls ai-gateway /api/chat with a service token and the "
             "user's session. ai-gateway loads saved history, the active LLM configuration and unavailable SKUs, then calls moks /internal/chat. moks reads the "
             "catalogue, retrieves evidence, confirms the configuration revision and calls the provider. ai-gateway reapplies stock and saves the turn.")
    s = Sequence(p, [("b", "browser", "Widget", "browser"), ("m", "agent", "moks", ""), ("g", "gateway", "ai-gateway", ""), ("x", "service", "catalogue", "/ provider")], bottom=600)
    s.message(96, "b", "m", "POST /moks/chat {message}")
    s.message(128, "m", "g", "GET /api/auth/me")
    s.message(166, "m", "g", "POST /api/chat\nservice token + rs_auth")
    s.self_note(182, "g", "Role and 10/min limit\nhistory, LLM snapshot", 46, 176)
    s.message(258, "g", "x", "GET catalogue, 2 s")
    s.self_note(268, "g", "Unavailable SKUs\nfrom the ledger", 46, 176)
    s.message(348, "g", "m", "POST /internal/chat, 18 s")
    s.message(382, "m", "x", "GET /api/products")
    s.self_note(392, "m", "Retrieve 4 at most\nbuild evidence", 46, 196, "agent")
    s.message(470, "m", "g", "GET /internal/llm/config")
    s.message(502, "m", "x", "Converse or Ollama /api/chat")
    s.message(534, "m", "g", "answer, cards, usage", kind="dashed")
    s.message(566, "g", "b", "stock re-applied, turn saved: JSON, no stream", kind="dashed")
    return p


def gateway_flow():
    p = Page("ai-gateway-request-flow", "POST /api/chat", 620, 836, "AI gateway internal request flow for POST /api/chat",
             "Ten numbered steps run from web through the Moks widget adapter into ai-gateway: transport limits, general rate limit and origin checks, session "
             "lookup, service token and role check, chat rate limit and schema, history and provider snapshot, catalogue and stock, two admission slots, "
             "the call to the moks engine, then stock re-application and saving the turn. Each step shows the response it returns when it refuses the request.")
    p.zone("Moks widget adapter (browser-facing)", 15, 12, 590, 96)
    p.zone("ai-gateway process (asgi_app.py, then server.py)", 15, 120, 590, 704)
    rows = [
        ("s1", "1. Widget checks", "Origin, 30/min, session, 8 KiB, 4 slots", "403, 429, 401, 413", 36, "agent"),
        ("s2", "2. dispatch: transport", "64 KiB, 10 s body, 8 workers, 23 s", "413, 408, 503", 146, "gateway"),
        ("s3", "3. route: shared guards", "300/min per address, Origin", "429, 403", 214, "gateway"),
        ("s4", "4. Session lookup", "user-service /internal/session", "503\nfails closed", 282, "gateway"),
        ("s5", "5. /api/chat authorization", "service token, then require_role", "403, 401", 350, "gateway"),
        ("s6", "6. Limit and contract", "10/min per address, ChatRequest", "429, 400", 418, "gateway"),
        ("s7", "7. History and LLM snapshot", "chat_history, llm_configuration", "200\nnot-configured", 486, "gateway"),
        ("s8", "8. Catalogue and stock", "2 s read, unavailableSkus", "503", 554, "gateway"),
        ("s9", "9. Admission", "2 chat slots", "429\nassistant-busy", 622, "gateway"),
        ("s10", "10. Call moks /internal/chat", "payload under 16 KiB, 18 s, no retry", "503\nfeature-unavailable", 690, "agent"),
    ]
    for id, title, line, reject, y, kind in rows:
        p.node(id, kind, 30, y, 350, 56, title, line)
        p.node(id + "x", "reject", 440, y + 8, 150, 40, *reject.split("\n"))
        p.edge(id, id + "x", kind="reject", a_side="r", b_side="l")
    p.node("s11", "gateway", 30, 758, 560, 54, "11. Re-apply live stock, save the turn", "validate ChatResponse, return buffered JSON")
    for a, b in zip([r[0] for r in rows], [r[0] for r in rows[1:]] + ["s11"]):
        first = a == "s1"
        p.edge(a, b, a_at=0.9 if first else 0.5, b_at=0.9 if first else 0.5 if b != "s11" else 0.3125)
    return p


def mcp_roles():
    p = Page("mcp-host-client-server", "Roles and trust", 620, 690, "MCP host, client and server in RoboShop AI",
             "The host and its MCP client run outside the application, for example a desktop assistant or the demo script. They reach mcp-server over stdio locally or "
             "Streamable HTTP through a port-forward, using the user's own RoboShop session. mcp-server holds no business data and calls ai-gateway with that session. "
             "Moks is on a separate path: the widget calls moks and moks calls ai-gateway, with no MCP client.")
    p.zone("Host: treat model output as untrusted", 15, 12, 590, 150)
    p.zone("Private to the cluster or the local machine", 15, 216, 590, 164)
    p.zone("Authorization boundary", 15, 430, 590, 134)
    p.node("host", "external", 30, 40, 270, 106, "MCP host", "AI client, IDE or script", "picks tools with its model", "keeps the session token")
    p.node("client", "external", 330, 40, 260, 106, "MCP client", "demo.py uses FastMCP Client", "discovers and calls tools")
    p.node("server", "mcp", 30, 246, 560, 118, "mcp-server (MCP server)", "protocol, discovery, input and output schemas", "Host and Origin guard, rate limits, confirmation of admin writes",
           "no business data, no privileged credential")
    p.node("gateway", "gateway", 30, 456, 270, 92, "ai-gateway", "session, role, Origin", "ownership, stock, revisions")
    p.node("services", "service", 330, 456, 260, 92, "Domain services", "user, catalogue, cart", "shipping")
    p.node("widget", "browser", 30, 602, 150, 62, "Moks widget", "browser")
    p.node("moks", "agent", 235, 602, 150, 62, "moks", "no MCP client")
    p.node("gw2", "gateway", 440, 602, 150, 62, "ai-gateway", "/api/chat")
    p.edge("host", "client", a_side="r", b_side="l", both=True)
    p.edge("client", "server", b_at=0.768, label="stdio, or POST /mcp\nBearer session", dx=0, dy=0, t=0.0)
    p.edge("server", "gateway", a_at=0.45, b_at=0.933, label="HTTP, cookie: rs_auth=caller", dx=0, dy=-10)
    p.edge("gateway", "services", a_side="r", b_side="l")
    p.edge("widget", "moks", a_side="r", b_side="l")
    p.edge("moks", "gw2", a_side="r", b_side="l", both=True)
    p.note(30, 576, "Separate path: the shopping assistant", 12, "#475569", True)
    return p


def mcp_sequence():
    p = Page("mcp-tool-invocation-sequence", "Tool call", 620, 640, "MCP tool invocation sequence for update_cart",
             "An MCP client sends tools/call with a bearer session. mcp-server applies the Host, Origin and body checks, verifies the session at ai-gateway, runs role "
             "and strict argument checks and admission limits, then calls the gateway with the caller's session in a cookie. ai-gateway authorizes the request again "
             "and writes through cart-service. The result is shaped and validated against the output schema before it returns.")
    s = Sequence(p, [("c", "external", "MCP client", ""), ("m", "mcp", "mcp-server", ""), ("g", "gateway", "ai-gateway", ""), ("d", "service", "cart-service", "Redis")], bottom=590)
    s.message(96, "c", "m", "tools/call update_cart, Bearer")
    s.self_note(108, "m", "Transport guards\nHost, Origin, 256 KiB", 46, 180, "mcp")
    s.message(186, "m", "g", "GET /api/auth/me, no cache")
    s.message(220, "g", "m", "user id and role", kind="dashed")
    s.self_note(232, "m", "Tool guards\nrole, schema, admission", 46, 180, "mcp")
    s.message(324, "m", "g", "POST /api/cart\ncookie rs_auth, origin", kind="write")
    s.self_note(334, "g", "Session and Origin\nownership, stock, pending", 46, 196)
    s.message(412, "g", "d", "replace(revision)", kind="write")
    s.message(446, "d", "g", "new revision", kind="dashed")
    s.message(480, "g", "m", "cart JSON, up to 1 MiB", kind="dashed")
    s.self_note(490, "m", "Shape the result\nvalidate output schema", 46, 180, "mcp")
    s.message(566, "m", "c", "structured result or isError", kind="dashed")
    p.note(30, 600, "A write is never retried. A read may be retried once, inside the 10 s tool deadline.", 12)
    return p


def agent_flow():
    p = Page("shopping-agent-flow", "Agent decision flow", 620, 880, "Moks shopping agent decision flow, including failure paths",
             "A fixed LangGraph runs search_catalogue, ground_evidence and generate_answer once, with no loop. No provider returns a setup message. search_catalogue may "
             "answer with a clarification without calling a model. generate_answer checks the configuration revision and calls the primary provider. Eligible failures with "
             "failover on make one Bedrock attempt. Failures return provider-unavailable. Valid output keeps only SKUs from the evidence. ai-gateway reapplies stock and saves the turn.")
    p.zone("ai-gateway, before the engine", 15, 12, 590, 88)
    p.zone("LangGraph: fixed path, no loop, no tool choice", 15, 112, 590, 356)
    p.zone("Provider routing (routing.py)", 15, 480, 590, 226)
    p.zone("After generation", 15, 718, 590, 150)
    p.node("snap", "gateway", 30, 36, 340, 52, "Provider configured?", "snapshot and revision from MongoDB")
    p.node("none", "reject", 420, 36, 170, 52, "No: setup message", "no model call")
    p.node("n1", "agent", 30, 140, 340, 70, "search_catalogue", "references, then budget and type rules", "retrieve at most 4 products")
    p.node("intro", "agent", 420, 130, 170, 44, "Introduction", "model, no evidence")
    p.node("clar", "reject", 420, 188, 170, 56, "Clarification", "one question, no model")
    p.node("n2", "agent", 30, 258, 340, 70, "ground_evidence", "bounded JSON: question, history, evidence", "drop whole records if over budget")
    p.node("n3", "agent", 30, 376, 340, 70, "generate_answer", "ChatPromptTemplate, then the router", "deadline checked between stages")
    p.node("nothing", "absent", 420, 268, 170, 66, "Nothing matched", "empty evidence still", "calls the model")
    p.node("guard", "gateway", 30, 506, 340, 54, "Revision still current?", "GET /internal/llm/config, before each attempt")
    p.node("stale", "reject", 420, 508, 170, 50, "No: unavailable", "no paid attempt")
    p.node("prim", "model", 30, 576, 340, 52, "Primary provider", "one attempt, 600 output tokens at most")
    p.node("fall", "model", 420, 576, 170, 52, "One Bedrock attempt", "only if failover is on")
    p.node("fail", "reject", 420, 642, 170, 54, "Failure", "not saved, widget 503")
    p.node("cards", "agent", 30, 744, 340, 52, "select_cards", "keep evidence SKUs, drop and count others")
    p.node("final", "gateway", 30, 808, 560, 48, "ai-gateway re-applies live stock", "saves the turn and returns JSON")
    p.edge("snap", "none", a_side="r", b_side="l", kind="reject")
    p.edge("snap", "n1", a_at=0.9, b_at=0.9)
    p.edge("n1", "intro", a_side="r", b_side="l", a_at=0.25, b_at=0.6, kind="dashed")
    p.edge("n1", "clar", a_side="r", b_side="l", a_at=0.75, b_at=0.5, kind="reject")
    p.edge("n1", "n2")
    p.edge("n2", "nothing", a_side="r", b_side="l", kind="dashed")
    p.edge("n2", "n3")
    p.edge("n3", "guard", a_at=0.7, b_at=0.7)
    p.edge("guard", "stale", a_side="r", b_side="l", kind="reject")
    p.edge("guard", "prim")
    p.edge("prim", "fall", a_side="r", b_side="l", kind="reject", label="eligible", dy=-11)
    p.edge("prim", "fail", kind="reject", a_at=0.9, b_side="l", via=[(336, 669)], label="not eligible", t=0.4, dy=-10)
    p.edge("fall", "fail", kind="reject")
    p.edge("prim", "cards", a_at=0.4, b_at=0.4, label="answer text")
    p.edge("cards", "final", b_at=0.3036)
    return p


FILES = {
    "roboshop-ai-architecture": [logical, deployment],
    "roboshop-shopping-sequence": [seq_browse, seq_chat, seq_checkout],
    "ai-gateway-request-flow": [gateway_flow],
    "mcp-tool-invocation": [mcp_roles, mcp_sequence],
    "shopping-agent-decision-loop": [agent_flow],
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    built = []
    for name, pages in FILES.items():
        mxfile = ET.Element("mxfile", host="app.diagrams.net", agent="build_diagrams.py", version="24.7.17", type="device")
        for index, make in enumerate(pages):
            page = make()
            for e in page.edges:
                for point in e["points"]:
                    if not (0 <= point[0] <= page.w and 0 <= point[1] <= page.h):
                        raise SystemExit(f"{page.figure}: edge {e['id']} leaves the page")
            for n in page.nodes.values():
                if n["x"] < 0 or n["y"] < 0 or n["x"] + n["w"] > page.w or n["y"] + n["h"] > page.h:
                    raise SystemExit(f"{page.figure}: {n['id']} leaves the page")
            mxfile.append(page_xml(page, index))
            (OUT / f"{page.figure}.svg").write_text(page_svg(page), encoding="utf-8")
            built.append((page.figure, page.w, page.h))
        ET.indent(mxfile)
        (HERE / f"{name}.drawio").write_bytes(ET.tostring(mxfile, encoding="utf-8", xml_declaration=False))
    (HERE / "figures.txt").write_text("".join(f"{f} {w} {h}\n" for f, w, h in built), encoding="utf-8")
    print(f"{len(FILES)} .drawio files, {len(built)} pages")


if __name__ == "__main__":
    main()
