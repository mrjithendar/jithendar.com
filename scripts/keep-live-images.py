#!/usr/bin/env python3
"""Keep the image each workload is running when its manifest is applied.

  kubectl get deployments,statefulsets -o json > live.json
  scripts/keep-live-images.py live.json < rendered.yaml > to-apply.yaml

The manifests in kubernetes/ name `<image>:latest`, which is only what a first apply starts with. After that the image
workflows decide what runs: each release sets its own tag (scripts/ci-rollout.py), and a rollback is a
`kubectl set image` to an earlier one. Applying the manifests as they are would put every workload back on `:latest`
each time a manifest changes: an unplanned roll-out, and the end of any rollback.

So, for every Deployment and StatefulSet in the manifests that already exists in the cluster, a container (or init
container) keeps the image it has there when all of this holds:

- the live workload has a container of the same name,
- from the same image repository,
- and the manifest asks for `:latest` (or no tag).

A manifest that names another repository, or pins a tag or digest on purpose, is applied as written. A workload that
does not exist yet is created as written. What was kept is listed on stderr. Needs PyYAML.
"""
from __future__ import annotations

import json
import sys

import yaml

KINDS = {"Deployment", "StatefulSet"}


def split(image: str) -> tuple[str, str]:
    """(repository, tag or digest); the tag is "latest" when the image names none."""
    name, at, digest = image.partition("@")
    head, _, last = name.rpartition("/")
    last, colon, tag = last.partition(":")
    repo = f"{head}/{last}" if head else last
    if at:
        return repo, digest
    return repo, tag if colon else "latest"


def keep_live(doc: dict, live: dict[tuple[str, str, str], dict]) -> list[str]:
    """Rewrite `doc` in place; return one line per container that keeps its live image."""
    meta = doc.get("metadata") or {}
    running = live.get((doc.get("kind", ""), meta.get("namespace") or "", meta.get("name", "")))
    if doc.get("kind") not in KINDS or running is None:
        return []
    kept = []
    spec = doc.get("spec", {}).get("template", {}).get("spec", {})
    live_spec = running.get("spec", {}).get("template", {}).get("spec", {})
    for group in ("initContainers", "containers"):
        current = {c["name"]: c.get("image", "") for c in live_spec.get(group) or []}
        for container in spec.get(group) or []:
            wanted, now = container.get("image", ""), current.get(container.get("name"), "")
            if not wanted or not now or wanted == now:
                continue
            repo, tag = split(wanted)
            if tag == "latest" and split(now)[0] == repo:
                container["image"] = now
                kept.append(f"{doc['kind']} {meta.get('name')}: {container['name']} stays on {now}")
    return kept


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <kubectl get deployments,statefulsets -o json> < rendered.yaml", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as f:
        items = json.load(f).get("items", [])
    live = {(i.get("kind", ""), i["metadata"].get("namespace") or "", i["metadata"]["name"]): i for i in items}
    docs = [d for d in yaml.safe_load_all(sys.stdin) if d]
    kept = [line for d in docs for line in keep_live(d, live)]
    yaml.safe_dump_all(docs, sys.stdout, sort_keys=False)
    print(f"Images kept from the cluster ({len(kept)}):" if kept else "No image differs from what the manifests ask for.", file=sys.stderr)
    for line in kept:
        print(f"  {line}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
