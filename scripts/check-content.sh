#!/usr/bin/env bash
# Check this site's content with moks-cms's own checks, in the moks-cms-builder image (this repository mounted
# read-only at /site): the MDX schema and internal links (tests/content.test.ts, tests/links.test.ts), and that the
# Python practice catalog is valid and up to date (services/executor/tools/build_problems.py --check).
#
#   scripts/check-content.sh registry.jithendar.com/jithendar/moks-cms-builder:<tag>
#
# CI runs it in check.yml (pull requests) and release.yml (job `content`). Locally, with a moks-cms checkout next to
# this one and no Docker: cd ../moks-cms/services/www && SITE_DIR=../../../jithendar.com npm run site -- --copy &&
# npx vitest run tests/content.test.ts tests/links.test.ts
set -euo pipefail
BUILDER="${1:?usage: $0 <moks-cms-builder image>}"
root="$(cd "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

docker run --rm -v "$root:/site:ro" "$BUILDER" sh -c '
  set -e
  npm run --silent site -- --copy
  npx vitest run tests/content.test.ts tests/links.test.ts
'
# The catalog builder writes nothing with --check; it reads /site/content/python-practice.
docker run --rm -v "$root:/site:ro" "$BUILDER" python3 /moks-cms/services/executor/tools/build_problems.py --check
