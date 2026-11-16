#!/usr/bin/env bash
# Sourced by CI steps that roll out (release.yml): writes a kubeconfig for ServiceAccount jithendar/github-ci-deployer
# from .github/jithendar-ci-deployer.yaml and the values scripts/setup-ci-deployer.sh stored (variables MK4_API_SERVER,
# MK4_CA_DATA, secret MK4_CI_TOKEN, passed in as environment variables), exports KUBECONFIG and removes the file when
# the step's shell exits.
#
#   source scripts/lib/ci-kubeconfig.sh
for v in MK4_API_SERVER MK4_CA_DATA MK4_CI_TOKEN; do
  [[ -n "${!v:-}" ]] || { echo "::error::$v is not set; run scripts/setup-ci-deployer.sh"; exit 1; }
done
KUBECONFIG="${RUNNER_TEMP:-/tmp}/kubeconfig-$$"
export KUBECONFIG
trap 'rm -f "$KUBECONFIG"' EXIT
(umask 077; perl -pe 's/\$\{(MK4_[A-Z_]+)\}/$ENV{$1}/g' "$(dirname -- "${BASH_SOURCE[0]}")/../../.github/jithendar-ci-deployer.yaml" > "$KUBECONFIG")
