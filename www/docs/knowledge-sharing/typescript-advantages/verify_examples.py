#!/usr/bin/env python3
"""Run every example in the TypeScript advantages article and check the claims made about it.

Usage (from www/):
  python3 docs/knowledge-sharing/typescript-advantages/verify_examples.py \
      --python /path/to/venv/bin/python --go /path/to/go/bin/go [--node node]

The venv needs pydantic, mypy, fastapi and uvicorn. Node must be 23.6+ (type stripping);
TypeScript and Zod come from www/node_modules. Examples are copied to a temp dir first.
"""
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

HERE = Path(__file__).resolve().parent
WWW = HERE.parents[2]
EXPECTED = [
    {"ok": True, "product": {"id": "p1", "name": "Coffee mug", "priceCents": 1299, "inStock": True}},
    {"ok": False, "field": "priceCents"},
    {"ok": False, "field": "name"},
    {"ok": False, "field": "inStock"},
]
ARTICLE = WWW / "content/blog/typescript-advantages-over-python-and-go.mdx"
COMMIT = "be1287a26e41b3618522d7ecbab50d314a6e5c9b"
# Article code block index -> where its lines must come from.
BLOCK_SOURCES = {
    0: "ts/product.ts", 2: "ts/mistakes.ts", 4: "ts/chat-state.ts", 5: "ts/chat-route.ts", 6: "ts/chat-client.ts",
    9: "python-ai-service/app.py", 10: "python/product.py", 11: "go/product.go",
    1: "git:www/src/app/api/practice/problems/[slug]/assist/route.ts",
    7: "git:www/src/lib/practice/ai/tutor.ts",
}
failures: list[str] = []


def code_part(line: str) -> str:
    """Strip indentation and a trailing '  # ...' or '  // ...' comment."""
    return re.split(r"\s{2,}(?:#|//) ", line.strip(), maxsplit=1)[0]


def check_excerpts(root: Path, tsc_mistakes_out: str) -> None:
    blocks = re.findall(r"^```(\w+)\n(.*?)^```", ARTICLE.read_text(), re.S | re.M)
    check("article has 12 code blocks", len(blocks) == 12, str(len(blocks)))
    for i, src in BLOCK_SOURCES.items():
        if src.startswith("git:"):
            text = subprocess.run(["git", "show", f"{COMMIT}:{src[4:]}"], cwd=WWW, capture_output=True, text=True).stdout
        else:
            text = (root / src).read_text()
        have = {code_part(l) for l in text.splitlines()}
        missing = [l for l in blocks[i][1].splitlines()
                   if l.strip() and not l.strip().startswith(("# ", "// ...")) and code_part(l) not in have
                   and not (l.strip().startswith("// ") and src.startswith("ts/") and l.strip() in text.splitlines()[0])]
        check(f"article block {i} matches {src}", not missing, f"lines not in source: {missing}")
    shown = blocks[3][1].strip().splitlines()
    got = [l for l in tsc_mistakes_out.strip().splitlines() if l.strip()]
    check("article shows the exact tsc output", [l.replace("ts/", "", 1) for l in got] == shown, f"{got}")


def run(cmd, cwd, env=None, expect_ok=True):
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    out = p.stdout + p.stderr
    if expect_ok and p.returncode != 0:
        failures.append(f"{' '.join(map(str, cmd))} failed:\n{out}")
    if not expect_ok and p.returncode == 0:
        failures.append(f"{' '.join(map(str, cmd))} was expected to fail")
    return out


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(f"{name} {detail}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", required=True)
    ap.add_argument("--go", required=True)
    ap.add_argument("--node", default="node")
    a = ap.parse_args()
    tsc = [a.node, str(WWW / "node_modules/typescript/bin/tsc")]

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "examples"
        shutil.copytree(HERE / "examples", root)
        (root / "node_modules").symlink_to(WWW / "node_modules")
        env = dict(os.environ, GOCACHE=str(Path(tmp) / "gocache"), GOPATH=str(Path(tmp) / "gopath"), GOFLAGS="-mod=mod")

        # 1. Same behaviour in all three languages.
        outs = {
            "TypeScript": run([a.node, "ts/main.ts", "cases.json"], root),
            "Python": run([a.python, "main.py", "../cases.json"], root / "python"),
            "Go": run([a.go, "run", ".", "../cases.json"], root / "go", env),
        }
        for lang, out in outs.items():
            try:
                got = [json.loads(line) for line in out.strip().splitlines()]
            except json.JSONDecodeError:
                got = out
            check(f"{lang} product example output", got == EXPECTED, f"got {got}")

        # 2. Compile-time checks.
        run(tsc + ["-p", "ts"], root)
        check("tsc strict passes on ts/", not any("tsc" in f for f in failures))
        out = run(tsc + ["--strict", "--module", "nodenext", "--allowImportingTsExtensions", "--noEmit", "--types", "node", "ts/mistakes.ts"], root, expect_ok=False)
        check("tsc catches unchecked union (TS2339)", "mistakes.ts(6,17): error TS2339" in out, out)
        tsc_mistakes_out = out
        check("tsc catches typo (TS2551, did you mean)", "mistakes.ts(10,27): error TS2551" in out and "Did you mean 'priceCents'?" in out, out)
        out = run([a.python, "-m", "mypy", "--strict", "product.py", "main.py"], root / "python")
        check("mypy --strict passes on product.py", "Success" in out, out)
        out = run([a.python, "-m", "mypy", "--strict", "mistakes.py"], root / "python", expect_ok=False)
        check("mypy catches typo", 'has no attribute "price_cent"; maybe "price_cents"?' in out, out)
        out = run([a.python, "mistakes.py"], root / "python", expect_ok=False)
        check("Python runs until the typo, then AttributeError", "AttributeError" in out, out)
        out = run([a.go, "vet", "."], root / "go", env)
        out = run([str(Path(a.go).parent / "gofmt"), "-l", "."], root / "go")
        check("gofmt clean", out.strip() == "", out)
        out = run([a.go, "build", "-o", os.devnull, "."], root / "go-mistake", env, expect_ok=False)
        check("go build catches typo", "has no field or method PriceCent" in out, out)
        out = run([a.python, "-m", "mypy", "--strict", "union.py"], root / "python", expect_ok=False)
        check("mypy catches unchecked Ok | Err union", 'TypedDict "Err" has no key "product"' in out, out)
        run([a.go, "vet", "."], root / "go-nil", env)
        out = run([a.go, "run", "."], root / "go-nil", env, expect_ok=False)
        check("Go compiles unchecked OK, then nil-pointer panic", "nil pointer dereference" in out, out)
        out = run([a.python, "-m", "mypy", "--strict", "app.py"], root / "python-ai-service")
        check("mypy --strict passes on app.py", "Success" in out, out)

        check_excerpts(root, tsc_mistakes_out)

        # 3. Streaming: TypeScript route + client against the FastAPI service.
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        svc = subprocess.Popen([a.python, "-m", "uvicorn", "app:app", "--port", str(port), "--log-level", "warning"],
                               cwd=root / "python-ai-service")
        try:
            for _ in range(50):
                try:
                    socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                    break
                except OSError:
                    time.sleep(0.2)
            out = run([a.node, "ts/stream-check.ts"], root, dict(os.environ, AI_SERVICE_URL=f"http://127.0.0.1:{port}"))
            try:
                got = json.loads(out.strip().splitlines()[-1])
            except (json.JSONDecodeError, IndexError):
                got = {}
            check("stream arrives in several chunks", got.get("chunks", 0) > 1, out)
            check("stream text intact", got.get("text") == "Checking recent latency for: Why is checkout slow?", out)
            check("route rejects empty body with 400", got.get("badStatus") == 400, out)
        finally:
            svc.terminate()
            svc.wait()

    vers = {
        "node": run([a.node, "--version"], WWW).strip(),
        "tsc": run(tsc + ["--version"], WWW).strip(),
        "go": run([a.go, "version"], WWW, env).strip(),
        "python": run([a.python, "--version"], WWW).strip(),
    }
    print(json.dumps(vers))
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
