#!/usr/bin/env bash
# Makes sure a DNS-only A record exists in Cloudflare and points where the apex (jithendar.com) points:
#
#   CLOUDFLARE_DNS_TOKEN=… scripts/cloudflare-dns-record.sh db.jithendar.com
#
# Idempotent: creates the record, fixes its address or proxy flag, or does nothing. Never deletes records.
# Used by .github/workflows/deploy-minikube.yml for db.jithendar.com (k8s/db-access): PostgreSQL is not HTTP, so the
# record must stay DNS only (proxied=false).
# The token needs Zone → DNS → Edit on the jithendar.com zone only (Cloudflare → My Profile → API Tokens);
# store it as the repository secret CLOUDFLARE_DNS_TOKEN. Needs curl and jq.
set -euo pipefail
NAME="${1:?usage: cloudflare-dns-record.sh <name.jithendar.com>}"
ZONE="${CLOUDFLARE_ZONE:-jithendar.com}"
: "${CLOUDFLARE_DNS_TOKEN:?CLOUDFLARE_DNS_TOKEN is not set}"
[[ "$NAME" == *."$ZONE" ]] || { echo "$NAME is not in zone $ZONE" >&2; exit 1; }
API=https://api.cloudflare.com/client/v4

cf() {
  local out
  out="$(curl -sS --max-time 20 -H "Authorization: Bearer $CLOUDFLARE_DNS_TOKEN" -H 'Content-Type: application/json' "$@")"
  jq -e '.success' >/dev/null <<<"$out" || { echo "Cloudflare API error: $(jq -c '.errors' <<<"$out" 2>/dev/null || echo "$out")" >&2; exit 1; }
  printf '%s' "$out"
}

zone_id="$(cf "$API/zones?name=$ZONE" | jq -r '.result[0].id // empty')"
[[ -n "$zone_id" ]] || { echo "Zone $ZONE not found for this token." >&2; exit 1; }

ip="$(cf "$API/zones/$zone_id/dns_records?type=A&name=$ZONE" | jq -r '.result[0].content // empty')"
[[ "$ip" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]] || { echo "No A record for $ZONE to copy." >&2; exit 1; }

body="$(jq -nc --arg name "$NAME" --arg ip "$ip" '{type: "A", name: $name, content: $ip, ttl: 300, proxied: false, comment: "k8s/db-access (deploy-minikube.yml)"}')"
record="$(cf "$API/zones/$zone_id/dns_records?type=A&name=$NAME" | jq -c '.result[0] // empty')"
if [[ -z "$record" ]]; then
  cf -X POST "$API/zones/$zone_id/dns_records" --data "$body" >/dev/null
  echo "Created $NAME → $ip (DNS only)."
elif [[ "$(jq -r '.content' <<<"$record")" != "$ip" || "$(jq -r '.proxied' <<<"$record")" != false ]]; then
  cf -X PATCH "$API/zones/$zone_id/dns_records/$(jq -r '.id' <<<"$record")" --data "$body" >/dev/null
  echo "Updated $NAME → $ip (DNS only)."
else
  echo "$NAME → $ip already in place."
fi
