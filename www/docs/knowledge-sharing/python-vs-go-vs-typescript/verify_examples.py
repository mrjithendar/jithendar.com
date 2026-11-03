#!/usr/bin/env python3
"""Check every example in content/blog/python-vs-go-vs-typescript.mdx.

What it does:
  1. Standalone comparison examples: writes each labelled group of blocks to its own folder and runs the
     Python with --python, the Go with `go run -race .` and the TypeScript with `node`, then compares stdout
     with the block's "Output:" comment. Groups labelled "Same output in all three languages" must also print
     identical text. A Go file containing "// Error:" lines must fail to build with each of those messages.
     Groups labelled "Test example" run pytest, `go test -race ./...` and Vitest instead.
  2. Static checks: gofmt and go vet on every Go folder; mypy on every Python file (lines marked
     "a type checker flags this line" must produce an error, no other line may); tsc in strict mode with
     erasableSyntaxOnly, for each --tsc compiler, over every TypeScript file.
  3. Actual project code: each excerpt must equal the cited lines of the file at the commit in the sources list.

Usage (from www/):
  python3 docs/knowledge-sharing/python-vs-go-vs-typescript/verify_examples.py \
      --python /path/to/venv/bin/python     # needs mypy and pytest installed
      --go /path/to/go/bin/go               # Go 1.25 or later
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
ARTICLE = WWW / "content" / "blog" / "python-vs-go-vs-typescript.mdx"
LABEL = re.compile(r"^\*(Standalone comparison example|Actual project code|Simplified from project code|Mock API response)\.\s*(.*)\*$")
PROJECT = re.compile(r"Repository: (\S+)\. File: `([^`]+)`, lines (\d+)–(\d+)\.")
FENCE = re.compile(r"^```(\w*)\s*$")
FILE_HEADER = re.compile(r"^(?:#|//) ([\w/.]+\.(?:py|go|ts))$")
FLAG = "a type checker flags this line"
LANGS = {"python": ("py", "#"), "go": ("go", "//"), "typescript": ("ts", "//")}


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
    root = tempfile.mkdtemp(prefix="pgts-mock-")
    Path(root, "user.json").write_text(user_json)

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            pass

    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", 8000)) == 0:
            sys.exit("port 8000 is in use; stop whatever is listening there and retry")
    server = ThreadingHTTPServer(("127.0.0.1", 8000), partial(Quiet, directory=root))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield
    finally:
        server.shutdown()


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=180, env=env)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--go", default="go")
    ap.add_argument("--node", default="node")
    ap.add_argument("--tsc", action="append", default=[])
    ap.add_argument("--workspace", default=str(WWW.parents[1]), help="folder holding jithendar.com, roboshop-ai and the other repositories")
    ap.add_argument("--keep", help="write the extracted examples to this folder instead of a temporary one")
    args = ap.parse_args()
    tscs = [str(Path(t).resolve()) for t in args.tsc] or [str(WWW / "node_modules" / "typescript" / "bin" / "tsc")]
    go = str(Path(args.go).resolve()) if os.sep in args.go else args.go
    gofmt = str(Path(go).with_name("gofmt")) if os.sep in go else "gofmt"
    go_env = {**os.environ, "GOTOOLCHAIN": "local", "GOFLAGS": "-mod=mod", "GOPROXY": "off"}

    text = ARTICLE.read_text()
    blocks = list(parse(text))
    commits = commits_from_sources(text)
    user_json = next(code for kind, _, _, lang, code in blocks if kind == "Mock API response" and lang == "json")
    failures: list[str] = []
    out = Path(args.keep or tempfile.mkdtemp(prefix="pgts-"))
    out.mkdir(parents=True, exist_ok=True)
    (out / "node_modules").unlink(missing_ok=True)
    (out / "node_modules").symlink_to(WWW / "node_modules")
    (out / "package.json").write_text('{"type": "module"}\n')

    groups: dict[int, dict] = {}
    for kind, label, label_id, lang, code in blocks:
        if kind in ("Standalone comparison example", "Simplified from project code") and lang in LANGS:
            g = groups.setdefault(label_id, {"label": label, "python": [], "go": [], "typescript": []})
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
            ok = want == code
            print(f"[project] {repo}/{path}:{start}-{end} at {commit[:7] if commit else '?'}: {'ok' if ok else 'MISMATCH'}")
            if not ok:
                failures.append(f"{repo}/{path}:{start}-{end} does not match the excerpt")

    counts = {"run": 0, "test": 0, "compile-fail": 0}
    with mock_server(user_json):
        for n, (_, g) in enumerate(sorted(groups.items()), 1):
            d = out / f"g{n:02d}"
            is_test = g["label"].startswith("Test example")
            outputs: dict[str, str] = {}
            for lang, (ext, comment) in LANGS.items():
                if not g[lang]:
                    continue
                ld = d / lang
                ld.mkdir(parents=True, exist_ok=True)
                entry, errors_expected = None, []
                for code in g[lang]:
                    header = FILE_HEADER.match(code.split("\n", 1)[0])
                    name = header.group(1) if header else f"example.{ext}"
                    (ld / name).parent.mkdir(parents=True, exist_ok=True)
                    (ld / name).write_text(code)
                    errors_expected += [line[len("// Error: ") :] for line in code.split("\n") if line.startswith("// Error: ")]
                    if expected_output(code, comment) is not None:
                        entry = (name, expected_output(code, comment))
                if lang == "go":
                    (ld / "go.mod").write_text("module example\n\ngo 1.25\n")
                    fmt = run([gofmt, "-l", "."], ld)
                    if fmt.stdout.strip():
                        failures.append(f"g{n:02d} gofmt would change: {fmt.stdout.split()}")
                    print(f"[gofmt] g{n:02d} {'ok' if not fmt.stdout.strip() else 'FAIL'}")
                if lang == "go" and errors_expected:
                    proc = run([go, "build", "./..."], ld, go_env)
                    ok = proc.returncode != 0 and all(e in proc.stderr for e in errors_expected)
                    counts["compile-fail"] += 1
                    print(f"[build] g{n:02d} go         {'ok (fails as documented)' if ok else 'FAIL'}")
                    if not ok:
                        failures.append(f"g{n:02d} go: expected build errors {errors_expected}\n{proc.stderr}")
                    continue
                if lang == "go":
                    vet = run([go, "vet", "./..."], ld, go_env)
                    print(f"[vet]   g{n:02d} {'ok' if vet.returncode == 0 else 'FAIL'}")
                    if vet.returncode != 0:
                        failures.append(f"g{n:02d} go vet:\n{vet.stderr}")
                if is_test:
                    cmd = {
                        "python": [args.python, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                        "go": [go, "test", "-race", "-count=1", "./..."],
                        "typescript": [str(WWW / "node_modules" / ".bin" / "vitest"), "run", "--root", str(ld)],
                    }[lang]
                    if lang == "typescript":
                        (ld / "node_modules").unlink(missing_ok=True)
                        (ld / "node_modules").symlink_to(WWW / "node_modules")
                    proc = run(cmd, ld, go_env if lang == "go" else None)
                    counts["test"] += 1
                    ok = proc.returncode == 0
                    print(f"[test]  g{n:02d} {lang:10} {'ok' if ok else 'FAIL'}  ({(proc.stdout.strip().splitlines() or [''])[-1].strip()})")
                    if not ok:
                        failures.append(f"g{n:02d} {lang} tests failed:\n{proc.stdout}\n{proc.stderr}")
                    continue
                if entry is None:
                    failures.append(f"g{n:02d} {lang}: no Output: comment")
                    continue
                name, want = entry
                cmd = {"python": [args.python, name], "go": [go, "run", "-race", "."], "typescript": [args.node, name]}[lang]
                proc = run(cmd, ld, go_env if lang == "go" else None)
                outputs[lang] = proc.stdout
                counts["run"] += 1
                ok = proc.returncode == 0 and proc.stdout == want and not proc.stderr.strip()
                print(f"[run]   g{n:02d} {lang:10} {'ok' if ok else 'FAIL'}  ({g['label']})")
                if not ok:
                    failures.append(f"g{n:02d} {lang}: exit {proc.returncode}\n--- expected\n{want}--- got\n{proc.stdout}--- stderr\n{proc.stderr}")
            if g["label"].startswith("Same output") and len(set(outputs.values())) > 1:
                failures.append(f"g{n:02d}: labelled same output, but the languages differ")

            pys = sorted(str(p.relative_to(d / "python")) for p in (d / "python").glob("*.py")) if (d / "python").exists() else []
            if pys:
                proc = run([args.python, "-m", "mypy", "--strict", "--no-error-summary", "--cache-dir", str(out / ".mypy_cache"), *pys], d / "python")
                errors = {(m.group(1), int(m.group(2))) for m in re.finditer(r"^(\S+\.py):(\d+): error", proc.stdout, re.M)}
                flagged = {(p, i) for p in pys for i, line in enumerate((d / "python" / p).read_text().split("\n"), 1) if FLAG in line}
                ok = errors == flagged
                print(f"[mypy]  g{n:02d} {'ok' if ok else 'FAIL'}" + (f" (expected errors on {len(flagged)} flagged line)" if flagged else ""))
                if not ok:
                    failures.append(f"g{n:02d} mypy: errors {sorted(errors)} flagged {sorted(flagged)}\n{proc.stdout}")

    for tsc in tscs:
        for extra in (False, True):
            cfg = {
                "compilerOptions": {
                    "strict": True, "noEmit": True, "target": "es2022", "module": "nodenext", "moduleResolution": "nodenext",
                    "allowImportingTsExtensions": True, "erasableSyntaxOnly": True, "moduleDetection": "force",
                    "skipLibCheck": True, "types": ["node"], **({"noUncheckedIndexedAccess": True} if extra else {}),
                },
                "include": ["g*/typescript/**/*.ts"],
            }
            (out / "tsconfig.json").write_text(json.dumps(cfg, indent=2))
            version = run([args.node, tsc, "--version"], out).stdout.strip()
            proc = run([args.node, tsc, "-p", "tsconfig.json"], out)
            label = f"{version}{' + noUncheckedIndexedAccess' if extra else ''}"
            print(f"[tsc]   {label}: {'ok' if proc.returncode == 0 else 'FAIL'}")
            if proc.returncode != 0:
                if extra:
                    print("        (informational: the article's tsconfig does not enable noUncheckedIndexedAccess)\n" + proc.stdout)
                else:
                    failures.append(f"tsc {label}:\n{proc.stdout}")

    print(f"\n{counts['run']} programs run, {counts['test']} test suites, {counts['compile-fail']} expected compile failures, "
          f"{sum(1 for b in blocks if b[0] == 'Actual project code')} project excerpts")
    if failures:
        print(f"\n{len(failures)} FAILURE(S):")
        for f in failures:
            print("-", f)
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
