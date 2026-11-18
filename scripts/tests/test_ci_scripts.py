"""Tests for scripts/keep-live-images.py. No cluster: kubectl is a stub on PATH.

  python3 -m unittest discover -s scripts/tests -p 'test_*.py'      (needs PyYAML)

CI runs them in .github/workflows/ci-repo.yml (job "hygiene").
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parents[1]
SITE = "registry.jithendar.com/jithendar/jithendar-com"
CONTENT = "registry.jithendar.com/jithendar/jithendar-com-content"

def deployment(name: str, containers: dict[str, str], init: dict[str, str] | None = None, kind: str = "Deployment") -> dict:
    spec: dict = {"containers": [{"name": n, "image": i} for n, i in containers.items()]}
    if init:
        spec["initContainers"] = [{"name": n, "image": i} for n, i in init.items()]
    return {"apiVersion": "apps/v1", "kind": kind, "metadata": {"name": name, "namespace": "jithendar"}, "spec": {"template": {"spec": spec}}}


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
        self.assertGreaterEqual(len(workloads), 2)
        out, notes = self.run_script([], workloads)
        self.assertEqual(out, workloads)
        self.assertIn("No image differs", notes)


if __name__ == "__main__":
    unittest.main()
