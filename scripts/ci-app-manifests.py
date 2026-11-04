#!/usr/bin/env python3
"""Pick the application objects CI may apply to mk4 from rendered manifests (kubectl kustomize output).

  kubectl kustomize k8s | python3 scripts/ci-app-manifests.py --rollouts rollouts.txt > apps.yaml

CI (.github/workflows/deploy-minikube.yml) applies only workloads and their routing in namespace jithendar. Anything
cluster-wide, or that grants identity or permissions, stays with a person (./deploy.sh and friends): the Namespace,
ClusterIssuers, Traefik's TLSStore, RBAC (including CI's own Roles), ServiceAccounts, Secrets, quotas, the gVisor
RuntimeClass and the admission policies. That way a change in Git can never widen what CI itself may do.

A kind in neither list stops the run (exit 2), so a new kind gets a deliberate decision. Needs PyYAML.
"""
import argparse
import sys

import yaml

NAMESPACE = "jithendar"

# (API group, kind) CI applies. Keep in step with the Role in k8s/85-ci-applier.yaml.
APPLY = {
    ("apps", "Deployment"),
    ("apps", "StatefulSet"),
    ("", "Service"),
    ("", "ConfigMap"),
    ("networking.k8s.io", "Ingress"),
    ("networking.k8s.io", "NetworkPolicy"),
    ("policy", "PodDisruptionBudget"),
    ("traefik.io", "Middleware"),
    ("traefik.io", "MiddlewareTCP"),
    ("traefik.io", "IngressRouteTCP"),
    ("traefik.io", "TLSOption"),
    ("cert-manager.io", "Certificate"),
}

# Applied by a person (./deploy.sh; kubectl apply -k k8s/practice-executor; setup scripts), never by CI.
MANUAL = {
    ("", "Namespace"),
    ("", "Secret"),
    ("", "ServiceAccount"),
    ("", "ResourceQuota"),
    ("rbac.authorization.k8s.io", "Role"),
    ("rbac.authorization.k8s.io", "RoleBinding"),
    ("rbac.authorization.k8s.io", "ClusterRole"),
    ("rbac.authorization.k8s.io", "ClusterRoleBinding"),
    ("cert-manager.io", "ClusterIssuer"),
    ("traefik.io", "TLSStore"),
    ("node.k8s.io", "RuntimeClass"),
    ("admissionregistration.k8s.io", "ValidatingAdmissionPolicy"),
    ("admissionregistration.k8s.io", "ValidatingAdmissionPolicyBinding"),
}

ROLLOUT_KINDS = {"Deployment": "deployment", "StatefulSet": "statefulset"}


def group_of(api_version: str) -> str:
    return api_version.split("/")[0] if "/" in api_version else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rollouts", help="write one kind/name per line for `kubectl rollout status`")
    args = parser.parse_args()

    applied, manual, problems = [], [], []
    for doc in yaml.safe_load_all(sys.stdin):
        if not doc:
            continue
        kind = doc.get("kind", "")
        meta = doc.get("metadata") or {}
        name, namespace = meta.get("name", "?"), meta.get("namespace")
        key = (group_of(doc.get("apiVersion", "")), kind)
        label = f"{kind} {namespace + '/' if namespace else ''}{name}"
        if key in APPLY:
            if namespace != NAMESPACE:
                problems.append(f"{label}: CI applies only namespace {NAMESPACE}")
            else:
                applied.append(doc)
        elif key in MANUAL:
            manual.append(label)
        else:
            problems.append(f"{label}: kind {key[1]} ({key[0] or 'core'}) is in neither list of scripts/ci-app-manifests.py")

    if problems:
        for p in problems:
            print(f"::error::{p}", file=sys.stderr)
        return 2

    yaml.safe_dump_all(applied, sys.stdout, sort_keys=False)
    if args.rollouts:
        with open(args.rollouts, "w", encoding="utf-8") as f:
            for d in applied:
                if d["kind"] in ROLLOUT_KINDS:
                    f.write(f"{ROLLOUT_KINDS[d['kind']]}/{d['metadata']['name']}\n")

    print(f"CI applies {len(applied)} objects:", file=sys.stderr)
    for d in applied:
        print(f"  {d['kind']} {d['metadata']['name']}", file=sys.stderr)
    print(f"Not applied by CI, a person applies these ({len(manual)}):", file=sys.stderr)
    for label in manual:
        print(f"  {label}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
