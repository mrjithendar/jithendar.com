"""What CI applies (scripts/ci-app-manifests.py) and what its ServiceAccount may do (kubernetes/85-ci-applier.yaml)
stay in step.

  python3 -m unittest discover -s scripts/tests -p 'test_*.py'      (needs PyYAML)

A kind in the script's lists without the Role's verbs fails the deploy's server-side dry run ("forbidden"); a Role
rule without the kind in the lists is a permission nobody uses. Reads the files only, no cluster.
"""
from __future__ import annotations

import importlib.util
import io
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "ci-app-manifests.py"
APPLY_VERBS = {"get", "list", "watch", "create", "patch", "update"}

spec = importlib.util.spec_from_file_location("ci_app_manifests", SCRIPT)
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


def plural(kind: str) -> str:
    k = kind.lower()
    if k.endswith("y"):
        return k[:-1] + "ies"
    if k.endswith("s"):
        return k + "es"
    return k + "s"


def role_rules() -> list[dict]:
    docs = yaml.safe_load_all((ROOT / "kubernetes" / "85-ci-applier.yaml").read_text())
    role = next(d for d in docs if d and d["kind"] == "Role" and d["metadata"]["name"] == "github-ci-applier")
    return role["rules"]


def allowed(group: str, resource: str) -> set[str]:
    verbs: set[str] = set()
    for rule in role_rules():
        if group in rule["apiGroups"] and resource in rule["resources"]:
            verbs |= set(rule["verbs"])
    return verbs


def select(objects: list[dict], *flags: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *flags], input=yaml.safe_dump_all(objects),
                          capture_output=True, text=True, check=False)


class RoleCoversAppliedKinds(unittest.TestCase):
    def test_every_applied_kind_has_the_apply_verbs(self):
        for group, kind in sorted(ci.APPLY | ci.APPLY_ALL):
            if (group, kind) == ("", "Namespace"):
                continue  # the ClusterRole in the same file, namespace jithendar only
            with self.subTest(kind=kind):
                self.assertLessEqual(APPLY_VERBS, allowed(group, plural(kind)), f"{kind}: Role github-ci-applier lacks verbs")

    def test_scaled_objects_are_applied_and_their_hpas_only_read(self):
        self.assertIn(("keda.sh", "ScaledObject"), ci.APPLY)
        self.assertEqual({"get", "list", "watch"}, allowed("autoscaling", "horizontalpodautoscalers"))

    def test_trigger_authentications_stay_a_decision(self):
        """They read Secrets: in neither list, so one in a manifest stops the deploy until someone decides."""
        kinds = ci.APPLY | ci.APPLY_ALL | ci.MANUAL
        self.assertNotIn(("keda.sh", "TriggerAuthentication"), kinds)
        self.assertNotIn(("keda.sh", "ClusterTriggerAuthentication"), kinds)
        self.assertFalse(allowed("keda.sh", "triggerauthentications"))


class Selection(unittest.TestCase):
    def test_a_scaled_object_in_jithendar_is_applied(self):
        so = {"apiVersion": "keda.sh/v1alpha1", "kind": "ScaledObject", "metadata": {"name": "web", "namespace": "jithendar"}}
        out = select([so], "--all")
        self.assertEqual(0, out.returncode, out.stderr)
        self.assertEqual([so], [d for d in yaml.safe_load_all(io.StringIO(out.stdout)) if d])

    def test_a_scaled_object_elsewhere_stops_the_run(self):
        so = {"apiVersion": "keda.sh/v1alpha1", "kind": "ScaledObject", "metadata": {"name": "web", "namespace": "other"}}
        self.assertEqual(2, select([so], "--all").returncode)

    def test_a_value_left_set_me_stops_the_run_and_is_named(self):
        so = {"apiVersion": "keda.sh/v1alpha1", "kind": "ScaledObject", "metadata": {"name": "web", "namespace": "jithendar"},
              "spec": {"maxReplicaCount": "SET-ME", "triggers": [{"type": "cpu", "metadata": {"value": "SET-ME"}}]}}
        out = select([so], "--all")
        self.assertEqual(2, out.returncode)
        self.assertIn("spec.maxReplicaCount is SET-ME", out.stderr)
        self.assertIn("spec.triggers[0].metadata.value is SET-ME", out.stderr)
        self.assertEqual("", out.stdout)  # nothing selected, so nothing is applied

    def test_set_me_inside_a_longer_string_is_not_a_placeholder(self):
        cm = {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "c", "namespace": "jithendar"},
              "data": {"note": "replace SET-ME values first"}}
        self.assertEqual(0, select([cm], "--all").returncode)

    def test_a_trigger_authentication_stops_the_run(self):
        ta = {"apiVersion": "keda.sh/v1alpha1", "kind": "TriggerAuthentication", "metadata": {"name": "x", "namespace": "jithendar"}}
        self.assertEqual(2, select([ta], "--all").returncode)


if __name__ == "__main__":
    unittest.main()
