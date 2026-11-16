#!/usr/bin/env bash
# Start a site's app image without its cluster secrets and check that it answers: /api/health reports <version>, and
# the image optimiser turns a JPEG into AVIF or WebP (sharp works in the image). Never push an image that fails this.
#
#   scripts/smoke-site-image.sh <image> <version> [<image path>]
#
# <image path> is a JPEG under the site's public/images (default /images/roboshop-ai/cart.jpg, which the test fixture
# site and jithendar.com both have).
set -euo pipefail
IMAGE="${1:?usage: $0 <image> <version> [<image path>]}"
VERSION="${2:?usage: $0 <image> <version> [<image path>]}"
JPEG="${3:-/images/roboshop-ai/cart.jpg}"
name="site-smoke-${GITHUB_RUN_ID:-local}-$$"

# The image defaults to APP_ENV=production, which expects the cluster's secrets. This check starts it bare, so it has
# to say that it is not the production site.
docker run -d --rm --name "$name" -e APP_ENV=development -p 127.0.0.1::3000 "$IMAGE" >/dev/null
trap 'docker logs "$name" 2>&1 | tail -50; docker rm -f "$name" >/dev/null 2>&1 || true' EXIT
port="$(docker port "$name" 3000/tcp | head -1 | sed 's/.*://')"
for _ in $(seq 1 30); do curl -fsS "http://127.0.0.1:$port/api/health" >/dev/null 2>&1 && break; sleep 1; done
curl -fsS "http://127.0.0.1:$port/api/health" | grep -q "\"version\":\"$VERSION\"" \
  || { echo "/api/health does not report version $VERSION" >&2; exit 1; }
url="$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$JPEG")"
type="$(curl -fsS -o /dev/null -w '%{content_type}' -H 'Accept: image/avif,image/webp' \
  "http://127.0.0.1:$port/_next/image?url=$url&w=640&q=75")"
[[ "$type" == image/avif* || "$type" == image/webp* ]] || { echo "Image optimiser returned: $type" >&2; exit 1; }
echo "Image healthy (version $VERSION); optimiser served $type"
