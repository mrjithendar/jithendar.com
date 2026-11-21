#!/usr/bin/env bash
# Print one group of the mk4 manifests in kubernetes/ as multi-document YAML, for kubectl apply/diff/delete -f -.
# kubernetes/ is one flat folder; the file name says which group a manifest belongs to:
#
#   site               kustomization.yaml (00-… to 85-…): the site, routing, mesh, CI accounts
#   seo-agent          seo-agent-*.yaml: SEO v4 agent service + the flow dispatcher CronJob (applied by hand, docs/seo/MANUAL_SETUP.md)
#   news-agent         news-agent-*.yaml: the news desk's service (mrjithendar/newsroom) + its dispatcher CronJob
#
#   scripts/manifests.sh site | kubectl apply -f -
#   scripts/manifests.sh seo-agent | kubectl diff -f -
#   scripts/manifests.sh news-agent | kubectl apply -f -
#
# The Python practice executor's manifests moved to moks-tech/practice-programming on 2026-11-16.
#
# Only the site uses kustomize (Kustomize allows one kustomization per folder). The other groups are plain
# files, printed in name order, which is the order they must be applied in.
set -euo pipefail

dir="$(cd "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/kubernetes"
group="${1:-}"

case "$group" in
  site)
    # site.json and config/ live at the repository root, outside kubernetes/ (configMapGenerator in kustomization.yaml).
    kubectl kustomize --load-restrictor=LoadRestrictionsNone "$dir"
    ;;
  seo-agent|news-agent)
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
    echo "usage: $0 site|seo-agent|news-agent" >&2
    exit 2
    ;;
esac
