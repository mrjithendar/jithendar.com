#!/usr/bin/env bash
# Report an image's size in the GitHub job summary and fail when it grew more than MAX_GROWTH (default 15 %) over the
# stored baseline. Used by the site image build (.github/workflows/release.yml; a copy of moks-cms's scripts/image-size.sh).
#
#   scripts/image-size.sh <image> <baseline.json>
#
# - uncompressed: `docker image inspect .Size` (what the node's disk holds once pulled)
# - compressed:   the image saved and gzipped (close to the registry/pull size; layers are gzip-compressed there too)
# baseline.json: {"image": "...", "uncompressed_bytes": N, "compressed_bytes": N, "measured": "YYYY-MM-DD", "commit": "..."}
# With null values (no baseline yet) the sizes are reported with a warning and the gate is skipped; copy the printed
# numbers into the file to arm it. Raise the baseline deliberately (in the same PR, with the reason in the commit
# message) when growth is expected, e.g. a new library recorded in DECISIONS.md.
set -euo pipefail
IMAGE="${1:?usage: $0 <image> <baseline.json>}"
BASELINE="${2:?usage: $0 <image> <baseline.json>}"
MAX_GROWTH="${MAX_GROWTH:-0.15}"
SUMMARY="${GITHUB_STEP_SUMMARY:-/dev/stdout}"

uncompressed="$(docker image inspect --format '{{.Size}}' "$IMAGE")"
compressed="$(docker save "$IMAGE" | gzip -c | wc -c | tr -d ' ')"
mib() { awk -v b="$1" 'BEGIN { printf "%.1f MiB", b / 1048576 }'; }

read -r base_u base_c < <(python3 -c '
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except (OSError, ValueError):
    d = {}
print(d.get("uncompressed_bytes") or 0, d.get("compressed_bytes") or 0)
' "$BASELINE")

status=0
{
  echo "### Image size: \`$IMAGE\`"
  echo
  echo "| | This build | Baseline | Change |"
  echo "|---|---|---|---|"
  for kind in uncompressed compressed; do
    now="${!kind}"
    base="$([[ $kind == uncompressed ]] && echo "$base_u" || echo "$base_c")"
    if [[ "$base" -gt 0 ]]; then
      change="$(awk -v n="$now" -v b="$base" 'BEGIN { printf "%+.1f %%", (n - b) * 100 / b }')"
      over="$(awk -v n="$now" -v b="$base" -v g="$MAX_GROWTH" 'BEGIN { print (n > b * (1 + g)) ? 1 : 0 }')"
      [[ "$over" == 1 ]] && status=1 && change="$change ❌ (limit +$(awk -v g="$MAX_GROWTH" 'BEGIN { printf "%.0f", g * 100 }') %)"
      echo "| $kind | $(mib "$now") ($now B) | $(mib "$base") | $change |"
    else
      echo "| $kind | $(mib "$now") ($now B) | none recorded | n/a |"
    fi
  done
  echo
  if [[ "$base_u" -eq 0 || "$base_c" -eq 0 ]]; then
    echo "No baseline in \`$BASELINE\` yet: the size gate is skipped. Record these numbers there to arm it."
  fi
} >>"$SUMMARY"

echo "uncompressed=$uncompressed compressed=$compressed baseline_uncompressed=$base_u baseline_compressed=$base_c"
if [[ "$base_u" -eq 0 || "$base_c" -eq 0 ]]; then
  [[ -n "${GITHUB_ACTIONS:-}" ]] && echo "::warning file=$BASELINE::no image size baseline recorded; gate skipped (uncompressed=$uncompressed compressed=$compressed)"
fi
if [[ "$status" -ne 0 ]]; then
  [[ -n "${GITHUB_ACTIONS:-}" ]] && echo "::error file=$BASELINE::$IMAGE grew more than $MAX_GROWTH over the baseline"
  echo "$IMAGE grew more than $(awk -v g="$MAX_GROWTH" 'BEGIN { printf "%.0f", g * 100 }') % over $BASELINE" >&2
fi
exit "$status"
