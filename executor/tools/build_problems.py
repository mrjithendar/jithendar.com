"""
Build the seed catalog for jithendar.com/python-practice.

    python executor/tools/build_problems.py            # validate and write the generated catalog
    python executor/tools/build_problems.py --check    # validate only (CI)

Reads   www/content/python-practice/{roles,topics}.yaml and problems/*.yaml (sources, written by people)
Writes  www/content/python-practice/catalog.generated.json (read by the web app's seeder)

For every problem it runs the canonical solution (and any alternative solutions) through the real sandbox
runner (sandbox/runner.py, locally: this is trusted, reviewed content) to compute the expected output of every
test case, checks hand-written `expected` values against it, and runs quality checks: required fields, three
hint levels, known roles and topics, enough hidden tests, starter code that loads but does not already pass,
and near-duplicate detection. Needs PyYAML.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "www" / "content" / "python-practice"
RUNNER = ROOT / "executor" / "sandbox" / "runner.py"
OUT = CONTENT / "catalog.generated.json"

DIFFICULTIES = ["beginner", "easy", "medium", "hard", "expert"]
COMPARATORS = {"exact", "unordered", "float"}
REQUIRED = ["slug", "title", "difficulty", "roles", "topics", "minutes", "entrypoint", "description", "starter", "hints", "solution", "examples", "hidden"]
SOLUTION_REQUIRED = ["code", "explanation", "time", "space", "alternatives", "edge_cases", "production"]
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def run(code: str, entrypoint: str, prelude: str, tests: list[dict], per_test: float = 5.0) -> dict:
    payload = {
        "nonce": "build",
        "code": code,
        "entrypoint": entrypoint,
        "prelude": prelude,
        "tests": [{"id": f"t{i}", "args": t.get("args", []), "kwargs": t.get("kwargs", {})} for i, t in enumerate(tests)],
        "limits": {"per_test_seconds": per_test, "total_seconds": 600, "memory_mb": 512, "output_bytes": 65536},
    }
    env = {"JOB_PAYLOAD": base64.b64encode(json.dumps(payload).encode()).decode(), "PYTHONHASHSEED": "0"}
    out = subprocess.run([sys.executable, "-I", str(RUNNER)], env=env, capture_output=True, text=True, timeout=900).stdout
    line = [x for x in out.splitlines() if x.startswith("<<<RESULT:build>>>")]
    if not line:
        raise RuntimeError(f"runner produced no result: {out[-500:]}")
    return json.loads(line[-1].split(">>>", 1)[1])


# Mirrors www/src/lib/practice/compare.ts. JSON has one number type, so 33 and 33.0 are the same value there.
def _ints(v: Any) -> Any:
    if isinstance(v, float) and v.is_integer() and abs(v) < 2**53:
        return int(v)
    if isinstance(v, list):
        return [_ints(x) for x in v]
    if isinstance(v, dict):
        return {k: _ints(x) for k, x in v.items()}
    return v


# Key order of dicts is not part of a result (the grader ignores it), but solutions that use threads or asyncio
# fill dicts in completion order. Sorting keeps catalog.generated.json identical between builds, which CI checks.
def _sorted(v: Any) -> Any:
    if isinstance(v, list):
        return [_sorted(x) for x in v]
    if isinstance(v, dict):
        return {k: _sorted(v[k]) for k in sorted(v)}
    return v


def canon(v: Any) -> str:
    return json.dumps(_ints(v), sort_keys=True, separators=(",", ":"))


def equal(actual: Any, expected: Any, comparator: str, tol: float = 1e-6) -> bool:
    if comparator == "unordered" and isinstance(actual, list) and isinstance(expected, list):
        return sorted(map(canon, actual)) == sorted(map(canon, expected))
    if comparator == "float":
        return close(actual, expected, tol)
    return canon(actual) == canon(expected)


def close(a: Any, b: Any, tol: float) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=tol, abs_tol=tol)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(close(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(close(a[k], b[k], tol) for k in a)
    return canon(a) == canon(b)


def shingles(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {" ".join(words[i : i + 3]) for i in range(max(0, len(words) - 2))}


def build(check_only: bool) -> int:
    roles = yaml.safe_load((CONTENT / "roles.yaml").read_text())
    topics = yaml.safe_load((CONTENT / "topics.yaml").read_text())
    role_slugs = {r["slug"] for r in roles}
    topic_slugs = {t["slug"] for t in topics}
    errors: list[str] = []
    problems: list[dict] = []
    for file in sorted((CONTENT / "problems").glob("*.yaml")):
        for p in yaml.safe_load(file.read_text()) or []:
            p["_file"] = file.name
            problems.append(p)

    seen: dict[str, str] = {}
    built = []
    for p in problems:
        where = f"{p.get('_file')}:{p.get('slug', '?')}"
        missing = [k for k in REQUIRED if not p.get(k)]
        if missing:
            errors.append(f"{where}: missing {', '.join(missing)}")
            continue
        if not SLUG.match(p["slug"]):
            errors.append(f"{where}: slug must be kebab-case")
        if p["slug"] in seen:
            errors.append(f"{where}: duplicate slug (also in {seen[p['slug']]})")
        seen[p["slug"]] = p["_file"]
        if p["difficulty"] not in DIFFICULTIES:
            errors.append(f"{where}: unknown difficulty {p['difficulty']}")
        for r in p["roles"]:
            if r not in role_slugs:
                errors.append(f"{where}: unknown role {r}")
        for t in p["topics"]:
            if t not in topic_slugs:
                errors.append(f"{where}: unknown topic {t}")
        if len(p["hints"]) != 3:
            errors.append(f"{where}: needs exactly three hints (concept, approach, pseudocode)")
        sol = p["solution"]
        smissing = [k for k in SOLUTION_REQUIRED if not sol.get(k)]
        if smissing:
            errors.append(f"{where}: solution missing {', '.join(smissing)}")
            continue
        comparator = p.get("comparator", "exact")
        if comparator not in COMPARATORS:
            errors.append(f"{where}: unknown comparator {comparator}")
        if len(p["hidden"]) < 2:
            errors.append(f"{where}: needs at least two hidden tests")
        if not (20 <= len(p["description"]) <= 6000):
            errors.append(f"{where}: description length out of range")

        cases = [("example", t) for t in p["examples"]] + [("public", t) for t in p.get("tests", [])] + [("hidden", t) for t in p["hidden"]]
        prelude = p.get("prelude", "")
        res = run(sol["code"], p["entrypoint"], prelude, [t for _, t in cases])
        if res.get("status") != "completed":
            errors.append(f"{where}: canonical solution failed to load: {json.dumps(res.get('load', res))[:300]}")
            continue
        out_tests = []
        for (kind, case), r in zip(cases, res["tests"]):
            if r["status"] != "ok" or "output" not in r:
                errors.append(f"{where}: canonical solution {r['status']} on {kind} input {json.dumps(case.get('args'))[:120]}: {json.dumps(r.get('error') or r.get('unserializable'))[:300]}")
                continue
            if "expected" in case and not equal(r["output"], case["expected"], comparator, p.get("tolerance", 1e-6)):
                errors.append(f"{where}: expected {json.dumps(case['expected'])[:200]} but canonical solution returned {json.dumps(r['output'])[:200]}")
            out_tests.append(
                {
                    "visibility": "hidden" if kind == "hidden" else "public",
                    "example": kind == "example",
                    "args": case.get("args", []),
                    "kwargs": case.get("kwargs", {}),
                    "expected": _sorted(r["output"]),
                    "explanation": case.get("explanation", ""),
                    "label": case.get("label", ""),
                }
            )
        for i, alt in enumerate(sol.get("alternative_code", []) or []):
            ares = run(alt, p["entrypoint"], prelude, [t for _, t in cases])
            fails = [j for j, (r, t) in enumerate(zip(ares.get("tests", []), out_tests)) if r.get("status") != "ok" or not equal(r.get("output"), t["expected"], comparator, p.get("tolerance", 1e-6))]
            if ares.get("status") != "completed" or fails:
                errors.append(f"{where}: alternative solution {i + 1} disagrees on cases {fails[:5]}")
        starter = run(p["starter"], p["entrypoint"], prelude, [t for _, t in cases])
        if starter.get("status") != "completed":
            errors.append(f"{where}: starter code must load and define {p['entrypoint']}() ({starter.get('status')})")
        elif all(r.get("status") == "ok" and equal(r.get("output"), t["expected"], comparator) for r, t in zip(starter["tests"], out_tests)):
            errors.append(f"{where}: starter code already passes every test")

        body = {k: v for k, v in p.items() if not k.startswith("_") and k not in ("examples", "tests", "hidden")}
        body["comparator"] = comparator
        body["tests"] = out_tests
        body["content_hash"] = hashlib.sha256(canon(body).encode()).hexdigest()
        built.append(body)

    # Near-duplicate detection (title + description).
    sh = [(b["slug"], shingles(b["title"] + " " + b["description"])) for b in built]
    for i in range(len(sh)):
        for j in range(i + 1, len(sh)):
            a, b = sh[i][1], sh[j][1]
            if a and b and len(a & b) / len(a | b) > 0.5:
                errors.append(f"{sh[i][0]} and {sh[j][0]} look like duplicates")

    by_diff = {d: sum(1 for b in built if b["difficulty"] == d) for d in DIFFICULTIES}
    by_role = {r: sum(1 for b in built if r in b["roles"]) for r in sorted(role_slugs)}
    for r, n in by_role.items():
        if n < 3:
            errors.append(f"role {r} has only {n} problems")
    print(f"{len(built)} problems  {by_diff}")
    print("per role:", by_role)
    if errors:
        print(f"\n{len(errors)} problem(s):", *errors, sep="\n  ")
        return 1
    if not check_only:
        OUT.write_text(json.dumps({"schema": 1, "roles": roles, "topics": topics, "problems": built}, indent=1, sort_keys=False) + "\n")
        print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(build("--check" in sys.argv))
