#!/usr/bin/env bash
# Give the SEO agent access to the shared moks-rag service (rag-api, namespace rag) as Secret jithendar/seo-agent-rag.
#   KUBE_CONTEXT=mk4 scripts/create-seo-agent-rag-secret.sh
#   (kube context: KUBE_CONTEXT=<name>, else the current context with a confirmation prompt; scripts/lib/kube-context.sh)
# Writes:
#   jithendar/seo-agent-rag   RAG_API_URL, RAG_BEARER_TOKEN
# RAG_BEARER_TOKEN is copied from rag/rag-secrets (moks-rag's own Secret; a Secret cannot be read across namespaces).
# rag-api has one token for every caller, so rotate it there and run this again. RAG_API_URL: $RAG_API_URL if set,
# otherwise rag-api's cluster address. Nothing is printed, written to disk or committed; the token travels on stdin.
# Until this Secret exists the agent runs with moks-rag switched off (both keys are optional in seo-agent-40).
set -euo pipefail
# shellcheck source=/dev/null
source "$(dirname -- "${BASH_SOURCE[0]}")/lib/kube-context.sh"
NS=jithendar
url="${RAG_API_URL:-http://rag-api.rag.svc.cluster.local:8000}"

token=$(kubectl -n rag get secret rag-secrets -o jsonpath='{.data.RAG_BEARER_TOKEN}' | base64 -d)
[[ -n "$token" ]] || { echo "rag/rag-secrets has no RAG_BEARER_TOKEN (moks-rag README, step 1)." >&2; exit 1; }

RU="$url" RT="$token" python3 -c 'import json, os; print(json.dumps({
  "apiVersion": "v1", "kind": "Secret", "type": "Opaque",
  "metadata": {"name": "seo-agent-rag", "namespace": "jithendar", "labels": {"app": "seo-agent", "app.kubernetes.io/part-of": "jithendar-com"}},
  "stringData": {"RAG_API_URL": os.environ["RU"], "RAG_BEARER_TOKEN": os.environ["RT"]}}))' \
  | kubectl -n "$NS" apply -f - >/dev/null
unset token

echo "Stored seo-agent-rag in $NS. Restart the agent to use it (Recreate: check that no flow is running first):"
echo "  kubectl -n $NS rollout restart deploy/seo-agent"
