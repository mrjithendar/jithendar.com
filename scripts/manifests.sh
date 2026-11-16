#!/usr/bin/env bash
# Print one group of the mk4 manifests in kubernetes/ as multi-document YAML, for kubectl apply/diff/delete -f -.
# kubernetes/ is one flat folder; the file name says which group a manifest belongs to:
#
#   site               kustomization.yaml (00-… to 85-…): the site, routing, mesh, CI accounts
#   seo-agent          seo-agent-*.yaml: SEO v4 agent service + flow-trigger CronJobs (applied by hand, docs/seo/MANUAL_SETUP.md)
#
#   scripts/manifests.sh site | kubectl apply -f -
#   scripts/manifests.sh seo-agent | kubectl diff -f -
#
# The Python practice executor's manifests moved to moks-tech/practice-programming on 2026-11-16.
#
# Only the site uses kustomize (Kustomize allows one kustomization per folder). The other group is plain
# files, printed in name order, which is the order they must be applied in.
set -euo pipefail

dir="$(cd "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/kubernetes"
group="${1:-}"

case "$group" in
  site)
    kubectl kustomize "$dir"
    ;;
  seo-agent)
    shopt -s nullglob
    files=("$dir/$group"-*.yaml)
    [[ ${#files[@]} -gt 0 ]] || { echo "No kubernetes/$group-*.yaml files" >&2; exit 1; }
    for f in "${files[@]}"; do
      printf -- '---\n# Source: kubernetes/%s\n' "$(basename "$f")"
      cat "$f"
      printf '\n'
    done
    ;;
  *)
    echo "usage: $0 site|seo-agent" >&2
    exit 2
    ;;
esac
