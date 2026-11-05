#!/usr/bin/env bash
# Creates Secret cert-manager/cloudflare-api-token (key api-token) for the DNS-01 ClusterIssuers in
# minikube/45-jithendar-letsencrypt.yaml. Run once from the Mac, before applying that file.
#
# Token: Cloudflare → My Profile → API Tokens → Create Token, permissions Zone:DNS:Edit and Zone:Zone:Read, zone
# resources "jithendar.com" only. Use a new token, not CI's CLOUDFLARE_DNS_TOKEN, so either can be revoked alone.
# The token is read without echo and sent to the API server on stdin; it is never printed or written to disk.
set -euo pipefail
CONTEXT="${KUBE_CONTEXT:-mk4}"
k() { kubectl --context="$CONTEXT" "$@"; }
if k -n cert-manager get secret cloudflare-api-token >/dev/null 2>&1 && [[ "${1:-}" != --replace ]]; then
  echo "Secret cert-manager/cloudflare-api-token exists; pass --replace to rotate it."; exit 0
fi
read -r -s -p 'Cloudflare API token (Zone:DNS:Edit, Zone:Zone:Read, jithendar.com): ' token; echo
[[ -n "$token" ]] || { echo 'No token entered.' >&2; exit 1; }
# printf is a shell builtin (no process argument list) and adds no trailing newline to the token.
printf '%s' "$token" | k -n cert-manager create secret generic cloudflare-api-token --from-file=api-token=/dev/stdin \
  --dry-run=client -o yaml | k apply -f - >/dev/null
unset token
echo 'Created Secret cert-manager/cloudflare-api-token (value not shown).'
