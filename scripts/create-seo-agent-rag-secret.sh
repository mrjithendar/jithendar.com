#!/usr/bin/env bash
# Give the SEO agent access to the shared moks-rag service (rag-api, namespace rag) as Secret jithendar/seo-agent-rag.
#   KUBE_CONTEXT=mk4 scripts/create-seo-agent-rag-secret.sh
#   (kube context: KUBE_CONTEXT=<name>, else the current context with a confirmation prompt; scripts/lib/kube-context.sh)
# Writes:
#   jithendar/seo-agent-rag   RAG_API_URL, RAG_BEARER_TOKEN
# The token. With rag-api 0.2.0 the agent has its own, which may write seo_intel and read cms_content only: run
# `scripts/issue-service-token.sh moks-seo-agent` in a moks-rag checkout, which writes RAG_BEARER_TOKEN into this Secret.
# This script then only sets RAG_API_URL and keeps that token. Before that (or with rag-api 0.1.0) it copies rag-api's
# shared RAG_BEARER_TOKEN from rag/rag-secrets (a Secret cannot be read across namespaces); FORCE_SHARED_TOKEN=1 copies
# the shared one even over the agent's own. RAG_API_URL: $RAG_API_URL if set, otherwise rag-api's cluster address.
# Nothing is printed, written to disk or committed; tokens travel on stdin.
# Until this Secret exists the agent runs with moks-rag switched off (both keys are optional; the seo-agent container
# of the site's pods reads them, kubernetes/30-jithendar-com.yaml).
set -euo pipefail
# shellcheck source=/dev/null
source "$(dirname -- "${BASH_SOURCE[0]}")/lib/kube-context.sh"
NS=jithendar
url="${RAG_API_URL:-http://rag-api.rag.svc.cluster.local:8000}"

shared=$(kubectl -n rag get secret rag-secrets -o jsonpath='{.data.RAG_BEARER_TOKEN}' 2>/dev/null | base64 -d || true)
current=$(kubectl -n "$NS" get secret seo-agent-rag -o jsonpath='{.data.RAG_BEARER_TOKEN}' 2>/dev/null | base64 -d || true)

if [[ -n "$current" && "$current" != "$shared" && "${FORCE_SHARED_TOKEN:-0}" != "1" ]]; then
  token="$current"
  kept="the agent's own token (kept)"
else
  [[ -n "$shared" ]] || { echo "rag/rag-secrets has no RAG_BEARER_TOKEN (moks-rag README, step 1)." >&2; exit 1; }
  token="$shared"
  kept="rag-api's shared token (moks-rag scripts/issue-service-token.sh moks-seo-agent gives the agent its own)"
fi

RU="$url" RT="$token" python3 -c 'import json, os; print(json.dumps({
  "apiVersion": "v1", "kind": "Secret", "type": "Opaque",
  "metadata": {"name": "seo-agent-rag", "namespace": "jithendar", "labels": {"app": "seo-agent", "app.kubernetes.io/part-of": "jithendar-com"}},
  "stringData": {"RAG_API_URL": os.environ["RU"], "RAG_BEARER_TOKEN": os.environ["RT"]}}))' \
  | kubectl -n "$NS" apply -f - >/dev/null
unset token shared current

echo "Stored seo-agent-rag in $NS with $kept."
echo "Restart the site's pods to use it: the agent is their seo-agent container (moks-cms D-105), one pod at a time, no"
echo "downtime. A flow still running on a pod stops with it, so check AI & SEO → Flow runs first:"
echo "  kubectl -n $NS rollout restart deploy/jithendar-com"
