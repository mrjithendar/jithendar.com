#!/usr/bin/env python3
"""Figures for content/blog/moks-sre-github-actions-ci-cd-pipeline.mdx:

    python3 docs/knowledge-sharing/moks-ci-pipeline/diagrams/build_diagrams.py   # writes the .drawio files
    bash docs/knowledge-sharing/moks-ci-pipeline/diagrams/export.sh              # draw.io CLI → public/images/moks-ci-pipeline/

After editing a .drawio file by hand, run only export.sh, or this script overwrites the edits.

Sources (20 November 2026): mrjithendar/moks-sre cd2f58f .github/workflows/ci.yml (unchanged since 7e09449),
docs/RELEASES.md, deploy/argocd/hetzner/; job timings from the GitHub Actions API for the 22 completed master runs
of 16-20 November 2026 (see ../README.md).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio_model import KINDS, Diagram  # noqa: E402

HERE = Path(__file__).resolve().parent
NOTE = 11


def job_graph():
    d = Diagram("moks-ci-job-graph", 1040, 760, "The moks workflow: 12 jobs and the needs between them (ci.yml on master)")
    d.node("trig", "client", 20, 262, 125, 90, "Trigger", "push to master", "pull request", "manual run")

    d.zone("z-a", "Every pull request and push", 180, 50, 290, 568, "cluster")
    a = dict(x=200, w=250, h=74)
    ys = (85, 173, 261, 349, 437, 525)
    d.node("check", "compute", a["x"], ys[0], a["w"], a["h"], "check  ·  7 min 56 s", "backend suite on pgvector 0.8.6",
           "frontend, Helm, Argo CD, Terraform")
    d.node("crewai", "compute", a["x"], ys[1], a["w"], a["h"], "crewai  ·  7 min 2 s", "the backend suite again on",
           "the CrewAI dependency set")
    d.node("rr", "compute", a["x"], ys[2], a["w"], a["h"], "reranker  ·  1 min", "reranker service tests",
           "(also covers the embedder)")
    d.node("image", "external", a["x"], ys[3], a["w"], a["h"], "image  ·  1 min", "moks image on arm64:",
           "build, smoke test, Trivy scan")
    d.node("e2e", "external", a["x"], ys[4], a["w"], a["h"], "e2e  ·  2 min 40 s", "chart on kind: investigate",
           "and remediate a lab incident")
    d.node("term", "external", a["x"], ys[5], a["w"], a["h"], "terminal (2 runners) · 3 min", "amd64 and arm64 runners:",
           "scan + isolation test on kind")

    d.zone("z-b", "Pushes to master only", 500, 50, 290, 480, "ai")
    b = dict(x=520, w=250, h=74)
    d.node("rel", "ops", b["x"], ys[0], b["w"], b["h"], "release  ·  1 min", "build, smoke test, push", "moks:latest")
    d.node("relc", "ops", b["x"], ys[1], b["w"], b["h"], "release-crewai  ·  2 min", "MOKS_CREWAI=true build,",
           "push moks-crewai:latest")
    d.node("rri", "ops", b["x"], ys[2], b["w"], b["h"], "reranker-image  ·  2 min", "offline smoke test, push",
           "moks-reranker:latest")
    d.node("emb", "ops", b["x"], ys[3], b["w"], b["h"], "embedder-image  ·  2 min", "real /embed, unit length,",
           "push moks-embedder:latest")
    d.node("ti", "ops", b["x"], ys[4], b["w"], b["h"], "terminal-image  ·  2 min", "needs nothing: arm64 + amd64,",
           "push moks-terminal:latest")

    d.zone("z-c", "Only if MK4_DEPLOY", 815, 50, 205, 200, "risk")
    d.node("dep", "optional", 830, 85, 180, 90, "deploy", "needs release (success)", "and release-crewai (any)",
           "Argo CD sync + restart", "skipped in all 22 runs")
    d.text("harbor", 815, 270, 205, 120,
           "<b>Every push job</b> logs in to Harbor (registry.jithendar.com, project jithendar) with a robot account, "
           "pushes one tag, latest, and uploads a release record: commit, digest, run.", size=NOTE)

    d.edge("trig", "z-a", kind="sync", exit=(1, 0.5), entry=(0, 0.42))
    d.edge("check", "rel", kind="needs", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("check", "relc", kind="needs", exit=(1, 0.8), entry=(0, 0.3), via=[(485, 144), (485, 195)])
    d.edge("crewai", "relc", kind="needs", exit=(1, 0.7), entry=(0, 0.7))
    d.edge("rr", "rri", kind="needs", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("rr", "emb", kind="needs", exit=(1, 0.8), entry=(0, 0.5), via=[(485, 320), (485, 386)])
    d.edge("rel", "dep", kind="needs", exit=(1, 0.3), entry=(0, 0.3))
    d.edge("relc", "dep", kind="after", exit=(1, 0.5), entry=(0.5, 1), via=[(920, 210)])

    d.text("gap", 500, 548, 520, 70,
           "<b>Nothing waits on image, e2e or terminal.</b> On master they report and stop nothing: run #245 released "
           "with both terminal jobs red, and run #257 pushed moks-terminal:latest while the terminal scan had failed "
           "on a HIGH CVE in the same image.", size=NOTE)
    d.text("src", 20, 640, 1000, 34,
           "Times are medians of the 14 successful master runs, 16 to 20 November 2026 (embedder-image: 3 runs). "
           "Source: mrjithendar/moks-sre .github/workflows/ci.yml and the GitHub Actions API.", size=NOTE)
    d.legend(684, labels={"compute": "Gates a release", "external": "Reports only", "ops": "Builds and pushes",
                          "optional": "Skipped", "client": "Trigger"})
    return d


# Run #279, commit 7e09449, 20 November 2026 10:25 UTC: seconds from the first job's creation.
RUN_279 = (
    ("check", 3, 576, "compute", True),
    ("crewai", 3, 423, "compute", False),
    ("reranker", 3, 66, "compute", False),
    ("image", 5, 69, "external", False),
    ("e2e", 3, 140, "external", False),
    ("terminal (ubuntu-24.04)", 3, 210, "external", False),
    ("terminal (ubuntu-24.04-arm)", 5, 202, "external", False),
    ("terminal-image", 5, 131, "ops", False),
    ("reranker-image", 71, 193, "ops", False),
    ("embedder-image", 71, 195, "ops", False),
    ("release", 581, 641, "ops", False),
    ("release-crewai", 581, 708, "ops", True),
)


def fmt(s):
    m, s = divmod(int(s), 60)
    return f"{m}:{s:02d}"


def run_timeline():
    d = Diagram("moks-ci-run-timeline", 1000, 640,
                "One real run: #279, commit 7e09449, 20 November 2026 (11 min 48 s from push to last job)")
    x0, scale, top, row = 280, 0.95, 70, 26
    end_axis = 720
    for m in range(0, end_axis // 60 + 1):
        x = x0 + m * 60 * scale
        d.rect(f"grid{m}", x, top - 4, 1, row * (len(RUN_279) + 1) + 4, "#e2e8f0")
        d.text(f"tick{m}", x - 20, top + row * (len(RUN_279) + 1) + 6, 40, 16, f"{m} min" if m else "0",
               size=NOTE, align="center")
    for i, (name, s, e, kind, critical) in enumerate(RUN_279):
        y = top + i * row
        fill, stroke, _ = KINDS[kind]
        d.text(f"lbl{i}", 20, y + 4, 250, 18, f"{name}  ·  {fmt(e - s)}", size=12, color="#0f172a")
        d.rect(f"bar{i}", x0 + s * scale, y + 5, max((e - s) * scale, 3), 16, fill,
               "#b91c1c;strokeWidth=2.5" if critical else stroke)
    y = top + len(RUN_279) * row
    d.text("lbl-dep", 20, y + 4, 250, 18, "deploy  ·  skipped", size=12, color="#64748b")
    d.text("dep-x", x0 + 709 * scale - 70, y + 4, 78, 18, "skipped ▸", size=NOTE, color="#64748b", align="right")

    ny = top + row * (len(RUN_279) + 1) + 34
    d.text("n1", 20, ny, 960, 54,
           "<b>Critical path (red outline):</b> check 9:33, of which the backend tests are 7:43, then release-crewai "
           "2:07. Both release jobs started at 9:41, five seconds after check passed; "
           "release-crewai also needed crewai, which had finished at 7:03.", size=12)
    d.text("n2", 20, ny + 60, 960, 54,
           "<b>Parallelism:</b> the 13 jobs used 37 min of runner time (2,220 s) in 11 min 48 s of wall clock, "
           "about 3.1 times faster than one after another. Everything except check, crewai and the two release jobs "
           "had finished by 3:30.", size=12)
    d.legend(ny + 124, extra_kinds=("compute", "external", "ops"),
             labels={"compute": "Gates a release", "external": "Reports only", "ops": "Builds and pushes"})
    return d


def release_deploy():
    d = Diagram("moks-ci-release-deploy", 1040, 700, "From a green check to running pods: release, Harbor and the deploy job")
    d.zone("z-gh", "release jobs on ubuntu-24.04-arm", 20, 50, 300, 440, "cluster")
    d.node("b", "compute", 40, 85, 260, 74, "docker build", "--build-arg GIT_COMMIT=<sha>",
           "release-crewai adds MOKS_CREWAI")
    d.node("s", "compute", 40, 180, 260, 90, "Smoke test", "/healthz, then /moks/ serves the UI",
           "/moks/api/health shows the sha", "reranker, embedder: --network none")
    d.node("p", "ops", 40, 291, 260, 58, "docker push …:latest", "one tag; the commit is inside")
    d.node("r", "data", 40, 370, 260, 100, "Release record artifact", "component, commit, digest, run",
           "(+ model for reranker, embedder)", "kept 400 days", shape="db")
    d.edge("b", "s", kind="sync", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("s", "p", kind="sync", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("p", "r", kind="sync", exit=(0.5, 1), entry=(0.5, 0))

    d.node("h", "data", 370, 215, 270, 136, "Harbor", "registry.jithendar.com/jithendar", "moks, moks-crewai, moks-reranker,",
           "moks-embedder, moks-terminal", "robot account: this project only", "keeps the last 10 builds each", shape="db")
    d.edge("p", "h", kind="push", exit=(1, 0.5), entry=(0, 0.6))

    d.zone("z-dep", "deploy job (MK4_DEPLOY unset: skipped)", 690, 50, 330, 440, "risk")
    d.node("c1", "optional", 710, 85, 290, 58, "argocd CLI v3.5.6", "SHA-256 checked before it runs")
    d.node("c2", "optional", 710, 160, 290, 74, "Token: project role moks/ci", "get, sync, restart; nothing else",
           "+ Cloudflare Access headers")
    d.node("c3", "optional", 710, 251, 290, 74, "Sync 9 Applications in order", "foundation, database, api, worker, …",
           "never --prune")
    d.node("c4", "optional", 710, 342, 290, 58, "Restart Deployments", "worker, api, executor, terminal")
    d.node("c5", "optional", 710, 417, 290, 58, "Verify the commit", "/moks/api/health, 30 × 10 s")
    for a, b in (("c1", "c2"), ("c2", "c3"), ("c3", "c4"), ("c4", "c5")):
        d.edge(a, b, kind="sync", exit=(0.5, 1), entry=(0.5, 0))

    d.zone("z-mk4", "mk4: k3s on three Hetzner cax21 (arm64), namespace moks-sre", 20, 520, 1000, 110, "plain")
    d.node("argo", "ops", 710, 550, 290, 64, "Argo CD (jithendar.com/argocd)", "auto-sync, selfHeal, no prune",
           "rolls pods when the chart changes")
    d.node("pods", "compute", 370, 550, 270, 64, "MOKS pods", "image :latest, pull Always")
    d.text("today", 40, 548, 300, 72,
           "<b>Today:</b> Argo CD applies chart changes from Git by itself; a new image reaches the pods only on "
           "<i>kubectl rollout restart</i> (docs/RELEASES.md).", size=NOTE)
    d.edge("argo", "pods", kind="push", exit=(0, 0.5), entry=(1, 0.5))
    d.edge("h", "pods", "pull on restart", kind="sync", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("c5", "argo", "sync, restart", kind="push", exit=(0.5, 1), entry=(0.5, 0))
    d.legend(650, labels={"compute": "Runs code", "ops": "Delivery", "data": "Stored output",
                          "optional": "Not running (skipped)"})
    return d


def chart_image_race():
    d = Diagram("moks-ci-chart-image-race", 1040, 560,
                "19 November 2026 (UTC): the chart arrived before its image, and nothing restarted the pods")
    cols = (150, 330, 510, 690, 870)
    times = ("10:53", "11:03", "11:31", "11:33", "11:40")
    lanes = (("GitHub Actions", 80), ("Harbor moks:latest", 200), ("mk4: Argo CD, pods", 300))
    for name, y in lanes:
        d.text(f"lane-{y}", 20, y + 20, 120, 40, f"<b>{name}</b>", size=12, color="#0f172a")
        d.rect(f"lane-line-{y}", 150, y + 90 if y == 80 else y + 85, 870, 1, "#e2e8f0")
    for i, (x, t) in enumerate(zip(cols, times)):
        d.text(f"t{i}", x, 50, 160, 20, f"<b>{t}</b>", size=13, color="#0f172a", align="center")
    d.node("ga1", "compute", cols[0], 80, 160, 74, "Run #221 starts", "Dependabot bump", "commit 5b1e709")
    d.node("ga2", "ops", cols[1], 80, 160, 74, "release pushes", "check passed;", "crewai failed")
    d.node("ga3", "compute", cols[2], 80, 160, 74, "#67 merged", "982dd05, run #225:", "check takes ~8 min")
    d.node("ga5", "ops", cols[4], 80, 150, 74, "release pushes", "moks:latest", "= 982dd05")
    d.node("h1", "data", cols[1], 200, 160, 64, "latest = 5b1e709", "until 11:40")
    d.node("h2", "data", cols[4], 200, 150, 64, "latest = 982dd05", "nobody pulls it")
    d.node("m1", "security", cols[3], 300, 160, 90, "Argo CD auto-sync", "#67's chart changed", "pod templates: pods",
           "pull latest = 5b1e709")
    d.node("m2", "optional", cols[4], 300, 150, 90, "Nothing restarts", "deploy is skipped;", "pods keep 5b1e709",
           "until a restart")
    d.marker(1, cols[3] + 160, 300)
    d.edge("ga1", "ga2", kind="sync", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("ga2", "h1", "push", kind="push", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("ga3", "m1", "Git poll", kind="push", exit=(0.5, 1), entry=(0.3, 0), via=[(590, 180), (738, 180)])
    d.edge("h1", "m1", "pull", kind="sync", exit=(1, 0.5), entry=(0, 0.3))
    d.edge("ga5", "h2", "push", kind="push", exit=(0.5, 1), entry=(0.5, 0))
    d.text("res", 20, 410, 1000, 70,
           "<b>Result:</b> new chart, old code. Knowledge → Rebuild index failed with \"pgvector is not installed\", "
           "because 5b1e709 has no enable_vector(), and bge-m3 got no traffic. It was found the next day. With "
           "MK4_DEPLOY true, the deploy job would have synced and restarted onto 982dd05 at about 11:40.", size=12)
    d.legend(490, labels={"compute": "Commit and CI run", "ops": "Release job", "data": "Registry tag",
                          "security": "Where it went wrong", "optional": "What did not happen"}, failure=True)
    return d


FIGURES = (job_graph, run_timeline, release_deploy, chart_image_race)

if __name__ == "__main__":
    names = []
    for build in FIGURES:
        d = build()
        (HERE / f"{d.name}.drawio").write_text(d.xml() + "\n")
        names.append(d.name)
        print(f"wrote {d.name}.drawio ({d.w}x{d.h})")
    (HERE / "figures.txt").write_text("\n".join(names) + "\n")
