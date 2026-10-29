#!/usr/bin/env bash
# Pin the production image by digest. Usage: scripts/set-image.sh <sha256:digest>
# Rewrites only the digest of the jithendar-com entry under `images:` in k8s/kustomization.yaml.
set -euo pipefail

DIGEST="$1"
FILE="$(dirname "$0")/../k8s/kustomization.yaml"

[[ "$DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]] || { echo "Invalid digest: $DIGEST" >&2; exit 1; }

awk -v digest="$DIGEST" '
  /^- name: .*\/jithendar-com$/ { entry = 1; print; next }
  entry && /^  digest: / { print "  digest: " digest; entry = 0; found = 1; next }
  /^[^ ]/ { entry = 0 }
  { print }
  END { if (!found) exit 2 }
' "$FILE" > "$FILE.tmp" || { rm -f "$FILE.tmp"; echo "No jithendar-com image digest in $FILE" >&2; exit 1; }
mv "$FILE.tmp" "$FILE"
