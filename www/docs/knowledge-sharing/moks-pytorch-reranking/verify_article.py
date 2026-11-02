#!/usr/bin/env python3
"""Check the PyTorch reranking article against the pinned MOKS commit. Run from www/: python3 <this file> ../..

Every code excerpt whose first line names a file must be a run of real lines from that file at the commit.
Every commit-pinned link must name a file that exists there, and its line anchors must be within the file.
Every figure must exist with alt text, and its .drawio file must parse. No account id or IP address may appear.
"""
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ARTICLE = Path("content/blog/pytorch-rag-reranking-moks-sre-agent.mdx")
DIAGRAMS = Path("docs/knowledge-sharing/moks-pytorch-reranking/diagrams")
IMAGES = "moks-pytorch-reranking"
COMMIT = "4928f094e1dab364156103234859f7e8efe7072d"
workspace = Path(sys.argv[1] if len(sys.argv) > 1 else "../..")
repo = workspace / "moks"
text = ARTICLE.read_text(encoding="utf-8")
failures, excerpts, links = [], 0, 0


def show(path: str) -> str | None:
    r = subprocess.run(["git", "-C", str(repo), "show", f"{COMMIT}:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


for lang, block in re.findall(r"```(python|dockerfile|yaml)\n(.*?)```", text, re.S):
    lines = block.rstrip("\n").splitlines()
    path = lines[0].removeprefix("# ").strip()
    source = show(path)
    if source is None:
        failures.append(f"{path}: not a file at {COMMIT[:7]}")
        continue
    excerpts += 1
    if "\n".join(lines[1:]) not in source:
        failures.append(f"{path}: excerpt is not a verbatim run of lines:\n" + "\n".join(lines[1:3]))

for kind, path, start, end in re.findall(rf"https://github\.com/mrjithendar/moks/(blob|tree)/{COMMIT}/([^)#\s]*)(?:#L(\d+)(?:-L(\d+))?)?", text):
    links += 1
    if kind == "tree":
        if path and subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{COMMIT}:{path.rstrip('/')}"]).returncode:
            failures.append(f"tree link to missing path {path}")
        continue
    source = show(path)
    if source is None:
        failures.append(f"link to missing file {path}")
    elif start and int(end or start) > len(source.splitlines()):
        failures.append(f"{path}#L{start}-L{end}: past the end of the file")

for match in re.findall(r"https://github\.com/mrjithendar/moks/(?:blob|tree)/([0-9a-f]+)", text):
    if match != COMMIT:
        failures.append(f"link pinned to another commit: {match}")

figures = re.findall(rf"!\[(.+?)\]\(/images/{IMAGES}/([a-z-]+)\.svg\)", text, re.S)
for alt, name in figures:
    if len(alt) < 100:
        failures.append(f"{name}: alt text is too short")
    if not Path(f"public/images/{IMAGES}/{name}.svg").exists():
        failures.append(f"{name}: SVG is missing")
    ET.parse(DIAGRAMS / f"{name}.drawio")
if len(figures) != 3:
    failures.append(f"expected 3 figures, found {len(figures)}")

front = text.split("---", 2)[1]
for key in ("description", "seoDescription"):
    value = re.search(rf'^{key}: "(.*)"$', front, re.M).group(1)
    if not 120 <= len(value) <= 160:
        failures.append(f"{key} is {len(value)} characters")
body = re.sub(r"```.*?```", "", text.split("---", 2)[2], flags=re.S)
if re.search(r"^# ", body, re.M):
    failures.append("the body has its own H1; the page renders the title as the H1")
if re.search(r"\b\d{12}\b", text) or re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", text):
    failures.append("an account id or IP address appears in the article")
for banned in ("game-changing", "seamless", "delve", "unlock the power", "production-ready", "revolutionize"):
    if banned in text.lower():
        failures.append(f"banned phrase: {banned}")

print(f"{excerpts} code excerpts, {links} pinned links, {len(figures)} figures checked")
if failures:
    raise SystemExit("\n".join(failures))
print("OK")
