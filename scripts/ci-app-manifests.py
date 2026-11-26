#!/usr/bin/env python3
"""Pick the application objects CI may apply to mk4 from rendered manifests (scripts/manifests.sh output).

  scripts/manifests.sh site | python3 scripts/ci-app-manifests.py --all --rollouts rollouts.txt > site.yaml
  scripts/manifests.sh seo-agent | python3 scripts/ci-app-manifests.py --rollouts rollouts.txt > apps.yaml

Two selections (.github/workflows/deploy-kubernetes.yml):

  default  the practice-executor and seo-agent groups: only workloads and their routing in namespace jithendar.
           Anything that grants identity or permissions, runs on a schedule or is cluster-wide stays with a person.
  --all    the site group (kubernetes/kustomization.yaml), which ./deploy.sh applied by hand until 2026-11-14: also
           the Namespace jithendar itself, ServiceAccounts, Roles and RoleBindings (including CI's own), quotas and
           the mesh policies. Owner decision 2026-11-14 (services/www/docs/DEPLOYMENT.md): a merged pull request
           can therefore change what CI itself may do in namespace jithendar.

Never applied by CI in either selection: Secrets (CI cannot read or write them), cluster-wide RBAC, ClusterIssuers,
the gVisor RuntimeClass, admission policies and CronJobs.

A kind in neither list stops the run (exit 2), so a new kind gets a deliberate decision. Needs PyYAML.
"""
import argparse
import sys

import yaml

NAMESPACE = "jithendar"

# (API group, kind) CI applies. Keep in step with the Role in kubernetes/85-ci-applier.yaml.
APPLY = {
    ("apps", "Deployment"),
    ("apps", "StatefulSet"),
    ("", "Service"),
    ("", "ConfigMap"),
    ("networking.k8s.io", "Ingress"),
    ("networking.k8s.io", "NetworkPolicy"),
    ("policy", "PodDisruptionBudget"),
    ("cert-manager.io", "Certificate"),
    ("networking.istio.io", "VirtualService"),
    # Scales a Deployment (min/max replicas, triggers); its HPA is KEDA's. TriggerAuthentication (reads Secrets) is in
    # neither list on purpose.
    ("keda.sh", "ScaledObject"),
}

# Added by --all (the site group). Keep in step with the Role and ClusterRole in kubernetes/85-ci-applier.yaml.
APPLY_ALL = {
    ("", "Namespace"),  # only the namespace named NAMESPACE (its labels, e.g. istio-injection)
    ("", "ServiceAccount"),
    ("", "ResourceQuota"),
    ("rbac.authorization.k8s.io", "Role"),
    ("rbac.authorization.k8s.io", "RoleBinding"),
    ("security.istio.io", "PeerAuthentication"),
    ("security.istio.io", "AuthorizationPolicy"),
}

# Applied by a person (scripts/manifests.sh <group> | kubectl apply -f -; setup scripts), never by CI, unless --all
# moves the kind to APPLY_ALL above.
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
    ("node.k8s.io", "RuntimeClass"),
    ("admissionregistration.k8s.io", "ValidatingAdmissionPolicy"),
    ("admissionregistration.k8s.io", "ValidatingAdmissionPolicyBinding"),
    ("security.istio.io", "PeerAuthentication"),  # mTLS posture: a commit must not be able to relax it
    ("security.istio.io", "AuthorizationPolicy"),  # 75-mesh.yaml allow-known-callers: a commit must not be able to widen it
    ("batch", "CronJob"),  # seo-agent reindex: a schedule that runs workloads stays a person's decision
}

ROLLOUT_KINDS = {"Deployment": "deployment", "StatefulSet": "statefulset"}


def group_of(api_version: str) -> str:
    return api_version.split("/")[0] if "/" in api_version else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rollouts", help="write one kind/name per line for `kubectl rollout status`")
    parser.add_argument("--all", action="store_true", help="the site group: also the Namespace, ServiceAccounts, RBAC, quotas and mesh policies")
    args = parser.parse_args()
    apply_kinds = APPLY | APPLY_ALL if args.all else APPLY

    applied, manual, problems = [], [], []
    for doc in yaml.safe_load_all(sys.stdin):
        if not doc:
            continue
        kind = doc.get("kind", "")
        meta = doc.get("metadata") or {}
        name, namespace = meta.get("name", "?"), meta.get("namespace")
        key = (group_of(doc.get("apiVersion", "")), kind)
        label = f"{kind} {namespace + '/' if namespace else ''}{name}"
        if key == ("", "Namespace") and key in apply_kinds:
            if name != NAMESPACE:
                problems.append(f"{label}: CI applies only namespace {NAMESPACE}")
            else:
                applied.append(doc)
        elif key in apply_kinds:
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
