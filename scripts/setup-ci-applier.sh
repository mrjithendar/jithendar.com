#!/usr/bin/env bash
# One-time: applies minikube/85-ci-applier.yaml (a ServiceAccount that may create and update the application objects in
# namespace jithendar, nothing else) and stores what .github/workflows/deploy-minikube.yml needs:
#   MK4_CI_APPLY_TOKEN       repository secret    ServiceAccount token (from Secret jithendar/github-ci-applier-token)
#   MINIKUBE_DEPLOY = true   repository variable  turns the workflow's deploy job on
# MK4_API_SERVER and MK4_CA_DATA are shared with the restart-only deployer: run scripts/setup-ci-deployer.sh first
# if they are not set yet. ./deploy.sh also applies the manifest (it is in minikube/kustomization.yaml).
#
#   scripts/setup-ci-applier.sh            # apply SA + Role + token, test the kubeconfig, store the values
#   SKIP_GH=1 scripts/setup-ci-applier.sh  # only apply and test; set the values in GitHub yourself
#   ROTATE=1 scripts/setup-ci-applier.sh   # replace the token (the old one stops working)
#
# The token goes straight into `gh secret set` (stdin) and is never printed.
# Needs: kubectl with cluster-admin on context mk4; gh CLI signed in with admin on the repository (unless SKIP_GH=1).
set -euo pipefail

REPO="${GITHUB_REPO:-mrjithendar/jithendar.com}"
CONTEXT="${KUBE_CONTEXT:-mk4}"
NS="jithendar"
SA="github-ci-applier"
TEMPLATE=".github/jithendar-ci-applier.yaml"
k() { kubectl --context "$CONTEXT" "$@"; }

cd "$(dirname -- "${BASH_SOURCE[0]}")/.."
python3 -c "import yaml" 2>/dev/null || { echo "scripts/ci-app-manifests.py needs PyYAML: python3 -m pip install --user pyyaml==6.0.3" >&2; exit 1; }

MK4_API_SERVER="$(kubectl config view --raw --minify --context "$CONTEXT" -o jsonpath='{.clusters[0].cluster.server}')"
MK4_CA_DATA="$(kubectl config view --raw --minify --context "$CONTEXT" -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')"
[[ -n "$MK4_CA_DATA" ]] || MK4_CA_DATA="$(base64 < "$(kubectl config view --raw --minify --context "$CONTEXT" -o jsonpath='{.clusters[0].cluster.certificate-authority}')" | tr -d '\n')"
[[ -n "$MK4_API_SERVER" && -n "$MK4_CA_DATA" ]] || { echo "Could not read server/CA of context $CONTEXT." >&2; exit 1; }

echo "→ Cluster $MK4_API_SERVER, ServiceAccount $NS/$SA, repository $REPO"
if [[ "${ROTATE:-0}" == "1" ]]; then
  echo "→ Deleting the old token"
  k -n "$NS" delete secret "$SA-token" --ignore-not-found
fi

echo "→ Applying minikube/85-ci-applier.yaml"
k apply -f minikube/85-ci-applier.yaml

echo "→ Waiting for the token"
MK4_CI_APPLY_TOKEN=""
for _ in $(seq 1 20); do
  MK4_CI_APPLY_TOKEN="$(k -n "$NS" get secret "$SA-token" -o jsonpath='{.data.token}' 2>/dev/null | base64 -d || true)"
  [[ -n "$MK4_CI_APPLY_TOKEN" ]] && break
  sleep 1
done
[[ -n "$MK4_CI_APPLY_TOKEN" ]] || { echo "Token was not issued for $NS/$SA-token." >&2; exit 1; }
export MK4_API_SERVER MK4_CA_DATA MK4_CI_APPLY_TOKEN

# Render the template exactly as the workflow does; check what it may and may not do.
echo "→ Testing $TEMPLATE with these values"
KCFG="$(mktemp)"
trap 'rm -f "$KCFG"' EXIT
perl -pe 's/\$\{(MK4_[A-Z_]+)\}/$ENV{$1}/g' "$TEMPLATE" > "$KCFG"
can() { kubectl --kubeconfig "$KCFG" auth can-i "$@" -n "$NS"; }
[[ "$(can patch deployments)" == yes && "$(can create ingresses.networking.k8s.io)" == yes ]] \
  || { echo "The rendered kubeconfig cannot apply the application manifests." >&2; exit 1; }
for denied in "get secrets" "create roles.rbac.authorization.k8s.io" "delete deployments" "create pods"; do
  # shellcheck disable=SC2086
  [[ "$(can $denied || true)" == no ]] || { echo "The ServiceAccount may '$denied'; it must not." >&2; exit 1; }
done
echo "→ Dry run of every application object as $SA"
for group in site practice-executor; do
  scripts/manifests.sh "$group" | python3 scripts/ci-app-manifests.py 2>/dev/null \
    | kubectl --kubeconfig "$KCFG" apply --dry-run=server -f - >/dev/null
done

if [[ "${SKIP_GH:-0}" == "1" ]]; then
  cat <<OUT
Done. Set these in $REPO → Settings → Secrets and variables → Actions:
  Secret   MK4_CI_APPLY_TOKEN = copy with: kubectl --context $CONTEXT -n $NS get secret $SA-token -o jsonpath='{.data.token}' | base64 -d | pbcopy
  Variable MINIKUBE_DEPLOY    = true
OUT
  exit 0
fi

echo "→ Storing secret MK4_CI_APPLY_TOKEN and variable MINIKUBE_DEPLOY"
printf '%s' "$MK4_CI_APPLY_TOKEN" | gh secret set MK4_CI_APPLY_TOKEN --repo "$REPO"
unset MK4_CI_APPLY_TOKEN
gh variable set MINIKUBE_DEPLOY --repo "$REPO" --body true
echo "Done: pushes to master that change minikube/ now apply the application manifests to mk4."
