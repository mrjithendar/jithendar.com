#!/usr/bin/env bash
# Export every figure listed in figures.txt with the draw.io desktop CLI (tested with draw.io 32.6.10):
#   public/images/mk4-github-runners/<name>.svg   used by the articles (light theme, no embedded fonts)
#   public/images/mk4-github-runners/<name>.png   2x raster, for social cards and editors that refuse SVG
# Install draw.io with `brew install --cask drawio` (macOS) or from https://github.com/jgraph/drawio-desktop/releases.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="$here/../../../../public/images/mk4-github-runners"
drawio="${DRAWIO:-drawio}"
mkdir -p "$out"
while read -r name; do
  [ -n "$name" ] || continue
  "$drawio" -x -f svg --theme light --embed-svg-fonts false -o "$out/$name.svg" "$here/$name.drawio" 2>/dev/null | grep -- '->' || true
  "$drawio" -x -f png --theme light -s 2 -o "$out/$name.png" "$here/$name.drawio" 2>/dev/null | grep -- '->' || true
  test -s "$out/$name.svg" && test -s "$out/$name.png"
done < "$here/figures.txt"
