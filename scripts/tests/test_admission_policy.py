"""The admission policies for the CI deployer's token (kubernetes/81-ci-deployer-admission.yaml) keep up with the
Deployments that token may patch (kubernetes/80-ci-deployer.yaml).

  python3 -m unittest discover -s scripts/tests -p 'test_*.py'      (needs PyYAML)

A release changes container images and the restartedAt annotation, nothing else. The two policies say so field by
field, so a pod-template field nobody listed is a field a leaked token could change. These tests read the manifests
only (no cluster, no CEL evaluation): every field the four Deployments use must be compared by a policy or named
below as deliberately left alone, together with the fields that are dangerous even though no manifest sets them.

CI runs them in .github/workflows/ci-repo.yml (job "hygiene").
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

KUBERNETES = Path(__file__).resolve().parents[2] / "kubernetes"
POLICIES = ("ci-deployer-rollouts", "ci-deployer-rollouts-extra")
DEPLOYER = "system:serviceaccount:jithendar:github-ci-deployer"

# What a release sets, and fields whose change gives no access to the workload or its Secrets.
CONTAINER_UNCHECKED = {
    "name",  # matched, not compared: the rules pair containers by name
    "image",  # what a release changes; the registry prefix is its own rule
    "imagePullPolicy",
    "resources",  # availability only; a CEL check on resources.limits did not type-check on this cluster
    "terminationMessagePath",
    "terminationMessagePolicy",
}
POD_UNCHECKED = {
    "containers",  # compared container by container
    "initContainers",
    "enableServiceLinks",
    "imagePullSecrets",
    "restartPolicy",  # a Deployment allows only Always
    "schedulerName",
    "terminationGracePeriodSeconds",
    "topologySpreadConstraints",
}

# Compared whether or not a manifest sets them today.
CONTAINER_REQUIRED = {
    *("command", "args", "env", "envFrom", "volumeMounts", "securityContext", "lifecycle"),
    *("livenessProbe", "readinessProbe", "startupProbe", "ports", "workingDir"),
}
INIT_CONTAINER_REQUIRED = CONTAINER_REQUIRED | {"restartPolicy"}
POD_REQUIRED = {
    *("volumes", "serviceAccountName", "securityContext", "hostNetwork", "hostPID", "hostIPC"),
    *("runtimeClassName", "shareProcessNamespace", "automountServiceAccountToken", "dnsPolicy", "dnsConfig", "hostAliases"),
}


def documents(name: str) -> list[dict]:
    return [d for d in yaml.safe_load_all((KUBERNETES / name).read_text(encoding="utf-8")) if d]


def deployer_deployments() -> set[str]:
    """The Deployments the deployer's Role lets it patch."""
    role = next(d for d in documents("80-ci-deployer.yaml") if d["kind"] == "Role")
    return {n for rule in role["rules"] if "patch" in rule["verbs"] for n in rule.get("resourceNames", [])}


def pod_specs(names: set[str]) -> dict[str, dict]:
    found = {}
    for path in sorted(KUBERNETES.glob("*.yaml")):
        for d in yaml.safe_load_all(path.read_text(encoding="utf-8")):
            if d and d.get("kind") == "Deployment" and d["metadata"]["name"] in names:
                found[d["metadata"]["name"]] = d["spec"]["template"]["spec"]
    return found


class AdmissionPolicies(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        docs = documents("81-ci-deployer-admission.yaml")
        cls.policies = {d["metadata"]["name"]: d for d in docs if d["kind"] == "ValidatingAdmissionPolicy"}
        cls.bindings = {d["spec"]["policyName"]: d for d in docs if d["kind"] == "ValidatingAdmissionPolicyBinding"}
        cls.expressions = [v["expression"] for p in cls.policies.values() for v in p["spec"]["validations"]]
        # Rules about init containers are the ones that iterate over them.
        cls.init_expressions = [e for e in cls.expressions if "initContainers.all(" in e]
        cls.container_expressions = [e for e in cls.expressions if "variables.pod.containers.all(" in e]

    def compared(self, expressions: list[str], prefix: str, field: str) -> bool:
        return any(re.search(rf"{re.escape(prefix)}{re.escape(field)}\b", e) for e in expressions)

    def test_both_policies_cover_only_the_deployers_updates_of_deployments(self) -> None:
        self.assertEqual(set(self.policies), set(POLICIES))
        for name, policy in self.policies.items():
            spec = policy["spec"]
            self.assertEqual(spec["failurePolicy"], "Fail", name)
            self.assertEqual(spec["matchConstraints"]["namespaceSelector"]["matchLabels"], {"kubernetes.io/metadata.name": "jithendar"}, name)
            self.assertEqual(spec["matchConstraints"]["resourceRules"], [{"apiGroups": ["apps"], "apiVersions": ["v1"], "operations": ["UPDATE"], "resources": ["deployments"]}], name)
            self.assertEqual([c["expression"] for c in spec["matchConditions"]], [f"request.userInfo.username == '{DEPLOYER}'"], name)
            self.assertEqual({v["name"]: v["expression"] for v in spec["variables"]}, {"pod": "object.spec.template.spec", "oldPod": "oldObject.spec.template.spec"}, name)

    def test_every_policy_is_bound_and_at_least_warns(self) -> None:
        self.assertEqual(set(self.bindings), set(POLICIES))
        for name, binding in self.bindings.items():
            actions = set(binding["spec"]["validationActions"])
            self.assertTrue(actions == {"Deny"} or actions == {"Warn", "Audit"}, f"{name}: {sorted(actions)}")

    def test_expressions_are_well_formed_enough_to_read(self) -> None:
        for e in self.expressions:
            self.assertEqual(e.count("("), e.count(")"), e)
            # `x == y` on an optional field is always written as has(x) == has(y) && (!has(x) || x == y).
            for field in re.findall(r"\(!has\(([\w.]+)\) \|\|", e):
                if field.endswith("initContainers") or field.endswith("annotations"):
                    continue  # guards of a whole rule, not of one comparison
                self.assertRegex(e, rf"has\({re.escape(field)}\) == has\(", f"{field} is compared without checking that both sides have it")

    def test_the_deployer_may_patch_only_deployments_that_exist(self) -> None:
        names = deployer_deployments()
        self.assertEqual(set(pod_specs(names)), names)

    def test_every_field_the_deployments_use_is_compared_or_left_alone_on_purpose(self) -> None:
        for name, spec in pod_specs(deployer_deployments()).items():
            for field in set(spec) - POD_UNCHECKED:
                self.assertTrue(self.compared(self.expressions, "variables.pod.", field), f"{name}: pod field {field} is in no policy rule and not in POD_UNCHECKED")
            for container in spec.get("containers", []):
                for field in set(container) - CONTAINER_UNCHECKED:
                    self.assertTrue(self.compared(self.container_expressions, "c.", field), f"{name}/{container['name']}: {field} is in no container rule and not in CONTAINER_UNCHECKED")
            for container in spec.get("initContainers") or []:
                for field in set(container) - CONTAINER_UNCHECKED:
                    self.assertTrue(self.compared(self.init_expressions, "c.", field), f"{name}/{container['name']}: {field} is in no init-container rule and not in CONTAINER_UNCHECKED")

    def test_fields_that_run_code_or_widen_access_are_always_compared(self) -> None:
        for field in sorted(CONTAINER_REQUIRED):
            self.assertTrue(self.compared(self.container_expressions, "c.", field), f"containers: {field}")
        for field in sorted(INIT_CONTAINER_REQUIRED):
            self.assertTrue(self.compared(self.init_expressions, "c.", field), f"init containers: {field}")
        for field in sorted(POD_REQUIRED):
            self.assertTrue(self.compared(self.expressions, "variables.pod.", field), f"pod: {field}")

    def test_images_come_from_this_projects_registry(self) -> None:
        rule = next(e for e in self.expressions if "c.image.startsWith(" in e)
        self.assertEqual(set(re.findall(r"c\.image\.startsWith\('([^']+)'\)", rule)), {"registry.jithendar.com/jithendar/"})
        for name, spec in pod_specs(deployer_deployments()).items():
            for container in [*spec.get("containers", []), *(spec.get("initContainers") or [])]:
                self.assertTrue(container["image"].startswith("registry.jithendar.com/jithendar/"), f"{name}/{container['name']}: {container['image']}")


if __name__ == "__main__":
    unittest.main()
