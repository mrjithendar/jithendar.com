#!/usr/bin/env bash
# Create (or rotate) the SEO v3 agent's Secret in namespace jithendar and give the site the matching tokens.
#   KUBE_CONTEXT=mk4 scripts/create-seo-agent-secrets.sh
#   (kube context: KUBE_CONTEXT=<name>, else the current context with a confirmation prompt; scripts/lib/kube-context.sh)
# Writes:
#   jithendar/seo-agent-env       ANTHROPIC_API_KEY, SEO_AGENT_TOKEN, SEO_AGENT_CALLBACK_TOKEN
#   jithendar/jithendar-com-env   SEO_AGENT_TOKEN, SEO_AGENT_CALLBACK_TOKEN (other keys are kept)
# ANTHROPIC_API_KEY: taken from $ANTHROPIC_API_KEY if set, otherwise copied from jithendar-com-env (the same key the v2
# drafting already uses; one key, one shared monthly budget). Two different random tokens: one per direction.
# Nothing is printed, written to disk or committed; secrets travel on stdin only. Restart commands are printed.
set -euo pipefail
# shellcheck source=/dev/null
source "$(dirname -- "${BASH_SOURCE[0]}")/lib/kube-context.sh"
NS=jithendar
k() { kubectl -n "$NS" "$@"; }

k get secret jithendar-com-env >/dev/null
agent_token=$(openssl rand -hex 32)
callback_token=$(openssl rand -hex 32)
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  ANTHROPIC_API_KEY=$(k get secret jithendar-com-env -o jsonpath='{.data.ANTHROPIC_API_KEY}' | base64 -d)
fi
[[ -n "$ANTHROPIC_API_KEY" ]] || { echo "ANTHROPIC_API_KEY is not set and not in jithendar-com-env." >&2; exit 1; }

AT="$agent_token" CT="$callback_token" AK="$ANTHROPIC_API_KEY" python3 -c 'import json, os; print(json.dumps({
  "apiVersion": "v1", "kind": "Secret", "type": "Opaque",
  "metadata": {"name": "seo-agent-env", "namespace": "jithendar", "labels": {"app.kubernetes.io/part-of": "jithendar-com"}},
  "stringData": {"ANTHROPIC_API_KEY": os.environ["AK"], "SEO_AGENT_TOKEN": os.environ["AT"], "SEO_AGENT_CALLBACK_TOKEN": os.environ["CT"]}}))' \
  | k apply -f - >/dev/null

AT="$agent_token" CT="$callback_token" python3 -c 'import json, os; print(json.dumps({"stringData": {
  "SEO_AGENT_TOKEN": os.environ["AT"], "SEO_AGENT_CALLBACK_TOKEN": os.environ["CT"]}}))' \
  | k patch secret jithendar-com-env --type merge --patch-file /dev/stdin >/dev/null
unset agent_token callback_token ANTHROPIC_API_KEY

echo "Stored seo-agent-env and the site's SEO_AGENT_TOKEN / SEO_AGENT_CALLBACK_TOKEN in $NS. Restart the site's pods (the"
echo "web app and the agent are two containers of each, moks-cms D-105, so one restart gives both the new tokens):"
echo "  kubectl -n $NS rollout restart deploy/jithendar-com"
