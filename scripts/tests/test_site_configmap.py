"""site.json and every config/*.json reach the pod: each is in the configMapGenerator of kubernetes/kustomization.yaml
and mapped back to its path by the "site" volume of kubernetes/30-jithendar-com.yaml.

  python3 -m unittest discover -s scripts/tests -p 'test_*.py'      (needs PyYAML)
"""
from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def expected() -> dict[str, str]:
    """ConfigMap key → path under /app/site."""
    files = {"site.json": "site.json"}
    for f in sorted((ROOT / "config").glob("*.json")):
        files[f"config.{f.name}"] = f"config/{f.name}"
    return files


class SiteConfigMap(unittest.TestCase):
    def test_generator_lists_every_file(self):
        kustomization = yaml.safe_load((ROOT / "kubernetes/kustomization.yaml").read_text())
        [generator] = [g for g in kustomization["configMapGenerator"] if g["name"] == "jithendar-com-site"]
        listed = dict(entry.split("=", 1) for entry in generator["files"])
        self.assertEqual(listed, {key: f"../{path}" for key, path in expected().items()})

    def test_volume_maps_every_key(self):
        docs = yaml.safe_load_all((ROOT / "kubernetes/30-jithendar-com.yaml").read_text())
        [deployment] = [d for d in docs if d and d["kind"] == "Deployment" and d["metadata"]["name"] == "jithendar-com"]
        [volume] = [v for v in deployment["spec"]["template"]["spec"]["volumes"] if v["name"] == "site"]
        self.assertEqual(volume["configMap"]["name"], "jithendar-com-site")
        self.assertEqual({i["key"]: i["path"] for i in volume["configMap"]["items"]}, expected())


if __name__ == "__main__":
    unittest.main()
