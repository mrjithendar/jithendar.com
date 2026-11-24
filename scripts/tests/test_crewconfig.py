"""Tests for scripts/crewconfig.py: the check of crewconfig/ (no network), and push / pull against a stand-in for the
CMS's /api/v1/crewai/config on 127.0.0.1.

  python3 -m unittest discover -s scripts/tests -p 'test_*.py'      (needs PyYAML and jsonschema)
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "crewconfig.py"
spec = importlib.util.spec_from_file_location("crewconfig", SCRIPT)
cc = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(cc)
KEY = "jk_test-key-for-the-stand-in-only"


def run(*argv: str, env: dict[str, str] | None = None) -> tuple[int, str]:
    out = io.StringIO()
    old = dict(os.environ)
    os.environ.update(env or {})
    try:
        with redirect_stdout(out), redirect_stderr(out):
            code = cc.main(list(argv))
    finally:
        os.environ.clear()
        os.environ.update(old)
    return code, out.getvalue()


class Check(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.dir = self.tmp / "crewconfig"
        shutil.copytree(cc.DEFAULT_DIR, self.dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)

    def errors(self) -> list[tuple[str, str]]:
        return cc.run_check(self.dir).errors

    def test_the_repositorys_crewconfig_passes(self) -> None:
        rep = cc.run_check(cc.DEFAULT_DIR)
        self.assertEqual(rep.errors, [])
        self.assertEqual(rep.warnings, [])
        items = cc.parse(cc.read_dir(cc.DEFAULT_DIR), cc.Report())
        manifest = json.loads((cc.DEFAULT_DIR / "manifest.json").read_text())
        for kind, ids in manifest["inventory"].items():
            self.assertEqual(len(items[kind]), len(ids), kind)

    def test_a_crew_must_list_exactly_its_agent_and_task_files(self) -> None:
        (self.dir / "agents/report/analyst.md").unlink()
        shutil.copy(self.dir / "tasks/report/write.md", self.dir / "tasks/report/extra.md")
        text = (self.dir / "tasks/report/extra.md").read_text().replace("key: write", "key: extra")
        (self.dir / "tasks/report/extra.md").write_text(text)
        msgs = [m for _, m in self.errors()]
        self.assertTrue(any("agent analyst has no file agents/report/analyst.md" in m for m in msgs), msgs)
        self.assertTrue(any("the crew report does not list this task" in m for m in msgs), msgs)

    def test_schema_errors_name_the_file_and_field(self) -> None:
        p = self.dir / "crews/report.yaml"
        p.write_text(p.read_text() + "surprise: 1\n")
        f = self.dir / "flows/report_flow.yaml"
        f.write_text(f.read_text().replace("definition: code", "definition: python"))
        errs = self.errors()
        self.assertTrue(any(path == "crews/report.yaml" and "surprise" in m for path, m in errs), errs)
        self.assertTrue(any(path == "flows/report_flow.yaml" and "definition" in m for path, m in errs), errs)

    def test_yaml_is_data_only(self) -> None:
        self.assertEqual(cc.load_yaml("a: on\nb: yes\nc: 2026-11-24\nd: true"), {"a": "on", "b": "yes", "c": "2026-11-24", "d": True})
        with self.assertRaises(Exception):
            cc.load_yaml("a: 1\na: 2\n")
        with self.assertRaises(Exception):
            cc.load_yaml("!!python/object/apply:os.system ['true']")
        with self.assertRaises(ValueError):
            cc.load_yaml("a: &x [1]\nb: [" + ", ".join(["*x"] * 101) + "]\n")
        p = self.dir / "crews/report.yaml"
        p.write_text("key: report\nkey: report\n")
        self.assertTrue(any("cannot read it" in m for _, m in self.errors()))

    def test_a_credential_is_refused_and_a_hand_edit_only_warned(self) -> None:
        p = self.dir / "skills/seo-briefing/SKILL.md"
        p.write_text(p.read_text() + "\nUse ghp_abcdefghijklmnopqrstuvwxyz0123456789 to test.\n")
        rep = cc.run_check(self.dir)
        self.assertTrue(any("credential" in m for _, m in rep.errors))
        self.assertTrue(any("changed since the manifest" in m for _, m in rep.warnings))
        code, _ = run("manifest", "--dir", str(self.dir))
        self.assertEqual(code, 0)
        self.assertFalse(any("changed since the manifest" in m for _, m in cc.run_check(self.dir).warnings))

    def test_unsafe_and_newer_bundles_are_refused(self) -> None:
        m = json.loads((self.dir / "manifest.json").read_text())
        m["format"] = 3
        (self.dir / "manifest.json").write_text(json.dumps(m))
        self.assertTrue(any("newer" in msg for _, msg in self.errors()))
        rep = cc.Report()
        cc.parse({"../x.yaml": "a: 1"}, rep)
        self.assertTrue(any("safe" in m for _, m in rep.errors))


class Site:
    """The stand-in's state: status answers, the plans it returns and what it was sent."""

    def __init__(self) -> None:
        self.ready_after = 0
        self.plan_ok = True
        self.fail_apply = False
        self.export_complete = True
        self.calls: list[tuple[str, str, dict]] = []
        self.files = {"crews/a_crew.yaml": "key: a_crew\n", "manifest.json": "{}\n"}


def serve(site: Site) -> tuple[ThreadingHTTPServer, str]:
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a: object) -> None:
            pass

        def reply(self, code: int, body: dict) -> None:
            raw = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:  # noqa: N802
            site.calls.append(("GET", self.path, {}))
            if self.headers.get("Authorization") != f"Bearer {KEY}":
                return self.reply(401, {"error": {"message": "no key"}})
            if self.path == "/api/v1/crewai/config/status":
                ready = site.ready_after <= 0
                site.ready_after -= 1
                return self.reply(200, {"data": {"database": "ok", "migrations": {"ok": ready, "pending": [] if ready else ["0042_crewai_config_sync.sql"]}, "agent": {"reachable": True, "version": "x"}, "configuration": {"version": "f" * 64, "lastImport": None}}})
            if self.path == "/api/v1/crewai/config":
                return self.reply(200, {"data": {"files": site.files, "report": {"complete": site.export_complete, "counts": {"crews": 1}, "unsupported": [], "redacted": []}}})
            self.reply(404, {"error": {"message": "not found"}})

        def do_POST(self) -> None:  # noqa: N802
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            site.calls.append(("POST", self.path, body))
            item = {"ref": "schedules:gsc-sync", "action": "conflict", "apply": False, "changes": ["cron: a → b"]}
            plan = {"ok": site.plan_ok, "counts": {"create": 0, "update": 0, "conflict": 1, "unchanged": 90, "error": 0 if site.plan_ok else 1}, "toApply": 0, "policy": body["policy"], "items": [item], "issues": [], "warnings": []}
            if body["dryRun"]:
                return self.reply(200, {"data": {"plan": plan, "result": None}})
            if site.fail_apply:
                return self.reply(500, {"error": {"message": "The import did not verify", "issues": ["crews:a_crew: role"]}, "plan": plan})
            self.reply(200, {"data": {"plan": plan, "result": {"status": "unchanged", "applied": {}, "recordId": "r1", "runtimeChecksum": "e" * 64, "verified": True}}})

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


class PushPull(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Site()
        self.srv, self.url = serve(self.site)
        sleep = mock.patch.object(cc.time, "sleep", lambda _s: None)  # no real waiting in tests
        sleep.start()
        self.addCleanup(sleep.stop)
        self.tmp = Path(tempfile.mkdtemp())
        self.summary = self.tmp / "summary.md"

    def tearDown(self) -> None:
        self.srv.shutdown()
        self.srv.server_close()
        shutil.rmtree(self.tmp)

    def push(self, *extra: str) -> tuple[int, str]:
        return run("push", "--site", self.url, "--summary", str(self.summary), "--revision", "a" * 40, "--source", "deploy", *extra, env={"JITHENDAR_CREWAI_KEY": KEY})

    def test_push_waits_for_the_migrations_plans_then_applies_with_the_revision(self) -> None:
        self.site.ready_after = 2
        code, out = self.push("--apply")
        self.assertEqual(code, 0, out)
        self.assertIn("waiting: migrations pending", out)
        posts = [b for m, p, b in self.site.calls if m == "POST"]
        self.assertEqual([b["dryRun"] for b in posts], [True, False])
        self.assertEqual(posts[1]["revision"], "a" * 40)
        self.assertEqual(posts[1]["policy"], "skip")
        self.assertEqual(posts[1]["source"], "deploy")
        self.assertIn("crews/report.yaml", posts[1]["files"])
        self.assertIn("differ on the site and were kept", out)
        self.assertIn("CrewAI configuration", self.summary.read_text())

    def test_without_apply_it_only_plans(self) -> None:
        code, _ = self.push()
        self.assertEqual(code, 0)
        self.assertEqual([b["dryRun"] for m, p, b in self.site.calls if m == "POST"], [True])

    def test_a_refused_plan_or_failed_import_fails_and_says_nothing_changed(self) -> None:
        self.site.plan_ok = False
        code, out = self.push("--apply")
        self.assertEqual(code, 1)
        self.assertIn("nothing was changed", out)
        self.site.plan_ok = True
        self.site.fail_apply = True
        code, out = self.push("--apply")
        self.assertEqual(code, 1)
        self.assertIn("crews:a_crew: role", out)

    def test_no_key_or_no_api_cannot_start(self) -> None:
        code, _ = run("push", "--site", self.url)
        self.assertEqual(code, 2)
        code, _ = run("push", "--site", self.url, env={"JITHENDAR_CREWAI_KEY": "jk_wrong-key-0123456789abcdef"})
        self.assertEqual(code, 2)

    def test_pull_writes_the_export_and_removes_stale_files(self) -> None:
        d = self.tmp / "crewconfig"
        (d / "flows").mkdir(parents=True)
        (d / "flows/old_flow.yaml").write_text("key: old_flow\n")
        (d / "notes.txt").write_text("mine\n")
        code, out = run("pull", "--site", self.url, "--dir", str(d), env={"JITHENDAR_CREWAI_KEY": KEY})
        self.assertEqual(code, 0, out)
        self.assertEqual((d / "crews/a_crew.yaml").read_text(), "key: a_crew\n")
        self.assertFalse((d / "flows").exists())
        self.assertTrue((d / "notes.txt").exists())
        self.site.export_complete = False
        code, out = run("pull", "--site", self.url, "--dir", str(d), env={"JITHENDAR_CREWAI_KEY": KEY})
        self.assertEqual(code, 1)
        self.assertIn("incomplete", out)


if __name__ == "__main__":
    unittest.main()
