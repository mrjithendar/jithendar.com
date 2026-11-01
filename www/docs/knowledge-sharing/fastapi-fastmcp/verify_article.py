#!/usr/bin/env python3
"""Check the FastAPI and FastMCP article against the pinned commits. Run from www/: python3 <this file> ../..

Every code excerpt must be a run of real lines from the file named in its first comment, at the commit
the article names. Every figure must exist with alt text, and its .drawio file must parse.
"""
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ARTICLE = Path("content/blog/fastapi-and-fastmcp-ai-projects.mdx")
DIAGRAMS = Path("docs/knowledge-sharing/fastapi-fastmcp/diagrams")
COMMITS = {"services/": ("roboshop-ai", "c81e85a1fd9d3552c69d4490be17ccf61d29437b"),
           "backend/": ("moks", "ab99cf7b17acef3f7af4ca4e11b64267563133fb")}
workspace = Path(sys.argv[1] if len(sys.argv) > 1 else "../..")
text = ARTICLE.read_text(encoding="utf-8")
failures, excerpts = [], 0

for block in re.findall(r"```python\n(.*?)```", text, re.S):
    lines = block.splitlines()
    path = lines[0].removeprefix("# ").strip()
    repo, commit = next(v for k, v in COMMITS.items() if path.startswith(k))
    source = subprocess.run(["git", "-C", str(workspace / repo), "show", f"{commit}:{path}"], capture_output=True, text=True, check=True).stdout
    excerpts += 1
    if "\n".join(lines[1:]) not in source:
        failures.append(f"{path}: excerpt is not a verbatim run of lines:\n" + "\n".join(lines[1:3]))

figures = re.findall(r"!\[(.+?)\]\(/images/fastapi-fastmcp/([a-z-]+)\.svg\)", text, re.S)
for alt, name in figures:
    if len(alt) < 100:
        failures.append(f"{name}: alt text is too short")
    if not Path(f"public/images/fastapi-fastmcp/{name}.svg").exists():
        failures.append(f"{name}: SVG is missing")
    ET.parse(DIAGRAMS / f"{name}.drawio")

for pin in {commit for _, commit in COMMITS.values()}:
    if pin not in text:
        failures.append(f"article does not link commit {pin}")
for banned in ("game-changing", "seamless", "delve", "unlock the power"):
    if banned in text.lower():
        failures.append(f"banned phrase: {banned}")

print(f"{excerpts} code excerpts, {len(figures)} figures checked")
if failures:
    raise SystemExit("\n".join(failures))
print("OK")
