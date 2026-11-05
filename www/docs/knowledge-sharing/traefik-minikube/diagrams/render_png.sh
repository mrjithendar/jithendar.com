#!/bin/sh
# PNG copies of the SVGs at 2x, as screenshots from an installed Google Chrome. Run from www/.
set -eu
here=docs/knowledge-sharing/traefik-minikube/diagrams
images="$PWD/public/images/traefik-minikube"
chrome="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
profile=$(mktemp -d)
trap 'rm -rf "$profile"' EXIT
while read -r figure width height; do
  "$chrome" --headless=new --disable-gpu --hide-scrollbars --user-data-dir="$profile" \
    --force-device-scale-factor=2 --window-size="$width,$height" --default-background-color=ffffffff \
    --screenshot="$images/$figure.png" "file://$images/$figure.svg" >/dev/null 2>&1
done < "$here/figures.txt"
