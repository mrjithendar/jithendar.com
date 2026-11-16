#!/usr/bin/env bash
# AI visibility (services/www/docs/seo/AI_VISIBILITY.md): store the optional assistant API keys (OpenAI, Perplexity,
# Gemini) in Secret jithendar/jithendar-com-env. The Deployment already loads that Secret (envFrom), so no manifest
# changes are needed. Claude uses the existing ANTHROPIC_API_KEY; Google AI Overview uses the DataForSEO credentials.
# Run by a person:
#   KUBE_CONTEXT=<name> scripts/set-ai-visibility-config.sh
#   (kube context: KUBE_CONTEXT=<name>, else the current context with a confirmation prompt; scripts/lib/kube-context.sh)
# Each key is optional (Enter skips it); the given ones are MERGED into the Secret and no value is printed.
set -euo pipefail
# shellcheck source=/dev/null
source "$(dirname -- "${BASH_SOURCE[0]}")/lib/kube-context.sh"
NS="jithendar"
command -v jq >/dev/null || { echo "jq is required" >&2; exit 1; }

read -r -s -p "OpenAI API key for ChatGPT (Enter to skip): " OPENAI; echo
read -r -s -p "Perplexity API key (Enter to skip): " PPLX; echo
read -r -s -p "Gemini API key (Enter to skip): " GEMINI; echo
[[ -n "$OPENAI$PPLX$GEMINI" ]] || { echo "Nothing to set." >&2; exit 1; }

PATCH="$(jq -n --arg o "$OPENAI" --arg p "$PPLX" --arg g "$GEMINI" '{data: ((if $o == "" then {} else {OPENAI_API_KEY: ($o | @base64)} end) + (if $p == "" then {} else {PERPLEXITY_API_KEY: ($p | @base64)} end) + (if $g == "" then {} else {GEMINI_API_KEY: ($g | @base64)} end))}')"
kubectl -n "$NS" get secret jithendar-com-env >/dev/null
kubectl -n "$NS" patch secret jithendar-com-env --type merge -p "$PATCH" >/dev/null
echo "Secret $NS/jithendar-com-env:${OPENAI:+ OPENAI_API_KEY}${PPLX:+ PERPLEXITY_API_KEY}${GEMINI:+ GEMINI_API_KEY} set."
echo "Restart: kubectl -n $NS rollout restart deployment/jithendar-com"
echo "Then: Settings → AI & drafts → AI visibility: enable the assistants (ChatGPT and Gemini also need a model id)."
