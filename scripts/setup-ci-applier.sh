#!/usr/bin/env bash
# One-time, and again whenever kubernetes/85-ci-applier.yaml's ClusterRole changes: applies that file (a ServiceAccount
# that may create and update the site group's objects in namespace jithendar, RBAC included, and patch the Namespace
# jithendar itself; see the file's header) and stores what .github/workflows/deploy-kubernetes.yml needs:
#   MK4_CI_APPLY_TOKEN       repository secret    ServiceAccount token (from Secret jithendar/github-ci-applier-token)
#   MINIKUBE_DEPLOY = true   repository variable  turns the workflow's deploy job on
# MK4_API_SERVER and MK4_CA_DATA are shared with the restart-only deployer: run scripts/setup-ci-deployer.sh first
# if they are not set yet. The workflow keeps the ServiceAccount, Role and RoleBinding up to date afterwards (they are
# in kubernetes/kustomization.yaml); the ClusterRole, ClusterRoleBinding and token Secret are only ever applied here.
#
#   KUBE_CONTEXT=mk4 scripts/setup-ci-applier.sh            # apply SA + Role + token, test the kubeconfig, store the values
#   KUBE_CONTEXT=mk4 SKIP_GH=1 scripts/setup-ci-applier.sh  # only apply and test; set the values in GitHub yourself
#   KUBE_CONTEXT=mk4 ROTATE=1 scripts/setup-ci-applier.sh   # replace the token (the old one stops working)
#   (kube context: KUBE_CONTEXT=<name>, else the current context with a confirmation prompt; scripts/lib/kube-context.sh)
#
# The token goes straight into `gh secret set` (stdin) and is never printed.
# Needs: kubectl with cluster-admin on context mk4; gh CLI signed in with admin on the repository (unless SKIP_GH=1).
set -euo pipefail
# shellcheck source=/dev/null
source "$(dirname -- "${BASH_SOURCE[0]}")/lib/kube-context.sh"

REPO="${GITHUB_REPO:-mrjithendar/jithendar.com}"
NS="jithendar"
SA="github-ci-applier"
TEMPLATE=".github/jithendar-ci-applier.yaml"
k() { kubectl "$@"; }

cd "$(dirname -- "${BASH_SOURCE[0]}")/.."
python3 -c "import yaml" 2>/dev/null || { echo "scripts/ci-app-manifests.py needs PyYAML: python3 -m pip install --user pyyaml==6.0.3" >&2; exit 1; }

MK4_API_SERVER="$(kubectl config view --raw --minify -o jsonpath='{.clusters[0].cluster.server}')"
MK4_CA_DATA="$(kubectl config view --raw --minify -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')"
[[ -n "$MK4_CA_DATA" ]] || MK4_CA_DATA="$(base64 < "$(kubectl config view --raw --minify -o jsonpath='{.clusters[0].cluster.certificate-authority}')" | tr -d '\n')"
[[ -n "$MK4_API_SERVER" && -n "$MK4_CA_DATA" ]] || { echo "Could not read server/CA of the current kubectl context." >&2; exit 1; }

echo "→ Cluster $MK4_API_SERVER, ServiceAccount $NS/$SA, repository $REPO"
if [[ "${ROTATE:-0}" == "1" ]]; then
  echo "→ Deleting the old token"
  k -n "$NS" delete secret "$SA-token" --ignore-not-found
fi

echo "→ Applying kubernetes/85-ci-applier.yaml"
k apply -f kubernetes/85-ci-applier.yaml

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
can() { command kubectl --kubeconfig "$KCFG" auth can-i "$@" -n "$NS"; }
for allowed in "patch deployments" "create ingresses.networking.k8s.io" "patch roles.rbac.authorization.k8s.io" "escalate roles.rbac.authorization.k8s.io" "patch serviceaccounts" "patch namespaces/$NS" "create pods/portforward"; do
  # shellcheck disable=SC2086
  [[ "$(can $allowed 2>/dev/null || true)" == yes ]] || { echo "The rendered kubeconfig may not '$allowed'; the workflow needs it." >&2; exit 1; }
done
for denied in "get secrets" "delete deployments" "create pods" "create namespaces" "patch namespaces/kube-system" "create clusterroles.rbac.authorization.k8s.io" "create clusterrolebindings.rbac.authorization.k8s.io"; do
  # shellcheck disable=SC2086
  [[ "$(can $denied 2>/dev/null || true)" == no ]] || { echo "The ServiceAccount may '$denied'; it must not." >&2; exit 1; }
done
echo "→ Dry run of every object the workflow applies, as $SA"
for group in site seo-agent; do
  flags=(); [[ "$group" == site ]] && flags=(--all)
  scripts/manifests.sh "$group" | python3 scripts/ci-app-manifests.py "${flags[@]}" 2>/dev/null \
    | command kubectl --kubeconfig "$KCFG" apply --dry-run=server -f - >/dev/null
done

if [[ "${SKIP_GH:-0}" == "1" ]]; then
  cat <<OUT
Done. Set these in $REPO → Settings → Secrets and variables → Actions:
  Secret   MK4_CI_APPLY_TOKEN = copy with: kubectl -n $NS get secret $SA-token -o jsonpath='{.data.token}' | base64 -d | pbcopy
  Variable MINIKUBE_DEPLOY    = true
OUT
  exit 0
fi

echo "→ Storing secret MK4_CI_APPLY_TOKEN and variable MINIKUBE_DEPLOY"
printf '%s' "$MK4_CI_APPLY_TOKEN" | gh secret set MK4_CI_APPLY_TOKEN --repo "$REPO"
unset MK4_CI_APPLY_TOKEN
gh variable set MINIKUBE_DEPLOY --repo "$REPO" --body true
echo "Done: pull requests merged into master that change kubernetes/ are now applied to mk4 by the deploy workflow."
