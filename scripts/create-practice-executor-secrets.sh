#!/usr/bin/env bash
# Create the executor's Secret in practice-exec and print the two values the site needs.
#   scripts/create-practice-executor-secrets.sh [context]
# Then add to Secret jithendar/jithendar-com-env:
#   PRACTICE_EXECUTOR_URL=http://practice-executor.practice-exec
#   PRACTICE_EXECUTOR_TOKEN=<the token printed below>
# Nothing is written to disk or committed. Re-running rotates the token (update the site's secret too).
set -euo pipefail
CTX="${1:-mk4}"
token=$(openssl rand -hex 32)
redis=$(openssl rand -hex 24)
kubectl --context "$CTX" get ns practice-exec >/dev/null
kubectl --context "$CTX" -n practice-exec create secret generic practice-executor-env \
  --from-literal=EXECUTOR_API_TOKEN="$token" \
  --from-literal=REDIS_PASSWORD="$redis" \
  --from-literal=EXECUTOR_REDIS_URL="redis://:$redis@practice-redis:6379/0" \
  --dry-run=client -o yaml | kubectl --context "$CTX" apply -f -
echo "PRACTICE_EXECUTOR_TOKEN=$token"
