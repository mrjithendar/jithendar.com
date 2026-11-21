#!/usr/bin/env python3
"""Figures for content/blog/github-actions-runners-k3s-arc-terraform.mdx (GitHub Actions runners on mk4).

    python3 docs/knowledge-sharing/mk4-github-runners/diagrams/build_diagrams.py   # writes the .drawio files
    bash docs/knowledge-sharing/mk4-github-runners/diagrams/export.sh              # draw.io CLI → public/images/mk4-github-runners/

After editing a .drawio file by hand, run only export.sh, or this script overwrites the edits.

Sources (21 November 2026): mrjithendar/k8s-deployments 381b585 (minikube-infrastructure/runners.tf,
deploy/minikube/runners/values.yaml, controller.yaml, image/Dockerfile, .github/workflows/build-runner-image.yml,
create-mk-infrastructure.yml, deploy/minikube/gatekeeper/constraints/values.yaml), the workflow runs listed in
../README.md, and read-only kubectl and helm on mk4.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio_model import Diagram  # noqa: E402

HERE = Path(__file__).resolve().parent
NOTE = 11


def architecture():
    d = Diagram("mk4-runners-architecture", 960, 760, "GitHub Actions runners on mk4: what runs where")

    d.zone("z-gh", "GitHub · mrjithendar", 20, 50, 230, 560, "plain")
    d.node("repos", "client", 35, 85, 200, 95, "10 repositories", "52 jobs: runs-on: mk4", "5 public, 5 private")
    d.node("group", "security", 35, 200, 200, 95, "Runner group Default", "all repositories",
           "public repos allowed")
    d.node("app", "security", 35, 315, 200, 95, "GitHub App", "Self-hosted runners:", "read and write")
    d.node("actions", "external", 35, 430, 200, 110, "Actions service", "queues jobs for mk4,", "gives each runner",
           "a just-in-time config")
    d.edge("repos", "group", "queued", exit=(0.5, 1), entry=(0.5, 0))

    d.zone("z-mk4", "mk4 · k3s v1.37.2+k3s1 · arm64 workers w1, w2, w3", 270, 50, 670, 560, "cluster")
    d.zone("z-sys", "runners-system · baseline", 285, 85, 230, 455, "plain")
    d.node("ctrl", "ops", 300, 120, 200, 95, "arc-gha-rs-controller", "release arc, ARC 0.15.1",
           "creates runner pods")
    d.node("listener", "ops", 300, 250, 200, 95, "mk4-…-listener", "long-polls GitHub", "as the GitHub App")
    d.edge("listener", "ctrl", "scale to N", kind="control", exit=(0.5, 0), entry=(0.5, 1))
    d.edge("listener", "actions", "HTTPS long poll", exit=(0.5, 1), entry=(1, 0.4), via=((400, 474),))
    d.edge("listener", "app", "signs in as", kind="control", exit=(0, 0.7), entry=(1, 0.5), via=((262, 316), (262, 362)))

    d.zone("z-run", "runners · Pod Security privileged", 530, 85, 395, 455, "risk")
    d.node("ars", "ops", 545, 120, 180, 95, "AutoscalingRunnerSet", "scale set mk4", "release arc-runners",
           "min, max: unset")
    d.node("secret", "data", 740, 120, 170, 95, "Secret github-app", "App ID, install ID,", "private key", shape="db")
    d.edge("ars", "secret", kind="control", exit=(1, 0.5), entry=(0, 0.5))

    d.zone("z-pod", "EphemeralRunner pod, one per job", 545, 235, 365, 290, "plain")
    d.node("init", "compute", 560, 265, 335, 60, "init-dind-externals", "copies the runner's externals")
    d.node("dind", "security", 560, 335, 335, 80, "dind: docker:29.9.2-dind", "privileged native sidecar",
           "dockerd on /var/run/docker.sock")
    d.node("runner", "compute", 560, 425, 335, 90, "runner: mk4-runner:2.338.2-48743dc57f6a",
           "runs the job's steps", "DOCKER_HOST=unix:///var/run/docker.sock")
    d.edge("dind", "runner", "socket", kind="sync", exit=(0.5, 1), entry=(0.5, 0), both=True)
    d.edge("ctrl", "z-pod", "creates", kind="control", exit=(1, 0.8), entry=(0, 0.5), via=((522, 196), (522, 380)))
    d.edge("runner", "actions", "HTTPS: steps, logs, result", exit=(0.5, 1), entry=(0.5, 1),
           via=((727, 575), (135, 575)), t=0.3)

    d.zone("z-net", "Where a runner pod may connect (NetworkPolicy runners: no ingress)", 20, 630, 920, 110, "plain")
    d.node("no", "optional", 40, 660, 260, 65, "Refused: no route", "pods, Services, nodes,", "Hetzner metadata (169.254/16)")
    d.node("dns", "network", 330, 660, 230, 65, "CoreDNS", "kube-system, port 53")
    d.node("net", "external", 590, 660, 335, 65, "Public internet, any port", "ghcr.io, Docker Hub, Harbor, PyPI, npm")
    d.edge("z-pod", "dns", "DNS", kind="sync", exit=(0.15, 1), entry=(0.5, 0))
    d.edge("z-pod", "net", kind="sync", exit=(0.58, 1), entry=(0.5, 0))
    d.legend(752, labels={"ops": "ARC controller and resources", "external": "GitHub and the internet",
                          "security": "Identity, privilege, policy", "optional": "Refused by NetworkPolicy"})
    return d


def job_lifecycle():
    d = Diagram("mk4-runners-job-lifecycle", 960, 430, "One job on mk4: from queued to deleted")
    w, h = 290, 105
    xs = (20, 335, 650)
    d.node("s1", "client", xs[0], 60, w, h, "1 · A job is queued", "a push, pull request or manual run",
           "the job says runs-on: mk4", "GitHub queues it for scale set mk4", align="left")
    d.node("s2", "ops", xs[1], 60, w, h, "2 · The listener sees it", "long poll, signed in as the GitHub App",
           "no minRunners: nothing waits idle", "asks the controller for one runner", align="left")
    d.node("s3", "ops", xs[2], 60, w, h, "3 · The controller makes a pod", "an EphemeralRunner with a JIT config",
           "pod mk4-runner-xxxxx in runners", "on any arm64 worker, w1 to w3", align="left")
    d.node("s4", "security", xs[2], 230, w, h, "4 · Docker comes up first", "init-dind-externals copies externals",
           "dind starts as a native sidecar", "startupProbe docker info, 24 × 5 s", align="left")
    d.node("s5", "compute", xs[1], 230, w, h, "5 · The runner runs the job", "registers with its JIT config",
           "waits up to 120 s for Docker", "steps, services:, docker build/run", align="left")
    d.node("s6", "compute", xs[0], 230, w, h, "6 · The pod is deleted", "the runner exits after one job",
           "emptyDirs go too: no image cache", "the next job gets a fresh pod", align="left")
    d.edge("s1", "s2", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("s2", "s3", kind="control", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("s3", "s4", kind="control", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("s4", "s5", exit=(0, 0.5), entry=(1, 0.5))
    d.edge("s5", "s6", exit=(0, 0.5), entry=(1, 0.5))
    d.text("measured", 20, 355, 920, 36,
           "Measured on 21 November 2026: jithendar.com content.yml, run 44874905707 attempt 3, pod mk4-runner-z2k2l. "
           "Started 06:55:28 UTC, finished 06:56:12 UTC (44 s), Git LFS checkout and docker run included.", size=NOTE)
    d.legend(400, labels={"client": "GitHub", "ops": "ARC", "security": "Privileged Docker daemon",
                          "compute": "Runner"})
    return d


def terraform():
    d = Diagram("mk4-runners-terraform", 1000, 660, "minikube-infrastructure/runners.tf: what Terraform creates")

    d.node("env", "security", 20, 70, 220, 100, "Environment mk4", "RUNNERS_GITHUB_APP_ID",
           "…_INSTALLATION_ID", "…_PRIVATE_KEY")
    d.node("wf", "ops", 20, 190, 220, 100, "create-mk-infrastructure", "TF_VAR_github_runners_app_*",
           "or a local apply: export the", "same TF_VAR_* (gh-app.sh)")
    d.node("tfvars", "ops", 20, 490, 220, 80, "vars/mk4.tfvars", "github_runners_config_url =",
           "https://github.com/mrjithendar")
    d.edge("env", "wf", "secrets", kind="control", exit=(0.5, 1), entry=(0.5, 0))

    d.zone("z-tf", "minikube-infrastructure/runners.tf", 255, 55, 510, 540, "cluster")
    d.node("ns", "compute", 270, 90, 210, 80, "2 namespaces", "runners-system: baseline", "runners: privileged")
    d.node("secret", "security", 270, 190, 210, 80, "runners_github_app", "kubernetes_secret_v1",
           "precondition: all 3 set")
    d.node("netpol", "network", 270, 290, 210, 80, "runners", "kubernetes_network_policy_v1",
           "egress: DNS + public only")
    d.node("gk", "security", 270, 390, 210, 80, "gatekeeper_constraints", "helm_release (gatekeeper.tf)",
           "privileged: runners excluded")
    d.node("ctrl", "ops", 560, 90, 190, 80, "arc_controller", "helm_release, release arc", "controller chart 0.15.1")
    d.node("runners", "ops", 560, 190, 190, 200, "arc_runners", "helm_release", "release arc-runners",
           "scale-set chart 0.15.1", "values.yaml +", "yamlencode(...): config", "URL, Secret, scale set",
           "name, controller SA")
    d.edge("ns", "ctrl", "namespace", kind="control", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("ctrl", "runners", "depends_on", kind="control", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("secret", "runners", "Secret", kind="control", exit=(1, 0.5), entry=(0, 0.2))
    d.edge("netpol", "runners", "depends_on", kind="control", exit=(1, 0.5), entry=(0, 0.7))
    d.edge("gk", "runners", "depends_on", kind="control", exit=(1, 0.5), entry=(0.3, 1))
    d.edge("wf", "secret", kind="control", exit=(1, 0.4), entry=(0, 0.5))
    d.edge("tfvars", "runners", "githubConfigUrl", kind="control", exit=(1, 0.5), entry=(0.75, 1),
           via=((702, 530),))

    d.zone("z-img", "The runner image", 775, 55, 205, 540, "plain")
    d.node("img", "ops", 785, 90, 185, 95, "build-runner-image", "ubuntu-24.04-arm", "smoke-tests tools",
           "pushes on master")
    d.node("ghcr", "data", 785, 210, 185, 95, "ghcr.io/mrjithendar", "mk4-runner:2.338.2-", "48743dc57f6a", shape="db")
    d.node("values", "ops", 785, 330, 185, 95, "runners/values.yaml", "image: …-48743dc57f6a", "dind sidecar layout",
           "no containerMode")
    d.edge("img", "ghcr", "docker push", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("ghcr", "values", "tag checked", kind="control", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("values", "runners", kind="control", exit=(0, 0.3), entry=(1, 0.8))
    d.text("tests", 20, 605, 960, 36,
           "terraform test (tests/releases.tftest.hcl): run github_runners checks versions, namespaces, wiring, the "
           "pinned images, the privileged sidecar and the NetworkPolicy; github_runners_without_app_fails and "
           "github_runners_bad_config_url_fails expect the precondition and the URL validation to stop the plan.",
           size=NOTE)
    d.legend(650, labels={"ops": "Terraform, workflows, files", "security": "Secrets and policy",
                          "compute": "Namespaces"})
    return d


def timeline():
    rows = [
        ("29 Oct", "external", None, "Before: runners as systemd services on the old Minikube host",
         "Builds competed with the cluster for memory and disk and froze the host twice. CI went back to GitHub-hosted runners."),
        ("05:12", "ops", 1, "PR #24 merged (a9cd274): ARC 0.15.1, scale set mk4, runners.tf, NetworkPolicy",
         "Deploy stops at Check CI settings: Not set: TF_VAR_github_runners_app_*. Fix: create the GitHub App, set 3 secrets."),
        ("06:02", "ops", 2, "CI cannot apply: Could not assume role with OIDC (the org rename broke the trust)",
         "Fix for now: terraform apply -target=helm_release.arc_runners from a laptop. Listener Running at 06:02."),
        ("06:14", "client", None, "c64ca5d and nine sibling commits: all 52 jobs in 10 repositories move to runs-on: mk4",
         "Runner group Default now allows public repositories. In the next hour 29 jobs run on mk4: 7 pass, 22 fail."),
        ("06:18", "security", 3, "jithendar.com content, attempt 1: Unable to locate executable file: git-lfs",
         "GitHub's actions-runner image is not ubuntu-latest: no git-lfs, shellcheck, gh, kubectl, helm, Docker daemon."),
        ("06:29", "ops", None, "18b905c: our own image ghcr.io/mrjithendar/mk4-runner, built on a GitHub-hosted arm64 runner",
         "git-lfs, Python, build-essential, shellcheck, gh, kubectl, helm... Helm revision 2 of arc-runners at 06:35."),
        ("06:38", "security", 4, "attempt 2: failed to connect to the docker API at unix:///var/run/docker.sock",
         "24 of the 52 jobs need a Docker daemon: docker build/run, docker/* actions, kind, services:, container actions."),
        ("06:45", "ops", None, "c06ac72: a privileged dind sidecar in every runner pod; Gatekeeper excludes namespace runners",
         "docker:29.9.2-dind, socket, workspace and /tmp shared, /var/lib/docker on an emptyDir. Helm revision 3 at 06:47."),
        ("06:55", "compute", None, "attempt 3 passes in 44 s on pod mk4-runner-z2k2l",
         "07:02 moks-cms hygiene (docker run promtool) passes; 07:03 roboshop's services: mongo:8.0 starts and answers."),
        ("open", "security", 5, "Build runner image fails on c06ac72: values.yaml now names mk4-runner twice",
         "Also open: the OIDC trust, practice-programming's sandbox tests, runner limits, fork pull request approval."),
    ]
    top, row_h = 60, 62
    d = Diagram("mk4-runners-timeline", 960, top + row_h * len(rows) + 20, "21 November 2026 (UTC): issues and fixes, in order")
    d.rect("axis", 101, top, 2, row_h * len(rows) - 10, "#94a3b8")
    for i, (when, kind, fail, title, line) in enumerate(rows):
        y = top + i * row_h
        d.text(f"t{i}", 20, y + 16, 70, 18, f"<b>{when}</b>", color="#0f172a", align="right")
        if fail:
            d.marker(fail, 102, y + 26)
        else:
            d.rect(f"tick{i}", 96, y + 20, 12, 12, "#475569")
        d.node(f"r{i}", kind, 130, y, 810, row_h - 10, title, line, align="left")
    d.legend(top + row_h * len(rows) + 4, failure=True,
             labels={"external": "Earlier attempt", "ops": "Change we made", "client": "Workflows moved",
                     "security": "Failure", "compute": "Passed on mk4"})
    return d


def main():
    for build in (architecture, job_lifecycle, terraform, timeline):
        d = build()
        (HERE / f"{d.name}.drawio").write_text(d.xml() + "\n")
        print(f"wrote {d.name}.drawio ({d.w}x{d.h})")


if __name__ == "__main__":
    main()
