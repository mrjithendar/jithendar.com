"""The practice executor's admission policies (kubernetes/practice-executor-15-admission.yaml) fit the sandbox images
its ConfigMap configures (kubernetes/practice-executor-40-executor.yaml).

  python3 -m unittest discover -s scripts/tests -p 'test_*.py'      (needs PyYAML)

The enforcing policies stay enforcing, and the image rule of the warn-only one accepts every runtime image the
executor is configured with. Without this, renaming the image in the ConfigMap would make that rule reject every
sandbox pod on the day it is switched to Deny. (Moved here from moks-cms's services/executor/tests with the manifests,
2026-11-16.)
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import yaml

KUBERNETES = Path(__file__).resolve().parents[2] / "kubernetes"


class AdmissionPoliciesFitTheSandboxImage(unittest.TestCase):
    def test_policies_fit_the_configured_sandbox_image(self) -> None:
        docs = [d for d in yaml.safe_load_all((KUBERNETES / "practice-executor-15-admission.yaml").read_text()) if d]
        actions = {d["spec"]["policyName"]: d["spec"]["validationActions"] for d in docs if d["kind"] == "ValidatingAdmissionPolicyBinding"}
        self.assertEqual(actions["practice-sandbox-pods"], ["Deny"])
        self.assertEqual(actions["practice-dispatcher-deletes"], ["Deny"])
        extra = next(d for d in docs if d["kind"] == "ValidatingAdmissionPolicy" and d["metadata"]["name"] == "practice-sandbox-pods-extra")
        prefixes = re.findall(r"c\.image\.startsWith\('([^']+)'\)", " ".join(v["expression"] for v in extra["spec"]["validations"]))
        self.assertEqual(len(prefixes), 1)
        config = next(
            d
            for d in yaml.safe_load_all((KUBERNETES / "practice-executor-40-executor.yaml").read_text())
            if d and d["kind"] == "ConfigMap" and "EXECUTOR_RUNTIMES" in d.get("data", {})
        )
        images = list(json.loads(config["data"]["EXECUTOR_RUNTIMES"]).values())
        self.assertTrue(images)
        for image in images:
            self.assertTrue(image.startswith(prefixes[0]), image)


if __name__ == "__main__":
    unittest.main()
