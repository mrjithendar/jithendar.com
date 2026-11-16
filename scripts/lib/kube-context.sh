# shellcheck shell=bash
# Kube-context guard for every script that changes a cluster. Source it right after `set -euo pipefail`:
#
#   source "$(dirname -- "${BASH_SOURCE[0]}")/lib/kube-context.sh"      # from scripts/
#   source "$(dirname -- "${BASH_SOURCE[0]}")/scripts/lib/kube-context.sh"  # from the repository root
#
# - The target context is KUBE_CONTEXT when set, otherwise kubectl's current context. Nothing is hard-coded.
#   It must exist in the kubeconfig, or the script stops before touching anything.
# - `kubectl` becomes a function that always passes `--context "$KCTX"`, so the whole script talks to one cluster
#   even if someone runs `kubectl config use-context` in another terminal half-way through. A call that brings its own
#   kubeconfig (`--kubeconfig …`, e.g. testing a generated CI kubeconfig) must use `command kubectl` instead.
# - It prints the context and its API server (stderr, so stdout stays clean for pipes).
# - It asks for confirmation only when the context was NOT named explicitly (KUBE_CONTEXT unset), YES is not 1, and
#   stdin is a terminal. CI and pipes never prompt.
#
#   KUBE_CONTEXT=mk4 scripts/create-secrets.sh      # explicit: no prompt
#   YES=1 scripts/create-secrets.sh                 # current context, no prompt

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is not on PATH" >&2
  exit 1
fi

if [[ -n "${KUBE_CONTEXT:-}" ]]; then
  KCTX="$KUBE_CONTEXT"
  _kctx_source="KUBE_CONTEXT"
else
  KCTX="$(command kubectl config current-context 2>/dev/null || true)"
  _kctx_source="current context"
fi

if [[ -z "$KCTX" ]]; then
  echo "No kube context: set KUBE_CONTEXT=<name> or select one with 'kubectl config use-context <name>'." >&2
  exit 1
fi

# Capture the list first: piping kubectl straight into `grep -q` races under pipefail (grep exits on the first match,
# kubectl gets SIGPIPE, and the pipeline "fails" even though the context exists).
_kctx_all="$(command kubectl config get-contexts -o name 2>/dev/null || true)"
if ! grep -Fqx -- "$KCTX" <<<"$_kctx_all"; then
  echo "Kube context '$KCTX' ($_kctx_source) does not exist in the kubeconfig." >&2
  echo "Available: $(tr '\n' ' ' <<<"$_kctx_all")" >&2
  exit 1
fi

KCTX_SERVER="$(command kubectl config view --minify --context "$KCTX" -o jsonpath='{.clusters[0].cluster.server}' 2>/dev/null || true)"
export KCTX KCTX_SERVER

kubectl() { command kubectl --context "$KCTX" "$@"; }

echo "→ Kube context: $KCTX ($_kctx_source), API server: ${KCTX_SERVER:-unknown}" >&2

if [[ -z "${KUBE_CONTEXT:-}" && "${YES:-0}" != "1" && -t 0 ]]; then
  read -r -p "Continue against '$KCTX'? [y/N] " _kctx_answer
  case "$_kctx_answer" in
    y | Y | yes | YES) ;;
    *)
      echo "Aborted." >&2
      exit 1
      ;;
  esac
fi
unset _kctx_source _kctx_answer _kctx_all
