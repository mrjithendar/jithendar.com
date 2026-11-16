#!/usr/bin/env python3
"""Roll every Deployment that runs an image repository to one tag, and wait until it is ready.

  scripts/ci-rollout.py registry.jithendar.com/jithendar/jithendar-com pr-123-1a2b3c4
  scripts/ci-rollout.py registry.jithendar.com/jithendar/jithendar-com pr-123-1a2b3c4 --previous registry.jithendar.com/jithendar/moks-cms

The release workflow calls this (.github/workflows/release.yml): after pushing the site's app or content image, and
with the tag pinned in moks-cms.json for the SEO agent and the practice executor:

- every Deployment in the namespace that has a container or an init container from <repository>, whatever its tag or
  digest, gets those containers set to <repository>:<tag> (`kubectl set image`). Nothing is matched by name, so a
  second Deployment that runs the same image is released with the first;
- a Deployment that is already on that tag is restarted instead: the job was run again and pushed the tag again,
  and imagePullPolicy Always pulls it on restart;
- `--previous <repository>` (repeatable) names a repository the image was renamed from: containers that still run it
  are moved to <repository>:<tag> as well. Without it, the first release after a rename would find no Deployment;
- each rollout is waited for (ROLLOUT_TIMEOUT, default 5m). One that does not finish fails the job; the others are
  still waited for.

The cluster therefore runs each release under its own tag. Which release is live is in the Deployment
(`kubectl get deploy -o wide`), a pod that restarts gets the same image again, and going back is
`scripts/ci-rollout.py <repository> pr-<earlier number>`, or the `kubectl set image` it prints.

Needs kubectl and a kubeconfig whose context names the namespace (or NAMESPACE). It reads and patches Deployments
and reads pods, which is all the CI deployer's Role allows (kubernetes/80-ci-deployer.yaml). Standard library only.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys


def repository(image: str) -> str:
    """The image without its tag or digest: registry:5000/a/b:tag@sha256:… → registry:5000/a/b."""
    name = image.split("@", 1)[0]
    head, _, last = name.rpartition("/")
    last = last.split(":", 1)[0]
    return f"{head}/{last}" if head else last


def plan(deployments: list[dict], repo: str, tag: str, previous: tuple[str, ...] = ()) -> tuple[dict[str, list[str]], list[str]]:
    """(Deployment → containers to set, Deployments already on the tag) for everything that runs `repo` (or one of
    the `previous` repositories it was renamed from)."""
    target = f"{repo}:{tag}"
    repos = {repo, *previous}
    to_set: dict[str, list[str]] = {}
    current: list[str] = []
    for d in deployments:
        spec = d.get("spec", {}).get("template", {}).get("spec", {})
        ours = [c for c in [*spec.get("initContainers", []), *spec.get("containers", [])] if repository(c.get("image", "")) in repos]
        if not ours:
            continue
        name = d["metadata"]["name"]
        behind = [c["name"] for c in ours if c["image"] != target]
        if behind:
            to_set[name] = behind
        else:
            current.append(name)
    return to_set, current


def kubectl(*args: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    namespace = os.environ.get("NAMESPACE")
    command = ["kubectl", *(["-n", namespace] if namespace else []), *args]
    if not capture:
        print("$ " + " ".join(command), flush=True)
    return subprocess.run(command, check=False, text=True, stdout=subprocess.PIPE if capture else None)


def main(argv: list[str]) -> int:
    usage = f"usage: {argv[0]} <image repository without a tag> <tag> [--previous <repository>]..."
    args, previous = argv[1:3], []
    rest = argv[3:]
    while rest:
        if rest[0] != "--previous" or len(rest) < 2 or not rest[1] or repository(rest[1]) != rest[1]:
            print(usage, file=sys.stderr)
            return 2
        previous.append(rest[1])
        rest = rest[2:]
    if len(args) != 2 or not args[1] or ":" in args[1] or not args[0] or repository(args[0]) != args[0]:
        print(usage, file=sys.stderr)
        return 2
    repo, tag = args
    target = f"{repo}:{tag}"
    timeout = os.environ.get("ROLLOUT_TIMEOUT", "5m")

    listed = kubectl("get", "deployments", "-o", "json", capture=True)
    if listed.returncode != 0:
        print("::error::Could not list Deployments (is the kubeconfig set up? scripts/setup-ci-deployer.sh)", file=sys.stderr)
        return 1
    to_set, current = plan(json.loads(listed.stdout).get("items", []), repo, tag, tuple(previous))
    if not to_set and not current:
        print(f"::error::No Deployment runs {repo}. Apply kubernetes/ first; the release only moves workloads that exist.", file=sys.stderr)
        return 2

    failed: list[str] = []
    for name, containers in to_set.items():
        if kubectl("set", "image", f"deployment/{name}", *[f"{c}={target}" for c in containers]).returncode != 0:
            print(f"::error::Could not set the image of deployment/{name} (does the CI deployer's Role name it? kubernetes/80-ci-deployer.yaml)", file=sys.stderr)
            failed.append(name)
    for name in current:
        # Already on this tag: the tag was pushed again, so start new pods to pull it.
        if kubectl("rollout", "restart", f"deployment/{name}").returncode != 0:
            failed.append(name)

    for name in [*to_set, *current]:
        if name in failed:
            continue
        if kubectl("rollout", "status", f"deployment/{name}", f"--timeout={timeout}").returncode != 0:
            print(f"::error::Rollout of {name} did not finish within {timeout}", file=sys.stderr)
            pods = kubectl("get", "pods", "-o", "wide", capture=True)
            print("\n".join(line for line in pods.stdout.splitlines() if line.startswith(("NAME", name))), file=sys.stderr)
            failed.append(name)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    lines = [f"### Rolled out `{target}`", ""]
    lines += [f"- deployment/{name}: {'**failed**' if name in failed else 'ready'} ({', '.join(containers)} set to `{tag}`)" for name, containers in to_set.items()]
    lines += [f"- deployment/{name}: {'**failed**' if name in failed else 'ready'} (already on `{tag}`, restarted)" for name in current]
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
