#!/usr/bin/env python3
"""Figure for the jithendar.com observability article: one editable .drawio file and a matching SVG.

Reuses the layout, palette and draw.io writer of the RoboShop AI series. Run from www/. The SVG is rendered here,
not exported by draw.io: if the .drawio file is edited by hand, re-export it from draw.io over the SVG.
Labels follow the 2026-11-04 review (jithendar.com www/, minikube/; tools deploy/minikube/observability).
"""
import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[3] / "public" / "images" / "jithendar-com-observability"
spec = importlib.util.spec_from_file_location("series_diagrams", HERE.parents[1] / "roboshop-ai" / "diagrams" / "build_diagrams.py")
series = importlib.util.module_from_spec(spec)
sys.modules["series_diagrams"] = series
spec.loader.exec_module(series)
Page = series.Page


def telemetry():
    p = Page("jithendar-com-telemetry-flow", "Telemetry flow", 620, 704, "Logs, traces and metrics of jithendar.com on the mk4 cluster",
             "A visitor reaches the Traefik ingress, which strips incoming trace headers and forwards to two Next.js pods in namespace jithendar. "
             "The pods send spans over OTLP/HTTP to the OpenTelemetry Collector, which removes URLs, SQL and exception text and forwards to Jaeger, "
             "which keeps the newest 5000 traces in memory. They write JSON log lines to stdout; Alloy reads them through the Kubernetes API, keeps "
             "only allowlisted fields and pushes logfmt lines with trace_id to Loki. Prometheus scrapes request and runtime metrics from port 9464. "
             "Grafana reads Prometheus and Loki and links a log line's trace_id to the Jaeger UI through a port-forward. The site sends traceparent "
             "only to the practice executor, whose audit lines carry the same trace_id.")
    p.zone("Internet and ingress", 15, 12, 590, 92)
    p.zone("Namespace jithendar", 15, 116, 590, 120)
    p.zone("Namespace observability", 15, 248, 280, 236, "br")
    p.zone("Namespace monitoring", 310, 248, 295, 444, "br")
    p.node("visitor", "browser", 30, 36, 170, 56, "Visitor", "browser or crawler, HTTPS")
    p.node("traefik", "edge", 225, 36, 365, 56, "Traefik ingress", "strips traceparent, tracestate, baggage")
    p.node("site", "gateway", 30, 140, 365, 84, "jithendar-com, 2 pods", "Next.js 16 + @vercel/otel", "JSON logs on stdout",
           "metrics on :9464 (cluster only)")
    p.node("exec", "service", 420, 140, 170, 84, "practice-executor", "FastAPI", "gets traceparent", "audit lines: trace_id")
    p.node("otel", "service", 30, 284, 250, 64, "OTel Collector 0.162", "receives OTLP/HTTP on :4318", "removes URLs, SQL, exception text")
    p.node("jaeger", "store", 30, 384, 250, 64, "Jaeger 2.22", "in memory, newest 5000 traces", "UI by port-forward only")
    p.node("alloy", "service", 325, 268, 265, 64, "Alloy", "reads pod stdout via the API", "keeps allowlisted fields only")
    p.node("loki", "store", 325, 360, 265, 64, "Loki", "logfmt lines, 7 days", "trace_id in the line, not a label")
    p.node("prom", "store", 325, 496, 265, 64, "Prometheus", "scrapes the pods on :9464", "alert rules, 7 days")
    p.node("grafana", "browser", 325, 592, 265, 64, "Grafana", "Overview and Logs dashboards", "trace_id opens Jaeger")
    p.edge("visitor", "traefik", a_side="r", b_side="l")
    p.edge("traefik", "site", a_at=0.2, b_at=0.734, label="x-request-id added by proxy", dx=96)
    p.edge("site", "exec", a_side="r", b_side="l")
    p.edge("site", "otel", a_at=0.342)
    p.edge("otel", "jaeger", label="filtered spans", dx=52)
    p.edge("site", "alloy", a_at=0.959, b_at=0.208)
    p.edge("exec", "alloy", b_at=0.679)
    p.edge("alloy", "loki")
    p.edge("site", "prom", a_at=0.745, b_side="l", via=[(302, 528)], kind="dashed")
    p.edge("prom", "grafana")
    p.edge("loki", "grafana", a_side="r", b_side="r", via=[(598, 388), (598, 624)])
    p.edge("grafana", "jaeger", a_side="l", b_side="b", via=[(155, 624)], kind="dashed", label="trace link", dy=-10, t=-0.5)
    return p


FILES = {"jithendar-com-telemetry-flow": telemetry}


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
