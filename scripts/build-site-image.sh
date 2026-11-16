#!/usr/bin/env bash
# Build jithendar.com's app image on a moks-cms-builder image (Dockerfile, a copy of moks-cms's Dockerfile.site).
#
#   scripts/build-site-image.sh <builder image> <site image> [<git sha>]
#   scripts/build-site-image.sh registry.jithendar.com/jithendar/moks-cms-builder:"$(jq -r .builder moks-cms.json)" jithendar-com:dev
#
# The builder is pulled (Harbor: docker login registry.jithendar.com first). Its moks-cms commit (image label
# org.opencontainers.image.revision) goes into the app image as MOKS_CMS_REVISION. linux/arm64 (PLATFORM to change).
set -euo pipefail
BUILDER="${1:?usage: $0 <builder image> <site image> [<git sha>]}"
SITE_IMAGE="${2:?usage: $0 <builder image> <site image> [<git sha>]}"
root="$(cd "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SHA="${3:-$(git -C "$root" rev-parse HEAD 2>/dev/null || echo dev)}"
PLATFORM="${PLATFORM:-linux/arm64}"

docker pull --quiet --platform "$PLATFORM" "$BUILDER" >/dev/null
revision="$(docker image inspect --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}' "$BUILDER")"
echo "Building on $BUILDER (moks-cms ${revision:-unknown})"
docker build --platform "$PLATFORM" --provenance=false -f "$root/Dockerfile" \
  --build-arg "MOKS_CMS_BUILDER=$BUILDER" --build-arg "GIT_SHA=$SHA" --build-arg "MOKS_CMS_REVISION=${revision:-unknown}" \
  -t "$SITE_IMAGE" "$root"
