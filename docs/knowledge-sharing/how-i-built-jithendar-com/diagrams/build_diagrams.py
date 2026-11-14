#!/usr/bin/env python3
"""Figures for "How I Built jithendar.com: CrewAI Pipelines, Istio Service Mesh and Gateway, and EKS-Style Patterns".

    python3 sites/jithendar.com/docs/knowledge-sharing/how-i-built-jithendar-com/diagrams/build_diagrams.py   (from services/www/)
    bash sites/jithendar.com/docs/knowledge-sharing/how-i-built-jithendar-com/diagrams/export.sh

The first command writes one editable .drawio file per figure beside this script; the second has the draw.io desktop
CLI export each to public/images/how-i-built-jithendar-com/<name>.svg and .png. After editing a .drawio file by hand,
run only export.sh, or this script overwrites the edits.

Sources: kubernetes/*.yaml, kubernetes/kong/seo-agent-mcp.deck.yaml, .github/workflows/*.yml, services/seo-agent/app
(flows, crews, runs.py) and docs/seo/FLOWS.md, CREWS.md, COSTS.md (13 November 2026). Internal hostnames are left out.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio_model import Diagram  # noqa: E402

HERE = Path(__file__).resolve().parent


def platform():
    d = Diagram("platform-architecture", 960, 900, "jithendar.com on mk4: request path and content pipeline")
    d.node("visitor", "client", 35, 56, 260, 56, "Reader", "browser")
    d.node("dns", "external", 360, 56, 280, 56, "Cloudflare DNS", "DNS only, no proxying")
    d.zone("z-host", "In front of the cluster (Hetzner Cloud, Falkenstein)", 20, 132, 920, 92, corner="right")
    d.node("haproxy", "network", 35, 156, 400, 56, "Load balancer mk4-edge :80 / :443", "Hetzner LB11, TCP, adds the PROXY header")
    d.zone("z-cluster", "k3s cluster mk4: 1 control plane, 3 Arm workers", 20, 244, 920, 494, "cluster", corner="right")
    d.node("gw", "network", 35, 274, 420, 74, "Istio ingress gateway", "wildcard TLS, www → apex, HTTP → HTTPS",
           "root VirtualService (cluster repo)")
    d.node("mcp", "optional", 505, 274, 420, 74, "/mcp/* route: not applied", "Kong decK file, or an Istio match",
           "documented, waiting for a person")
    d.zone("z-ns", "namespace jithendar: STRICT mTLS, sidecars", 35, 368, 890, 252, valign="bottom")
    d.node("web", "service", 50, 404, 270, 88, "jithendar-com ×2", "Next.js, delegate route",
           "callback API on :9465")
    d.node("agent", "ai", 345, 404, 270, 88, "seo-agent", "CrewAI Flows and Crews", ":8080 API · :8090 MCP")
    d.node("cron", "ops", 640, 404, 270, 88, "CronJobs seo-flow-*", "python -m app.trigger <flow>",
           "only POSTs a kickoff")
    d.node("exec", "compute", 50, 512, 270, 76, "practice-executor", "gVisor sandboxes,", "no network")
    d.node("review", "security", 345, 512, 270, 76, "/admin/review (in the site)", "a person approves:",
           "the only publish trigger")
    d.node("mon", "ops", 640, 512, 270, 76, "Prometheus scrape :9464", "over mTLS, own sidecar",
           "OTel → Jaeger, Alloy → Loki")
    d.node("pg", "data", 35, 646, 280, 76, "PostgreSQL", "CloudNativePG, shared", "pgvector, seo_flow_runs", shape="db")
    d.node("vk", "data", 335, 646, 280, 76, "Valkey (shared)", "site cache bus,", "pub/sub only", shape="db")
    d.node("graf", "ops", 640, 646, 285, 76, "Grafana", "dashboards from sites/…/grafana", "installed by Terraform")
    d.node("r2", "external", 35, 758, 280, 56, "Cloudflare R2", "media, backups, report PDFs")
    d.node("claude", "external", 335, 758, 280, 56, "Anthropic API", "every call budget-guarded")
    d.node("google", "external", 640, 758, 285, 56, "Google APIs", "Search Console, GA4 (site sync)")

    d.edge("visitor", "dns", exit=(1, 0.5), entry=(0, 0.5), label="lookup")
    d.edge("visitor", "haproxy", exit=(0.5, 1), entry=((165 - 35) / 400, 0), label="80 / 443")
    d.edge("haproxy", "gw", exit=(0.5, 1), entry=((235 - 35) / 420, 0), label="NodePort, PROXY")
    d.edge("gw", "web", exit=((185 - 35) / 420, 1), entry=(0.5, 0), label="delegate VirtualService")
    d.edge("mcp", "agent", exit=(0.1, 1), entry=(0.85, 0), kind="control", label=":8090 only")
    d.edge("cron", "agent", exit=(0, 0.5), entry=(1, 0.5))
    d.edge("agent", "web", exit=(0, 0.35), entry=(1, 0.35))
    d.edge("review", "agent", exit=(0.5, 0), entry=(0.5, 1), kind="control", label="approve")
    d.edge("agent", "pg", exit=(0, 0.85), entry=(0.85, 0), via=[(332, 479), (332, 632), (273, 632)])
    d.edge("agent", "claude", exit=(1, 0.85), entry=(0.85, 0), via=[(627, 479), (627, 742), (573, 742)])
    d.edge("mon", "graf", exit=(0.5, 1), entry=(0.5, 0), kind="control")
    d.text("note", 20, 826, 920, 32, "seo-agent writes drafts to the site's callback port; CronJobs only POST a kickoff. The site owns only its delegate route; the Gateway, certificate and root routing table "
           "live in the cluster repository. Traefik was removed on 9 November 2026; Kong was prepared but never became the edge. Since 10 November mk4 runs on k3s on Hetzner Cloud.",
           size=11)
    d.legend(866)
    return d


def pipeline():
    d = Diagram("crewai-content-pipeline", 960, 980, "The CrewAI content pipeline: agents draft, a person publishes")
    d.node("cron", "ops", 35, 56, 280, 56, "CronJobs seo-flow-*", "schedules live in the manifests")
    d.node("button", "client", 340, 56, 280, 56, "Admin “Run now”", "the same kickoff endpoint")
    d.node("mcpk", "optional", 645, 56, 280, 56, "MCP kickoff_flow", "allowlisted flows, rate limited")
    d.node("runner", "ai", 35, 144, 890, 62, "FlowRunner: POST /flows/{name}/kickoff",
           "one active run per flow + target (partial unique index + advisory lock)")
    d.zone("z-draft", "Drafting flows (CrewAI 1.15, sequential crews)", 20, 232, 920, 222, "ai", corner="right")
    d.node("opt", "ai", 50, 268, 300, 110, "optimize_article_flow", "Optimization Crew:",
           "analyst → editor → reviewer", "validate_draft, retry once")
    d.node("new", "ai", 370, 268, 300, 110, "new_article_flow", "Editorial Crew: researcher →",
           "writer → reviewer → SEO editor", "SEO editor returns metadata only")
    d.node("guard", "security", 690, 268, 235, 172, "Crew guardrails", "read-only tool allowlist",
           "no delegation, no code", "max_iter 4 per agent", "150k tokens per run", "600 s wall clock",
           "monthly budget cap", align="left")
    d.node("drafts", "data", 35, 478, 280, 72, "seo_drafts", "draft awaiting review", shape="db")
    d.node("rq", "security", 340, 478, 280, 72, "Review queue (a person)", "word diff, accept each change",
           "fact-check flags block approval")
    d.node("cms", "service", 645, 478, 280, 72, "CMS draft post", "calendar articles wait for", "the editor's Publish button")
    d.zone("z-pub", "publish_flow: only from a human approval", 20, 574, 920, 196, "risk", corner="right")
    steps = [("apply", "apply_changes", "accepted changes"), ("pub", "cms_publish", "CMS publish"),
             ("verify", "verify_live", "check the live page"), ("submit", "submit_search", "search engines"),
             ("reindex", "reindex", "pgvector chunks")]
    for i, (key, title, sub) in enumerate(steps):
        d.node(key, "service", 50 + i * 175, 612, 160, 56, title, sub)
    d.node("rollback", "optional", 400, 700, 160, 56, "offer_rollback", "if the check fails")
    d.node("measure", "ops", 750, 700, 160, 56, "schedule_measure", "outcomes at +28 days")
    d.zone("z-rec", "Recorded for every run", 20, 790, 920, 104)
    d.node("runs", "data", 35, 818, 280, 68, "seo_flow_runs", "status, steps, tokens, cost", shape="db")
    d.node("usage", "data", 340, 818, 280, 68, "seo_llm_usage", "one row per model call", shape="db")
    d.node("spans", "ops", 645, 818, 280, 68, "OTel spans", "crew.<crew>.<agent>")

    d.edge("cron", "runner", exit=(0.5, 1), entry=((175 - 35) / 890, 0))
    d.edge("button", "runner", exit=(0.5, 1), entry=((480 - 35) / 890, 0))
    d.edge("mcpk", "runner", exit=(0.5, 1), entry=((785 - 35) / 890, 0))
    d.edge("runner", "opt", exit=((200 - 35) / 890, 1), entry=(0.5, 0))
    d.edge("runner", "new", exit=((520 - 35) / 890, 1), entry=(0.5, 0))
    d.edge("opt", "drafts", exit=(0.5, 1), entry=((200 - 35) / 280, 0))
    d.edge("new", "cms", exit=(0.5, 1), entry=(0.5, 0), via=[(520, 464), (785, 464)])
    d.edge("drafts", "rq", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("rq", "apply", exit=(0.5, 1), entry=(0.5, 0), via=[(480, 600), (130, 600)], kind="control",
           label="approve (single use)")
    for a, b in (("apply", "pub"), ("pub", "verify"), ("verify", "submit"), ("submit", "reindex")):
        d.edge(a, b, exit=(1, 0.5), entry=(0, 0.5))
    d.edge("verify", "rollback", exit=(0.5, 1), entry=(0.5, 0), label="failed")
    d.edge("reindex", "measure", exit=(0.5, 1), entry=(0.5, 0))
    d.text("note", 20, 904, 920, 32, "Agents only read: creating a draft is a flow step, never a tool. Data steps (sync, scoring, "
           "crawling, link limits) are plain Python. A run that dies is marked failed on restart and rerun from the start.",
           size=11)
    d.legend(944, labels={"security": "Human gate and limits"})
    return d


def release():
    d = Diagram("release-pipeline", 960, 840, "Releases: built only when a pull request is merged, tagged pr-<number>")
    d.node("pr", "client", 35, 56, 280, 56, "Pull request", "opened, updated or reopened")
    d.node("push", "optional", 645, 56, 280, 56, "Push straight to master", "no push trigger: nothing runs")
    d.zone("z-check", "check job (every PR update)", 20, 132, 920, 94, corner="right")
    d.node("check", "ops", 50, 160, 860, 52, "lint · typecheck · test · build",
           "and render the production manifests with kubectl kustomize")
    d.node("merge", "client", 35, 246, 280, 56, "PR merged into master", "event: closed + merged")
    d.zone("z-rel", "release job: GitHub-hosted arm64 runner, from the merge commit", 20, 322, 920, 208, "cluster", corner="right")
    steps = [("scope", "scope", "image files", "changed?"), ("build", "lint, test, build", "one step each,", "in sequence"),
             ("size", "image size gate", "fails above +15 %", "of the baseline"),
             ("smoke", "smoke test", "/api/health = SHA", "AVIF or WebP"), ("pushs", "push two tags", ":pr-<n>", ":latest")]
    for i, (key, title, a, b) in enumerate(steps):
        d.node(key, "ops", 50 + i * 175, 358, 160, 72, title, a, b)
    d.node("restart", "security", 750, 456, 160, 60, "ci-rollout.py", "patch + watch only")
    d.node("reg", "data", 35, 550, 280, 70, "Harbor registry", "every release keeps :pr-<n>", shape="db")
    d.node("deploy", "service", 340, 550, 280, 70, "deploy/jithendar-com", "runs moks-cms:pr-<n>,", "the live release on record")
    d.node("rb", "ops", 645, 550, 280, 70, "Rollback", "kubectl set image", "… :pr-<last good>")
    d.zone("z-other", "Other workflows", 20, 640, 920, 100)
    d.node("content", "ops", 50, 668, 270, 62, "ci-content.yml (push)", "MDX checks, content image;",
           "restart only if published")
    d.node("manifests", "security", 345, 668, 270, 62, "deploy-kubernetes.yml", "merged PR touching kubernetes/:",
           "applier SA, app objects only")
    d.node("infra", "ops", 640, 668, 270, 62, "ci-seo-agent.yml,", "ci-practice-executor.yml:", "same pr-<n> releases")

    d.edge("pr", "check", exit=(0.5, 1), entry=((175 - 50) / 860, 0))
    d.edge("merge", "scope", exit=(0.5, 1), entry=(0.5, 0), via=[(175, 340), (130, 340)])
    for a, b in (("scope", "build"), ("build", "size"), ("size", "smoke"), ("smoke", "pushs")):
        d.edge(a, b, exit=(1, 0.5), entry=(0, 0.5))
    d.edge("pushs", "restart", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("pushs", "reg", exit=(0.2, 1), entry=(0.5, 0), via=[(782, 442), (175, 442)])
    d.edge("restart", "deploy", exit=(0, 0.5), entry=(0.5, 0), via=[(480, 486)], label="set image :pr-<n>")
    d.edge("rb", "deploy", exit=(0, 0.5), entry=(1, 0.5), kind="control")
    d.text("note", 20, 752, 920, 32, "Every release maps to a reviewed pull request, and its tag is the rollback handle. "
           "The deployer may only patch and watch named Deployments; RBAC, Secrets and mesh policy stay with a person.",
           size=11)
    d.legend(792, labels={"security": "Least-privilege CI identity", "optional": "Does nothing"})
    return d


FIGURES = [platform, pipeline, release]


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
