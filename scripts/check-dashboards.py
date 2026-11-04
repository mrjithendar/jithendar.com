#!/usr/bin/env python3
"""Static checks for the Grafana dashboards in grafana/ (run by .github/workflows/grafana-dashboards.yml).

  python3 scripts/check-dashboards.py

Checks that every JSON file is in grafana/kustomization.yaml (and the other way round), that uids and titles are
unique, that panels use only the data sources Grafana provisions (tools: deploy/minikube/observability/grafana/
values.yaml), that panel ids are unique and panels do not overlap, that every $variable a query uses is defined,
and that dashboard links point at dashboards that exist. Queries are not run: that needs the cluster.
Standard library only.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "grafana"
# uid → type, as provisioned by the grafana values in the tools repo.
DATASOURCES = {"roboshop-prometheus": "prometheus", "roboshop-loki": "loki", "jaeger": "jaeger"}
BUILTIN = {"__interval", "__interval_ms", "__range", "__range_s", "__range_ms", "__rate_interval", "__all",
           "__url_time_range", "__value", "__from", "__to", "__dashboard", "__name", "__field", "__series",
           "__data", "__auto", "__span", "__trace", "__org", "__user", "__timezone"}
VARIABLE = re.compile(r"\$\{(\w+)(?:[.:][^}]*)?\}|\$(\w+)|\[\[(\w+)(?::\w+)?\]\]")


def panels_of(dashboard):
    for panel in dashboard.get("panels", []):
        yield panel
        yield from panel.get("panels", [])  # collapsed rows


def query_texts(target):
    for key in ("expr", "query"):
        value = target.get(key)
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict) and isinstance(value.get("query"), str):
            yield value["query"]


def check(path, problems):
    name = path.name
    try:
        dashboard = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        problems.append(f"{name}: not valid JSON ({e})")
        return None
    uid, title = dashboard.get("uid"), dashboard.get("title")
    if not uid or not title:
        problems.append(f"{name}: uid and title are required")
    if dashboard.get("id") is not None:
        problems.append(f"{name}: id must be null (Grafana assigns it)")
    defined = {v["name"] for v in dashboard.get("templating", {}).get("list", [])}

    ids, cells = set(), {}
    for panel in panels_of(dashboard):
        pid, label = panel.get("id"), f"{name}: panel {panel.get('id')} {panel.get('title', '')!r}"
        if pid in ids:
            problems.append(f"{label}: duplicate panel id")
        ids.add(pid)
        pos = panel.get("gridPos") or {}
        if pos.get("x", 0) + pos.get("w", 0) > 24:
            problems.append(f"{label}: wider than the 24-column grid")
        if panel.get("type") != "row" or not panel.get("collapsed"):
            for x in range(pos.get("x", 0), pos.get("x", 0) + pos.get("w", 0)):
                for y in range(pos.get("y", 0), pos.get("y", 0) + pos.get("h", 0)):
                    if (x, y) in cells and cells[(x, y)] != pid:
                        problems.append(f"{label}: overlaps panel {cells[(x, y)]}")
                        break
                    cells[(x, y)] = pid
                else:
                    continue
                break
        sources = [panel.get("datasource")] + [t.get("datasource") for t in panel.get("targets", [])]
        for ds in filter(None, sources):
            if ds.get("uid") not in DATASOURCES or DATASOURCES[ds["uid"]] != ds.get("type"):
                problems.append(f"{label}: unknown data source {ds}")
        texts = [q for t in panel.get("targets", []) for q in query_texts(t)] + [panel.get("title", "")]
        for text in texts:
            for groups in VARIABLE.findall(text):
                var = next(g for g in groups if g)
                if var not in defined and var not in BUILTIN:
                    problems.append(f"{label}: uses ${var}, which the dashboard does not define")
    return uid, title, dashboard


def main() -> int:
    problems = []
    listed = set(re.findall(r"^\s*-\s+(\S+\.json)\s*$", (ROOT / "kustomization.yaml").read_text(), re.M))
    present = {p.name for p in ROOT.glob("*.json")}
    for missing in sorted(present - listed):
        problems.append(f"{missing}: not listed in grafana/kustomization.yaml, so Grafana never sees it")
    for missing in sorted(listed - present):
        problems.append(f"{missing}: listed in grafana/kustomization.yaml but missing")

    results = [r for p in sorted(ROOT.glob("*.json")) if (r := check(p, problems))]
    uids = [uid for uid, _, _ in results]
    titles = [title for _, title, _ in results]
    for dup in {u for u in uids if uids.count(u) > 1}:
        problems.append(f"uid {dup} is used by more than one dashboard")
    for dup in {t for t in titles if titles.count(t) > 1}:
        problems.append(f"title {dup!r} is used by more than one dashboard")
    for _, title, dashboard in results:
        for link in dashboard.get("links", []):
            m = re.match(r"^/grafana/d/([\w-]+)", link.get("url", ""))
            if m and m.group(1) not in uids:
                problems.append(f"{title}: link {link['url']} points at no dashboard here")

    for p in problems:
        print(f"::error::{p}")
    if problems:
        return 1
    print(f"{len(results)} dashboards OK: {', '.join(titles)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
