#!/usr/bin/env bash
# DataForSEO (services/www/docs/seo/DATAFORSEO.md): store the API login and password in Secret
# jithendar/jithendar-com-env. The Deployment already loads that Secret (envFrom), so no manifest changes are needed.
# Run by a person:
#   KUBE_CONTEXT=<name> scripts/set-dataforseo-config.sh
#   (kube context: KUBE_CONTEXT=<name>, else the current context with a confirmation prompt; scripts/lib/kube-context.sh)
# It MERGES the two keys into the existing Secret (other keys are kept) and prints no secret values.
# Then restart, and switch DataForSEO on in Admin → Automation & AI → Settings → Data sources.
set -euo pipefail
# shellcheck source=/dev/null
source "$(dirname -- "${BASH_SOURCE[0]}")/lib/kube-context.sh"
NS="jithendar"
command -v jq >/dev/null || { echo "jq is required" >&2; exit 1; }

read -r -p "DataForSEO API login (the e-mail on app.dataforseo.com → API Access): " LOGIN
[[ -n "$LOGIN" ]] || { echo "The login is required" >&2; exit 1; }
read -r -s -p "DataForSEO API password (not the dashboard password): " PASSWORD; echo
[[ -n "$PASSWORD" ]] || { echo "The password is required" >&2; exit 1; }

PATCH="$(jq -n --arg l "$LOGIN" --arg p "$PASSWORD" '{data: {DATAFORSEO_LOGIN: ($l | @base64), DATAFORSEO_PASSWORD: ($p | @base64)}}')"
kubectl -n "$NS" get secret jithendar-com-env >/dev/null
kubectl -n "$NS" patch secret jithendar-com-env --type merge -p "$PATCH" >/dev/null
echo "Secret $NS/jithendar-com-env: DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD set."
echo "Restart: kubectl -n $NS rollout restart deployment/jithendar-com"
echo "Then: Settings → Data sources → DataForSEO → Enabled, set the market and the monthly cap, and Integrations → DataForSEO → Run now."
