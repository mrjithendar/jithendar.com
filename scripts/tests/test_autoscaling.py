"""The site's autoscaling (kubernetes/35-autoscaling.yaml, KEDA) and its Deployment (kubernetes/30-jithendar-com.yaml)
stay consistent.

  python3 -m unittest discover -s scripts/tests -p 'test_*.py'      (needs PyYAML)

KEDA owns the replica count, so the Deployment must not set one (every deploy would apply it over KEDA's). The
ScaledObject keeps at least two pods, more than the PodDisruptionBudget's minAvailable. Its numbers are the owner's:
while one is SET-ME its test is skipped, naming it, and the deploy leaves the ScaledObject out
(scripts/ci-app-manifests.py); once it is set, it must be a valid number. Reads the files only, no cluster.
"""
from __future__ import annotations

import unittest
from pathlib import Path

import yaml

KUBERNETES = Path(__file__).resolve().parents[2] / "kubernetes"
UNSET = "SET-ME"


def documents(name: str) -> list[dict]:
    return [d for d in yaml.safe_load_all((KUBERNETES / name).read_text()) if d]


def one(name: str, kind: str, object_name: str) -> dict:
    return next(d for d in documents(name) if d["kind"] == kind and d["metadata"]["name"] == object_name)


DEPLOYMENT = one("30-jithendar-com.yaml", "Deployment", "jithendar-com")
PDB = one("30-jithendar-com.yaml", "PodDisruptionBudget", "jithendar-com")
SCALED = one("35-autoscaling.yaml", "ScaledObject", "jithendar-com")
SPEC = SCALED["spec"]
TRIGGERS = {t["type"]: t for t in SPEC["triggers"]}


def is_number(value) -> bool:
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


class Wiring(unittest.TestCase):
    def test_the_deployment_sets_no_replicas(self):
        self.assertNotIn("replicas", DEPLOYMENT["spec"], "KEDA owns the count: a replicas field is applied over it on every deploy")

    def test_the_scaled_object_is_deployed_with_the_site(self):
        resources = yaml.safe_load((KUBERNETES / "kustomization.yaml").read_text())["resources"]
        self.assertIn("35-autoscaling.yaml", resources)
        self.assertEqual("jithendar", SCALED["metadata"]["namespace"])
        self.assertEqual("jithendar-com", SPEC["scaleTargetRef"]["name"])
        self.assertNotIn("kind", SPEC["scaleTargetRef"])  # Deployment, KEDA's default

    def test_at_least_two_pods_and_more_than_the_disruption_budget(self):
        self.assertGreaterEqual(SPEC["minReplicaCount"], 2)
        self.assertGreater(SPEC["minReplicaCount"], PDB["spec"]["minAvailable"])

    def test_requests_per_second_from_the_public_service(self):
        prom = TRIGGERS["prometheus"]
        self.assertEqual("AverageValue", prom["metricType"])
        self.assertEqual("http://prometheus.monitoring:9090/prometheus", prom["metadata"]["serverAddress"])
        query = prom["metadata"]["query"]
        for selector in ('reporter="destination"', 'destination_workload_namespace="jithendar"',
                         'destination_workload="jithendar-com"', 'destination_service_name="jithendar-com"'):
            self.assertIn(selector, query)

    def test_cpu_of_the_web_container_only(self):
        cpu = TRIGGERS["cpu"]
        self.assertEqual("Utilization", cpu["metricType"])
        containers = {c["name"]: c for c in DEPLOYMENT["spec"]["template"]["spec"]["containers"]}
        self.assertIn(cpu["metadata"]["containerName"], containers)
        self.assertIn("cpu", containers[cpu["metadata"]["containerName"]]["resources"]["requests"])

    def test_no_trigger_needs_credentials(self):
        for t in SPEC["triggers"]:
            self.assertNotIn("authenticationRef", t)


class OwnersNumbers(unittest.TestCase):
    """The values in 35-autoscaling.yaml marked SET-ME (kubernetes/README.md, "Autoscaling"): skipped while SET-ME,
    checked once set."""

    def chosen(self, value, what: str):
        if value == UNSET:
            self.skipTest(f"{what} is {UNSET}: the owner's to choose; until then the deploy leaves the ScaledObject out")
        return value

    def test_maximum_is_not_below_the_minimum(self):
        value = self.chosen(SPEC["maxReplicaCount"], "maxReplicaCount (upper bound)")
        self.assertIsInstance(value, int)
        self.assertGreaterEqual(value, SPEC["minReplicaCount"])

    def test_requests_per_second_threshold_is_a_number(self):
        value = self.chosen(TRIGGERS["prometheus"]["metadata"]["threshold"], "prometheus threshold (requests per second per pod)")
        self.assertTrue(is_number(value), f"prometheus threshold is {value!r}: requests per second per pod")

    def test_cpu_target_is_a_number(self):
        value = self.chosen(TRIGGERS["cpu"]["metadata"]["value"], "cpu value (percent of the web container's request)")
        self.assertTrue(is_number(value), f"cpu value is {value!r}: percent of the web container's request")

    def test_optional_values_are_set_when_present(self):
        fallback = SPEC.get("fallback")
        if fallback is not None:
            self.assertIsInstance(fallback.get("failureThreshold"), int)
            self.assertIsInstance(fallback.get("replicas"), int)
            self.assertGreaterEqual(fallback["replicas"], SPEC["minReplicaCount"])
        behavior = SPEC.get("advanced", {}).get("horizontalPodAutoscalerConfig", {}).get("behavior", {})
        window = behavior.get("scaleDown", {}).get("stabilizationWindowSeconds")
        if "stabilizationWindowSeconds" in behavior.get("scaleDown", {}):
            self.assertIsInstance(window, int)


if __name__ == "__main__":
    unittest.main()
