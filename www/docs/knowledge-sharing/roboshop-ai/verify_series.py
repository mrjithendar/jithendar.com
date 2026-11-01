#!/usr/bin/env python3
"""Check the RoboShop AI series against its sources (standard library only).

    python3 docs/knowledge-sharing/roboshop-ai/verify_series.py ../../roboshop-ai   (from www/)

Checks: code excerpts exist in the named file, images and internal links resolve, .drawio XML is
well formed with valid references, SEO fields are the targeted length, and no secret-like text,
banned phrase or account ID appears. Exits non-zero on any failure.
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

WWW = Path(__file__).resolve().parents[3]
SERIES = ["roboshop-ai-architecture", "roboshop-ai-gateway", "roboshop-ai-mcp-server", "roboshop-ai-shopping-agent"]
BANNED = ["seamless", "delve", "game-changing", "game changer", "unlock the power", "rapidly evolving", "revolutionize", "cutting-edge", "leverage"]
SECRET = re.compile(r"AKIA[0-9A-Z]{12,}|\b\d{12}\.dkr\.ecr|-----BEGIN|\b[a-f0-9]{64}\b|rzp_(live|test)_[A-Za-z0-9]{6,}|\bpassword\s*=\s*\S+", re.I)
PIN = "c81e85a1fd9d3552c69d4490be17ccf61d29437b"


def main():
    repo = Path(sys.argv[1]).resolve()
    failures, excerpts = [], 0

    for slug in SERIES:
        path = WWW / "content/blog" / f"{slug}.mdx"
        text = path.read_text()
        front, body = text.split("---\n", 2)[1:]
        fields = dict(re.findall(r'^(seoTitle|seoDescription|title|description): "(.*)"$', front, re.M))
        if not 50 <= len(fields["seoTitle"]) <= 60:
            failures.append(f"{slug}: SEO title is {len(fields['seoTitle'])} characters")
        if not 140 <= len(fields["seoDescription"]) <= 160:
            failures.append(f"{slug}: meta description is {len(fields['seoDescription'])} characters")
        if len(re.findall(r"^# ", re.sub(r"```.*?```", "", body, flags=re.S), re.M)):
            failures.append(f"{slug}: body has an H1")

        for language, code in re.findall(r"```(\w+)\n(.*?)```", body, re.S):
            lines = code.rstrip("\n").split("\n")
            match = re.match(r"# (services/\S+)$", lines[0])
            if not match:
                continue
            excerpts += 1
            source = {line.strip() for line in (repo / match[1]).read_text().split("\n")}
            for line in lines[1:]:
                if line.strip() and line.strip() not in source:
                    failures.append(f"{slug}: excerpt line not in {match[1]}: {line.strip()[:70]}")

        for image in re.findall(r"!\[[^\]]+\]\((/images/[^)]+)\)", body):
            if not (WWW / "public" / image.lstrip("/")).is_file():
                failures.append(f"{slug}: missing image {image}")
        if re.search(r"!\[\]\(", body):
            failures.append(f"{slug}: image without alt text")
        for link in re.findall(r"\]\((/blog/[a-z0-9-]+)", body):
            if not (WWW / "content/blog" / f"{link.removeprefix('/blog/')}.mdx").is_file():
                failures.append(f"{slug}: broken link {link}")
        others = [s for s in SERIES if s != slug]
        for other in others:
            if f"/blog/{other}" not in body:
                failures.append(f"{slug}: no link to {other}")
        for link in re.findall(r"github\.com/mrjithendar/roboshop-ai/(?:blob|tree)/([0-9a-f]+)", text):
            if link != PIN:
                failures.append(f"{slug}: unpinned repository link {link}")
        lowered = body.lower()
        for phrase in BANNED:
            if phrase in lowered:
                failures.append(f"{slug}: banned phrase '{phrase}'")
        if SECRET.search(text):
            failures.append(f"{slug}: secret-like text: {SECRET.search(text)[0][:20]}")
        prose = re.sub(r"```.*?```|<Todo>.*?</Todo>|!\[[^\]]*\]\([^)]*\)", " ", body, flags=re.S)
        print(f"{slug}: {len(prose.split())} words")

    for path in sorted((WWW / "docs/knowledge-sharing/roboshop-ai/diagrams").glob("*.drawio")):
        root = ET.parse(path).getroot()
        if root.tag != "mxfile":
            failures.append(f"{path.name}: root is {root.tag}")
        for diagram in root.findall("diagram"):
            cells = diagram.findall(".//mxCell")
            ids = [c.get("id") for c in cells]
            if len(ids) != len(set(ids)):
                failures.append(f"{path.name}/{diagram.get('name')}: duplicate cell ids")
            for cell in cells:
                for key in ("source", "target", "parent"):
                    if cell.get(key) and cell.get(key) not in ids:
                        failures.append(f"{path.name}: {cell.get('id')} has unknown {key}")
        print(f"{path.name}: {len(root.findall('diagram'))} page(s)")

    for figure in (WWW / "public/images/roboshop-ai-series").glob("*.svg"):
        svg = figure.read_text()
        ET.fromstring(svg)
        if "<title" not in svg or "<desc" not in svg:
            failures.append(f"{figure.name}: missing title or desc")
        if SECRET.search(svg):
            failures.append(f"{figure.name}: secret-like text")
        if not figure.with_suffix(".png").is_file():
            failures.append(f"{figure.name}: no PNG")

    print(f"{excerpts} code excerpts checked")
    for failure in failures:
        print("FAIL", failure)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
