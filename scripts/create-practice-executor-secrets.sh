#!/usr/bin/env bash
# Create (or rotate) the executor's Secret in namespace jithendar and give the site the matching token.
#   scripts/create-practice-executor-secrets.sh [context]
# Writes:
#   jithendar/practice-executor-env   EXECUTOR_API_TOKEN, REDIS_PASSWORD, EXECUTOR_REDIS_URL
#   jithendar/jithendar-com-env       PRACTICE_EXECUTOR_URL, PRACTICE_EXECUTOR_TOKEN (other keys are kept)
# Nothing is printed, written to disk or committed. Then restart the executor and the site (printed at the end).
set -euo pipefail
CTX="${1:-mk4}"
NS=jithendar
k() { kubectl --context "$CTX" -n "$NS" "$@"; }

k get secret jithendar-com-env >/dev/null
token=$(openssl rand -hex 32)
redis=$(openssl rand -hex 24)

k create secret generic practice-executor-env \
  --from-literal=EXECUTOR_API_TOKEN="$token" \
  --from-literal=REDIS_PASSWORD="$redis" \
  --from-literal=EXECUTOR_REDIS_URL="redis://:$redis@practice-redis:6379/0" \
  --dry-run=client -o yaml | k apply -f - >/dev/null

# Patch body on stdin, so the token never appears in a process list.
TOKEN="$token" python3 -c 'import json, os; print(json.dumps({"stringData": {
  "PRACTICE_EXECUTOR_URL": "http://practice-executor.jithendar",
  "PRACTICE_EXECUTOR_TOKEN": os.environ["TOKEN"]}}))' \
  | k patch secret jithendar-com-env --type merge --patch-file /dev/stdin >/dev/null
unset token redis

echo "Stored practice-executor-env and the site's PRACTICE_EXECUTOR_URL/TOKEN in $NS. Now restart both:"
echo "  kubectl --context $CTX -n $NS rollout restart deploy/practice-redis deploy/practice-executor-api deploy/practice-dispatcher"
echo "  kubectl --context $CTX -n $NS rollout restart deploy/jithendar-com"
