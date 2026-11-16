#!/usr/bin/env bash
# Promotion (services/www/docs/seo/PROMOTION.md): store the Reddit API client id and secret in Secret
# jithendar/jithendar-com-env. The Deployment already loads that Secret (envFrom), so no manifest changes are needed.
# The site only READS public subreddit listings with them (application-only OAuth); it never posts.
# Get them at https://www.reddit.com/prefs/apps → "create another app" → type "script". Run by a person:
#   KUBE_CONTEXT=mk4 scripts/set-reddit-config.sh
#   (kube context: KUBE_CONTEXT=<name>, else the current context with a confirmation prompt; scripts/lib/kube-context.sh)
# It MERGES keys into the existing Secret (other keys are kept) and prints no secret values.
# Then restart: kubectl -n jithendar rollout restart deployment/jithendar-com
set -euo pipefail
# shellcheck source=/dev/null
source "$(dirname -- "${BASH_SOURCE[0]}")/lib/kube-context.sh"
NS="jithendar"
command -v jq >/dev/null || { echo "jq is required" >&2; exit 1; }

read -r -p "Reddit app client id (the string under the app's name): " CLIENT_ID
[[ -n "$CLIENT_ID" ]] || { echo "The client id is required" >&2; exit 1; }
read -r -s -p "Reddit app secret: " CLIENT_SECRET; echo
[[ -n "$CLIENT_SECRET" ]] || { echo "The secret is required" >&2; exit 1; }
read -r -p "Your Reddit username, for the User-Agent Reddit asks for (optional, Enter to skip): " USERNAME
USERNAME="${USERNAME#u/}"
[[ -z "$USERNAME" || "$USERNAME" =~ ^[A-Za-z0-9_-]{3,20}$ ]] || { echo "That is not a Reddit username" >&2; exit 1; }
UA=""
if [[ -n "$USERNAME" ]]; then UA="web:com.jithendar.promotion:v1.0 (by /u/$USERNAME)"; fi

PATCH="$(jq -n --arg i "$CLIENT_ID" --arg s "$CLIENT_SECRET" --arg u "$UA" \
  '{data: ({REDDIT_CLIENT_ID: ($i | @base64), REDDIT_CLIENT_SECRET: ($s | @base64)} + (if $u == "" then {} else {REDDIT_USER_AGENT: ($u | @base64)} end))}')"
kubectl -n "$NS" get secret jithendar-com-env >/dev/null
kubectl -n "$NS" patch secret jithendar-com-env --type merge -p "$PATCH" >/dev/null
unset CLIENT_SECRET PATCH
echo "Secret $NS/jithendar-com-env: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET${UA:+ and REDDIT_USER_AGENT} set."
echo "Restart: kubectl -n $NS rollout restart deployment/jithendar-com"
echo "Then: Admin → Promotion → Settings → Test connection."
