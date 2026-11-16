"""Tests for scripts/ci-rollout.py and scripts/keep-live-images.py. No cluster: kubectl is a stub on PATH.

  python3 -m unittest discover -s scripts/tests -p 'test_*.py'      (needs PyYAML)

CI runs them in .github/workflows/ci-repo.yml (job "hygiene").
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parents[1]
SITE = "registry.jithendar.com/jithendar/jithendar-com"
CONTENT = "registry.jithendar.com/jithendar/jithendar-com-content"

# Stub kubectl: prints the Deployments in STUB_DEPLOYMENTS for `get deployments -o json`, logs every call, and fails
# `set image` / `rollout status` for the Deployment names in STUB_FAIL_SET / STUB_FAIL_STATUS.
STUB = """#!/usr/bin/env python3
import os, sys
args = sys.argv[1:]
with open(os.environ["KUBECTL_LOG"], "a") as log:
    log.write(" ".join(args) + "\\n")
if args[:1] == ["-n"]:
    args = args[2:]
if args[:2] == ["get", "deployments"]:
    sys.stdout.write(open(os.environ["STUB_DEPLOYMENTS"]).read())
elif args[:2] == ["get", "pods"]:
    print("NAME READY STATUS\\njithendar-com-abc 0/1 ImagePullBackOff\\nother-xyz 1/1 Running")
elif args[:2] == ["set", "image"]:
    sys.exit(1 if args[2].split("/")[1] in os.environ.get("STUB_FAIL_SET", "").split() else 0)
elif args[:2] == ["rollout", "status"]:
    sys.exit(1 if args[2].split("/")[1] in os.environ.get("STUB_FAIL_STATUS", "").split() else 0)
"""


def deployment(name: str, containers: dict[str, str], init: dict[str, str] | None = None, kind: str = "Deployment") -> dict:
    spec: dict = {"containers": [{"name": n, "image": i} for n, i in containers.items()]}
    if init:
        spec["initContainers"] = [{"name": n, "image": i} for n, i in init.items()]
    return {"apiVersion": "apps/v1", "kind": kind, "metadata": {"name": name, "namespace": "jithendar"}, "spec": {"template": {"spec": spec}}}


class Rollout(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        stub = self.dir / "bin" / "kubectl"
        stub.parent.mkdir()
        stub.write_text(STUB)
        stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
        self.log = self.dir / "kubectl.log"
        self.log.write_text("")

    def run_script(self, deployments: list[dict], *args: str, **env: str) -> tuple[int, list[str], str]:
        live = self.dir / "deployments.json"
        live.write_text(json.dumps({"kind": "List", "items": deployments}))
        self.log.write_text("")
        summary = self.dir / "summary.md"
        summary.write_text("")
        inherited = {k: v for k, v in os.environ.items() if k not in ("NAMESPACE", "ROLLOUT_TIMEOUT")}
        environ = {**inherited, "PATH": f"{self.dir / 'bin'}{os.pathsep}{os.environ['PATH']}", "KUBECTL_LOG": str(self.log), "STUB_DEPLOYMENTS": str(live), "GITHUB_STEP_SUMMARY": str(summary), **env}
        done = subprocess.run([sys.executable, str(SCRIPTS / "ci-rollout.py"), *args], env=environ, capture_output=True, text=True, check=False)
        return done.returncode, self.log.read_text().splitlines(), summary.read_text() + done.stderr

    def test_a_deployment_on_latest_is_set_to_the_release_tag(self) -> None:
        code, calls, _ = self.run_script([deployment("jithendar-com", {"jithendar-com": f"{SITE}:latest"}, init={"content": f"{CONTENT}:latest"})], SITE, "pr-7")
        self.assertEqual(code, 0)
        self.assertEqual(calls, ["get deployments -o json", f"set image deployment/jithendar-com jithendar-com={SITE}:pr-7", "rollout status deployment/jithendar-com --timeout=5m"])

    def test_every_deployment_that_runs_the_image_is_released_and_others_are_left_alone(self) -> None:
        live = [
            deployment("jithendar-com", {"jithendar-com": f"{SITE}:pr-5"}),
            deployment("jithendar-com-worker", {"worker": f"{SITE}@sha256:{'a' * 64}"}, init={"migrate": f"{SITE}:pr-5"}),
            deployment("seo-agent", {"seo-agent": "registry.jithendar.com/jithendar/seo-agent:pr-5"}),
            # A longer repository name that starts the same way is another image.
            deployment("lookalike", {"x": f"{SITE}-extras:latest"}),
        ]
        code, calls, summary = self.run_script(live, SITE, "pr-7", ROLLOUT_TIMEOUT="90s")
        self.assertEqual(code, 0)
        self.assertEqual(
            calls,
            [
                "get deployments -o json",
                f"set image deployment/jithendar-com jithendar-com={SITE}:pr-7",
                f"set image deployment/jithendar-com-worker migrate={SITE}:pr-7 worker={SITE}:pr-7",
                "rollout status deployment/jithendar-com --timeout=90s",
                "rollout status deployment/jithendar-com-worker --timeout=90s",
            ],
        )
        self.assertIn("deployment/jithendar-com-worker: ready", summary)

    def test_a_deployment_already_on_the_tag_is_restarted(self) -> None:
        code, calls, summary = self.run_script([deployment("jithendar-com", {"jithendar-com": f"{SITE}:pr-7"})], SITE, "pr-7")
        self.assertEqual(code, 0)
        self.assertEqual(calls, ["get deployments -o json", "rollout restart deployment/jithendar-com", "rollout status deployment/jithendar-com --timeout=5m"])
        self.assertIn("restarted", summary)

    def test_the_namespace_is_passed_when_given(self) -> None:
        _, calls, _ = self.run_script([deployment("seo-agent", {"seo-agent": "r.example/seo-agent:latest"})], "r.example/seo-agent", "pr-9", NAMESPACE="jithendar")
        self.assertEqual(calls[0], "-n jithendar get deployments -o json")
        self.assertEqual(calls[1], "-n jithendar set image deployment/seo-agent seo-agent=r.example/seo-agent:pr-9")

    def test_nothing_to_release_is_an_error_and_changes_nothing(self) -> None:
        code, calls, output = self.run_script([deployment("seo-agent", {"seo-agent": "r.example/seo-agent:latest"})], SITE, "pr-7")
        self.assertEqual(code, 2)
        self.assertEqual(calls, ["get deployments -o json"])
        self.assertIn("No Deployment runs", output)

    def test_a_rollout_that_does_not_finish_fails_but_the_others_are_still_waited_for(self) -> None:
        live = [deployment("jithendar-com", {"jithendar-com": f"{SITE}:latest"}), deployment("jithendar-com-worker", {"worker": f"{SITE}:latest"})]
        code, calls, output = self.run_script(live, SITE, "pr-7", STUB_FAIL_STATUS="jithendar-com")
        self.assertEqual(code, 1)
        self.assertIn("rollout status deployment/jithendar-com-worker --timeout=5m", calls)
        self.assertIn("deployment/jithendar-com: **failed**", output)
        self.assertIn("deployment/jithendar-com-worker: ready", output)
        self.assertIn("ImagePullBackOff", output)  # the pods of the failed Deployment are shown
        self.assertNotIn("other-xyz", output)

    def test_a_refused_patch_fails_without_waiting_for_that_deployment(self) -> None:
        code, calls, output = self.run_script([deployment("jithendar-com-worker", {"worker": f"{SITE}:latest"})], SITE, "pr-7", STUB_FAIL_SET="jithendar-com-worker")
        self.assertEqual(code, 1)
        self.assertNotIn("rollout status deployment/jithendar-com-worker --timeout=5m", calls)
        self.assertIn("80-ci-deployer.yaml", output)

    def test_previous_moves_a_deployment_off_the_repository_the_image_was_renamed_from(self) -> None:
        old = "registry.jithendar.com/jithendar/moks-cms"  # the app image until the site moved here (2026-11-16)
        live = [
            deployment("jithendar-com", {"web": f"{old}:latest"}, init={"content": f"{CONTENT}:latest"}),
            deployment("seo-agent", {"seo-agent": "registry.jithendar.com/jithendar/seo-agent:pr-5"}),
        ]
        code, calls, summary = self.run_script(live, SITE, "pr-7", "--previous", old)
        self.assertEqual(code, 0)
        self.assertEqual(calls, ["get deployments -o json", f"set image deployment/jithendar-com web={SITE}:pr-7", "rollout status deployment/jithendar-com --timeout=5m"])
        self.assertIn("deployment/jithendar-com: ready", summary)
        # Without --previous the renamed image is not found, as before.
        code, calls, output = self.run_script(live, SITE, "pr-7")
        self.assertEqual(code, 2)
        self.assertIn("No Deployment runs", output)

    def test_bad_arguments_are_refused_before_anything_runs(self) -> None:
        for args in ([], [SITE], [f"{SITE}:latest", "pr-7"], [SITE, "pr-7:1"], [f"{SITE}@sha256:abc", "pr-7"],
                     [SITE, "pr-7", "--previous"], [SITE, "pr-7", "--previous", f"{SITE}:latest"], [SITE, "pr-7", "--other", SITE]):
            code, calls, _ = self.run_script([], *args)
            self.assertEqual(code, 2, args)
            self.assertEqual(calls, [], args)


class KeepLiveImages(unittest.TestCase):
    def run_script(self, live: list[dict], manifests: list[dict]) -> tuple[list[dict], str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "live.json"
            path.write_text(json.dumps({"kind": "List", "items": live}))
            done = subprocess.run([sys.executable, str(SCRIPTS / "keep-live-images.py"), str(path)], input=yaml.safe_dump_all(manifests), capture_output=True, text=True, check=True)
        return [d for d in yaml.safe_load_all(done.stdout) if d], done.stderr

    @staticmethod
    def images(doc: dict) -> dict[str, str]:
        spec = doc["spec"]["template"]["spec"]
        return {c["name"]: c["image"] for c in [*spec.get("initContainers", []), *spec["containers"]]}

    def test_a_released_tag_survives_a_manifest_apply(self) -> None:
        manifest = deployment("jithendar-com", {"jithendar-com": f"{SITE}:latest"}, init={"content": f"{CONTENT}:latest"})
        live = deployment("jithendar-com", {"jithendar-com": f"{SITE}:pr-61"}, init={"content": f"{CONTENT}:latest"})
        out, notes = self.run_script([live], [manifest, {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "c", "namespace": "jithendar"}, "data": {"A": "1"}}])
        self.assertEqual(self.images(out[0]), {"content": f"{CONTENT}:latest", "jithendar-com": f"{SITE}:pr-61"})
        self.assertEqual(out[1]["data"], {"A": "1"})  # everything else passes through untouched
        self.assertIn(f"jithendar-com stays on {SITE}:pr-61", notes)

    def test_a_new_workload_and_a_new_container_are_created_as_written(self) -> None:
        manifest = deployment("jithendar-com-worker", {"worker": f"{SITE}:latest"})
        out, _ = self.run_script([deployment("jithendar-com", {"jithendar-com": f"{SITE}:pr-61"})], [manifest])
        self.assertEqual(self.images(out[0]), {"worker": f"{SITE}:latest"})
        renamed = deployment("jithendar-com", {"web": f"{SITE}:latest"})
        out, _ = self.run_script([deployment("jithendar-com", {"jithendar-com": f"{SITE}:pr-61"})], [renamed])
        self.assertEqual(self.images(out[0]), {"web": f"{SITE}:latest"})

    def test_a_pinned_tag_or_another_repository_in_the_manifest_wins(self) -> None:
        live = [deployment("jithendar-com", {"jithendar-com": f"{SITE}:pr-61"})]
        out, _ = self.run_script(live, [deployment("jithendar-com", {"jithendar-com": f"{SITE}:pr-40"})])
        self.assertEqual(self.images(out[0]), {"jithendar-com": f"{SITE}:pr-40"})
        out, _ = self.run_script(live, [deployment("jithendar-com", {"jithendar-com": "registry.jithendar.com/jithendar/site-v2:latest"})])
        self.assertEqual(self.images(out[0]), {"jithendar-com": "registry.jithendar.com/jithendar/site-v2:latest"})
        out, _ = self.run_script(live, [deployment("jithendar-com", {"jithendar-com": f"{SITE}@sha256:{'b' * 64}"})])
        self.assertEqual(self.images(out[0]), {"jithendar-com": f"{SITE}@sha256:{'b' * 64}"})

    def test_kinds_and_namespaces_are_not_mixed_up(self) -> None:
        live = [deployment("postgres", {"db": "r.example/db:16.4"}, kind="StatefulSet"), {**deployment("jithendar-com", {"jithendar-com": f"{SITE}:pr-61"}), "metadata": {"name": "jithendar-com", "namespace": "other"}}]
        manifests = [deployment("postgres", {"db": "r.example/db:latest"}, kind="StatefulSet"), deployment("postgres", {"db": "r.example/db:latest"}), deployment("jithendar-com", {"jithendar-com": f"{SITE}:latest"})]
        out, _ = self.run_script(live, manifests)
        self.assertEqual(self.images(out[0]), {"db": "r.example/db:16.4"})  # the StatefulSet keeps its image
        self.assertEqual(self.images(out[1]), {"db": "r.example/db:latest"})  # a Deployment of the same name is another object
        self.assertEqual(self.images(out[2]), {"jithendar-com": f"{SITE}:latest"})  # another namespace is another object

    def test_the_real_manifests_pass_through(self) -> None:
        # Nothing live: the output is the input, for every Deployment and StatefulSet the repository ships.
        docs = [d for f in sorted((SCRIPTS.parent / "kubernetes").glob("*.yaml")) if f.name != "kustomization.yaml" for d in yaml.safe_load_all(f.read_text()) if d]
        workloads = [d for d in docs if d.get("kind") in ("Deployment", "StatefulSet")]
        self.assertGreaterEqual(len(workloads), 4)
        out, notes = self.run_script([], workloads)
        self.assertEqual(out, workloads)
        self.assertIn("No image differs", notes)


if __name__ == "__main__":
    unittest.main()
