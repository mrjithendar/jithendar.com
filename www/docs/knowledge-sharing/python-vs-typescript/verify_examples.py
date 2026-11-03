#!/usr/bin/env python3
"""Check every example in content/blog/python-vs-typescript.mdx.

What it does:
  1. Standalone comparison examples: writes each group of blocks to its own folder, runs the Python with
     --python and the TypeScript with `node`, and compares stdout with the block's "Output:" comment.
     Pairs labelled "Same output in both languages" must also print identical text.
  2. Type checks: every TypeScript file with each --tsc compiler (strict, then strict plus
     noUncheckedIndexedAccess), and every Python file with mypy (run by --python). Python lines marked
     "a type checker flags this line" must produce a mypy error; no other line may.
  3. Actual project code: each excerpt must equal the cited lines of the file at the commit in the sources list.

Usage (from www/):
  python3 docs/knowledge-sharing/python-vs-typescript/verify_examples.py \
      --python /path/to/venv/bin/python   # needs pydantic==2.14.2 and mypy installed
      --tsc node_modules/typescript/bin/tsc --tsc ../../roboshop-ai/node_modules/typescript/bin/tsc

Exit code 0 when every check passes. It never touches the network beyond 127.0.0.1.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WWW = Path(__file__).resolve().parents[3]
ARTICLE = WWW / "content" / "blog" / "python-vs-typescript.mdx"
LABEL = re.compile(r"^\*(Standalone comparison example|Actual project code|Simplified from project code)\.\s*(.*)\*$")
PROJECT = re.compile(r"Repository: (\S+)\. File: `([^`]+)`, lines (\d+)–(\d+)\.")
FENCE = re.compile(r"^```(\w*)\s*$")
FILE_HEADER = re.compile(r"^(?:#|//) (\w+\.(?:py|ts))$")
FLAG = "a type checker flags this line"


def parse(text: str):
    """Yield (label_kind, label_text, label_id, lang, code) for each fenced block."""
    body = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    lines = body.split("\n")
    kind, label, label_id, i = None, "", 0, 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("## ") or line.startswith("### "):
            kind, label = None, ""
        m = LABEL.match(line.strip())
        if m:
            kind, label, label_id = m.group(1), m.group(2), label_id + 1
        f = FENCE.match(line)
        if f:
            lang, j = f.group(1), i + 1
            while not lines[j].startswith("```"):
                j += 1
            yield kind, label, label_id, lang, "\n".join(lines[i + 1 : j]) + "\n"
            i = j
        i += 1


def expected_output(code: str, comment: str) -> str | None:
    lines = code.rstrip("\n").split("\n")
    marker = f"{comment} Output:"
    if marker not in lines:
        return None
    tail = lines[lines.index(marker) + 1 :]
    return "".join(line[len(comment) + 1 :] + "\n" if line != comment else "\n" for line in tail)


def commits_from_sources(text: str) -> dict[str, str]:
    return {m.group(1): m.group(2) for m in re.finditer(r"github\.com/mrjithendar/([\w.-]+)/tree/([0-9a-f]{40})", text)}


@contextlib.contextmanager
def mock_server(user_json: str):
    root = tempfile.mkdtemp(prefix="pvts-mock-")
    Path(root, "user.json").write_text(user_json)
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            pass

    handler = partial(Quiet, directory=root)
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", 8000)) == 0:
            sys.exit("port 8000 is in use; stop whatever is listening there and retry")
    server = ThreadingHTTPServer(("127.0.0.1", 8000), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield
    finally:
        server.shutdown()


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--node", default="node")
    ap.add_argument("--tsc", action="append", default=[])
    ap.add_argument("--workspace", default=str(WWW.parents[1]), help="folder holding jithendar.com, moks and roboshop-ai")
    ap.add_argument("--keep", help="write the extracted examples to this folder instead of a temporary one")
    args = ap.parse_args()
    tscs = [str(Path(t).resolve()) for t in args.tsc] or [str(WWW / "node_modules" / "typescript" / "bin" / "tsc")]

    text = ARTICLE.read_text()
    blocks = list(parse(text))
    commits = commits_from_sources(text)
    user_json = next(code for _, _, _, lang, code in blocks if lang == "json")
    failures: list[str] = []
    out = Path(args.keep or tempfile.mkdtemp(prefix="pvts-"))
    out.mkdir(parents=True, exist_ok=True)
    (out / "node_modules").unlink(missing_ok=True)
    (out / "node_modules").symlink_to(WWW / "node_modules")
    (out / "package.json").write_text('{"type": "module"}\n')

    # Group standalone blocks by label occurrence.
    groups: dict[int, dict] = {}
    for kind, label, label_id, lang, code in blocks:
        if kind == "Standalone comparison example" and lang in ("python", "typescript"):
            g = groups.setdefault(label_id, {"label": label, "python": [], "typescript": []})
            g[lang].append(code)
        elif kind == "Actual project code":
            m = PROJECT.search(label)
            if not m:
                failures.append(f"project label not parsed: {label}")
                continue
            repo, path, start, end = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
            commit = commits.get(repo)
            src = subprocess.run(["git", "-C", str(Path(args.workspace) / repo), "show", f"{commit}:{path}"], capture_output=True, text=True)
            if src.returncode != 0:
                failures.append(f"{repo}/{path}: git show failed: {src.stderr.strip()}")
                continue
            want = "\n".join(src.stdout.split("\n")[start - 1 : end]) + "\n"
            status = "ok" if want == code else "MISMATCH"
            print(f"[project] {repo}/{path}:{start}-{end} at {commit[:7] if commit else '?'}: {status}")
            if want != code:
                failures.append(f"{repo}/{path}:{start}-{end} does not match the excerpt")

    results = []
    with mock_server(user_json):
        for n, (label_id, g) in enumerate(sorted(groups.items()), 1):
            d = out / f"g{n:02d}"
            d.mkdir(exist_ok=True)
            outputs: dict[str, str] = {}
            for lang, ext, comment in (("python", "py", "#"), ("typescript", "ts", "//")):
                entry = None
                for code in g[lang]:
                    header = FILE_HEADER.match(code.split("\n", 1)[0])
                    name = header.group(1) if header else f"example.{ext}"
                    (d / name).write_text(code)
                    if expected_output(code, comment) is not None:
                        entry = (name, expected_output(code, comment))
                if not g[lang]:
                    continue
                if entry is None:
                    failures.append(f"g{n:02d} {lang}: no Output: comment")
                    continue
                name, want = entry
                cmd = [args.python, name] if lang == "python" else [args.node, name]
                proc = run(cmd, d)
                outputs[lang] = proc.stdout
                ok = proc.returncode == 0 and proc.stdout == want and not proc.stderr.strip()
                results.append({"group": n, "lang": lang, "label": g["label"], "ok": ok, "stdout": proc.stdout, "stderr": proc.stderr})
                print(f"[run] g{n:02d} {lang:10} {'ok' if ok else 'FAIL'}  ({g['label']})")
                if not ok:
                    failures.append(f"g{n:02d} {lang}: exit {proc.returncode}\n--- expected\n{want}--- got\n{proc.stdout}--- stderr\n{proc.stderr}")
            if g["label"].startswith("Same output") and len(outputs) == 2 and outputs["python"] != outputs["typescript"]:
                failures.append(f"g{n:02d}: labelled same output, but Python and TypeScript differ")

            # mypy per group (module names repeat across groups).
            pys = sorted(p.name for p in d.glob("*.py"))
            if pys:
                proc = run([args.python, "-m", "mypy", "--no-error-summary", "--cache-dir", str(out / ".mypy_cache"), *pys], d)
                errors = {(m.group(1), int(m.group(2))) for m in re.finditer(r"^(\S+\.py):(\d+): error", proc.stdout, re.M)}
                flagged = {(p, i) for p in pys for i, line in enumerate((d / p).read_text().split("\n"), 1) if FLAG in line}
                ok = errors == flagged
                print(f"[mypy] g{n:02d} {'ok' if ok else 'FAIL'}" + (f" (expected errors on {len(flagged)} flagged line)" if flagged else ""))
                if not ok:
                    failures.append(f"g{n:02d} mypy: errors {sorted(errors)} flagged {sorted(flagged)}\n{proc.stdout}")

    # One tsc run per compiler and setting over every TypeScript file.
    for tsc in tscs:
        for extra in ([], ["--noUncheckedIndexedAccess"]):
            cfg = {
                "compilerOptions": {
                    "strict": True, "noEmit": True, "target": "es2022", "module": "nodenext", "moduleResolution": "nodenext",
                    "allowImportingTsExtensions": True, "moduleDetection": "force", "skipLibCheck": True, "types": ["node"],
                    **({"noUncheckedIndexedAccess": True} if extra else {}),
                },
                "include": ["g*/*.ts"],
            }
            (out / "tsconfig.json").write_text(json.dumps(cfg, indent=2))
            proc = run([args.node, tsc, "-p", "tsconfig.json"], out)
            version = run([args.node, tsc, "--version"], out).stdout.strip()
            ok = proc.returncode == 0
            print(f"[tsc] {version} strict{' + noUncheckedIndexedAccess' if extra else ''}: {'ok' if ok else 'FAIL'}")
            if not ok:
                failures.append(f"tsc {version} {extra}:\n{proc.stdout}{proc.stderr}")

    (out / "results.json").write_text(json.dumps(results, indent=2))
    py_version = run([args.python, "--version"], out).stdout.strip()
    node_version = run([args.node, "--version"], out).stdout.strip()
    print(f"\n{py_version}, Node.js {node_version}; examples in {out}")
    if failures:
        print(f"\n{len(failures)} failure(s):")
        for f in failures:
            print("-", f)
        return 1
    print(f"All checks passed: {len(groups)} example groups, {sum(1 for b in blocks if b[0] == 'Actual project code')} project excerpts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
