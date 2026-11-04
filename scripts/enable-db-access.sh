#!/usr/bin/env bash
# One-time, from the owner's Mac: the privileged steps behind database access through the ingress
# (Adminer at https://jithendar.com/db/, PostgreSQL at db.jithendar.com:443; see k8s/db-access/README.md).
# Everything else (the k8s/db-access objects, the DNS record) is deployed by .github/workflows/deploy-minikube.yml.
#
#   HOST_SSH=root@jithendar.com scripts/enable-db-access.sh    # also runs the HAProxy step on the host over SSH
#   scripts/enable-db-access.sh                                 # prints the host command instead and waits
#
# Steps, each skipped when already done, each checked before the next:
#   1. Traefik trusts the PROXY protocol from the minikube network (helm upgrade with tools' values file).
#   2. The host's HAProxy sends it (tools deploy/minikube/expose-ingress.sh, on the host).
#   3. Check: the site now logs this Mac's real IP, not a node's.
#   4. The PostgreSQL login jithendar_remote (scripts/create-db-remote-user.sh, prints the password once).
#   5. CI's applier Role gets the db-access kinds (k8s/85-ci-applier.yaml; CI cannot change its own Role).
#   6. Run the deploy workflow (gh), unless NO_DEPLOY=1.
#
# Needs: kubectl and helm with admin on context mk4, a tools checkout (TOOLS_DIR, default ../tools), gh signed in.
# Undo: k8s/db-access/README.md → Rollback.
set -euo pipefail

CONTEXT="${KUBE_CONTEXT:-mk4}"
REPO="${GITHUB_REPO:-mrjithendar/jithendar.com}"
cd "$(dirname -- "${BASH_SOURCE[0]}")/.."
TOOLS_DIR="${TOOLS_DIR:-../tools}"
HOST_TOOLS_DIR="${HOST_TOOLS_DIR:-tools}"
VALUES="$TOOLS_DIR/deploy/minikube/traefik/values.yaml"
k() { kubectl --context "$CONTEXT" "$@"; }
fail() { echo "ERROR: $*" >&2; exit 1; }
site_ok() { [[ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 https://jithendar.com/api/health)" == 200 ]]; }

[[ -f "$VALUES" ]] || fail "$VALUES not found; set TOOLS_DIR to your tools checkout."
grep -q 'proxyProtocol' "$VALUES" || fail "$VALUES has no proxyProtocol settings; pull the tools repo."

echo "→ 1. Traefik accepts the PROXY protocol"
if k -n traefik get deploy traefik -o jsonpath='{.spec.template.spec.containers[0].args}' | grep -q 'websecure.proxyProtocol.trustedIPs'; then
  echo "   already enabled"
else
  version="$(helm --kube-context "$CONTEXT" -n traefik list -f '^traefik$' -o json | jq -r '.[0].chart' | sed 's/^traefik-//')"
  [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "Could not read the installed Traefik chart version."
  helm --kube-context "$CONTEXT" upgrade traefik traefik --repo https://traefik.github.io/charts --version "$version" \
    --namespace traefik -f "$VALUES" --wait --timeout 5m
  k -n traefik rollout status deploy/traefik --timeout=3m
fi
site_ok || fail "https://jithendar.com/api/health is not 200 after the Traefik step; roll back with: helm --kube-context $CONTEXT -n traefik rollback traefik"

echo "→ 2 + 3. HAProxy on the host sends client IPs"
probe="db-access-probe-$RANDOM$RANDOM"
seen_ip() {
  curl -s -o /dev/null --max-time 10 -A "$probe" https://jithendar.com/robots.txt || true
  sleep 3
  k -n jithendar logs -l app=jithendar-com --since=2m --max-log-requests=4 2>/dev/null \
    | grep -F "\"userAgent\":\"$probe\"" | grep -o '"ip":"[^"]*"' | tail -1 | cut -d'"' -f4
}
ip="$(seen_ip)"
if [[ -z "$ip" || "$ip" == 192.168.49.* ]]; then
  # The host pulls tools from GitHub, so the HAProxy change must be pushed, not only committed here.
  git -C "$TOOLS_DIR" fetch -q origin master
  git -C "$TOOLS_DIR" show origin/master:deploy/minikube/expose-ingress.sh | grep -q 'send-proxy-v2' \
    || fail "tools on GitHub (origin/master) has no send-proxy-v2 in deploy/minikube/expose-ingress.sh: commit and push tools first."
  host_cmd="cd $HOST_TOOLS_DIR && git pull --ff-only && grep -q send-proxy-v2 deploy/minikube/expose-ingress.sh && bash deploy/minikube/expose-ingress.sh"
  if [[ -n "${HOST_SSH:-}" ]]; then
    # shellcheck disable=SC2029  # expanded here on purpose: the command is built from local settings
    ssh "$HOST_SSH" "$host_cmd"
  else
    echo "   On the Hetzner host, run:  $host_cmd"
    read -r -p "   Press Enter when it has finished… " _
  fi
  site_ok || fail "The site is not answering after the HAProxy step. On the host: remove send-proxy-v2 and rerun expose-ingress.sh."
  ip="$(seen_ip)"
fi
[[ -n "$ip" && "$ip" != 192.168.49.* ]] || fail "The site still sees '${ip:-nothing}' instead of a public IP; check HAProxy on the host."
echo "   the site sees this Mac as $ip"
grep -q -- "- $ip/32" k8s/db-access/allowlist.yaml \
  || echo "   NOTE: $ip is not in k8s/db-access/allowlist.yaml. Add it to both lists and push, or /db stays closed to this Mac."

echo "→ 4. PostgreSQL login"
if k -n jithendar get secret jithendar-db-remote >/dev/null 2>&1; then
  echo "   jithendar_remote exists (rotate with scripts/create-db-remote-user.sh)"
else
  bash scripts/create-db-remote-user.sh
fi

echo "→ 5. CI applier permissions"
k apply -f k8s/85-ci-applier.yaml >/dev/null
echo "   k8s/85-ci-applier.yaml applied"

if [[ "${NO_DEPLOY:-0}" != 1 ]]; then
  echo "→ 6. Deploy workflow"
  gh workflow run deploy-minikube.yml --repo "$REPO" --ref master
  echo "   started; follow it with: gh run watch --repo $REPO"
fi
cat <<OUT

Then, from an allowed IP:
  https://jithendar.com/db/   System PostgreSQL, Server jithendar-postgres, user jithendar_remote, database jithendar
  psql "host=db.jithendar.com port=443 dbname=jithendar user=jithendar_remote sslmode=verify-full sslrootcert=system"
OUT
