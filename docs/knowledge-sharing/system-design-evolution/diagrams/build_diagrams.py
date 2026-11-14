#!/usr/bin/env python3
"""Figures for the two-part "System Design Evolution" article.

    python3 sites/jithendar.com/docs/knowledge-sharing/system-design-evolution/diagrams/build_diagrams.py   (from www/)
    bash sites/jithendar.com/docs/knowledge-sharing/system-design-evolution/diagrams/export.sh

The first command writes one editable .drawio file per figure beside this script. The second has the draw.io
desktop app (CLI) export each one to public/images/system-design-evolution/<name>.svg and .png, so the website
images are real draw.io renders. After editing a .drawio file in draw.io, run export.sh again; do not rerun this
script, or it will overwrite the hand edits.

Historical figures are illustrations of typical designs, not records of one real system. The RoboShop AI
figure was checked against roboshop-ai 02a4478 and the live mk4 cluster on 8 November 2026.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio_model import Diagram  # noqa: E402

HERE = Path(__file__).resolve().parent


def client_server_1990s():
    d = Diagram("1990s-client-server", 760, 860, "Early 1990s: a two-tier client-server application (illustration)")
    d.zone("z-floor", "Office floor: desktop PCs", 20, 48, 720, 124)
    d.node("pc1", "client", 35, 78, 220, 80, "Desktop PC (fat client)", "screens and business rules", "installed by hand: v2.1")
    d.node("pc2", "client", 270, 78, 220, 80, "Desktop PC (fat client)", "same program, local copy", "installed by hand: v2.1")
    d.node("pc3", "client", 505, 78, 220, 80, "Desktop PC (fat client)", "nobody updated this one", "still on v1.9")
    d.marker(1, 717, 84)
    d.node("lan", "network", 35, 196, 690, 50, "Shared LAN segment", "Ethernet or Token Ring inside one building")
    d.marker(2, 717, 202)
    d.zone("z-room", "Server room, same building", 20, 270, 720, 248)
    d.node("app", "compute", 35, 302, 330, 92, "Application / file server", "NetWare or Unix", "shared files, printing, some logic")
    d.node("db", "data", 395, 296, 330, 108, "Database server", "Oracle7 or DB2, stored procedures", "one machine, local disks",
           shape="db")
    d.marker(3, 717, 306)
    d.node("batch", "compute", 35, 420, 330, 80, "Overnight batch jobs", "statements, interest, reports")
    d.node("tape", "external", 395, 420, 330, 80, "Tape backup", "nightly full copy", "tapes driven offsite weekly")
    d.marker(4, 717, 428)
    d.zone("z-hq", "Head office data centre", 20, 548, 720, 100, corner="right")
    d.node("mf", "compute", 35, 576, 330, 60, "Mainframe", "CICS online work, overnight batch")
    d.marker(5, 352, 532)
    d.edge("pc1", "lan", exit=(0.5, 1), entry=(0.155, 0))
    d.edge("pc2", "lan", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("pc3", "lan", exit=(0.5, 1), entry=(0.845, 0))
    d.edge("lan", "app", exit=(0.29, 1), entry=(0.5, 0), label="file and print")
    d.edge("lan", "db", exit=(0.81, 1), entry=(0.5, 0), label="SQL from each PC")
    d.edge("app", "db", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("app", "batch", exit=(0.5, 1), entry=(0.5, 0), kind="batch", label="02:00 schedule")
    d.edge("db", "tape", exit=(0.5, 1), entry=(0.5, 0), kind="batch", label="nightly dump")
    d.edge("batch", "mf", exit=(0.5, 1), entry=(0.5, 0), kind="batch", label="file transfer, leased line")
    d.node("fails", "security", 20, 666, 720, 116, "Typical failure points",
           "1  Version drift: each PC runs whatever was last installed on it",
           "2  One cable fault or broadcast storm stops the whole floor",
           "3  One database server: a disk or CPU fault stops everyone",
           "4  Tapes exist, but nobody has rehearsed a restore",
           "5  Leased line down: head office gets no overnight file", align="left")
    d.legend(800, failure=True)
    return d


def three_tier_web():
    d = Diagram("late-1990s-three-tier-web", 860, 960, "Late 1990s: a three-tier web shop (illustration)")
    d.zone("z-home", "Customers at home and work", 20, 48, 700, 102)
    d.node("b1", "client", 35, 76, 330, 62, "Web browser", "HTML pages, forms and a session cookie")
    d.node("b2", "client", 375, 76, 330, 62, "Web browser", "over dial-up or an office connection")
    d.node("net", "external", 270, 168, 200, 70, "The Internet", shape="cloud")
    d.zone("z-dmz", "Data centre: DMZ", 20, 256, 700, 290)
    d.node("fw1", "security", 35, 284, 670, 46, "Firewall", "only HTTP (80) and HTTPS (443) come in")
    d.node("lb", "network", 220, 350, 300, 62, "Load balancer", "spreads requests, sticky sessions")
    d.node("web1", "compute", 35, 436, 330, 94, "Web server 1", "Apache httpd: static HTML, images",
           "CGI or modules for dynamic pages")
    d.node("web2", "compute", 375, 436, 330, 94, "Web server 2", "same content, same config", "copied by hand or script")
    d.zone("z-int", "Data centre: internal network", 20, 566, 700, 360, corner="right")
    d.node("fw2", "security", 35, 594, 670, 46, "Second firewall", "the web tier may call the app tier, nothing else")
    d.node("app1", "service", 35, 660, 330, 94, "Application server 1", "Java servlets, EJB, ASP or Perl",
           "cart kept in the user's session")
    d.node("app2", "service", 375, 660, 330, 94, "Application server 2", "same code, deployed at night",
           "session lost if this box dies")
    d.node("db", "data", 220, 790, 300, 118, "Database", "Oracle or SQL Server, one primary",
           "customers, catalogue, orders", shape="db")
    d.node("t1", "optional", 730, 436, 120, 94, "Presentation", "tier 1")
    d.node("t2", "optional", 730, 660, 120, 94, "Logic", "tier 2")
    d.node("t3", "optional", 730, 790, 120, 118, "Data", "tier 3")
    d.edge("b1", "net", exit=(0.5, 1), entry=(0.2, 0.2))
    d.edge("b2", "net", exit=(0.5, 1), entry=(0.8, 0.2))
    d.edge("net", "fw1", exit=(0.5, 0.9), entry=(0.5, 0), label="HTTP")
    d.edge("fw1", "lb", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("lb", "web1", exit=(0.2, 1), entry=(0.6, 0))
    d.edge("lb", "web2", exit=(0.8, 1), entry=(0.4, 0))
    d.edge("web1", "fw2", exit=(0.5, 1), entry=(0.246, 0))
    d.edge("web2", "fw2", exit=(0.5, 1), entry=(0.754, 0))
    d.edge("fw2", "app1", exit=(0.246, 1), entry=(0.5, 0), label="servlet or RPC call")
    d.edge("fw2", "app2", exit=(0.754, 1), entry=(0.5, 0))
    d.edge("app1", "db", exit=(0.6, 1), entry=(0.2, 0.08), label="SQL")
    d.edge("app2", "db", exit=(0.4, 1), entry=(0.8, 0.08), label="SQL")
    d.legend(944)
    return d


def cloud_native_microservices():
    d = Diagram("2010s-cloud-native-microservices", 860, 800, "2010s: cloud-native microservices (illustration)")
    d.node("users", "client", 280, 48, 300, 56, "Users", "browsers and mobile apps")
    d.node("lb", "network", 280, 124, 300, 56, "Cloud load balancer", "TLS, health checks, several zones")
    d.zone("z-k8s", "Kubernetes cluster: schedules, restarts and scales every box inside", 20, 204, 820, 440, "cluster")
    d.node("gw", "network", 230, 236, 400, 56, "API gateway", "routing, authentication, rate limits")
    services = [("users", "Users", "owns accounts", "Postgres", "users"),
                ("cat", "Catalogue", "owns products", "MongoDB", "products"),
                ("cart", "Cart", "owns carts", "Redis", "carts"),
                ("orders", "Orders", "owns orders", "Postgres", "orders"),
                ("pay", "Payments", "owns payments", "Postgres", "payments"),
                ("ship", "Shipping", "owns shipments", "Postgres", "shipping")]
    for i, (key, title, line, store, holds) in enumerate(services):
        x = 35 + i * 134
        d.node(f"s-{key}", "service", x, 332, 122, 74, title, "service", line)
        d.node(f"d-{key}", "data", x, 440, 96, 84, store, holds, shape="db")
        d.edge("gw", f"s-{key}", exit=(0.05 + i * 0.18, 1), entry=(0.5, 0))
        d.edge(f"s-{key}", f"d-{key}", exit=(48 / 122, 1), entry=(0.5, 0))
    d.node("kafka", "messaging", 35, 560, 792, 62, "Kafka event log",
           "order-placed and payment-captured events, kept so consumers can replay them", shape="queue")
    lane = lambda i: 35 + i * 134 + 110
    d.edge("s-orders", "kafka", exit=(110 / 122, 1), entry=((lane(3) - 35) / 792, 0), kind="async")
    d.edge("s-pay", "kafka", exit=(110 / 122, 1), entry=((lane(4) - 35) / 792, 0), kind="async")
    d.edge("kafka", "s-ship", exit=((lane(5) - 35) / 792, 0), entry=(110 / 122, 1), kind="async")
    d.edge("s-orders", "s-pay", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("users", "lb", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("lb", "gw", exit=(0.5, 1), entry=(0.5, 0), label="HTTPS")
    d.zone("z-ops", "Platform and operations", 20, 664, 820, 104)
    d.node("ci", "ops", 35, 694, 190, 60, "CI pipeline", "build, test, scan, push")
    d.node("reg", "ops", 240, 694, 190, 60, "Container registry", "versioned images")
    d.node("gitops", "ops", 445, 694, 190, 60, "GitOps (Argo CD)", "applies manifests")
    d.node("obs", "ops", 650, 694, 175, 60, "Observability", "metrics, logs, traces")
    d.edge("ci", "reg", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("gitops", "z-k8s", exit=(0.5, 0), entry=(0.658, 1), kind="control", label="deploy")
    d.edge("z-k8s", "obs", exit=(0.896, 1), entry=(0.5, 0), kind="control", label="telemetry")
    d.legend(788)
    return d


def ai_native_architecture():
    d = Diagram("2026-ai-native-architecture", 860, 800, "2026: an application with optional AI capabilities (illustration)")
    d.node("fe", "client", 230, 48, 400, 56, "Web or mobile frontend", "normal pages, plus a chat panel")
    d.node("idp", "security", 660, 48, 180, 56, "Identity provider", "OIDC, SSO, MFA")
    d.node("apigw", "network", 230, 128, 400, 56, "API gateway", "authenticate, rate limit, route")
    d.zone("z-app", "Conventional application", 20, 208, 400, 428)
    d.node("app", "service", 35, 240, 370, 274, "Application services", "orders, catalogue, cart, accounts",
           "deterministic business rules", "the only path that changes data",
           "re-checks the user's permissions")
    d.node("db", "data", 35, 536, 175, 84, "PostgreSQL", "orders, users, audit", shape="db")
    d.node("mq", "messaging", 230, 536, 175, 84, "Message broker", "Kafka or RabbitMQ", shape="queue")
    d.zone("z-ai", "AI capabilities (optional)", 440, 208, 400, 428, "ai")
    d.node("aigw", "ai", 455, 240, 200, 64, "AI gateway", "model routing, budgets", "redaction, caching")
    d.node("llm", "external", 670, 240, 155, 64, "LLM providers", "hosted API or", "self-hosted model")
    d.node("orch", "ai", 455, 344, 200, 64, "Agent orchestrator", "LangGraph state machine", "step, tool and time limits")
    d.node("approve", "security", 670, 344, 155, 64, "Human approval", "a person confirms", "risky writes")
    d.node("mcp", "ai", 455, 450, 200, 64, "MCP server", "typed tools that call", "app APIs as the user")
    d.node("rag", "ai", 670, 450, 155, 64, "RAG retrieval", "embed, search, rank")
    d.node("vec", "data", 670, 536, 155, 84, "Vector database", "chunks + embeddings", shape="db")
    d.node("obs", "ops", 20, 656, 820, 60, "Observability",
           "OpenTelemetry traces across services and agent steps; Langfuse for prompts, tokens, cost and evaluations")
    d.edge("fe", "apigw", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("apigw", "idp", exit=(1, 0.5), entry=(0.5, 1), label="verify token")
    d.edge("apigw", "app", exit=(0.1, 1), entry=(235 / 370, 0))
    d.edge("app", "aigw", exit=(1, 32 / 274), entry=(0, 0.5))
    d.edge("aigw", "llm", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("aigw", "orch", exit=(0.5, 1), entry=(0.5, 0), both=True, label="workflow and model calls")
    d.edge("orch", "approve", exit=(1, 0.5), entry=(0, 0.5), kind="control")
    d.edge("orch", "mcp", exit=(0.5, 1), entry=(0.5, 0), label="tool call")
    d.edge("orch", "rag", exit=(0.85, 1), entry=(0.3, 0), via=[(625, 430), (716, 430)])
    d.edge("rag", "vec", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("mcp", "app", exit=(0, 0.5), entry=(1, 242 / 274))
    d.edge("app", "db", exit=(87.5 / 370, 1), entry=(0.5, 0))
    d.edge("app", "mq", exit=(282.5 / 370, 1), entry=(0.5, 0), kind="async")
    d.legend(736)
    return d


TIMELINE = [
    # (row, date, line 1, line 2, kind)
    (0, "Mar 1989", "Berners-Lee proposes", "the Web at CERN", "network"),
    (0, "30 Apr 1993", "CERN releases the Web", "software, public domain", "network"),
    (0, "Apr 1995", "Apache httpd 0.6.2,", "first public release", "network"),
    (0, "23 May 1995", "Sun announces Java", "at SunWorld", "network"),
    (0, "May 1996", "HTTP/1.0 published", "as RFC 1945", "network"),
    (0, "2000", "Brewer's CAP keynote;", "Fielding's REST thesis", "data"),
    (0, "2003 and 2004", "Google File System and", "MapReduce papers", "data"),
    (0, "Mar and Aug 2006", "Amazon S3 launches;", "EC2 beta follows", "ops"),
    (0, "2007", "Amazon's Dynamo paper", "at SOSP", "data"),
    (1, "15 Mar 2013", "Docker shown publicly", "at PyCon", "ops"),
    (1, "6 Jun 2014", "First Kubernetes", "commit", "ops"),
    (1, "2015", "Google's Borg paper", "at EuroSys", "data"),
    (1, "21 Jul 2015", "Kubernetes 1.0;", "CNCF announced", "ops"),
    (1, "May 2019", "OpenTracing + OpenCensus", "merge: OpenTelemetry", "ops"),
    (1, "May 2020", "Retrieval-augmented", "generation paper", "data"),
    (1, "6 Dec 2022", "Argo graduates", "in the CNCF", "ops"),
    (1, "25 Nov 2024", "Anthropic introduces the", "Model Context Protocol", "ai"),
    (1, "2026", "Agents, GitOps, platform", "teams: this article", "ai"),
]


def timeline():
    d = Diagram("system-design-timeline", 960, 560, "Milestones that shaped system design, 1989 to 2026 (spacing not to scale)")
    bands = {0: [("1989-1999", 0, 4, "#e0e7ff"), ("2000-2009", 5, 8, "#dcfce7")],
             1: [("2010-2019", 0, 4, "#fef3c7"), ("2020-2026", 5, 8, "#f3e8ff")]}
    axis_y = {0: 160, 1: 420}
    x_of = lambda i: 110 + i * 92.5
    for row, spans in bands.items():
        for label, first, last, fill in spans:
            x0, x1 = x_of(first) - 46, x_of(last) + 46
            d._add(f"band{row}{first}", "", f"rounded=1;arcSize=40;html=1;strokeColor=none;fillColor={fill};",
                   x0, axis_y[row] - 11, x1 - x0, 22)
            d.text(f"bandlabel{row}{first}", x_of(first) + 10, axis_y[row] + 13, 74, 16,
                   f"<b>{label.replace('-', '&#8211;')}</b>", size=11, align="center")
    counters = {0: 0, 1: 0}
    order = sorted(range(len(TIMELINE)), key=lambda k: (TIMELINE[k][0], k))
    for k in order:
        row, date, l1, l2, kind = TIMELINE[k]
        i = counters[row]
        counters[row] += 1
        cx = x_of(i)
        above = i % 2 == 0
        y = axis_y[row] - 108 if above else axis_y[row] + 42
        box = d.node(f"ev{k}", kind, cx - 88, y, 176, 66, date, l1, l2)
        dot = f"dot{k}"
        d._add(dot, "", "ellipse;fillColor=#0f172a;strokeColor=#ffffff;strokeWidth=2;", cx - 6, axis_y[row] - 6, 12, 12)
        d.edge(dot, box, exit=(0.5, 0 if above else 1), entry=(0.5, 1 if above else 0), kind="sync", arrow=False)
    d.legend(552, labels={"network": "Web and software releases", "data": "Papers and talks",
                          "ops": "Cloud and cloud native", "ai": "AI systems"})
    return d


def era_skeleton(d, cluster_label=None):
    """Zones shared by the three retail figures, so their rows line up for side-by-side reading."""
    d.zone("z-cust", "Customers", 20, 48, 720, 88)
    d.zone("z-entry", "Entry point", 20, 152, 720, 96)
    d.zone("z-app", cluster_label or "Application and data", 20, 264, 720, 272, "cluster" if cluster_label else "plain")
    d.zone("z-out", "Outside partners", 20, 552, 720, 96, valign="bottom")


def retail_1992():
    d = Diagram("retail-1992-client-server", 760, 760, "The same shop in 1992: client-server retail (illustration)")
    era_skeleton(d, "Server room: one program, one database")
    d.node("cust", "client", 35, 74, 690, 50, "Customers are not on the system", "they phone, post a mail-order form or visit a store")
    d.node("oe", "client", 35, 180, 330, 56, "Order-entry PCs", "clerks key in every order")
    d.node("wh", "client", 395, 180, 330, 56, "Warehouse terminals", "pick lists, stock counts")
    d.node("mono", "service", 35, 296, 440, 118, "Retail application (one program)", "users, catalogue, cart (the order form)",
           "orders, payments, inventory, shipping", "modules compiled and released together")
    d.node("db", "data", 505, 292, 220, 122, "Relational DB", "Oracle or DB2", "one schema, all modules", shape="db")
    d.node("batch", "compute", 35, 440, 440, 78, "Overnight batch", "settle card payments, reorder stock, print manifests")
    d.node("tape", "external", 505, 440, 220, 78, "Tape backup", "nightly, offsite weekly")
    d.node("bank", "external", 35, 576, 330, 52, "Card processor", "batch file or dial-up line")
    d.node("carrier", "external", 395, 576, 330, 52, "Carrier", "printed manifests, phone calls")
    d.node("ops", "ops", 20, 664, 720, 58, "Releases", "a new version installed on every PC by hand, over a weekend")
    d.edge("cust", "oe", exit=(0.24, 1), entry=(0.5, 0), kind="batch", label="phone, post")
    d.edge("oe", "mono", exit=(0.5, 1), entry=(0.375, 0), label="LAN")
    d.edge("wh", "mono", exit=(0.25, 1), entry=(0.94, 0))
    d.edge("mono", "db", exit=(1, 0.5), entry=(0, 0.5), label="SQL")
    d.edge("mono", "batch", exit=(0.5, 1), entry=(0.5, 0), kind="batch")
    d.edge("db", "tape", exit=(0.5, 1), entry=(0.5, 0), kind="batch")
    d.edge("batch", "bank", exit=(0.375, 1), entry=(0.5, 0), kind="batch", label="nightly file")
    d.edge("batch", "carrier", exit=(0.9, 1), entry=(0.2, 0), kind="batch", label="manifests")
    d.legend(740)
    return d


def retail_2012():
    d = Diagram("retail-2012-web-tier", 760, 760, "The same shop in 2012: a scaled-out web application (illustration)")
    era_skeleton(d, "Virtual machines, cloud or colocation")
    d.node("cust", "client", 35, 74, 690, 50, "Browsers", "desktop web, early smartphones")
    d.node("cdn", "network", 35, 180, 330, 56, "CDN", "images, CSS, JavaScript")
    d.node("lb", "network", 395, 180, 330, 56, "Load balancer", "HTTPS, health checks")
    d.node("app", "service", 35, 296, 440, 118, "Web/app servers ×4 (one codebase)", "users, catalogue, cart, orders",
           "payments, inventory, shipping as modules", "stateless: sessions live in the cache")
    d.node("cache", "data", 505, 292, 220, 54, "Memcached or Redis", "sessions, page cache")
    d.node("db", "data", 505, 356, 220, 84, "MySQL", "primary + read replicas", shape="db")
    d.node("workers", "service", 35, 440, 210, 78, "Background workers", "emails, labels, stock sync")
    d.node("mq", "messaging", 265, 440, 210, 78, "Message queue", "RabbitMQ: order jobs", shape="queue")
    d.node("bank", "external", 35, 576, 330, 52, "Payment gateway", "hosted card form, tokens")
    d.node("carrier", "external", 395, 576, 330, 52, "Carrier API", "rates and labels")
    d.node("ops", "ops", 20, 664, 720, 58, "Releases", "scripted deploys from a CI server, one server at a time behind the load balancer")
    d.edge("cust", "cdn", exit=(0.24, 1), entry=(0.5, 0), label="static files")
    d.edge("cust", "lb", exit=(0.76, 1), entry=(0.5, 0), label="pages, API")
    d.edge("lb", "app", exit=(0.3, 1), entry=(0.9, 0))
    d.edge("app", "cache", exit=(1, 0.2), entry=(0, 0.5))
    d.edge("app", "db", exit=(1, 0.75), entry=(0, 0.5), label="SQL")
    d.edge("app", "mq", exit=(335 / 440, 1), entry=(0.5, 0), kind="async", label="order placed")
    d.edge("mq", "workers", exit=(0, 0.5), entry=(1, 0.5), kind="async")
    d.edge("app", "bank", exit=(0, 0.8), entry=(0.06, 0), via=[(27, 390), (27, 566), (55, 566)])
    d.edge("workers", "carrier", exit=(0.5, 1), entry=(0.3, 0), via=[(140, 540), (494, 540)])
    d.legend(740)
    return d


def retail_2026():
    d = Diagram("retail-2026-cloud-native", 760, 860, "The same shop in 2026: cloud-native, AI optional (illustration)")
    era_skeleton(d, "Kubernetes cluster: one service per capability, each owns its data")
    d.node("cust", "client", 35, 74, 690, 50, "Next.js frontend", "web and mobile, server-rendered pages")
    d.node("cdn", "network", 35, 180, 330, 56, "CDN", "static assets, edge cache")
    d.node("gw", "network", 395, 180, 330, 56, "API gateway", "auth, rate limits, routing")
    cols = [35, 210, 385, 560]
    for (key, title, line), x in zip([("users", "Users", "accounts, sessions"), ("cat", "Catalogue", "products, search"),
                                      ("cart", "Cart", "carts"), ("orders", "Orders", "checkout, status")], cols):
        d.node(key, "service", x, 296, 150, 56, title, line)
    for (key, title, line, kind), x in zip([("pay", "Payments", "provider calls", "service"),
                                            ("inv", "Inventory", "stock, reservations", "service"),
                                            ("ship", "Shipping", "rates, labels", "service"),
                                            ("ai", "AI assistant", "read-only, opt-in", "optional")], cols):
        d.node(key, kind, x, 364, 150, 56, title, line)
    d.node("pg", "data", 35, 440, 230, 84, "PostgreSQL", "users, orders, payments, stock", shape="db")
    d.node("mongo", "data", 280, 440, 120, 84, "MongoDB", "catalogue", shape="db")
    d.node("redis", "data", 415, 440, 120, 84, "Redis", "carts, cache")
    d.node("kafka", "messaging", 570, 440, 155, 84, "Kafka", "order events", shape="queue")
    d.node("bank", "external", 35, 576, 210, 52, "Payment provider", "cards, UPI, wallets")
    d.node("carrier", "external", 275, 576, 210, 52, "Carrier APIs", "rates, labels, tracking")
    d.node("llm", "optional", 515, 576, 210, 52, "LLM provider", "only if the assistant is on")
    d.zone("z-ops", "Operations", 20, 664, 720, 96)
    d.node("gitops", "ops", 35, 692, 330, 56, "GitOps (Argo CD)", "Git is the source of truth")
    d.node("otel", "ops", 395, 692, 330, 56, "OpenTelemetry", "traces, metrics, logs to one backend")
    d.edge("cust", "cdn", exit=(0.24, 1), entry=(0.5, 0), label="static files")
    d.edge("cust", "gw", exit=(0.76, 1), entry=(0.5, 0), label="API calls")
    d.edge("gw", "z-app", exit=(0.5, 1), entry=(540 / 720, 0), label="HTTPS")
    d.edge("orders", "kafka", exit=(0, 0.8), entry=(0, 0.5), via=[(547, 341), (547, 482)], kind="async")
    d.edge("pay", "bank", exit=(0, 0.5), entry=(0.1, 0), via=[(27, 392), (27, 566), (56, 566)])
    d.edge("ship", "carrier", exit=(22 / 150, 1), entry=(132 / 210, 0))
    d.edge("ai", "llm", exit=(1, 0.5), entry=(0.9, 0), via=[(732, 392), (732, 566), (704, 566)])
    d.edge("gitops", "z-app", exit=(225 / 330, 0), entry=(240 / 720, 1), kind="control")
    d.edge("z-app", "otel", exit=(480 / 720, 1), entry=(105 / 330, 0), kind="control")
    d.legend(780)
    return d


def roboshop_ai():
    d = Diagram("roboshop-ai-on-mk4", 860, 960, "RoboShop AI as deployed on mk4 (namespace roboshop-ai), 8 November 2026")
    d.zone("z-out", "Outside the cluster", 20, 48, 820, 96)
    d.node("browser", "client", 35, 76, 250, 56, "Browser", "storefront + Moks widget")
    d.node("model", "optional", 305, 76, 250, 56, "Model provider", "Bedrock or Ollama: none set")
    d.node("mcpc", "optional", 575, 76, 250, 56, "MCP client", "Claude, an IDE or a script")
    d.zone("z-ns", "mk4: roboshop-ai", 20, 164, 820, 586, "cluster")
    d.node("traefik", "network", 35, 194, 250, 56, "Traefik ingress", "/roboshop, prefix stripped")
    d.node("web", "network", 35, 272, 250, 72, "web (NGINX)", "static storefront", "proxies /api/* and /moks/*")
    d.node("moks", "ai", 305, 272, 250, 72, "moks", "widget + 3-node LangGraph", "reads catalogue, no writes")
    d.node("mcp", "ai", 575, 272, 250, 72, "mcp-server (FastMCP)", "ClusterIP + NetworkPolicy", "no public route")
    d.node("gw", "service", 35, 370, 790, 62, "ai-gateway (FastAPI)",
           "public API, authorization, server-side prices and stock, chat history, order ledger + outbox")
    svc = [("user", "user", "Python", "MongoDB"), ("cat", "catalogue", "Node.js", "MongoDB reads"),
           ("cart", "cart", "Python", "Redis"), ("ship", "shipping", "Spring Boot", "PostgreSQL"),
           ("pay", "payment", "Node.js", "Razorpay API"), ("cur", "currency", "Go", "ECB rates")]
    xs = [35 + round(i * 134.4) for i in range(6)]
    for (key, title, lang, uses), x in zip(svc, xs):
        d.node(f"s-{key}", "service", x, 456, 118, 66, title, lang, uses)
        d.edge("gw", f"s-{key}", exit=((x + 59 - 35) / 790, 1), entry=(0.5, 0))
    d.node("mongo", "data", 35, 546, 252, 80, "MongoDB", "products, users, chats", shape="db")
    d.node("redis", "data", xs[2], 546, 118, 80, "Redis", "carts")
    d.node("pg", "data", xs[3], 546, 118, 80, "PostgreSQL", "shipping-db", shape="db")
    d.edge("s-user", "mongo", exit=(0.5, 1), entry=(59 / 252, 0))
    d.edge("s-cat", "mongo", exit=(0.5, 1), entry=((xs[1] + 59 - 35) / 252, 0))
    d.edge("s-cart", "redis", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("s-ship", "pg", exit=(0.5, 1), entry=(0.5, 0))
    d.node("ledger", "data", 35, 652, 125, 80, "Order ledger", "JSON file,", "one writer", shape="db")
    d.node("rabbit", "messaging", 172, 652, 125, 80, "RabbitMQ", "order queues", shape="queue")
    d.node("bridge", "service", 309, 652, 125, 80, "kafka-bridge", "Python", "relays orders")
    d.node("kafka", "messaging", 446, 652, 115, 80, "Kafka", "analytics", shape="queue")
    d.edge("gw", "ledger", exit=(0, 0.5), entry=(0, 0.5), via=[(27, 401), (27, 692)])
    d.edge("ledger", "rabbit", exit=(1, 0.5), entry=(0, 0.5), kind="async")
    d.edge("rabbit", "bridge", exit=(1, 0.5), entry=(0, 0.5), kind="async")
    d.edge("bridge", "kafka", exit=(1, 0.5), entry=(0, 0.5), kind="async")
    d.edge("rabbit", "s-ship", exit=(0.5, 0), entry=(1, 0.5), via=[(234, 638), (565, 638), (565, 489)], kind="async",
           label="paid orders", t=-0.2)
    d.edge("browser", "traefik", exit=(0.5, 1), entry=(0.5, 0), label="HTTPS")
    d.edge("traefik", "web", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("web", "gw", exit=(0.5, 1), entry=(125 / 790, 0), label="/api/*")
    d.edge("web", "moks", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("moks", "gw", exit=(0.35, 1), entry=((392.5 - 35) / 790, 0), label="/api/chat")
    d.edge("gw", "moks", exit=((470 - 35) / 790, 0), entry=(165 / 250, 1), label="/internal/chat")
    d.edge("moks", "model", exit=(0.5, 0), entry=(0.5, 1), label="only if configured")
    d.edge("mcpc", "mcp", exit=(0.5, 1), entry=(0.5, 0), label="POST /mcp (no route today)")
    d.edge("mcp", "gw", exit=(0.5, 1), entry=((700 - 35) / 790, 0), label="caller's session")
    d.zone("z-ext", "Outside services", 20, 766, 820, 74)
    d.node("argo", "ops", 35, 790, 500, 42, "Argo CD (manual sync) + Harbor images")
    d.node("rzp", "external", xs[4], 790, 118, 42, "Razorpay")
    d.node("ecb", "external", xs[5], 790, 118, 42, "ECB feed")
    d.edge("s-pay", "rzp", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("s-cur", "ecb", exit=(0.5, 1), entry=(0.5, 0), label="hourly")
    d.edge("argo", "z-ns", exit=(0.85, 0), entry=((460 - 20) / 820, 1), kind="control", label="sync")
    d.text("facts", 20, 852, 820, 36, "Boxes in the services row are the *-service Deployments. Every Deployment runs one replica. Tracing code is present, but OTEL_SDK_DISABLED=true "
           "on mk4. Checked against roboshop-ai 02a4478 and the live cluster.", size=11)
    d.legend(894)
    return d


FIGURES = [client_server_1990s, three_tier_web, cloud_native_microservices, timeline, ai_native_architecture,
           retail_1992, retail_2012, retail_2026, roboshop_ai]


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
