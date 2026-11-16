#!/bin/sh
# PNG copies of the SVGs at 2x with rsvg-convert (librsvg). Run from the repository root.
set -eu
here=docs/knowledge-sharing/crewai/diagrams
images="$PWD/public/images/crewai"
while read -r figure width height; do
  rsvg-convert -z 2 -b white "$images/$figure.svg" -o "$images/$figure.png"
done < "$here/figures.txt"
