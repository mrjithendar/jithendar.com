#!/usr/bin/env bash
# SEO intelligence platform (services/www/docs/seo/MANUAL_SETUP.md): store the Google service-account key and optional
# PageSpeed key in Secret jithendar/jithendar-com-env, and the property ids in ConfigMap jithendar-com-public.
# Both are already loaded by the Deployment (envFrom), so no manifest changes are needed. Run by a person:
#   KUBE_CONTEXT=mk4 scripts/set-seo-config.sh /path/to/service-account.json
#   (kube context: KUBE_CONTEXT=<name>, else the current context with a confirmation prompt; scripts/lib/kube-context.sh)
# It MERGES keys into the existing Secret/ConfigMap (other keys are kept) and prints no secret values.
# Then restart: kubectl -n jithendar rollout restart deployment/jithendar-com
set -euo pipefail
# shellcheck source=/dev/null
source "$(dirname -- "${BASH_SOURCE[0]}")/lib/kube-context.sh"
KEY_FILE="${1:?usage: $0 /path/to/service-account.json}"
NS="jithendar"
command -v jq >/dev/null || { echo "jq is required" >&2; exit 1; }
[[ -r "$KEY_FILE" ]] || { echo "Cannot read $KEY_FILE" >&2; exit 1; }
[[ "$(jq -r .type "$KEY_FILE")" == "service_account" ]] || { echo "$KEY_FILE is not a service-account key" >&2; exit 1; }
echo "Service account: $(jq -r .client_email "$KEY_FILE")"

read -r -p "Search Console property (sc-domain:jithendar.com or https://jithendar.com/) [sc-domain:jithendar.com]: " GSC
GSC="${GSC:-sc-domain:jithendar.com}"
read -r -p "GA4 numeric property id (Admin → Property details; not the G- id): " GA4
[[ "$GA4" =~ ^[0-9]+$ ]] || { echo "The GA4 property id is numeric" >&2; exit 1; }
read -r -s -p "PageSpeed Insights API key (optional, Enter to skip): " PSI; echo

B64="$(base64 < "$KEY_FILE" | tr -d '\n')"
PATCH="$(jq -n --arg k "$B64" --arg p "$PSI" '{data: ({GOOGLE_SEO_SERVICE_ACCOUNT_JSON: ($k | @base64)} + (if $p == "" then {} else {PAGESPEED_API_KEY: ($p | @base64)} end))}')"
kubectl -n "$NS" get secret jithendar-com-env >/dev/null
kubectl -n "$NS" patch secret jithendar-com-env --type merge -p "$PATCH" >/dev/null
echo "Secret $NS/jithendar-com-env: GOOGLE_SEO_SERVICE_ACCOUNT_JSON${PSI:+ and PAGESPEED_API_KEY} set."

if kubectl -n "$NS" get configmap jithendar-com-public >/dev/null 2>&1; then
  kubectl -n "$NS" patch configmap jithendar-com-public --type merge -p "$(jq -n --arg g "$GSC" --arg a "$GA4" '{data: {SEO_GSC_PROPERTY: $g, SEO_GA4_PROPERTY_ID: $a}}')" >/dev/null
else
  kubectl -n "$NS" create configmap jithendar-com-public --from-literal="SEO_GSC_PROPERTY=$GSC" --from-literal="SEO_GA4_PROPERTY_ID=$GA4" >/dev/null
fi
echo "ConfigMap $NS/jithendar-com-public: SEO_GSC_PROPERTY, SEO_GA4_PROPERTY_ID set."
echo "Restart: kubectl -n $NS rollout restart deployment/jithendar-com"
echo "Then: Admin → SEO intelligence → Integrations → Test connection."
