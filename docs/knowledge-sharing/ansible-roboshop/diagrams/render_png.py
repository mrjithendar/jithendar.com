#!/usr/bin/env python3
"""PNG copies of the figures' SVGs at 2x (the featured image and social previews need a raster). Run from www/.
Uses Playwright's Chromium; set CHROMIUM_PATH if the project's Playwright version has no matching browser."""
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[3] / "public" / "images" / "ansible-roboshop"
JS = """
const { chromium } = require('playwright');
(async () => {
  const [svg, png, w, h] = process.argv.slice(1); // node -e: arguments start at argv[1]
  const exe = process.env.CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(exe ? { executablePath: exe } : {});
  const page = await browser.newPage({ viewport: { width: +w, height: +h }, deviceScaleFactor: 2 });
  await page.goto('file://' + svg);
  await page.screenshot({ path: png, omitBackground: false });
  await browser.close();
})();
"""
for line in (HERE / "figures.txt").read_text().splitlines():
    figure, w, h = line.split()
    subprocess.run(["node", "-e", JS, str(OUT / f"{figure}.svg"), str(OUT / f"{figure}.png"), w, h], check=True)
    print(f"{figure}.png")
