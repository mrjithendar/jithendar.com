#!/usr/bin/env bash
# Fails when a tracked file looks like a cloud-sync conflict copy: "name 2.ext" or "name (1).ext" (iCloud, Dropbox,
# Google Drive). Such copies are stale duplicates (e.g. "README 2.md" differed from README.md). CI: ci-repo.yml.
set -euo pipefail
cd "${1:-$(dirname -- "${BASH_SOURCE[0]}")/..}"
bad="$(git ls-files | grep -E '(^|/)[^/]* [0-9]{1,2}\.[^/]*$|(^|/)[^/]* \([0-9]{1,2}\)\.[^/]*$' || true)"
if [[ -n "$bad" ]]; then
  echo "Tracked files that look like cloud-sync conflict copies (merge anything newer into the original, then delete):" >&2
  while IFS= read -r f; do
    echo "  $f" >&2
    [[ -n "${GITHUB_ACTIONS:-}" ]] && echo "::error file=$f::cloud-sync conflict copy"
  done <<<"$bad"
  exit 1
fi
echo "No conflict copies tracked."
