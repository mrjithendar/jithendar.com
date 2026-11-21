#!/usr/bin/env bash
# Create (or rotate) the news agent's Secret in namespace jithendar, and give the site and the seo-agent the matching
# tokens (mrjithendar/newsroom; moks-cms docs/news/MANUAL_SETUP.md §2).
#   KUBE_CONTEXT=mk4 scripts/create-news-agent-secrets.sh
#   (kube context: KUBE_CONTEXT=<name>, else the current context with a confirmation prompt; scripts/lib/kube-context.sh)
# Writes:
#   jithendar/news-agent-env      NEWS_AGENT_TOKEN, NEWS_AGENT_CALLBACK_TOKEN, SEO_AGENT_NEWS_TOKEN, ANTHROPIC_API_KEY,
#                                 OPENAI_API_KEY (only when one is given or already there)
#   jithendar/jithendar-com-env   NEWS_AGENT_TOKEN, NEWS_AGENT_CALLBACK_TOKEN (other keys are kept)
#   jithendar/seo-agent-env       SEO_AGENT_NEWS_TOKEN (other keys are kept): /search and the one LLM budget's holds only
# ANTHROPIC_API_KEY: $NEWS_ANTHROPIC_API_KEY if set (recommended: a key of its own Anthropic Console workspace, with that
# workspace's spend limit), else the one already in news-agent-env, else the seo-agent's (seo-agent-env).
# OPENAI_API_KEY: $NEWS_OPENAI_API_KEY if set, else kept from news-agent-env, else copied from seo-agent-env if there.
# Three different random tokens, one per caller and direction. Nothing is printed, written to disk or committed;
# secrets travel on stdin only. Restart commands are printed.
set -euo pipefail
# shellcheck source=/dev/null
source "$(dirname -- "${BASH_SOURCE[0]}")/lib/kube-context.sh"
NS=jithendar
k() { kubectl -n "$NS" "$@"; }
key_of() { k get secret "$1" -o jsonpath="{.data.$2}" --ignore-not-found 2>/dev/null | base64 -d 2>/dev/null || true; }

k get secret jithendar-com-env >/dev/null
k get secret seo-agent-env >/dev/null
agent_token=$(openssl rand -hex 32)
callback_token=$(openssl rand -hex 32)
seo_news_token=$(openssl rand -hex 32)
anthropic="${NEWS_ANTHROPIC_API_KEY:-}"
[[ -n "$anthropic" ]] || anthropic=$(key_of news-agent-env ANTHROPIC_API_KEY)
if [[ -z "$anthropic" ]]; then
  anthropic=$(key_of seo-agent-env ANTHROPIC_API_KEY)
  [[ -n "$anthropic" ]] && echo "Note: ANTHROPIC_API_KEY copied from seo-agent-env. Set NEWS_ANTHROPIC_API_KEY to give the news agent a workspace of its own."
fi
[[ -n "$anthropic" ]] || { echo "No ANTHROPIC_API_KEY: set NEWS_ANTHROPIC_API_KEY." >&2; exit 1; }
openai="${NEWS_OPENAI_API_KEY:-}"
[[ -n "$openai" ]] || openai=$(key_of news-agent-env OPENAI_API_KEY)
[[ -n "$openai" ]] || openai=$(key_of seo-agent-env OPENAI_API_KEY)

AT="$agent_token" CT="$callback_token" ST="$seo_news_token" AK="$anthropic" OK="$openai" python3 -c 'import json, os
data = {"NEWS_AGENT_TOKEN": os.environ["AT"], "NEWS_AGENT_CALLBACK_TOKEN": os.environ["CT"], "SEO_AGENT_NEWS_TOKEN": os.environ["ST"], "ANTHROPIC_API_KEY": os.environ["AK"]}
if os.environ["OK"]:
    data["OPENAI_API_KEY"] = os.environ["OK"]
print(json.dumps({"apiVersion": "v1", "kind": "Secret", "type": "Opaque",
  "metadata": {"name": "news-agent-env", "namespace": "jithendar", "labels": {"app.kubernetes.io/part-of": "jithendar-com"}},
  "stringData": data}))' \
  | k apply -f - >/dev/null

AT="$agent_token" CT="$callback_token" python3 -c 'import json, os; print(json.dumps({"stringData": {
  "NEWS_AGENT_TOKEN": os.environ["AT"], "NEWS_AGENT_CALLBACK_TOKEN": os.environ["CT"]}}))' \
  | k patch secret jithendar-com-env --type merge --patch-file /dev/stdin >/dev/null
ST="$seo_news_token" python3 -c 'import json, os; print(json.dumps({"stringData": {"SEO_AGENT_NEWS_TOKEN": os.environ["ST"]}}))' \
  | k patch secret seo-agent-env --type merge --patch-file /dev/stdin >/dev/null
unset agent_token callback_token seo_news_token anthropic openai

echo "Stored news-agent-env, the site's NEWS_AGENT_TOKEN / NEWS_AGENT_CALLBACK_TOKEN and the seo-agent's SEO_AGENT_NEWS_TOKEN in $NS."
echo "Restart all three (seo-agent: check its logs for a running flow first, it is Recreate):"
echo "  kubectl -n $NS rollout restart deploy/seo-agent"
echo "  kubectl -n $NS rollout restart deploy/jithendar-com"
echo "  kubectl -n $NS rollout restart deploy/news-agent   # if it exists yet"
