#!/usr/bin/env python3
"""Check every example in content/blog/shell-scripting-vs-python.mdx.

What it does:
  1. Builds the practice folder once by running the block labelled "Setup for the examples".
  2. Starts the article's mock API (the block whose first line is "# mock_api.py") on 127.0.0.1:8765.
  3. Standalone comparison examples: each labelled group gets a fresh copy of the practice folder. Every
     block is written to the file named on its first line (second line after a shebang), then each "# Run:" case is executed with
     `bash -c` and its stdout, stderr and exit status are compared with the block's comments:
         # Run: bash args.sh "two words"
         # Exit status: 2        (optional, default 0)
         # Output:               (stdout, one "# " line per output line, "#" for an empty line)
         # Stderr:               (optional; without it stderr must be empty)
     Inside `bash -c`, `bash` is the --bash interpreter, `sh` is dash (a strict POSIX shell) and
     `python3` is the --python interpreter. LC_ALL=C, so glob and sort order is byte order.
  4. ShellCheck on every bash and sh block (shell taken from the fence). Lines ending in
     "# ShellCheck warns" must produce a diagnostic; no other line may.
  5. py_compile on every python block.
  6. Actual repository code: each excerpt must equal the cited lines of the file at the commit listed in
     the article's sources (sibling checkouts of jithendar.com, moks, roboshop-ai and tools).

Usage (from www/):
  python3 docs/knowledge-sharing/shell-vs-python/verify_examples.py [--bash PATH] [--python PATH]

Needs bash, dash, jq, curl, shellcheck and git. Never touches the network beyond 127.0.0.1.
Exit code 0 when every check passes.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

WWW = Path(__file__).resolve().parents[3]
WORK = WWW.parents[1]
ARTICLE = WWW / "content" / "blog" / "shell-scripting-vs-python.mdx"
LABEL = re.compile(r"^\*(Standalone comparison example|Actual repository code|Simplified from repository code|Setup for the examples)\.\*\s*(.*)$")
REPO_REF = re.compile(r"Repository: (\S+?)\. File: `([^`]+)`, lines? (\d+)(?:–(\d+))?\.")
FENCE = re.compile(r"^```(\w*)\s*$")
NAME = re.compile(r"^# ([\w.-]+\.(?:sh|py))$")
WARN = "# ShellCheck warns"
MOCK_PORT = 8765


def parse(text: str):
    """Yield (kind, label_text, group_id, lang, code) for every fenced block."""
    body = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    lines = body.split("\n")
    kind, label, group, i = None, "", 0, 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("## ") or line.startswith("### "):
            kind, label = None, ""
        m = LABEL.match(line.strip())
        if m:
            kind, label, group = m.group(1), m.group(2), group + 1
        f = FENCE.match(line)
        if f and f.group(1):
            j = i + 1
            while not lines[j].startswith("```"):
                j += 1
            yield kind, label, group, f.group(1), "\n".join(lines[i + 1 : j]) + "\n"
            i = j
        i += 1


def run_cases(code: str):
    """Split the trailing comment section of a block into run cases."""
    cases, current, section = [], None, None
    for line in code.rstrip("\n").split("\n"):
        if line.startswith("# Run: "):
            current = {"cmd": line[len("# Run: "):], "status": 0, "stdout": [], "stderr": None}
            cases.append(current)
            section = None
            continue
        if current is None:
            continue
        if line.startswith("# Exit status: "):
            current["status"] = int(line.split(": ", 1)[1])
        elif line == "# Output:":
            section = "stdout"
        elif line == "# Stderr:":
            section, current["stderr"] = "stderr", []
        elif section and (line == "#" or line.startswith("# ")):
            current[section].append(line[2:])
        else:
            raise ValueError(f"unexpected line in run section: {line!r}")
    return cases


def shims(directory: Path, bash: str, python: str) -> Path:
    directory.mkdir()
    for name, target in (("bash", bash), ("sh", shutil.which("dash") or "/bin/sh"), ("python3", python)):
        (directory / name).symlink_to(target)
    return directory


def environment(shim: Path, home: Path) -> dict[str, str]:
    path = os.pathsep.join([str(shim), "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"])
    return {"PATH": path, "HOME": str(home), "LC_ALL": "C", "LANG": "C", "TERM": "dumb", "PYTHONDONTWRITEBYTECODE": "1"}


def commits_from_sources(text: str) -> dict[str, str]:
    return {m.group(1): m.group(2) for m in re.finditer(r"github\.com/mrjithendar/([\w.-]+)/tree/([0-9a-f]{40})", text)}


def shellcheck(path: Path, shell: str, code: str) -> list[str]:
    result = subprocess.run(["shellcheck", "-s", shell, "-f", "json", str(path)], capture_output=True, text=True)
    found = {}
    for item in json.loads(result.stdout or "[]"):
        found.setdefault(item["line"], []).append(f"SC{item['code']}")
    problems = []
    for number, line in enumerate(code.split("\n"), start=1):
        expected = line.rstrip().endswith(WARN)
        if expected and number not in found:
            problems.append(f"line {number}: expected a ShellCheck warning")
        if not expected and number in found:
            problems.append(f"line {number}: unexpected {', '.join(found[number])}: {line.strip()}")
    return problems


def wait_for_port(port: int, seconds: float = 10) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.1)
    raise RuntimeError(f"mock API did not start on port {port}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bash", default=shutil.which("bash", path="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"))
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--skip-shellcheck", action="store_true", help="for compatibility runs with another bash")
    args = parser.parse_args()
    text = ARTICLE.read_text(encoding="utf-8")
    blocks = list(parse(text))
    failures: list[str] = []
    counts = {"run cases": 0, "shellcheck files": 0, "python files": 0, "excerpts": 0}
    version = subprocess.run([args.bash, "-c", "echo $BASH_VERSION"], capture_output=True, text=True).stdout.strip()
    print(f"bash {version} ({args.bash}); python {subprocess.run([args.python, '-V'], capture_output=True, text=True).stdout.strip()}")

    with tempfile.TemporaryDirectory(prefix="shell vs python ") as temp:
        root = Path(temp)
        shim = shims(root / "shims", args.bash, args.python)
        template = root / "practice"
        template.mkdir()
        env = environment(shim, template)

        setup = [code for kind, _, _, _, code in blocks if kind == "Setup for the examples" and code.startswith("# setup.sh\n")]
        assert len(setup) == 1, "exactly one setup block expected"
        (template / "setup.sh").write_text(setup[0])
        subprocess.run([args.bash, "setup.sh"], cwd=template, env=env, check=True)
        (template / "setup.sh").unlink()

        mock = [code for kind, _, _, lang, code in blocks if lang == "python" and code.startswith("# mock_api.py\n")]
        assert len(mock) == 1, "exactly one mock_api.py block expected"
        mock_dir = root / "mock"
        mock_dir.mkdir()
        (mock_dir / "mock_api.py").write_text(mock[0])
        server = subprocess.Popen([args.python, "mock_api.py"], cwd=mock_dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            wait_for_port(MOCK_PORT)
            groups: dict[int, list[tuple[str, str, str]]] = {}
            for kind, label, group, lang, code in blocks:
                if kind != "Standalone comparison example" or lang not in ("bash", "sh", "python"):
                    continue
                first, second = (code.split("\n") + [""])[:2]
                name = NAME.match(second if first.startswith("#!") else first)
                if not name:
                    failures.append(f"group {group}: {lang} block has no '# file.ext' first line: {code[:60]!r}")
                    continue
                groups.setdefault(group, []).append((name.group(1), lang, code))

            for group, files in groups.items():
                workdir = root / f"group-{group:03d}"
                shutil.copytree(template, workdir, symlinks=True)
                for filename, lang, code in files:
                    (workdir / filename).write_text(code)
                    if lang in ("bash", "sh") and not args.skip_shellcheck:
                        counts["shellcheck files"] += 1
                        failures += [f"{filename}: {p}" for p in shellcheck(workdir / filename, lang, code)]
                    if lang == "python":
                        counts["python files"] += 1
                        compiled = subprocess.run([args.python, "-m", "py_compile", filename], cwd=workdir, env=env, capture_output=True, text=True)
                        if compiled.returncode:
                            failures.append(f"{filename}: py_compile failed: {compiled.stderr.strip()}")
                for filename, lang, code in files:
                    for case in run_cases(code):
                        counts["run cases"] += 1
                        try:
                            result = subprocess.run([args.bash, "-c", case["cmd"]], cwd=workdir, env={**env, "HOME": str(workdir)},
                                                    capture_output=True, text=True, timeout=60)
                        except subprocess.TimeoutExpired:
                            failures.append(f"{filename}: `{case['cmd']}` timed out")
                            continue
                        expected_out = "".join(line + "\n" for line in case["stdout"])
                        expected_err = "".join(line + "\n" for line in case["stderr"] or [])
                        problems = []
                        if result.returncode != case["status"]:
                            problems.append(f"exit status {result.returncode}, expected {case['status']}")
                        if result.stdout != expected_out:
                            problems.append(f"stdout:\n{result.stdout}--- expected:\n{expected_out}")
                        if result.stderr != expected_err:
                            problems.append(f"stderr:\n{result.stderr}--- expected:\n{expected_err}")
                        if problems:
                            failures.append(f"{filename}: `{case['cmd']}`\n  " + "\n  ".join(problems))
        finally:
            server.terminate()
            server.wait(timeout=10)

    commits = commits_from_sources(text)
    for kind, label, group, lang, code in blocks:
        if kind != "Actual repository code":
            continue
        ref = REPO_REF.search(label)
        if not ref:
            failures.append(f"group {group}: actual code label lacks 'Repository: X. File: `p`, lines a–b.': {label}")
            continue
        repo, path, start = ref.group(1), ref.group(2), int(ref.group(3))
        end = int(ref.group(4) or start)
        if repo not in commits:
            failures.append(f"{repo}: no commit in the article's sources")
            continue
        shown = subprocess.run(["git", "-C", str(WORK / repo), "show", f"{commits[repo]}:{path}"], capture_output=True, text=True)
        if shown.returncode:
            failures.append(f"{repo}:{path}: {shown.stderr.strip()}")
            continue
        wanted = "".join(line + "\n" for line in shown.stdout.split("\n")[start - 1 : end])
        counts["excerpts"] += 1
        if wanted != code:
            failures.append(f"{repo}:{path} lines {start}–{end} differ from the excerpt:\n{code}--- file has:\n{wanted}")

    for failure in failures:
        print("FAIL", failure)
    print(", ".join(f"{v} {k}" for k, v in counts.items()) + f"; {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
