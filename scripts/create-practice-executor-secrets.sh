#!/usr/bin/env bash
# Create (or rotate) the executor's Secret in namespace jithendar and give the site the matching token.
#   KUBE_CONTEXT=mk4 scripts/create-practice-executor-secrets.sh
#   (kube context: KUBE_CONTEXT=<name>, else the current context with a confirmation prompt; scripts/lib/kube-context.sh)
# Writes:
#   jithendar/practice-executor-env   EXECUTOR_API_TOKEN
#     (the queue is the shared Valkey: EXECUTOR_REDIS_URL comes from redis-practice-credentials, written by Terraform
#     in the miniKube repository)
#   jithendar/jithendar-com-env       PRACTICE_EXECUTOR_URL, PRACTICE_EXECUTOR_TOKEN (other keys are kept)
# Nothing is printed, written to disk or committed. Then restart the executor and the site (printed at the end).
set -euo pipefail
# shellcheck source=/dev/null
source "$(dirname -- "${BASH_SOURCE[0]}")/lib/kube-context.sh"
NS=jithendar
k() { kubectl -n "$NS" "$@"; }

k get secret jithendar-com-env >/dev/null
token=$(openssl rand -hex 32)

k create secret generic practice-executor-env \
  --from-literal=EXECUTOR_API_TOKEN="$token" \
  --dry-run=client -o yaml | k apply -f - >/dev/null

# Patch body on stdin, so the token never appears in a process list.
TOKEN="$token" python3 -c 'import json, os; print(json.dumps({"stringData": {
  "PRACTICE_EXECUTOR_URL": "http://practice-executor.jithendar",
  "PRACTICE_EXECUTOR_TOKEN": os.environ["TOKEN"]}}))' \
  | k patch secret jithendar-com-env --type merge --patch-file /dev/stdin >/dev/null
unset token

echo "Stored practice-executor-env and the site's PRACTICE_EXECUTOR_URL/TOKEN in $NS. Now restart both:"
echo "  kubectl -n $NS rollout restart deploy/practice-executor-api deploy/practice-dispatcher"
echo "  kubectl -n $NS rollout restart deploy/jithendar-com"
