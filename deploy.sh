#!/usr/bin/env bash
# Deploy jithendar.com to the mk4 cluster: apply minikube/ (the site group), restart the site so it pulls jithendar-com:latest,
# wait and smoke-test. CI already restarts the site after every push to master; run this for manifest
# changes or a manual redeploy.
#
#   ./deploy.sh
#
# Started as `sh deploy.sh`? Re-run under full bash (macOS sh is bash in POSIX mode).
if [ -z "${BASH_VERSION:-}" ] || case ":${SHELLOPTS:-}:" in *:posix:*) true ;; *) false ;; esac; then
  exec bash "$0" "$@"
fi
set -euo pipefail

CONTEXT="${KUBE_CONTEXT:-mk4}"
k() { kubectl --context "$CONTEXT" "$@"; }

cd "$(dirname -- "${BASH_SOURCE[0]}")"

echo "→ Checking Secrets"
for s in jithendar-postgres jithendar-redis jithendar-com-env; do
  k -n jithendar get secret "$s" >/dev/null 2>&1 || {
    echo "Secret jithendar/$s is missing. Run scripts/create-secrets.sh once first." >&2
    exit 1
  }
done

echo "→ Validating against the cluster"
k apply -k minikube --dry-run=server >/dev/null

echo "→ Applying"
k apply -k minikube

echo "→ Waiting for Postgres and Redis"
k -n jithendar rollout status statefulset/jithendar-postgres --timeout=5m
k -n jithendar rollout status deployment/jithendar-redis --timeout=3m

echo "→ Restarting the site on jithendar-com:latest"
k -n jithendar rollout restart deployment/jithendar-com
if ! k -n jithendar rollout status deployment/jithendar-com --timeout=5m; then
  k -n jithendar get pods -l app=jithendar-com -o wide || true
  echo "Rollout failed. The old pods keep serving; fix the image and push again." >&2
  exit 1
fi

echo "→ Smoke test"
scripts/smoke.sh https://jithendar.com

echo "Deployed jithendar-com:latest."
