#!/usr/bin/env bash
# Deploy jithendar.com to the mk4 cluster.
#
#   ./deploy.sh               # deploy the most recently pushed image in ECR
#   ./deploy.sh <commit-sha>  # deploy the image built from a specific commit (e.g. to roll back)
#
# CI only builds and pushes jithendar-com:<commit-sha> to ECR. This script looks up the image's
# digest, pins it in k8s/kustomization.yaml, applies, waits and smoke-tests. Commit the updated
# kustomization.yaml afterwards so Git records what is live.
# Started as `sh deploy.sh`? Re-run under full bash (macOS sh is bash in POSIX mode).
if [ -z "${BASH_VERSION:-}" ] || case ":${SHELLOPTS:-}:" in *:posix:*) true ;; *) false ;; esac; then
  exec bash "$0" "$@"
fi
set -euo pipefail

# Use the first AWS CLI that actually runs (an Intel-only copy fails on Apple Silicon without Rosetta).
AWS=""
for candidate in $(type -ap aws) /opt/homebrew/bin/aws /usr/local/bin/aws; do
  if "$candidate" --version >/dev/null 2>&1; then AWS="$candidate"; break; fi
done
[[ -n "$AWS" ]] || { echo "No working AWS CLI found. Install it with: brew install awscli" >&2; exit 1; }

CONTEXT="${KUBE_CONTEXT:-mk4}"
REGION="${AWS_REGION:-us-east-1}"
REPOSITORY="jithendar-com"
SHA="${1:-}"
k() { kubectl --context "$CONTEXT" "$@"; }

cd "$(dirname -- "${BASH_SOURCE[0]}")"

if [[ -z "$SHA" ]]; then
  echo "→ Finding the most recently pushed image in ECR ($REGION)"
  read -r SHA DIGEST PUSHED <<<"$("$AWS" ecr describe-images --region "$REGION" --repository-name "$REPOSITORY" \
    --filter tagStatus=TAGGED --query "sort_by(imageDetails,&imagePushedAt)[-1].[imageTags[?@ != 'latest'] | [0],imageDigest,imagePushedAt]" --output text)"
  [[ -n "${SHA:-}" && "$SHA" != "None" ]] || { echo "No tagged images in $REPOSITORY." >&2; exit 1; }
  echo "  latest: $SHA (pushed $PUSHED)"
else
  echo "→ Looking up $REPOSITORY:$SHA in ECR ($REGION)"
  DIGEST="$("$AWS" ecr describe-images --region "$REGION" --repository-name "$REPOSITORY" \
    --image-ids imageTag="$SHA" --query 'imageDetails[0].imageDigest' --output text 2>/dev/null || true)"
  [[ -n "$DIGEST" && "$DIGEST" != "None" ]] || { echo "No image tagged $SHA. Has CI finished building that commit?" >&2; exit 1; }
fi

echo "→ Pinning $DIGEST"
scripts/set-image.sh "$DIGEST"

echo "→ Checking Secrets"
for s in jithendar-postgres jithendar-redis jithendar-com-env; do
  k -n jithendar get secret "$s" >/dev/null 2>&1 || {
    echo "Secret jithendar/$s is missing. Run scripts/create-secrets.sh once first." >&2
    exit 1
  }
done

echo "→ Validating against the cluster"
k apply -k k8s --dry-run=server >/dev/null

echo "→ Applying"
k apply -k k8s

echo "→ Waiting for Postgres and Redis"
k -n jithendar rollout status statefulset/jithendar-postgres --timeout=5m
k -n jithendar rollout status deployment/jithendar-redis --timeout=3m

echo "→ Waiting for the site"
if ! k -n jithendar rollout status deployment/jithendar-com --timeout=5m; then
  k -n jithendar get pods -l app=jithendar-com -o wide || true
  echo "Rollout failed; rolling back to the previous version." >&2
  k -n jithendar rollout undo deployment/jithendar-com
  exit 1
fi

echo "→ Smoke test"
scripts/smoke.sh https://jithendar.com "$SHA"

echo "Deployed $SHA. Commit k8s/kustomization.yaml so Git records what is live."
