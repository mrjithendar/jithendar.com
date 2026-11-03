#!/usr/bin/env python3
"""Checks the TypeScript tutorial draft against the code it quotes.

Run from www/:  python3 -I docs/knowledge-sharing/typescript-tutorial/verify_article.py

1. Every fenced block is labelled "Actual project code", "Simplified from project code" or
   "Standalone teaching example".
2. Actual blocks appear byte for byte in the cited file at the pinned commit (git show).
3. Simplified blocks: every line except "// ..." markers appears in the cited file.
4. Teaching blocks in ts/tsx compile with the project's compiler and strictness settings. A block
   that contains "// error TSnnnn" must fail with exactly those codes; any other block must compile.
   JavaScript blocks without JSX are syntax-checked with node --check.
5. Prose (outside code) has no bare < > { } that MDX or the visual editor would misread.
6. Frontmatter lengths match src/lib/content/schema.ts; every GitHub link is pinned to the commit.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

COMMIT = "dc249e807f83ef5a0e2aaa34638c42399e91e905"
WWW = os.getcwd()
ARTICLE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WWW, "content/blog/learning-typescript-real-project-jithendar-com.mdx")
LABEL = re.compile(r"^\*(Actual project code|Simplified from project code|Standalone teaching example)\b")
PATH_IN_LABEL = re.compile(r"\(https://github\.com/mrjithendar/jithendar\.com/blob/([0-9a-f]+)/(www/[^)]+)\)")
TSCONFIG = {
    "compilerOptions": {
        "target": "ES2022", "lib": ["dom", "dom.iterable", "esnext"], "strict": True,
        "noUncheckedIndexedAccess": True, "noEmit": True, "module": "esnext", "moduleResolution": "bundler",
        "isolatedModules": True, "jsx": "react-jsx", "skipLibCheck": True, "types": [],
    },
    "include": ["*.ts", "*.tsx"],
}

failures = []


def fail(msg):
    failures.append(msg)


def git_file(path):
    from urllib.parse import unquote
    return subprocess.run(["git", "show", f"{COMMIT}:{unquote(path)}"], capture_output=True, text=True, check=True,
                          cwd=os.path.dirname(WWW)).stdout


text = open(ARTICLE, encoding="utf-8").read()
fm_match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
fm, body = fm_match.group(1), text[fm_match.end():]

# 6. frontmatter
def fm_value(key):
    m = re.search(rf'^{key}: "(.*)"$', fm, re.M)
    return m.group(1) if m else None

for key, lo, hi in [("title", 10, 110), ("description", 50, 160), ("seoTitle", 10, 110), ("seoDescription", 50, 160)]:
    v = fm_value(key)
    if v is None or not lo <= len(v) <= hi:
        fail(f"frontmatter {key}: length {len(v) if v else 'missing'} outside {lo}-{hi}")
if "status: review" not in fm:
    fail("frontmatter status must stay review (draft for owner review)")
for url in re.findall(r"https://github\.com/mrjithendar/jithendar\.com/(?:blob|tree)/([0-9a-f]+)", body):
    if url != COMMIT:
        fail(f"GitHub link not pinned to {COMMIT[:7]}: {url}")

# split into prose and fences
lines = body.split("\n")
blocks, prose = [], []
i = 0
while i < len(lines):
    m = re.match(r"^```(\w*)", lines[i])
    if m:
        lang, start = m.group(1), i
        j = i + 1
        while not lines[j].startswith("```"):
            j += 1
        label = next((lines[k] for k in range(start - 1, -1, -1) if lines[k].strip()), "")
        blocks.append({"lang": lang, "code": "\n".join(lines[i + 1:j]), "label": label, "line": start + 1})
        i = j + 1
        continue
    prose.append((i + 1, lines[i]))
    i += 1

# 5. prose safety
for n, line in prose:
    outside = re.sub(r"`[^`]*`", "", line)
    outside = re.sub(r"\]\([^)]*\)", "]", outside)  # link targets
    if line.startswith("|") or line.startswith("#"):
        pass
    if re.search(r"[<>{}]", outside):
        fail(f"prose line {n + fm.count(chr(10)) + 2}: bare < > {{ }} outside code: {line[:80]}")

# 1-4. blocks
tmp = tempfile.mkdtemp(prefix="ts-tutorial-")
os.symlink(os.path.join(WWW, "node_modules"), os.path.join(tmp, "node_modules"))
expected = {}
counts = {"actual": 0, "simplified": 0, "teaching": 0}
for idx, b in enumerate(blocks):
    m = LABEL.match(b["label"])
    where = f"block at body line {b['line']} ({b['lang']})"
    if not m:
        fail(f"{where}: missing label, found {b['label'][:60]!r}")
        continue
    kind = m.group(1)
    if kind == "Actual project code" or kind == "Simplified from project code":
        p = PATH_IN_LABEL.search(b["label"])
        if not p:
            if kind == "Simplified from project code" and b["lang"] == "text":
                counts["simplified"] += 1
                continue
            fail(f"{where}: label has no pinned source link")
            continue
        source = git_file(p.group(2))
        if kind == "Actual project code":
            counts["actual"] += 1
            if b["code"] not in source:
                fail(f"{where}: not found verbatim in {p.group(2)}")
        else:
            counts["simplified"] += 1
            src_lines = {l.strip() for l in source.split("\n")}
            for l in b["code"].split("\n"):
                s = l.strip()
                if not s or s in ("// ...", "// ... 20 more fields") or s.startswith("// ..."):
                    continue
                if s not in src_lines:
                    fail(f"{where}: line not in {p.group(2)}: {s[:70]}")
        continue
    counts["teaching"] += 1
    if b["lang"] in ("ts", "tsx"):
        name = f"b{idx:02d}.{b['lang']}"
        code = b["code"]
        if not re.search(r"^\s*(import|export)\b", code, re.M):
            code += "\nexport {};\n"
        open(os.path.join(tmp, name), "w").write(code)
        expected[name] = (sorted(set(re.findall(r"// error (TS\d+)", b["code"]))), where)
    elif b["lang"] == "js" and not re.search(r"<\w", b["code"]):
        r = subprocess.run(["node", "--check", "--input-type=module"], input=b["code"], capture_output=True, text=True)
        if r.returncode:
            fail(f"{where}: node --check failed: {r.stderr.strip()[:200]}")

# tsc reports only syntax errors (TS1xxx) while any file has one, so files with syntax errors are
# recorded and moved out of the program, then the rest is compiled again for type errors.
got, pending = {}, set(expected)
while pending:
    json.dump({**TSCONFIG, "include": sorted(pending)}, open(os.path.join(tmp, "tsconfig.json"), "w"))
    r = subprocess.run([os.path.join(tmp, "node_modules/.bin/tsc"), "-p", tmp], capture_output=True, text=True)
    found = {}
    for line in r.stdout.splitlines():
        m = re.search(r"(b\d+\.tsx?)\(\d+,\d+\): error (TS\d+)", line)
        if m:
            found.setdefault(m.group(1), set()).add(m.group(2))
    syntax = {f for f, codes in found.items() if any(c.startswith("TS1") and len(c) == 6 for c in codes)}
    if not syntax:
        got.update(found)
        break
    for f in syntax:
        got[f] = found[f]
    pending -= syntax
for name, (codes, where) in expected.items():
    actual = sorted(got.get(name, set()))
    if actual != codes:
        fail(f"{where}: expected errors {codes or 'none'}, compiler gave {actual or 'none'}")

tsc_version = subprocess.run([os.path.join(tmp, "node_modules/.bin/tsc"), "-v"], capture_output=True, text=True).stdout.strip()
print(f"{len(blocks)} code blocks: {counts['actual']} actual, {counts['simplified']} simplified, {counts['teaching']} teaching")
print(f"{len(expected)} ts/tsx teaching blocks compiled with {tsc_version}; "
      f"{sum(1 for c, _ in expected.values() if c)} are deliberate-error examples")
if failures:
    print(f"\nFAIL ({len(failures)})")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("OK")
