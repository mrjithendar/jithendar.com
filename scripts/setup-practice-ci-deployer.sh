#!/usr/bin/env bash
# One-time: lets CI roll out the Python practice executor (ci-practice-executor.yml, job "deploy").
# Applies k8s/practice-executor/90-ci-deployer.yaml (ServiceAccount practice-exec/practice-ci-deployer, which may only
# repoint the executor Deployments and the sandbox runtime map at new image digests) and stores its token as:
#   PRACTICE_CI_TOKEN  repository secret
# The kubeconfig template .github/jithendar-ci-deployer.yaml also needs MK4_API_SERVER and MK4_CA_DATA, which
# scripts/setup-ci-deployer.sh already stored for the site.
#
#   scripts/setup-practice-ci-deployer.sh            # apply SA + Role + token, test the kubeconfig, store the token
#   SKIP_GH=1 scripts/setup-practice-ci-deployer.sh  # only apply and test; set the secret in GitHub yourself
#   ROTATE=1 scripts/setup-practice-ci-deployer.sh   # replace the token (the old one stops working)
#
# Deploys stay off until you also set repository variable PRACTICE_EXECUTOR_DEPLOY=true, which you should do only
# after scripts/verify-practice-sandbox.sh passes (www/docs/PYTHON_PRACTICE_EXECUTOR.md).
# Needs: kubectl with cluster-admin on context mk4, namespace practice-exec already applied (kubectl apply -k
# k8s/practice-executor); gh CLI signed in with admin on the repository (unless SKIP_GH=1).
set -euo pipefail

REPO="${GITHUB_REPO:-mrjithendar/jithendar.com}"
CONTEXT="${KUBE_CONTEXT:-mk4}"
NS="practice-exec"
SA="practice-ci-deployer"
TEMPLATE=".github/jithendar-ci-deployer.yaml"
k() { kubectl --context "$CONTEXT" "$@"; }

cd "$(dirname -- "${BASH_SOURCE[0]}")/.."

k get namespace "$NS" >/dev/null || { echo "Namespace $NS is missing: apply k8s/practice-executor first." >&2; exit 1; }

MK4_API_SERVER="$(kubectl config view --raw --minify --context "$CONTEXT" -o jsonpath='{.clusters[0].cluster.server}')"
MK4_CA_DATA="$(kubectl config view --raw --minify --context "$CONTEXT" -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')"
[[ -n "$MK4_CA_DATA" ]] || MK4_CA_DATA="$(base64 < "$(kubectl config view --raw --minify --context "$CONTEXT" -o jsonpath='{.clusters[0].cluster.certificate-authority}')" | tr -d '\n')"
[[ -n "$MK4_API_SERVER" && -n "$MK4_CA_DATA" ]] || { echo "Could not read server/CA of context $CONTEXT." >&2; exit 1; }

echo "→ Cluster $MK4_API_SERVER, ServiceAccount $NS/$SA, repository $REPO"
if [[ "${ROTATE:-0}" == "1" ]]; then
  echo "→ Deleting the old token"
  k -n "$NS" delete secret "$SA-token" --ignore-not-found
fi

echo "→ Applying k8s/practice-executor/90-ci-deployer.yaml"
k apply -f k8s/practice-executor/90-ci-deployer.yaml

echo "→ Waiting for the token"
MK4_CI_TOKEN=""
for _ in $(seq 1 20); do
  MK4_CI_TOKEN="$(k -n "$NS" get secret "$SA-token" -o jsonpath='{.data.token}' 2>/dev/null | base64 -d || true)"
  [[ -n "$MK4_CI_TOKEN" ]] && break
  sleep 1
done
[[ -n "$MK4_CI_TOKEN" ]] || { echo "Token was not issued for $NS/$SA-token." >&2; exit 1; }
export MK4_API_SERVER MK4_CA_DATA MK4_CI_TOKEN

# Render the template exactly as the CI step does, and check what the token can and cannot do.
echo "→ Testing the rendered kubeconfig"
KCFG="$(mktemp)"
trap 'rm -f "$KCFG"' EXIT
perl -pe 's/\$\{(MK4_[A-Z_]+)\}/$ENV{$1}/g' "$TEMPLATE" > "$KCFG"
can() { kubectl --kubeconfig "$KCFG" auth can-i "$@" 2>/dev/null || true; }
for check in "patch deployment/practice-executor-api -n $NS" "patch deployment/practice-dispatcher -n $NS" \
             "patch configmap/practice-executor-config -n $NS"; do
  # shellcheck disable=SC2086
  [[ "$(can $check)" == yes ]] || { echo "The token cannot: $check" >&2; exit 1; }
done
for check in "get secrets -n $NS" "create pods -n $NS" "create pods -n practice-sandbox" \
             "patch deployment/jithendar-com -n jithendar" "patch runtimeclass/gvisor-nonet"; do
  # shellcheck disable=SC2086
  [[ "$(can $check)" == no ]] || { echo "The token is allowed too much: $check" >&2; exit 1; }
done

if [[ "${SKIP_GH:-0}" == "1" ]]; then
  cat <<EOF
Done. Set in $REPO → Settings → Secrets and variables → Actions:
  Secret PRACTICE_CI_TOKEN = copy with: kubectl --context $CONTEXT -n $NS get secret $SA-token -o jsonpath='{.data.token}' | base64 -d | pbcopy
Then, once scripts/verify-practice-sandbox.sh passes: variable PRACTICE_EXECUTOR_DEPLOY = true
EOF
  exit 0
fi

echo "→ Storing secret PRACTICE_CI_TOKEN"
printf '%s' "$MK4_CI_TOKEN" | gh secret set PRACTICE_CI_TOKEN --repo "$REPO"
unset MK4_CI_TOKEN
gh variable get MK4_API_SERVER --repo "$REPO" >/dev/null 2>&1 \
  || echo "Variable MK4_API_SERVER is not set: run scripts/setup-ci-deployer.sh too." >&2

echo "Done. Deploys start once you set: gh variable set PRACTICE_EXECUTOR_DEPLOY --repo $REPO --body true"
echo "(only after scripts/verify-practice-sandbox.sh passes)."
