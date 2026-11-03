#!/usr/bin/env python3
"""Check the Python tutorial against the pinned MOKS and RoboShop AI commits, and run its examples.

Run from www/ with an interpreter that has fastapi, httpx and pytest installed (see README.md):

    python docs/knowledge-sharing/python-tutorial/verify_article.py ../..

Code blocks are recognised by their first line:
  # backend/... or # services/...    actual project code: must be a verbatim run of lines at the commit,
                                     and the label before it must link to exactly those lines
  # Simplified from <path>           adapted code: the path must exist at the commit
  # <name>.py (or .txt, .json)       standalone teaching example: written to a scratch folder
A ```text block whose first line starts with "$ " is run in that folder, and its output must match.
"""
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

ARTICLE = Path("content/blog/python-tutorial-beginners-real-projects.mdx")
REPOS = {
    "moks": ("ef6908ac90730beac312813f539cd0bc57d94810", "backend/"),
    "roboshop-ai": ("c81e85a1fd9d3552c69d4490be17ccf61d29437b", "services/"),
}
SHOWN_DIR = "/home/you/python-tutorial"
workspace = Path(sys.argv[1] if len(sys.argv) > 1 else "../..")
text = ARTICLE.read_text(encoding="utf-8")
failures: list[str] = []
counts = {"actual": 0, "simplified": 0, "standalone": 0, "runs": 0, "links": 0}


def repo_for(path: str) -> str:
    return "roboshop-ai" if path.startswith("services/") else "moks"


LABEL = re.compile(r"^\*(Standalone teaching example|Actual project code|Simplified from project code)\b.*$", re.M)


def label_before(position: int) -> str:
    """The nearest label paragraph above a block, so a second file after a first still finds its label."""
    found = [m for m in LABEL.finditer(text, 0, position)]
    return found[-1].group(0) if found else ""


def show(repo: str, path: str) -> str | None:
    commit = REPOS[repo][0]
    r = subprocess.run(["git", "-C", str(workspace / repo), "show", f"{commit}:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def normalise(out: str, folder: str) -> str:
    out = out.replace(os.path.realpath(folder), SHOWN_DIR).replace(folder, SHOWN_DIR)
    out = re.sub(r"\bin \d+\.\d+s\b", "in Ns", out)
    out = re.sub(r"0x[0-9a-f]+", "0x…", out)
    return "\n".join(line.rstrip() for line in out.strip("\n").splitlines())


def run(command: str, folder: str) -> str:
    env = {"PATH": os.environ["PATH"], "PYTHONUNBUFFERED": "1", "PYTHONDONTWRITEBYTECODE": "1", "HOME": folder,
           "PYTHONPATH": str((workspace / "moks" / "backend").resolve()),  # chunk_demo.py imports MOKS
           # A reader's environment from section 2 has no pytest-asyncio; a MOKS one does, and it warns.
           "PYTEST_ADDOPTS": "-p no:asyncio -p no:cacheprovider"}
    args = shlex.split(command)
    while args and re.fullmatch(r"[A-Z_]+=.*", args[0]):
        key, value = args.pop(0).split("=", 1)
        env[key] = value
    if args[0] in ("python", "python3"):
        args[0] = sys.executable
    r = subprocess.run(args, cwd=folder, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60)
    return r.stdout


blocks = list(re.finditer(r"^```(\w+)\n(.*?)^```", text, re.S | re.M))
with tempfile.TemporaryDirectory() as folder:
    for match in blocks:
        lang, body = match.group(1), match.group(2)
        lines = body.rstrip("\n").splitlines()
        first = lines[0] if lines else ""
        label = label_before(match.start())
        if lang == "text" and first.startswith("$ "):
            counts["runs"] += 1
            expected = normalise("\n".join(lines[1:]), folder)
            actual = normalise(run(first[2:], folder), folder)
            if expected != actual:
                failures.append(f"output of `{first[2:]}` differs.\n--- article\n{expected}\n--- actual\n{actual}")
            continue
        if lang in ("text", "bash", "json") and not first.startswith("# "):
            continue
        name = first.removeprefix("# ").strip()
        if name.startswith("Simplified from "):
            path = name.removeprefix("Simplified from ")
            counts["simplified"] += 1
            if show(repo_for(path), path) is None:
                failures.append(f"simplified block names a missing file: {path}")
            if "Simplified from project code" not in label:
                failures.append(f"{path}: simplified block is not labelled")
            continue
        if name.startswith(("backend/", "services/")) or name == "backend/pyproject.toml":
            repo = repo_for(name)
            source = show(repo, name)
            counts["actual"] += 1
            if source is None:
                failures.append(f"{name}: not a file at {REPOS[repo][0][:7]}")
                continue
            excerpt = lines[1:]
            src = source.splitlines()
            starts = [i for i in range(len(src)) if src[i : i + len(excerpt)] == excerpt]
            if not starts:
                failures.append(f"{name}: excerpt is not a verbatim run of lines:\n" + "\n".join(excerpt[:2]))
                continue
            start, end = starts[0] + 1, starts[0] + len(excerpt)
            anchor = f"{REPOS[repo][0]}/{name}#L{start}-L{end}"
            if "Actual project code" not in label or anchor not in label:
                failures.append(f"{name}: label must say 'Actual project code' and link to #L{start}-L{end}")
            continue
        if re.fullmatch(r"[\w/]+\.(py|txt|json)", name):
            counts["standalone"] += 1
            if "Standalone teaching example" not in label:
                failures.append(f"{name}: standalone block is not labelled")
            target = Path(folder) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body if lang != "python" else "\n".join(lines) + "\n")
            continue
        if lang in ("python", "toml"):
            failures.append(f"unlabelled {lang} block starting: {first[:60]}")

for repo, (commit, _) in REPOS.items():
    for path, start, end in re.findall(rf"https://github\.com/mrjithendar/{repo}/blob/{commit}/([^)#\s]*)(?:#L(\d+)(?:-L(\d+))?)?", text):
        counts["links"] += 1
        source = show(repo, path)
        if source is None:
            failures.append(f"link to missing file {repo}/{path}")
        elif start and int(end or start) > len(source.splitlines()):
            failures.append(f"{repo}/{path}#L{start}-L{end}: past the end of the file")
    for other in re.findall(rf"https://github\.com/mrjithendar/{repo}/(?:blob|tree)/([0-9a-f]+)", text):
        if other != commit:
            failures.append(f"{repo} link pinned to another commit: {other}")

# Internal links: only pages that returned 200 on https://jithendar.com when the draft was written (2026-11-03).
LIVE = {"/python-practice", "/projects/moks", "/projects/roboshop-ai", "/blog/fastapi-and-fastmcp-ai-projects",
        "/blog/roboshop-ai-mcp-server", "/blog/moks-rag-and-skills-design", "/blog/langchain-vs-langgraph-sre-agent-moks"}
for link in re.findall(r"\]\((/[^)\s#]*)", text):
    if link not in LIVE:
        failures.append(f"internal link not in the verified list: {link}")

front, body = text.split("---", 2)[1], text.split("---", 2)[2]
for key in ("description", "seoDescription"):
    value = re.search(rf'^{key}: "(.*)"$', front, re.M).group(1)
    if not 120 <= len(value) <= 160:
        failures.append(f"{key} is {len(value)} characters")
prose = re.sub(r"^```.*?^```", "", body, flags=re.S | re.M)
if re.search(r"^# ", prose, re.M):
    failures.append("the body has its own H1; the page renders the title as the H1")
if re.search(r"\b\d{12}\b", text) or re.search(r"\b(?!127\.0\.0\.1\b)\d{1,3}(?:\.\d{1,3}){3}\b", text):
    failures.append("an account id or IP address appears in the article")
for banned in ("game-changing", "seamless", "delve", "unlock the power", "production-ready", "revolutionize", "supercharge"):
    if banned in text.lower():
        failures.append(f"banned phrase: {banned}")

words = len(re.findall(r"\b\w+\b", prose))
print(f"{counts['actual']} actual excerpts, {counts['simplified']} simplified, {counts['standalone']} standalone files, "
      f"{counts['runs']} commands run, {counts['links']} pinned links; about {words} words of prose")
if failures:
    print(f"\n{len(failures)} problem(s):")
    for f in failures:
        print(f"- {f}")
    sys.exit(1)
print("OK")
