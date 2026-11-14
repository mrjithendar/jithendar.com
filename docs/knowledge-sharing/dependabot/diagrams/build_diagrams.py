#!/usr/bin/env python3
"""Figure for the Dependabot article: an editable .drawio file and a matching SVG.

Reuses the layout, palette and draw.io writer of the RoboShop AI series. Run from www/. The SVG is rendered here,
not exported by draw.io: if the .drawio file is edited by hand, re-export it from draw.io over the SVG.
Labels follow the .github/dependabot.yml files and GitHub settings of the five repositories on 2026-11-09.
"""
import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[3] / "public" / "images" / "dependabot"
spec = importlib.util.spec_from_file_location("series_diagrams", HERE.parents[1] / "roboshop-ai" / "diagrams" / "build_diagrams.py")
series = importlib.util.module_from_spec(spec)
sys.modules["series_diagrams"] = series
spec.loader.exec_module(series)
Page = series.Page


def flow():
    p = Page("dependabot-flow", "Dependabot flow", 900, 750,
             "How a dependency update travels from GitHub to a running system in my repositories",
             "Two things start Dependabot. A new advisory in the GitHub Advisory Database that matches the dependency graph "
             "raises a Dependabot alert. If a fixed version is reachable, Dependabot opens a security update PR for that one "
             "package, with no cooldown and no grouping; if the parent package pins the vulnerable range, the fix is made by "
             "hand with npm overrides or the alert is dismissed with a reason. The weekly schedule, Monday 06:00 New York time, "
             "starts a version update run that reads .github/dependabot.yml, skips releases younger than the 3-day cooldown and "
             "versions matched by ignore rules, and opens grouped PRs: family groups first, then one minor and patch group per "
             "directory, with each major version in its own PR. Every PR runs CI on its branch with a read-only token and no "
             "repository secrets. A failing PR gets an ignore rule and @dependabot recreate. A passing PR is reviewed by a "
             "person, because there is no auto-merge, and merging to master deploys: jithendar.com and MOKS release an image, "
             "Argo CD syncs miniKube, and tools applies Terraform.")
    p.zone("Triggers", 15, 12, 870, 108)
    p.zone("Dependabot", 15, 140, 870, 226)
    p.zone("Pull request on a Dependabot branch", 15, 386, 870, 212, "br")
    p.zone("Merge to master is a deploy", 15, 618, 870, 116, "br")

    p.node("adv", "external", 30, 36, 270, 76, "GitHub Advisory Database", "new advisory for a package",
           "in the dependency graph")
    p.node("sched", "external", 315, 36, 270, 76, "Weekly schedule", "Monday 06:00 America/New_York",
           "RoboShop AI: 09:00 Asia/Kolkata")
    p.node("cfg", "store", 600, 36, 270, 76, ".github/dependabot.yml", "one entry per ecosystem + directory",
           "groups, cooldown, ignore, labels")

    p.node("alert", "reject", 30, 164, 415, 76, "Dependabot alert",
           "Security tab: severity, runtime or development scope",
           "settings: alerts + security updates on in all five repos")
    p.node("run", "edge", 460, 164, 410, 76, "Version update run",
           "cooldown: skip releases younger than 3 days",
           "ignore: database majors, runtimes, known breaks")
    p.node("su", "service", 30, 262, 200, 92, "Security update PR", "one package, own PR",
           "no cooldown, not grouped", "same labels and prefix")
    p.node("manual", "absent", 245, 262, 200, 92, "No reachable fix", "parent pins the bad range",
           "npm overrides by hand", "or dismiss with a reason")
    p.node("groups", "edge", 460, 262, 410, 92, "Grouped version update PRs",
           "family groups first: opentelemetry, next-react",
           "then one minor + patch group per directory",
           "majors arrive one PR each")

    p.node("ci", "gateway", 30, 410, 840, 76, "CI on the Dependabot branch",
           "lint, typecheck, test, build · terraform fmt + validate · Helm and manifest checks",
           "read-only GITHUB_TOKEN, no repository secrets · pull requests from forks are skipped")
    p.node("review", "browser", 30, 506, 560, 76, "Human review (no auto-merge)",
           "lock-file diff, release notes, new transitive packages",
           "stateful images: check the node before merging")
    p.node("broken", "reject", 605, 506, 265, 76, "CI fails", "add an ignore rule with a reason",
           "then @dependabot recreate")

    p.node("site", "service", 30, 642, 200, 76, "jithendar.com", "image built and pushed", "./deploy.sh rolls it out")
    p.node("moks", "service", 243, 642, 200, 76, "moks", "image built and pushed", "MOKS pods restarted")
    p.node("mk", "service", 456, 642, 200, 76, "miniKube", "Argo CD auto-sync (selfHeal)", "Terraform apply on push")
    p.node("tools", "service", 670, 642, 200, 76, "tools", "push to master only", "terraform apply runs")

    p.edge("adv", "alert", b_at=(165 - 30) / 415, label="matches", dx=34)
    p.edge("sched", "run", a_at=(558 - 315) / 270, b_at=(558 - 460) / 410, label="starts", dx=26)
    p.edge("cfg", "run", b_at=(735 - 460) / 410, kind="dashed", label="reads", dx=24)
    p.edge("alert", "su", a_at=(130 - 30) / 415, label="fixed version exists", dx=68)
    p.edge("alert", "manual", a_at=(345 - 30) / 415, kind="dashed")
    p.edge("run", "groups")
    p.edge("su", "ci", b_at=(130 - 30) / 840)
    p.edge("manual", "ci", b_at=(345 - 30) / 840, kind="dashed", label="manual PR", dx=40)
    p.edge("groups", "ci", b_at=(665 - 30) / 840)
    p.edge("ci", "review", a_at=(310 - 30) / 840, label="green", dx=24)
    p.edge("ci", "broken", a_at=(737.5 - 30) / 840, kind="reject", label="red", dx=18)
    p.edge("broken", "groups", a_side="r", b_side="r", kind="dashed", via=[(880, 544), (880, 308)])
    p.edge("review", "site", a_at=(130 - 30) / 560, kind="write", label="merge", dx=26)
    p.edge("review", "moks", a_at=(343 - 30) / 560, kind="write")
    p.edge("review", "mk", a_at=(500 - 30) / 560, kind="write", via=[(500, 608), (556, 608)])
    p.edge("review", "tools", a_at=(575 - 30) / 560, kind="write", via=[(575, 608), (770, 608)])
    return p


FILES = {"dependabot-flow": flow}


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
