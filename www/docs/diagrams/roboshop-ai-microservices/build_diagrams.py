#!/usr/bin/env python3
"""Generate the blog's architecture SVGs (standard library only).

    python3 docs/diagrams/roboshop-ai-microservices/build_diagrams.py   (from www/)

Writes public/images/roboshop-ai/roboshop-ai-*.svg for content/blog/roboshop-ai-microservices.mdx.
The `.mmd` files beside this script are the editable Mermaid equivalents. When a
component or call changes, update both and re-run this script.
"""
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / "public" / "images" / "roboshop-ai"
FONT = "Inter, 'Segoe UI', system-ui, -apple-system, Helvetica, Arial, sans-serif"

KINDS = {  # fill, stroke, title colour
    "client": ("#f8fafc", "#334155", "#0f172a"),
    "edge": ("#eef2ff", "#4338ca", "#1e1b4b"),
    "svc": ("#ecfdf5", "#047857", "#064e3b"),
    "ai": ("#f5f3ff", "#6d28d9", "#2e1065"),
    "store": ("#fffbeb", "#b45309", "#451a03"),
    "bus": ("#fff1f2", "#be123c", "#4c0519"),
    "external": ("#f1f5f9", "#64748b", "#0f172a"),
    "obs": ("#f0fdf4", "#15803d", "#14532d"),
}
ARROWS = {  # stroke, width, dash
    "sync": ("#475569", 1.8, None),
    "async": ("#be123c", 3.2, None),
    "telemetry": ("#15803d", 1.8, "6 4"),
    "dlq": ("#be123c", 1.8, "6 4"),
}


class Svg:
    def __init__(self, width, height, title, desc):
        self.w, self.h, self.parts = width, height, []
        self.title, self.desc = title, desc

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size=13, weight=400, fill="#334155", anchor="middle", halo=False, italic=False):
        extra = ' paint-order="stroke" stroke="#ffffff" stroke-width="5" stroke-linejoin="round"' if halo else ""
        style = ' font-style="italic"' if italic else ""
        self.add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
                 f'text-anchor="{anchor}"{style}{extra}>{escape(s)}</text>')

    def band(self, x, y, w, h, label, sub=None, gutter=False):
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="#f8fafc" stroke="#e2e8f0"/>')
        if gutter:  # rotated label in a left gutter, so no arrow can cross it
            cx, cy = x + 17, y + h / 2
            self.add(f'<text x="{cx}" y="{cy}" transform="rotate(-90 {cx} {cy})" font-size="11" font-weight="700" '
                     f'fill="#475569" text-anchor="middle" letter-spacing="1">{escape(label.upper())}</text>')
            return
        self.text(x + 16, y + 22, label.upper(), 11.5, 700, "#475569", "start")
        if sub:
            self.text(x + 16, y + 39, sub, 12, 400, "#64748b", "start")

    def node(self, x, y, w, h, kind, title, lines=(), optional=False, chips=(), bold=False):
        fill, stroke, ink = KINDS[kind]
        dash = ' stroke-dasharray="6 4"' if optional else ""
        sw = 2.4 if bold else 1.6
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{dash}/>')
        cx = x + w / 2
        rows = 1 + len(lines)
        body = 20 * rows + (26 if chips else 0)
        ty = y + (h - body) / 2 + 15
        self.text(cx, ty, title, 15, 700, ink)
        for i, line in enumerate(lines):
            self.text(cx, ty + 20 * (i + 1), line, 12.5, 400, "#334155")
        if chips:
            cy = ty + 20 * len(lines) + 12
            widths = [len(c[1]) * 6.6 + 18 for c in chips]
            cxs = cx - (sum(widths) + 6 * (len(chips) - 1)) / 2
            for (ck, label), cw in zip(chips, widths):
                cf, cs, ci = KINDS[ck]
                self.add(f'<rect x="{cxs:.1f}" y="{cy}" width="{cw:.1f}" height="21" rx="10.5" fill="{cf}" stroke="{cs}" stroke-width="1.2"/>')
                self.text(cxs + cw / 2, cy + 14.5, label, 11.5, 600, ci)
                cxs += cw + 6
        if optional:  # badge straddling the top border
            self.add(f'<rect x="{x + w - 66}" y="{y - 9}" width="58" height="18" rx="9" fill="#ffffff" stroke="{stroke}" stroke-width="1.2"/>')
            self.text(x + w - 37, y + 4, "optional", 10.5, 600, stroke, italic=True)

    def cylinder(self, x, y, w, h, kind, title, lines=()):
        fill, stroke, ink = KINDS[kind]
        e = 9
        self.add(f'<path d="M{x},{y + e} a{w / 2},{e} 0 0 0 {w},0 a{w / 2},{e} 0 0 0 {-w},0 v{h - 2 * e} '
                 f'a{w / 2},{e} 0 0 0 {w},0 v{-(h - 2 * e)}" fill="{fill}" stroke="{stroke}" stroke-width="1.6"/>')
        cx = x + w / 2
        ty = y + e + (h - e - 20 * (1 + len(lines))) / 2 + 15
        self.text(cx, ty, title, 15, 700, ink)
        for i, line in enumerate(lines):
            self.text(cx, ty + 20 * (i + 1), line, 12.5, 400, "#334155")

    def arrow(self, pts, kind="sync", label=None, at=None, anchor="middle", lsize=12):
        stroke, width, dash = ARROWS[kind]
        d = "M" + " L".join(f"{px},{py}" for px, py in pts)
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{width}"{dash_attr} '
                 f'stroke-linejoin="round" marker-end="url(#arrow-{kind})"/>')
        if label:
            lx, ly = at
            for i, part in enumerate(label.split("\n")):
                self.text(lx, ly + i * 15, part, lsize, 600, "#1e293b", anchor, halo=True)

    def step(self, x, y, n):
        self.add(f'<circle cx="{x}" cy="{y}" r="10" fill="#0f172a"/>')
        self.text(x, y + 4.2, str(n), 11.5, 700, "#ffffff")

    def legend(self, x, y, items):
        cx = x
        for kind, label in items:
            if kind in ARROWS:
                stroke, width, dash = ARROWS[kind]
                dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
                self.add(f'<path d="M{cx},{y} L{cx + 30},{y}" stroke="{stroke}" stroke-width="{width}"{dash_attr} marker-end="url(#arrow-{kind})"/>')
                cx += 40
            elif kind == "optional":
                self.add(f'<rect x="{cx}" y="{y - 8}" width="26" height="16" rx="4" fill="#ffffff" stroke="#64748b" stroke-width="1.4" stroke-dasharray="4 3"/>')
                cx += 34
            else:
                fill, stroke, _ = KINDS[kind]
                self.add(f'<rect x="{cx}" y="{y - 8}" width="26" height="16" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>')
                cx += 34
            self.text(cx, y + 4.5, label, 12.5, 500, "#334155", "start")
            cx += len(label) * 6.9 + 22

    def render(self, name):
        markers = "".join(
            f'<marker id="arrow-{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="{13 if k == "async" else 9}" '
            f'markerHeight="{13 if k == "async" else 9}" orient="auto-start-reverse" markerUnits="userSpaceOnUse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{v[0]}"/></marker>'
            for k, v in ARROWS.items()
        )
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" '
            f'role="img" aria-labelledby="{name}-title {name}-desc" font-family="{FONT}">\n'
            f'<title id="{name}-title">{escape(self.title)}</title>\n<desc id="{name}-desc">{escape(self.desc)}</desc>\n'
            f'<defs>{markers}</defs>\n<rect width="100%" height="100%" rx="18" fill="#ffffff"/>\n'
            + "\n".join(self.parts) + "\n</svg>\n"
        )
        (OUT / f"{name}.svg").write_text(svg)


def overview():
    s = Svg(560, 1200, "RoboShop AI service map",
            "Browser traffic enters through Traefik and the web NGINX service. NGINX sends /api requests to ai-gateway "
            "and /moks requests to the optional Moks AI agent. A private mcp-server serves MCP clients and calls the "
            "gateway with the caller's session. The gateway calls the Moks engine for chat and calls the user, catalogue, "
            "cart, payment, shipping and currency services over HTTP. Each service's data store or provider is shown on "
            "it. Paid orders leave the gateway's outbox as RabbitMQ events consumed by shipping-service and kafka-bridge.")
    s.text(24, 40, "RoboShop AI: service map", 20, 700, "#0f172a", "start")
    s.text(24, 62, "Requests, data ownership and the paid-order event.", 12.5, 400, "#475569", "start")

    s.band(12, 80, 536, 104, "Clients", gutter=True)
    s.node(48, 100, 200, 64, "client", "Browser", ["storefront pages", "+ Moks widget"])
    s.node(336, 100, 200, 64, "client", "MCP client", ["IDE, desktop app, script", "stdio or private /mcp"])

    s.band(12, 196, 536, 100, "Edge", gutter=True)
    s.node(48, 219, 170, 54, "edge", "Traefik ingress", ["TLS, strips /roboshop"])
    s.node(266, 219, 180, 54, "edge", "web (NGINX)", ["storefront + proxy"])
    s.arrow([(133, 164), (133, 219)])
    s.arrow([(218, 246), (266, 246)])
    s.arrow([(500, 164), (500, 480)])

    s.band(12, 308, 536, 258, "Entry and orchestration", gutter=True)
    s.node(48, 340, 150, 80, "ai", "moks", ["Python · AI agent", "LangGraph engine"], optional=True)
    s.node(258, 340, 190, 112, "svc", "ai-gateway", ["Python · public API,", "sessions, ledger, outbox"],
           chips=[("store", "MongoDB"), ("store", "JSON ledger")], bold=True)
    s.node(48, 470, 150, 56, "external", "Bedrock or Ollama", ["chosen by super admin"], optional=True)
    s.node(392, 480, 144, 70, "ai", "mcp-server", ["Python · private", "MCP tools"])
    s.arrow([(356, 273), (356, 340)], label="/api/*", at=(364, 316), anchor="start")
    s.arrow([(290, 273), (290, 302), (123, 302), (123, 340)], label="/moks/*", at=(206, 298))
    s.arrow([(258, 384), (198, 384)], label="/internal\n/chat", at=(228, 360))
    s.arrow([(123, 420), (123, 470)], label="model call", at=(131, 450), anchor="start")
    s.arrow([(420, 480), (420, 452)], label="caller's session", at=(412, 472), anchor="end")

    s.band(12, 578, 536, 334, "Domain services", gutter=True)
    s.arrow([(292, 452), (292, 592)], label="HTTP", at=(300, 540), anchor="start")
    tiles = [
        ("user-service", "Python · accounts, MFA", ("store", "MongoDB: users")),
        ("catalogue-service", "Node.js · product reads", ("store", "MongoDB: products")),
        ("cart-service", "Python · cart lines", ("store", "Redis")),
        ("payment-service", "Node.js · Razorpay adapter", ("external", "Razorpay")),
        ("shipping-service", "Java · quotes, shipments", ("store", "PostgreSQL")),
        ("currency-service", "Go · exchange rates", ("external", "ECB feed")),
    ]
    for i, (name, line, chip) in enumerate(tiles):
        s.node((48, 300)[i % 2], 600 + (i // 2) * 92, 236, 80, "svc", name, [line], chips=[chip],
               optional=name == "currency-service")
    s.text(48, 884, "web also proxies /api/currency/rates directly to currency-service.", 11.5, 400, "#64748b", "start")
    s.text(48, 900, "The MongoDB chips are separate collections in one shared instance.", 11.5, 400, "#64748b", "start")

    s.band(12, 924, 536, 144, "Events", gutter=True)
    s.text(48, 946, "Paid orders publish order.paid; consumers deduplicate by event ID.", 12, 400, "#475569", "start")
    s.node(48, 962, 120, 56, "svc", "ai-gateway", ["ledger outbox"])
    s.node(206, 962, 130, 56, "bus", "RabbitMQ", ["roboshop.orders"])
    s.node(380, 954, 156, 46, "svc", "shipping-service", ["→ PostgreSQL"])
    s.node(380, 1010, 156, 46, "svc", "kafka-bridge", ["→ Kafka"])
    s.arrow([(168, 990), (206, 990)], "async")
    s.arrow([(336, 982), (358, 982), (358, 977), (380, 977)], "async")
    s.arrow([(336, 998), (358, 998), (358, 1033), (380, 1033)], "async")

    s.band(12, 1080, 536, 108, "Legend", gutter=True)
    s.legend(48, 1108, [("sync", "Synchronous HTTP"), ("async", "Asynchronous event")])
    s.legend(48, 1138, [("optional", "Optional / configurable"), ("store", "Data store")])
    s.legend(48, 1168, [("external", "External provider"), ("telemetry", "Telemetry (Figure 4)")])
    s.render("roboshop-ai-overview")


def ai_paths():
    s = Svg(800, 900, "RoboShop AI: Moks and MCP request paths",
            "Path A: the browser widget sends a message through web to the Moks widget routes, which call ai-gateway "
            "/api/chat with the user's session. The gateway adds history references, unavailable SKUs and the active "
            "model configuration, then calls the Moks engine. The engine reads the catalogue from catalogue-service, "
            "checks the configuration revision with the gateway and calls Bedrock or Ollama. Path B: an MCP client calls "
            "the private mcp-server with the user's session; mcp-server calls the gateway, which re-authorizes the call. "
            "Moks does not use MCP.")
    s.text(40, 44, "AI request paths", 21, 700, "#0f172a", "start")
    s.text(40, 66, "Two independent entry points. Moks never calls the MCP server.", 13, 400, "#475569", "start")

    s.band(24, 84, 752, 520, "A. Moks shopping assistant", "Browser widget → gateway → agent engine. Both moks boxes are one Deployment.")
    xs = (40, 230, 420, 610)
    s.node(xs[0], 140, 150, 64, "client", "Browser", ["Moks widget"])
    s.node(xs[1], 140, 150, 64, "edge", "web (NGINX)", ["/moks/chat"])
    s.node(xs[2], 140, 150, 64, "ai", "moks", ["widget routes"])
    s.node(xs[3], 140, 150, 64, "svc", "ai-gateway", ["/api/chat"])
    for a, b in ((0, 1), (1, 2), (2, 3)):
        s.arrow([(xs[a] + 150, 172), (xs[b], 172)])
    s.step(205, 160, 1)
    s.step(395, 160, 2)
    s.step(585, 160, 3)
    s.node(xs[3], 268, 150, 64, "ai", "moks", ["engine", "/internal/chat"])
    s.arrow([(668, 204), (668, 268)])
    s.step(652, 236, 4)
    s.arrow([(702, 268), (702, 204)])
    s.step(718, 236, 6)
    s.node(xs[2], 268, 150, 64, "svc", "catalogue-service", ["/api/products"])
    s.arrow([(610, 300), (570, 300)])
    s.step(590, 285, 5)
    s.node(xs[3], 380, 150, 64, "external", "Bedrock or Ollama", ["admin-selected"], optional=True)
    s.arrow([(685, 332), (685, 380)])
    s.step(668, 356, 7)
    steps = [
        "Widget sends only the message; the browser cannot supply history or a user ID.",
        "NGINX forwards /moks/* to the Moks widget routes (direct /api/chat is blocked).",
        "Moks checks the session and Origin, then calls gateway /api/chat with the session cookie.",
        "Gateway adds saved product references, unavailable SKUs and the model config + revision.",
        "Engine reads the catalogue and filters evidence: stock, budget, currency, at most four products.",
        "Before generating, the engine confirms the config revision with the gateway.",
        "One provider call (optional failover). The gateway then re-applies stock and saves the turn.",
    ]
    for i, line in enumerate(steps):
        y = 470 + i * 18.5
        s.text(40, y, f"{i + 1}. {line}", 12.2, 400, "#334155", "start")
    s.text(40, 362, "LangGraph:", 12.5, 700, "#2e1065", "start")
    s.text(40, 380, "search_catalogue →", 12.5, 400, "#334155", "start")
    s.text(40, 398, "ground_evidence →", 12.5, 400, "#334155", "start")
    s.text(40, 416, "generate_answer", 12.5, 400, "#334155", "start")
    s.text(40, 438, "No tools, no cart or order actions.", 12.5, 400, "#334155", "start")

    s.band(24, 620, 752, 200, "B. MCP tools", "Private ClusterIP Service, no ingress. Local stdio or a port-forward.")
    s.node(xs[0], 676, 150, 64, "client", "MCP client", ["stdio or /mcp"])
    s.node(xs[1], 676, 150, 64, "ai", "mcp-server", ["schemas, limits"])
    s.node(xs[2], 676, 150, 64, "svc", "ai-gateway", ["re-authorizes"])
    s.node(xs[3], 676, 150, 64, "svc", "domain services", ["user, catalogue,", "cart, shipping"])
    for a, b in ((0, 1), (1, 2), (2, 3)):
        s.arrow([(xs[a] + 150, 708), (xs[b], 708)])
    s.text(40, 766, "The bearer token is the caller's own RoboShop session, checked on every request.", 12.2, 400, "#334155", "start")
    s.text(40, 784, "Ten read tools and update_cart are registered; admin write tools need MCP_ENABLE_ADMIN_WRITES", 12.2, 400, "#334155", "start")
    s.text(40, 802, "and a signed, one-time confirmation. There are no payment, order or refund tools.", 12.2, 400, "#334155", "start")

    s.band(24, 836, 752, 50, "Legend")
    s.legend(120, 862, [("sync", "Synchronous HTTP / MCP"), ("optional", "Optional / configurable")])
    s.render("roboshop-ai-ai-paths")


def checkout_events():
    s = Svg(800, 824, "RoboShop AI: checkout and paid-order events",
            "Checkout is synchronous: the browser creates an order at ai-gateway with an idempotency key, the gateway "
            "reserves stock in its ledger and calls payment-service, which talks to Razorpay. Razorpay sends a signed "
            "webhook back to the gateway. After a verified capture the ledger records the order as paid with an event ID. "
            "A background publisher sends the event to the RabbitMQ exchange roboshop.orders. Live paid orders go to the "
            "shipping queue and shipping-service, which writes a shipment request to PostgreSQL; failures go to a "
            "dead-letter queue. Test orders go to an audit queue. Both kinds go to a Kafka queue read by kafka-bridge.")
    s.text(40, 44, "Checkout and background events", 21, 700, "#0f172a", "start")
    s.text(40, 66, "Money moves synchronously; fulfilment and analytics follow asynchronously.", 13, 400, "#475569", "start")

    xs = (40, 230, 420, 610)
    s.band(24, 84, 752, 330, "Checkout", "Synchronous HTTP, idempotent, server-verified")
    s.node(xs[0], 168, 150, 64, "client", "Browser", ["checkout page"])
    s.node(xs[1], 168, 150, 64, "svc", "ai-gateway", ["reserve, verify"], bold=True)
    s.node(xs[2], 168, 150, 64, "svc", "payment-service", ["HMAC, capture"])
    s.node(xs[3], 168, 150, 64, "external", "Razorpay", ["test mode default"])
    s.arrow([(190, 200), (230, 200)])
    s.arrow([(380, 200), (420, 200)])
    s.arrow([(570, 200), (610, 200)])
    s.arrow([(685, 168), (685, 140), (305, 140), (305, 168)], label="signed webhook (recovery path)", at=(495, 136))
    s.cylinder(xs[1], 264, 150, 74, "store", "Ledger + outbox", ["single writer"])
    s.arrow([(305, 232), (305, 264)])
    states = ["creating", "payment_pending", "paid"]
    s.text(420, 290, "Order states", 12.5, 700, "#334155", "start")
    x = 420
    for i, label in enumerate(states):
        w = len(label) * 7.0 + 18
        s.add(f'<rect x="{x}" y="300" width="{w:.0f}" height="24" rx="12" fill="#ffffff" stroke="#94a3b8"/>')
        s.text(x + w / 2, 316, label, 12, 600, "#0f172a")
        x += w
        if i < len(states) - 1:
            s.arrow([(x + 4, 312), (x + 22, 312)])
            x += 26
    s.text(420, 344, "An unknown provider outcome becomes payment_review", 12, 400, "#475569", "start")
    s.text(420, 361, "and keeps its stock reservation.", 12, 400, "#475569", "start")
    s.text(40, 372, "Idempotency-Key on create; capture, amount and currency", 12, 400, "#475569", "start")
    s.text(40, 389, "checked before the order becomes paid.", 12, 400, "#475569", "start")

    s.band(24, 430, 752, 270, "Paid-order events", "Asynchronous, at least once. Queue names are prefixed roboshop.")
    s.node(xs[0], 520, 150, 64, "svc", "ai-gateway", ["outbox publisher"])
    s.node(xs[1], 520, 150, 64, "bus", "RabbitMQ", ["exchange: orders"])
    s.node(xs[2], 482, 150, 50, "bus", "shipping.orders", ["order.paid"])
    s.node(xs[2], 545, 150, 50, "bus", "test.orders", ["audit, no consumer"])
    s.node(xs[2], 618, 150, 50, "bus", "kafka.orders", ["both keys"])
    s.node(xs[3], 474, 150, 66, "svc", "shipping-service", [], chips=[("store", "PostgreSQL")])
    s.node(xs[3], 550, 150, 50, "bus", "shipping.failed", ["after 5 failures"])
    s.node(xs[3], 610, 150, 66, "svc", "kafka-bridge", [], chips=[("store", "Kafka")])
    s.arrow([(190, 552), (230, 552)], "async")
    s.arrow([(380, 540), (400, 540), (400, 507), (420, 507)], "async")
    s.arrow([(380, 552), (400, 552), (400, 570), (420, 570)], "async")
    s.arrow([(380, 564), (392, 564), (392, 643), (420, 643)], "async")
    s.arrow([(570, 500), (610, 500)], "async")
    s.arrow([(570, 643), (610, 643)], "async")
    s.arrow([(570, 520), (590, 520), (590, 575), (610, 575)], "dlq")

    s.band(24, 716, 752, 92, "Legend")
    s.legend(44, 756, [("sync", "Synchronous HTTP"), ("async", "Asynchronous event"), ("dlq", "Dead-letter route")])
    s.legend(44, 786, [("store", "Data store"), ("external", "External provider")])
    s.render("roboshop-ai-checkout-events")


def observability():
    s = Svg(800, 600, "RoboShop AI: telemetry paths",
            "Every RoboShop service sends OpenTelemetry spans over OTLP/HTTP to the OpenTelemetry Collector, which strips "
            "sensitive attributes and forwards to Jaeger. Prometheus scrapes each service's /metrics endpoint. Alloy reads "
            "pod logs through the Kubernetes API and pushes them to Loki. Grafana queries Prometheus and Loki. When "
            "credentials are configured, Moks also sends metadata-only model spans to Langfuse Cloud.")
    s.text(40, 44, "Telemetry paths", 21, 700, "#0f172a", "start")
    s.text(40, 66, "Arrows follow the data. Prometheus and Alloy pull; services push spans.", 13, 400, "#475569", "start")

    s.band(24, 84, 752, 380, "Signals")
    s.node(40, 124, 170, 214, "svc", "RoboShop services", ["OTLP spans", "/metrics", "JSON logs (stdout)", "W3C traceparent", "propagated"])
    s.node(240, 124, 170, 64, "obs", "OTel Collector", ["redacts attributes"])
    s.node(240, 224, 170, 64, "obs", "Prometheus", ["job: roboshop"])
    s.node(240, 324, 170, 64, "obs", "Alloy", ["tails pod logs"])
    s.cylinder(440, 124, 150, 64, "obs", "Jaeger", ["in-memory"])
    s.cylinder(440, 324, 150, 64, "obs", "Loki", [])
    s.node(620, 224, 140, 164, "obs", "Grafana", ["dashboards,", "Explore"])
    s.arrow([(210, 156), (240, 156)], "telemetry")
    s.arrow([(210, 256), (240, 256)], "telemetry")
    s.arrow([(210, 316), (225, 316), (225, 356), (240, 356)], "telemetry")
    s.arrow([(410, 156), (440, 156)], "telemetry")
    s.arrow([(410, 356), (440, 356)], "telemetry")
    s.arrow([(410, 256), (620, 256)], "telemetry", label="queries", at=(515, 248))
    s.arrow([(590, 356), (620, 356)], "telemetry")
    s.text(440, 210, "Jaeger UI via port-forward", 11.5, 400, "#64748b", "start")
    s.node(40, 372, 170, 64, "ai", "moks", ["gen_ai model spans"])
    s.node(440, 400, 320, 50, "external", "Langfuse Cloud", ["metadata only, when credentials exist"], optional=True)
    s.arrow([(210, 425), (440, 425)], "telemetry", label="optional", at=(325, 417))

    s.band(24, 480, 752, 104, "What is not recorded")
    s.text(44, 516, "Access logs omit query strings, cookies and bodies. Model spans record provider, model, token use", 12.5, 400, "#334155", "start")
    s.text(44, 535, "and latency, not prompts or replies, unless a synthetic-capture switch is set. Alerts are evaluated", 12.5, 400, "#334155", "start")
    s.text(44, 554, "in Prometheus, but no Alertmanager is installed, so nothing is paged.", 12.5, 400, "#334155", "start")
    s.legend(560, 568, [("telemetry", "Telemetry")])
    s.render("roboshop-ai-observability")


if __name__ == "__main__":
    overview()
    ai_paths()
    checkout_events()
    observability()
