#!/usr/bin/env bash
# One-time: applies k8s/80-ci-deployer.yaml (a ServiceAccount that can only restart deployment/jithendar-com in
# namespace jithendar) and stores the values CI fills into the kubeconfig template .github/jithendar-ci-deployer.yaml:
#   MK4_API_SERVER  repository variable  cluster API URL         (from the mk4 context)
#   MK4_CA_DATA     repository variable  base64 CA certificate   (from the mk4 context)
#   MK4_CI_TOKEN    repository secret    ServiceAccount token    (from Secret jithendar/github-ci-deployer-token)
# ./deploy.sh also applies the manifest (it is in k8s/kustomization.yaml).
#
#   scripts/setup-ci-deployer.sh            # apply SA + Role + token, test the kubeconfig, store the values
#   SKIP_GH=1 scripts/setup-ci-deployer.sh  # only apply and test; set the values in GitHub yourself
#   ROTATE=1 scripts/setup-ci-deployer.sh   # replace the token (the old one stops working)
#
# The token goes straight into `gh secret set` (stdin) and is never printed. The script renders the template to a
# temporary file to check the kubeconfig can restart jithendar-com, then deletes it.
# Needs: kubectl with cluster-admin on context mk4; gh CLI signed in with admin on the repository (unless SKIP_GH=1).
# The cluster API (server in the mk4 context) must be reachable from GitHub-hosted runners.
set -euo pipefail

REPO="${GITHUB_REPO:-mrjithendar/jithendar.com}"
CONTEXT="${KUBE_CONTEXT:-mk4}"
NS="jithendar"
SA="github-ci-deployer"
TEMPLATE=".github/jithendar-ci-deployer.yaml"
k() { kubectl --context "$CONTEXT" "$@"; }

cd "$(dirname -- "${BASH_SOURCE[0]}")/.."

# get cluster endpoint: ex https://jithendar.com:32771
MK4_API_SERVER="$(kubectl config view --raw --minify --context "$CONTEXT" -o jsonpath='{.clusters[0].cluster.server}')"
# get cluster certificate-authority-data
MK4_CA_DATA="$(kubectl config view --raw --minify --context "$CONTEXT" -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')"
# if CA is empty, base64 the CA file the context points to instead
[[ -n "$MK4_CA_DATA" ]] || MK4_CA_DATA="$(base64 < "$(kubectl config view --raw --minify --context "$CONTEXT" -o jsonpath='{.clusters[0].cluster.certificate-authority}')" | tr -d '\n')"
# if SERVER or CA is empty script should exit
[[ -n "$MK4_API_SERVER" && -n "$MK4_CA_DATA" ]] || { echo "Could not read server/CA of context $CONTEXT." >&2; exit 1; }

echo "→ Cluster $MK4_API_SERVER, ServiceAccount $NS/$SA, repository $REPO"
if [[ "${ROTATE:-0}" == "1" ]]; then
  echo "→ Deleting the old token"
  k -n "$NS" delete secret "$SA-token" --ignore-not-found
fi

echo "→ Applying k8s/80-ci-deployer.yaml"
k apply -f k8s/80-ci-deployer.yaml

echo "→ Waiting for the token"
MK4_CI_TOKEN=""
for _ in $(seq 1 20); do
  MK4_CI_TOKEN="$(k -n "$NS" get secret "$SA-token" -o jsonpath='{.data.token}' 2>/dev/null | base64 -d || true)"
  [[ -n "$MK4_CI_TOKEN" ]] && break
  sleep 1
done
[[ -n "$MK4_CI_TOKEN" ]] || { echo "Token was not issued for $NS/$SA-token." >&2; exit 1; }
export MK4_API_SERVER MK4_CA_DATA MK4_CI_TOKEN

# Render the template exactly as the CI step does, and check the result can restart jithendar-com.
echo "→ Testing $TEMPLATE with these values"
KCFG="$(mktemp)" # create a temp file, save its path in KCFG
trap 'rm -f "$KCFG"' EXIT # delete it when the script exits, whether it succeeds or fails
# write the filled-in kubeconfig into it
perl -pe 's/\$\{(MK4_[A-Z_]+)\}/$ENV{$1}/g' "$TEMPLATE" > "$KCFG"

# test the login with $KCFG filled file
[[ "$(kubectl --kubeconfig "$KCFG" auth can-i patch deployment/jithendar-com -n "$NS")" == yes ]] \
  || { echo "The rendered kubeconfig cannot restart deployment/jithendar-com." >&2; exit 1; }

if [[ "${SKIP_GH:-0}" == "1" ]]; then
  cat <<EOF
Done. Set these in $REPO → Settings → Secrets and variables → Actions:
  Variable MK4_API_SERVER = $MK4_API_SERVER
  Variable MK4_CA_DATA    = output of: kubectl config view --raw --minify --context $CONTEXT -o jsonpath='{.clusters[0].cluster.certificate-authority-data}'
  Secret   MK4_CI_TOKEN   = copy with: kubectl --context $CONTEXT -n $NS get secret $SA-token -o jsonpath='{.data.token}' | base64 -d | pbcopy
EOF
  exit 0
fi

echo "→ Storing variables MK4_API_SERVER, MK4_CA_DATA and secret MK4_CI_TOKEN"
gh variable set MK4_API_SERVER --repo "$REPO" --body "$MK4_API_SERVER"
gh variable set MK4_CA_DATA --repo "$REPO" --body "$MK4_CA_DATA"
printf '%s' "$MK4_CI_TOKEN" | gh secret set MK4_CI_TOKEN --repo "$REPO"
unset MK4_CI_TOKEN

echo "Done: $REPO can now restart deployment/jithendar-com."
echo "The old secret KUBECONFIG_MK4 is no longer used; remove it with: gh secret delete KUBECONFIG_MK4 --repo $REPO"
