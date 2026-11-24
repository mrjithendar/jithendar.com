#!/usr/bin/env python3
"""The CrewAI configuration in crewconfig/: check it, restore it on the site, and pull it from the site.

  scripts/crewconfig.py check [--dir crewconfig]
  JITHENDAR_CREWAI_KEY=jk_… scripts/crewconfig.py push [--apply] [--policy skip|overwrite|fail] [--prune] …
  JITHENDAR_CREWAI_KEY=jk_… scripts/crewconfig.py pull [--force]
  scripts/crewconfig.py manifest

crewconfig/ is the site's CrewAI configuration as files (moks-cms docs/seo/CREWCONFIG.md): every crew with its agents
and tasks, flow, skill, schedule, content source and category, and, read-only, the tools, prompt guardrails and model
providers. The CMS writes it (AI & SEO → Configuration → Write to Git, or `pull` here) and imports it (a deployment,
the crewconfig workflow, or `push` here).

check     Every file against its JSON Schema (crewconfig/schemas/, written by the CMS from the schemas its importer
          uses), the bundle's own structure (a crew lists exactly the agents and tasks that have files; a task's agent
          is one of its crew's; a task's context names earlier tasks; what flows and schedules name is in the bundle),
          the manifest (format; stale checksums are warnings: a file was edited by hand), and no secrets. YAML is read
          as data, as the CMS reads it: no tags, no aliases beyond a few, duplicate keys refused, only true/false are
          booleans and dates stay text. No network. Exit 1 on any error.
push      Restore crewconfig/ on the site: wait until GET /api/v1/crewai/config/status says the database answers, every
          migration is applied and the SEO agent answers (--wait seconds, default 300); plan (POST
          /api/v1/crewai/config/import, dryRun); with --apply, apply it in one transaction with the commit as revision.
          The site verifies what it saved and records the import. --policy skip (default) keeps an item an admin changed
          on the site since the last sync and reports it; overwrite applies the files; fail refuses the import. Nothing
          is removed without --prune. Exit 1 when the site refuses or the import fails (nothing changed), 2 when it
          cannot start (no key, the site has no such API).
pull      Write the site's configuration (GET /api/v1/crewai/config) to crewconfig/, removing files of items that no
          longer exist. Refused when the site's export is incomplete (its SEO agent did not answer), unless --force.
manifest  Rewrite manifest.json's list of files and their SHA-256 after a hand edit (the CMS rewrites the rest of it on
          its next write).

The key is an admin's API key (Admin → API keys) with the scopes crewai:read and crewai:import (crewai:read is enough
for pull). Python 3.10+, PyYAML and jsonschema.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "crewconfig"
FORMAT = 2
KIND = "moks-crewai-bundle"
MAX_FILE = 256 * 1024
MAX_TOTAL = 8 * 1024 * 1024

COLLECTIONS = {
    "categories/categories.yaml": ("categories", "categories.schema.json"),
    "schedules/schedules.yaml": ("schedules", "schedules.schema.json"),
    "sources/sources.yaml": ("sources", "sources.schema.json"),
    "tools/tools.yaml": ("tools", "tools.schema.json"),
    "prompts/guardrails.yaml": ("guardrails", "guardrails.schema.json"),
    "providers/providers.yaml": ("providers", "providers.schema.json"),
}
KEY = r"[a-z][a-z0-9_]{1,39}"
SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
PATTERNS = [
    ("crews", re.compile(rf"^crews/({KEY})\.yaml$"), ("key",), "crew.schema.json", None),
    ("flows", re.compile(rf"^flows/({KEY})\.yaml$"), ("key",), "flow.schema.json", None),
    ("agents", re.compile(rf"^agents/({KEY})/({KEY})\.md$"), ("crew", "key"), "agent.schema.json", "backstory"),
    ("tasks", re.compile(rf"^tasks/({KEY})/({KEY})\.md$"), ("crew", "key"), "task.schema.json", "instructions"),
    ("skills", re.compile(rf"^skills/({SLUG})/SKILL\.md$"), ("name",), "skill.schema.json", "instructions"),
]
SAFE_PATH = re.compile(r"^(?!.*\.\.)(?!/)[A-Za-z0-9_./-]{1,300}$")
FRONT = re.compile(r"^﻿?---\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)([\s\S]*)$")
SECRETS = [
    ("Anthropic or OpenAI key", re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{16,}")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google token", re.compile(r"\bya29\.[\w-]{20,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("GitHub token", re.compile(r"\b(?:ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{20,}")),
    ("site API key", re.compile(r"\bjk_[A-Za-z0-9_-]{20,}")),
    ("Slack token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("bearer token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{24,}=*")),
    ("password in a URL", re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s/:@]+:[^\s/@]{3,}@", re.I)),
]


# --- reading ------------------------------------------------------------------------------------------------------------


class Loader(yaml.SafeLoader):
    """YAML as the CMS reads it (YAML 1.2 core schema): only true/false are booleans, no timestamps, no duplicate keys."""

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:  # type: ignore[override]
        seen: set[Any] = set()
        for k, _ in node.value:
            key = self.construct_object(k, deep=deep)
            if key in seen:
                raise yaml.constructor.ConstructorError(None, None, f"duplicate key {key!r}", k.start_mark)
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


Loader.yaml_implicit_resolvers = {k: [r for r in v if r[0] not in ("tag:yaml.org,2002:bool", "tag:yaml.org,2002:timestamp")] for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()}
Loader.add_implicit_resolver("tag:yaml.org,2002:bool", re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"), list("tTfF"))


def load_yaml(text: str) -> Any:
    # Alias bombs: the CMS caps aliases at 100 too.
    if sum(1 for t in yaml.scan(text, Loader=Loader) if isinstance(t, yaml.AliasToken)) > 100:
        raise ValueError("more than 100 aliases")
    return yaml.load(text, Loader=Loader)  # noqa: S506 - Loader is a SafeLoader


def read_dir(d: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for p in sorted(d.rglob("*")):
        if p.is_file() and not p.name.startswith("."):
            files[p.relative_to(d).as_posix()] = p.read_text(encoding="utf-8")
    return files


class Report:
    def __init__(self) -> None:
        self.errors: list[tuple[str, str]] = []
        self.warnings: list[tuple[str, str]] = []

    def error(self, path: str, msg: str) -> None:
        self.errors.append((path, msg))

    def warn(self, path: str, msg: str) -> None:
        self.warnings.append((path, msg))


def _validator(schemas: dict[str, Any], name: str) -> Any:
    from jsonschema import validators

    schema = schemas.get(name)
    if schema is None:
        return None
    cls = validators.validator_for(schema)
    return cls(schema, format_checker=cls.FORMAT_CHECKER)


def parse(files: dict[str, str], rep: Report) -> dict[str, list[dict[str, Any]]]:
    """Files → items per kind (as the CMS's fromFiles), each checked against its schema."""
    schemas: dict[str, Any] = {}
    for p, t in files.items():
        if re.fullmatch(r"schemas/[a-z-]+\.schema\.json", p):
            try:
                schemas[p.split("/", 1)[1]] = json.loads(t)
            except json.JSONDecodeError as e:
                rep.error(p, f"not JSON: {e}")
    if not schemas:
        rep.error("schemas/", "no schemas: the CMS writes them with every export")
    items: dict[str, list[dict[str, Any]]] = {k: [] for k in ("categories", "crews", "agents", "tasks", "flows", "skills", "schedules", "sources", "tools", "guardrails", "providers")}
    seen: dict[str, str] = {}
    total = 0

    def check(path: str, name: str, value: Any, prefix: str = "") -> bool:
        v = _validator(schemas, name)
        if v is None:
            rep.error(path, f"no schema {name} in schemas/")
            return False
        errs = sorted(v.iter_errors(value), key=lambda e: list(e.path))
        for e in errs[:20]:
            rep.error(path, f"{prefix}{'.'.join(str(x) for x in e.path) or 'file'}: {e.message}")
        return not errs

    def add(kind: str, path: str, item: dict[str, Any], ident: str) -> None:
        ref = f"{kind}:{ident}"
        if ref in seen:
            rep.error(path, f"{kind[:-1]} {ident} is also defined in {seen[ref]}")
            return
        seen[ref] = path
        items[kind].append(item)

    for path, text in sorted(files.items()):
        total += len(text.encode())
        if not SAFE_PATH.match(path):
            rep.error(path, "not a safe relative path")
            continue
        if len(text.encode()) > MAX_FILE:
            rep.error(path, f"larger than {MAX_FILE // 1024} KB")
            continue
        if path == "manifest.json" or path.endswith("README.md") or path.startswith("schemas/"):
            continue
        try:
            if path in COLLECTIONS:
                kind, schema = COLLECTIONS[path]
                doc = load_yaml(text)
                if not isinstance(doc, dict):
                    raise ValueError(f'holds an object with a "{kind}" list')
                if check(path, schema, doc):
                    for i, item in enumerate(doc.get(kind) or []):
                        ident = item["url"] if kind == "sources" else item.get("slug") or item.get("name") or item.get("id")
                        add(kind, path, item, str(ident))
                continue
            for kind, rx, ids, schema, body in PATTERNS:
                m = rx.match(path)
                if not m:
                    continue
                named = dict(zip(ids, m.groups()))
                if body:
                    fm = FRONT.match(text)
                    if not fm:
                        raise ValueError("starts with front matter between --- lines")
                    meta = load_yaml(fm.group(1)) or {}
                    if not isinstance(meta, dict):
                        raise ValueError("front matter is a YAML object")
                    raw = {**named, **meta}
                    text_body = re.sub(r"^\s*\n", "", fm.group(2)).rstrip()
                else:
                    doc = load_yaml(text)
                    if not isinstance(doc, dict):
                        raise ValueError("holds a YAML object")
                    raw = {**named, **doc}
                    text_body = None
                wrong = [k for k, v in named.items() if raw.get(k) != v]
                if wrong:
                    rep.error(path, f"{', '.join(f'{k} {raw.get(k)}' for k in wrong)} differs from the file's name")
                    break
                if body and not text_body:
                    rep.error(path, f"the body ({body}) is empty")
                    break
                if check(path, schema, raw):
                    item = {**raw, **({body: text_body} if body else {})}
                    ident = f"{raw['crew']}.{raw['key']}" if kind in ("agents", "tasks") else str(raw.get("key") or raw.get("name"))
                    add(kind, path, item, ident)
                break
            else:
                rep.warn(path, "not part of the bundle layout: ignored")
        except (yaml.YAMLError, ValueError) as e:
            rep.error(path, f"cannot read it: {str(e).splitlines()[0][:300]}")
    if total > MAX_TOTAL:
        rep.error("", f"more than {MAX_TOTAL // 1024 // 1024} MB of files")
    return items


def structure(items: dict[str, list[dict[str, Any]]], rep: Report) -> None:
    """The bundle's own references (moks-cms src/lib/crewai/bundle/check.ts)."""
    agents: dict[str, set[str]] = {}
    tasks: dict[str, dict[str, dict[str, Any]]] = {}
    for a in items["agents"]:
        agents.setdefault(a["crew"], set()).add(a["key"])
    for t in items["tasks"]:
        tasks.setdefault(t["crew"], {})[t["key"]] = t
    crews = {c["key"] for c in items["crews"]}
    for c in items["crews"]:
        k = c["key"]
        p = f"crews/{k}.yaml"
        for a in c["agents"]:
            if a not in agents.get(k, set()):
                rep.error(p, f"agent {a} has no file agents/{k}/{a}.md")
        for a in agents.get(k, set()) - set(c["agents"]):
            rep.error(f"agents/{k}/{a}.md", f"the crew {k} does not list this agent")
        for t in c["tasks"]:
            if t not in tasks.get(k, {}):
                rep.error(p, f"task {t} has no file tasks/{k}/{t}.md")
        for t in set(tasks.get(k, {})) - set(c["tasks"]):
            rep.error(f"tasks/{k}/{t}.md", f"the crew {k} does not list this task")
        for i, tk in enumerate(c["tasks"]):
            t = tasks.get(k, {}).get(tk)
            if not t:
                continue
            if t["agent"] not in c["agents"]:
                rep.error(f"tasks/{k}/{tk}.md", f"agent {t['agent']} is not one of the crew's agents")
            for x in t.get("context") or []:
                if x not in c["tasks"][:i]:
                    rep.error(f"tasks/{k}/{tk}.md", f"context {x} is not an earlier task of the crew")
        if c["definition"] == "code" and not c.get("code"):
            rep.warn(p, "a crew defined in code without its read-only code block (an export writes it)")
    for a in items["agents"]:
        if a["crew"] not in crews:
            rep.error(f"agents/{a['crew']}/{a['key']}.md", f"no crew {a['crew']} (crews/{a['crew']}.yaml)")
    for t in items["tasks"]:
        if t["crew"] not in crews:
            rep.error(f"tasks/{t['crew']}/{t['key']}.md", f"no crew {t['crew']} (crews/{t['crew']}.yaml)")
    cats = {c["slug"] for c in items["categories"]}
    urls = {s["url"] for s in items["sources"]}
    spec_flows = {f["key"] for f in items["flows"] if f["definition"] == "spec"}
    for c in items["crews"]:
        for x in c.get("categories") or []:
            if x not in cats:
                rep.warn(f"crews/{c['key']}.yaml", f"category {x} is not in categories/categories.yaml (the site must have it)")
    for f in items["flows"]:
        p = f"flows/{f['key']}.yaml"
        for x in f.get("categories") or []:
            if x not in cats:
                rep.warn(p, f"category {x} is not in categories/categories.yaml (the site must have it)")
        if f["definition"] == "code" and f["key"] != f.get("flow_name"):
            rep.error(p, f"a flow defined in code keeps its name as its key ({f.get('flow_name')})")
        if f["definition"] == "spec":
            if not f.get("spec"):
                rep.error(p, "a spec flow needs its spec (inputs and steps)")
            for s in (f.get("spec") or {}).get("steps") or []:
                if s.get("kind") == "crew" and s.get("crew") not in crews:
                    rep.warn(p, f"step crew {s.get('crew')} is not in the bundle (the site must have it)")
        if f["definition"] == "content":
            if not re.fullmatch(r"content_[0-9a-f]{12}", f["key"]):
                rep.error(p, "a content flow's key is content_ and 12 hex digits")
            for u in (f.get("content") or {}).get("sources") or []:
                if u not in urls:
                    rep.warn(p, f"source {u} is not in sources/sources.yaml (the site must have it)")
    for s in items["schedules"]:
        if s["flow"] == "custom_flow" and (s.get("inputs") or {}).get("flow") not in spec_flows:
            rep.warn("schedules/schedules.yaml", f"{s['name']}: inputs.flow is not a spec flow in the bundle (the site must have it)")


def secrets(files: dict[str, str], rep: Report) -> None:
    for p, t in files.items():
        if p.startswith("schemas/"):
            continue
        for name, rx in SECRETS:
            if rx.search(t):
                rep.error(p, f"looks like it holds a credential ({name}): keys never belong in crewconfig/")


def manifest_check(files: dict[str, str], rep: Report) -> None:
    raw = files.get("manifest.json")
    if raw is None:
        rep.warn("manifest.json", "no manifest: an export writes one")
        return
    try:
        m = json.loads(raw)
    except json.JSONDecodeError as e:
        rep.error("manifest.json", f"not JSON: {e}")
        return
    if m.get("kind") != KIND:
        rep.error("manifest.json", f"kind is {m.get('kind')!r}, not {KIND}")
    if int(m.get("format") or 0) > FORMAT:
        rep.error("manifest.json", f"format {m.get('format')} is newer than this check knows ({FORMAT})")
    listed = {f["path"]: f["sha256"] for f in m.get("files") or []}
    stale = [p for p, s in listed.items() if p in files and hashlib.sha256(files[p].encode()).hexdigest() != s]
    added = [p for p in files if p != "manifest.json" and listed and p not in listed]
    gone = [p for p in listed if p not in files]
    if stale:
        rep.warn("manifest.json", f"changed since the manifest was written: {', '.join(stale[:10])} (scripts/crewconfig.py manifest refreshes it)")
    if added:
        rep.warn("manifest.json", f"not in the manifest: {', '.join(added[:10])}")
    if gone:
        rep.warn("manifest.json", f"in the manifest but missing: {', '.join(gone[:10])}")


def run_check(d: Path) -> Report:
    rep = Report()
    if not d.is_dir():
        rep.error(str(d), "no such folder")
        return rep
    files = read_dir(d)
    items = parse(files, rep)
    structure(items, rep)
    secrets(files, rep)
    manifest_check(files, rep)
    return rep


def annotate(rep: Report, d: Path) -> None:
    gh = os.environ.get("GITHUB_ACTIONS") == "true"
    rel = d.relative_to(ROOT).as_posix() if d.is_relative_to(ROOT) else str(d)
    for level, rows in (("error", rep.errors), ("warning", rep.warnings)):
        for p, msg in rows:
            if gh:
                print(f"::{level} file={rel}/{p}::{msg}")
            else:
                print(f"{level}: {rel}/{p}: {msg}")


# --- the site -----------------------------------------------------------------------------------------------------------


class SiteError(Exception):
    def __init__(self, status: int, message: str, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


def call(site: str, key: str, method: str, path: str, body: Any = None, timeout: int = 120) -> Any:
    data = None if body is None else json.dumps(body).encode()
    last: Exception | None = None
    for attempt in range(4):
        req = urllib.request.Request(f"{site.rstrip('/')}{path}", data=data, method=method, headers={"Authorization": f"Bearer {key}", "Accept": "application/json", "User-Agent": "jithendar.com-crewconfig", **({"Content-Type": "application/json"} if data else {})})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                parsed = json.loads(raw or b"{}")
            except json.JSONDecodeError:
                parsed = {"error": {"message": raw[:300].decode(errors="replace")}}
            if e.code in (429, 502, 503, 504) and attempt < 3:
                last = e
                time.sleep(2 * (attempt + 1))
                continue
            err = parsed.get("error") if isinstance(parsed, dict) else None
            msg = err.get("message") if isinstance(err, dict) else str(err or e.reason)
            raise SiteError(e.code, msg, parsed) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e
            if attempt < 3:
                time.sleep(2 * (attempt + 1))
                continue
    raise SiteError(0, f"the site did not answer: {last}")


def wait_ready(site: str, key: str, seconds: int) -> dict[str, Any]:
    deadline = time.monotonic() + seconds
    while True:
        try:
            s = call(site, key, "GET", "/api/v1/crewai/config/status")["data"]
            if s["migrations"]["ok"] and s["agent"]["reachable"]:
                return s
            why = f"migrations pending: {', '.join(s['migrations']['pending']) or 'the sync table'}" if not s["migrations"]["ok"] else "the SEO agent does not answer yet"
        except SiteError as e:
            if e.status in (401, 403, 404):
                raise
            why = str(e)
            s = None
        if time.monotonic() >= deadline:
            if s and s["migrations"]["ok"]:
                print(f"::warning::{why}: importing anyway (changed crews, flows and schedules the agent must check will be refused)")
                return s
            raise SiteError(0, f"not ready after {seconds} s: {why}")
        print(f"waiting: {why}")
        time.sleep(5)


def plan_lines(plan: dict[str, Any]) -> list[str]:
    c = plan["counts"]
    out = [f"{c.get('create', 0)} new, {c.get('update', 0)} changed, {c.get('conflict', 0)} differ on the site, {c.get('remove', 0)} removed, {c.get('error', 0)} refused, {c.get('unchanged', 0)} unchanged ({plan['toApply']} to apply, conflicts: {plan['policy']})"]
    for i in plan["items"]:
        if i["action"] in ("create", "update", "conflict", "remove", "error"):
            mark = "" if i.get("apply") else " (not applied)"
            out.append(f"  {i['action']:<9} {i['ref']}{mark}: {i.get('error') or ' · '.join(i.get('changes') or [])}")
    for iss in plan.get("issues") or []:
        if iss["severity"] == "error" and not iss.get("ref"):
            out.append(f"  problem   {iss['path']}: {iss['message']}")
    for w in plan.get("warnings") or []:
        out.append(f"  warning   {w}")
    return out


def summary(lines: list[str], path: str | None) -> None:
    if not path:
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write("### CrewAI configuration\n\n```\n" + "\n".join(lines) + "\n```\n")


def cmd_push(a: argparse.Namespace) -> int:
    key = os.environ.get("JITHENDAR_CREWAI_KEY", "").strip()
    if not key:
        print("JITHENDAR_CREWAI_KEY is not set: an admin's API key with crewai:read and crewai:import (Admin → API keys)", file=sys.stderr)
        return 2
    d = Path(a.dir)
    rep = run_check(d)
    annotate(rep, d)
    if rep.errors:
        print(f"crewconfig/ has {len(rep.errors)} problem(s): nothing sent", file=sys.stderr)
        return 1
    files = {p: t for p, t in read_dir(d).items()}
    body = {"files": files, "policy": a.policy, "prune": a.prune, "allowPartial": a.allow_partial, "source": a.source, "revision": a.revision or None, "ref": a.ref or None, "url": a.url or None}
    try:
        status = wait_ready(a.site, key, a.wait)
        print(f"site ready: configuration {status['configuration']['version'][:12]}, last import {((status['configuration'].get('lastImport') or {}).get('revision') or 'none')[:12]}")
        plan = call(a.site, key, "POST", "/api/v1/crewai/config/import", {**body, "dryRun": True})["data"]["plan"]
    except SiteError as e:
        msg = "the site has no /api/v1/crewai/config yet: deploy a moks-cms with it first" if e.status == 404 else str(e)
        print(f"::error::{msg}")
        return 2 if e.status in (0, 401, 403, 404) else 1
    lines = plan_lines(plan)
    print("\n".join(lines))
    if not plan["ok"]:
        summary(["Refused: nothing was changed.", *lines], a.summary)
        print("::error::the site refuses this configuration: nothing was changed")
        return 1
    if not a.apply:
        summary(["Plan only (dry run).", *lines], a.summary)
        return 0
    try:
        out = call(a.site, key, "POST", "/api/v1/crewai/config/import", {**body, "dryRun": False})["data"]
    except SiteError as e:
        detail = (e.body or {}).get("error", {}).get("issues") if isinstance(e.body, dict) else None
        summary([f"Failed: {e} (nothing was changed)", *(detail or []), *lines], a.summary)
        print(f"::error::the import failed and nothing was changed: {e}")
        for x in detail or []:
            print(f"  {x}")
        return 1
    r = out["result"]
    done = f"{r['status']}: {', '.join(f'{n} {k}' for k, n in r['applied'].items()) or 'nothing to change'}; verified; record {r['recordId']}; configuration {r['runtimeChecksum'][:12]}"
    print(done)
    kept = [i for i in plan["items"] if i["action"] == "conflict" and not i.get("apply")]
    if kept:
        print(f"::warning::{len(kept)} item(s) differ on the site and were kept (policy {plan['policy']}): {', '.join(i['ref'] for i in kept[:20])}. Write the site's configuration to Git, or run with policy overwrite.")
    summary([done, *lines], a.summary)
    return 0


def cmd_pull(a: argparse.Namespace) -> int:
    key = os.environ.get("JITHENDAR_CREWAI_KEY", "").strip()
    if not key:
        print("JITHENDAR_CREWAI_KEY is not set: an admin's API key with crewai:read (Admin → API keys)", file=sys.stderr)
        return 2
    try:
        data = call(a.site, key, "GET", "/api/v1/crewai/config")["data"]
    except SiteError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    report = data.get("report") or {}
    if not report.get("complete", True) and not a.force:
        print("the site's export is incomplete (its SEO agent did not answer): nothing written (--force writes it anyway)", file=sys.stderr)
        for u in report.get("unsupported") or []:
            print(f"  {u['component']}: {u['reason']}", file=sys.stderr)
        return 1
    d = Path(a.dir)
    files: dict[str, str] = data["files"]
    for p in files:
        if not SAFE_PATH.match(p):
            print(f"refused: unsafe path {p}", file=sys.stderr)
            return 1
    managed = re.compile(r"^(crews|flows|agents|tasks|skills|categories|schedules|sources|tools|prompts|providers|schemas)/|^manifest\.json$|^README\.md$")
    removed = 0
    if d.is_dir():
        for p in read_dir(d):
            if managed.match(p) and p not in files:
                (d / p).unlink()
                removed += 1
    for p, t in files.items():
        (d / p).parent.mkdir(parents=True, exist_ok=True)
        (d / p).write_text(t, encoding="utf-8")
    for sub in sorted((x for x in d.rglob("*") if x.is_dir()), reverse=True):
        if not any(sub.iterdir()):
            sub.rmdir()
    counts = report.get("counts") or {}
    print(f"wrote {len(files)} files, removed {removed}: " + ", ".join(f"{n} {k}" for k, n in counts.items() if n))
    for r in report.get("redacted") or []:
        print(f"redacted: {r['item']} {r['path']} ({r['pattern']})")
    return 0


def cmd_manifest(a: argparse.Namespace) -> int:
    d = Path(a.dir)
    p = d / "manifest.json"
    m = json.loads(p.read_text(encoding="utf-8"))
    files = read_dir(d)
    m["files"] = [{"path": k, "sha256": hashlib.sha256(v.encode()).hexdigest()} for k, v in sorted(files.items()) if k != "manifest.json"]
    p.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"manifest.json lists {len(m['files'])} files")
    return 0


def site_default() -> str:
    try:
        return f"https://{json.loads((ROOT / 'site.json').read_text())['host']}"
    except (OSError, KeyError, json.JSONDecodeError):
        return "https://jithendar.com"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "push", "pull", "manifest"):
        s = sub.add_parser(name)
        s.add_argument("--dir", default=str(DEFAULT_DIR))
        if name in ("push", "pull"):
            s.add_argument("--site", default=os.environ.get("SITE_URL") or site_default())
        if name == "push":
            s.add_argument("--apply", action="store_true", help="apply the plan (default: plan only)")
            s.add_argument("--policy", choices=("skip", "overwrite", "fail"), default="skip")
            s.add_argument("--prune", action="store_true", help="remove what crewconfig/ does not have (never code crews or flows, shipped skills, built-in schedules)")
            s.add_argument("--allow-partial", action="store_true", help="leave out refused items and apply the rest")
            s.add_argument("--source", choices=("deploy", "api"), default="api")
            s.add_argument("--revision", default=os.environ.get("GITHUB_SHA", ""))
            s.add_argument("--ref", default=os.environ.get("GITHUB_REF_NAME", ""))
            s.add_argument("--url", default="")
            s.add_argument("--wait", type=int, default=300, help="seconds to wait for the site to be ready")
            s.add_argument("--summary", default=os.environ.get("GITHUB_STEP_SUMMARY"))
        if name == "pull":
            s.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        d = Path(a.dir)
        rep = run_check(d)
        annotate(rep, d)
        print(f"crewconfig: {len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")
        return 1 if rep.errors else 0
    if a.cmd == "push":
        return cmd_push(a)
    if a.cmd == "pull":
        return cmd_pull(a)
    return cmd_manifest(a)


if __name__ == "__main__":
    sys.exit(main())
