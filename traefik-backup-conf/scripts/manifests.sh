#!/usr/bin/env bash
# Print one group of the mk4 manifests in minikube/ as multi-document YAML, for kubectl apply/diff/delete -f -.
# minikube/ is one flat folder; the file name says which group a manifest belongs to:
#
#   site               kustomization.yaml (00-… to 85-…): the site, Postgres, Redis, TLS, ingress, CI accounts
#   practice-executor  practice-executor-*.yaml: Python practice runner (applied by hand once gVisor is verified)
#   db-access          db-access-*.yaml: Adminer at /db/ and PostgreSQL at db.jithendar.com (minikube/DB_ACCESS.md)
#
#   scripts/manifests.sh site | kubectl --context mk4 apply -f -
#   scripts/manifests.sh practice-executor | kubectl --context mk4 diff -f -
#   scripts/manifests.sh db-access | kubectl --context mk4 delete -f -
#
# Only the site uses kustomize (Kustomize allows one kustomization per folder). The other two groups are plain
# files, printed in name order, which is the order they must be applied in.
set -euo pipefail

dir="$(cd "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/minikube"
group="${1:-}"

case "$group" in
  site)
    kubectl kustomize "$dir"
    ;;
  practice-executor|db-access)
    shopt -s nullglob
    files=("$dir/$group"-*.yaml)
    [[ ${#files[@]} -gt 0 ]] || { echo "No minikube/$group-*.yaml files" >&2; exit 1; }
    for f in "${files[@]}"; do
      printf -- '---\n# Source: minikube/%s\n' "$(basename "$f")"
      cat "$f"
      printf '\n'
    done
    ;;
  *)
    echo "usage: $0 site|practice-executor|db-access" >&2
    exit 2
    ;;
esac
