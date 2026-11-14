#!/bin/sh
# PNG copies of the SVGs at 2x with rsvg-convert (librsvg). Run from www/.
set -eu
here=sites/jithendar.com/docs/knowledge-sharing/lets-encrypt/diagrams
images="$PWD/public/images/lets-encrypt"
while read -r figure width height; do
  rsvg-convert -z 2 -b white "$images/$figure.svg" -o "$images/$figure.png"
done < "$here/figures.txt"
