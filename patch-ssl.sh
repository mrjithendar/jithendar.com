#!/usr/bin/env bash
# Point every jithendar.com Traefik route at the shared certificate. Usage: ./patch-ssl.sh
# KUBE_CONTEXT selects the cluster (default mk4).
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "${PYTHON:-python3}" "$ROOT/shared-tls/configure.py" "$@"
