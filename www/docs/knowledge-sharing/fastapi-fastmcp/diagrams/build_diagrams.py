#!/usr/bin/env python3
"""Figures for the FastAPI and FastMCP article: one editable .drawio file per figure and a matching SVG.

Reuses the layout, palette and draw.io writer of the RoboShop AI series, so the figures look alike and
the colours keep their meaning. Run from www/. The SVGs are rendered here, not exported by draw.io.
"""
import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[3] / "public" / "images" / "fastapi-fastmcp"
spec = importlib.util.spec_from_file_location("series_diagrams", HERE.parents[1] / "roboshop-ai" / "diagrams" / "build_diagrams.py")
series = importlib.util.module_from_spec(spec)
sys.modules["series_diagrams"] = series
spec.loader.exec_module(series)
Page, Sequence = series.Page, series.Sequence


def overview():
    p = Page("fastapi-fastmcp-overview", "Overview", 620, 716, "Where FastAPI and FastMCP run across RoboShop AI and MOKS",
             "Two projects use these packages, in four services. In RoboShop AI, ai-gateway uses FastAPI and mcp-server uses FastMCP, and mcp-server calls "
             "ai-gateway over HTTP. The moks shopping assistant uses Waitress and the domain services use neither package. In the MOKS portal, moks-api and "
             "moks-terminal use FastAPI, and the worker has no HTTP API. No MOKS component uses MCP.")
    p.zone("Outside the clusters", 15, 12, 590, 92)
    p.zone("RoboShop AI: FastAPI and FastMCP, in separate services", 15, 116, 590, 254, "br")
    p.zone("MOKS portal: FastAPI only, no MCP", 15, 382, 590, 322)
    p.node("browser", "browser", 30, 36, 170, 56, "Browser", "storefront, MOKS UI")
    p.node("client", "external", 420, 36, 170, 56, "MCP host and client", "not in my repositories")
    p.node("gateway", "gateway", 30, 148, 200, 72, "ai-gateway", "FastAPI 0.159.1", "Uvicorn, port 3000")
    p.node("mcp", "mcp", 400, 148, 190, 72, "mcp-server", "FastMCP 4.1.3", "Uvicorn, port 4107")
    p.node("shop", "absent", 30, 276, 200, 72, "moks assistant", "Waitress, WSGI", "neither package")
    p.node("services", "absent", 250, 276, 340, 72, "Domain services", "Python, Node.js, Go and Java", "neither package")
    p.node("api", "gateway", 30, 414, 270, 72, "moks-api", "FastAPI 0.162.0, Uvicorn", "REST and Server-Sent Events")
    p.node("terminal", "gateway", 320, 414, 270, 72, "moks-terminal", "FastAPI 0.162.0, Uvicorn", "REST and WebSocket")
    p.node("pg", "store", 30, 520, 270, 60, "PostgreSQL", "state, events and the job queue")
    p.node("worker", "absent", 320, 520, 270, 60, "moks worker", "claims jobs, typed tools, no HTTP")
    p.node("live", "external", 320, 626, 270, 60, "Live systems", "Kubernetes, Prometheus, Loki")
    p.edge("browser", "gateway", label="HTTPS via web", a_at=0.3, b_at=0.255, dx=46)
    p.edge("client", "mcp", label="POST /mcp, or stdio", b_at=0.553, dx=-58)
    p.edge("mcp", "gateway", a_side="l", b_side="r", label="HTTP with the\ncaller's session", dy=-26)
    p.edge("gateway", "shop", label="/internal/chat", dx=46)
    p.edge("gateway", "services", a_at=0.9, b_at=0.2, label="HTTP", dx=24)
    p.edge("browser", "api", a_side="l", b_side="l", via=[(8, 64), (8, 450)])
    p.edge("api", "pg", label="short sessions", dx=52)
    p.edge("worker", "pg", a_side="l", b_side="r")
    p.edge("worker", "live", label="read and allowlisted writes", dx=0)
    return p


def request_sequence():
    p = Page("fastapi-request-sequence", "FastAPI request", 620, 690, "FastAPI request sequence for a MOKS investigation",
             "The browser posts an investigation with its session cookie and CSRF token. moks-api loads the session, validates the body, checks the namespace "
             "scope and commits a queued row and audit record before answering 201. The browser opens a Server-Sent Events stream. A separate worker claims the "
             "row with SKIP LOCKED, writes events and the API streams them from PostgreSQL until the investigation ends.")
    s = Sequence(p, [("b", "browser", "Browser", "React UI"), ("a", "gateway", "moks-api", "FastAPI"), ("d", "store", "PostgreSQL", ""), ("w", "absent", "moks worker", "no HTTP")], bottom=674)
    s.message(114, "b", "a", "POST /investigations\ncookie, x-csrf-token", kind="write")
    s.self_note(124, "a", "Dependencies\nget_auth: 401, CSRF 403\nCreateIn: 422 if invalid", 58, 196)
    s.self_note(186, "a", "Policy\nrequire(), effective_scope()\n403 and an audit record", 58, 196)
    s.message(282, "a", "d", "INSERT queued row,\nevent 0 and audit", kind="write")
    s.message(314, "d", "a", "commit, before the response", kind="dashed")
    s.message(346, "a", "b", "201 with the investigation id", kind="dashed")
    s.message(382, "b", "a", "GET /investigations/{id}/events")
    s.message(422, "w", "d", "claim: SKIP LOCKED", kind="write")
    s.self_note(434, "w", "Runs the graph\nToolExecutor to live systems", 46, 190, "absent")
    s.message(506, "w", "d", "INSERT events", kind="write")
    s.message(546, "a", "d", "poll new events, every 0.5 s")
    s.message(586, "d", "a", "rows after the cursor", kind="dashed")
    s.message(626, "a", "b", "SSE events, then event: end", kind="dashed")
    s.message(660, "b", "a", "reconnect with Last-Event-ID", kind="dashed", number=False)
    return p


def mcp_sequence():
    p = Page("fastmcp-tool-call-sequence", "MCP tool call", 620, 760, "MCP tool call sequence through FastMCP",
             "On the left, outside the cluster, a host with its model and an MCP client. On the right, inside the cluster, mcp-server and ai-gateway. The client lists tools "
             "and mcp-server verifies the session and returns the tools for that role. The model picks search_products, a read that may be retried once. It then picks "
             "update_cart, a write that is never retried. ai-gateway authorizes both calls again, and the session is verified on every request with no cache.")
    p.zone("Trust boundary: the user's AI application", 15, 8, 296, 744, "br")
    p.zone("Trust boundary: cluster, namespace roboshop-ai", 314, 8, 291, 744, "br")
    s = Sequence(p, [("h", "external", "Host and model", "not in repo"), ("c", "external", "MCP client", "in the host"), ("m", "mcp", "mcp-server", "FastMCP"), ("g", "gateway", "ai-gateway", "FastAPI")], top=20, bottom=724)
    s.message(106, "c", "m", "tools/list, Bearer session")
    p.node("guards", "mcp", 322, 118, 180, 28, "Host, Origin, 256 KiB")
    s.message(186, "m", "g", "GET /api/auth/me")
    s.message(220, "g", "m", "id and role", kind="dashed")
    s.message(254, "m", "c", "8 tools for a customer", kind="dashed")
    s.message(288, "c", "h", "schemas", kind="dashed")
    s.message(328, "h", "c", "search_products")
    s.message(368, "c", "m", "tools/call, read")
    s.message(408, "m", "g", "GET /api/recommendations")
    s.message(442, "g", "m", "products", kind="dashed")
    s.message(476, "m", "c", "structuredContent", kind="dashed")
    s.message(516, "h", "c", "update_cart", kind="write")
    s.message(556, "c", "m", "tools/call, write", kind="write")
    p.node("limits", "mcp", 322, 568, 180, 28, "Role, schema, limits")
    s.message(636, "m", "g", "POST /api/cart, no retry", kind="write")
    s.message(670, "g", "m", "cart, or a refusal", kind="dashed")
    s.message(704, "m", "c", "result, or isError", kind="dashed")
    return p


def integration():
    p = Page("fastapi-fastmcp-integration", "Integration", 620, 690, "How FastMCP and FastAPI connect in RoboShop AI",
             "mcp-server and ai-gateway are separate pods with separate ASGI applications. An external client calls POST /mcp, handled by HTTPTracing, the FastMCP "
             "http_app and GatewayTool. GatewayClient calls ai-gateway over plain HTTP with the caller's rs_auth cookie, an origin header on writes and trace headers. "
             "A browser reaches the same FastAPI dispatch route. Gateway.handle makes the authorization decision for both paths, then calls the domain services.")
    p.zone("Outside the cluster", 15, 12, 590, 92)
    p.zone("Pod ai-gateway: FastAPI", 15, 116, 285, 450, "br")
    p.zone("Pod mcp-server: FastMCP, no FastAPI", 320, 116, 285, 450, "br")
    p.node("browser", "browser", 40, 36, 235, 56, "Browser", "cookie rs_auth")
    p.node("client", "external", 345, 36, 235, 56, "MCP client", "Bearer session")
    p.node("dispatch", "gateway", 40, 240, 235, 66, "dispatch()", "body limit, 8 worker slots")
    p.node("handle", "reject", 40, 366, 235, 76, "Gateway.handle", "authorization boundary", "session, role, ownership")
    p.node("asgi", "mcp", 345, 140, 235, 66, "HTTPTracing + http_app", "Host, Origin, Bearer, 256 KiB")
    p.node("tool", "mcp", 345, 252, 235, 66, "GatewayTool.run", "schema, role, rate, deadline")
    p.node("http", "mcp", 345, 364, 235, 66, "GatewayClient", "allowlisted headers only")
    p.node("spec", "mcp", 345, 476, 235, 66, "ToolSpec catalogue", "request and output shaping")
    p.node("domain", "service", 40, 600, 540, 66, "Domain services", "user, catalogue, cart, payment, shipping")
    p.edge("browser", "dispatch", label="HTTPS via web", dx=48, t=-0.2)
    p.edge("client", "asgi", label="POST /mcp")
    p.edge("asgi", "tool")
    p.edge("tool", "http")
    p.edge("tool", "spec", a_side="r", b_side="r", a_at=0.7, b_at=0.5, via=[(598, 298), (598, 509)], kind="dashed")
    p.edge("http", "dispatch", a_side="l", b_side="r", kind="write", via=[(310, 397), (310, 273)], label="plain HTTP", t=-0.5, dy=-36, dx=2)
    p.edge("dispatch", "handle", label="thread pool", dx=42)
    p.edge("handle", "domain", a_at=0.2, b_at=0.087, label="internal HTTP", dx=48, t=-0.5)
    p.note(345, 438, "No mount, no shared process", 12, "#475569", True)
    return p


FILES = {
    "fastapi-fastmcp-overview": overview,
    "fastapi-request-sequence": request_sequence,
    "fastmcp-tool-call-sequence": mcp_sequence,
    "fastapi-fastmcp-integration": integration,
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    built = []
    for name, make in FILES.items():
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
        (HERE / f"{name}.drawio").write_bytes(ET.tostring(mxfile, encoding="utf-8", xml_declaration=False))
        (OUT / f"{page.figure}.svg").write_text(series.page_svg(page), encoding="utf-8")
        built.append((page.figure, page.w, page.h))
    (HERE / "figures.txt").write_text("".join(f"{f} {w} {h}\n" for f, w, h in built), encoding="utf-8")
    print(f"{len(built)} .drawio files and SVGs")


if __name__ == "__main__":
    main()
