#!/usr/bin/env python3
"""Check the two-part Kubernetes tools series: every YAML block, the Kustomize overlay, KEDA triggers,
the Kyverno CEL expressions, the PromQL and the shell blocks.

Usage (from www/):
  python3 -m venv /tmp/k8s-tools-venv && /tmp/k8s-tools-venv/bin/pip install pyyaml jsonschema cel-python
  /tmp/k8s-tools-venv/bin/python sites/jithendar.com/docs/knowledge-sharing/kubernetes-tools/verify_examples.py [--context mk4]

cel-python needs a Python with google-re2 wheels (3.11 works; 3.15 did not build on 2026-11-08).
CRD schemas are downloaded once, at the versions the article names, into --cache. With --context, core
Kubernetes types are validated against that cluster's OpenAPI v3 and the PromQL runs against its Prometheus
through the API server's service proxy (read-only GETs). Without it those checks are skipped, not passed.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

# PyYAML reads a bare "=" as the YAML 1.1 value tag; one upstream CRD has an enum of "=". Keep it a string.
yaml.SafeLoader.add_constructor("tag:yaml.org,2002:value", lambda loader, node: loader.construct_scalar(node))

HERE = Path(__file__).resolve().parent
WWW = HERE.parents[2]
EXAMPLES = HERE / "examples"
ARTICLES = [WWW / "content/blog/15-essential-kubernetes-tools-devops-engineers-2026.mdx",
            WWW / "content/blog/15-essential-kubernetes-tools-devops-engineers-2026-part-2.mdx"]
GH, RAW = "https://github.com", "https://raw.githubusercontent.com"
# Versions are the latest stable releases on 2026-11-08, the ones the article names.
CRDS = {
    "argocd-application.yaml": f"{RAW}/argoproj/argo-cd/v3.6.1/manifests/crds/application-crd.yaml",
    "argocd-applicationset.yaml": f"{RAW}/argoproj/argo-cd/v3.6.1/manifests/crds/applicationset-crd.yaml",
    "flux.yaml": f"{GH}/fluxcd/flux2/releases/download/v2.10.0/install.yaml",
    "promop.yaml": f"{GH}/prometheus-operator/prometheus-operator/releases/download/v0.95.1/stripped-down-crds.yaml",
    "karpenter-nodepools.yaml": f"{RAW}/aws/karpenter-provider-aws/v1.15.1/pkg/apis/crds/karpenter.sh_nodepools.yaml",
    "karpenter-ec2nodeclasses.yaml": f"{RAW}/aws/karpenter-provider-aws/v1.15.1/pkg/apis/crds/karpenter.k8s.aws_ec2nodeclasses.yaml",
    "keda.yaml": f"{GH}/kedacore/keda/releases/download/v2.21.0/keda-2.21.0-crds.yaml",
    "istio.yaml": f"{RAW}/istio/istio/1.31.4/manifests/charts/base/files/crd-all.gen.yaml",
    "cilium-cnp.yaml": f"{RAW}/cilium/cilium/v1.20.4/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnetworkpolicies.yaml",
    "cert-manager.yaml": f"{GH}/cert-manager/cert-manager/releases/download/v1.21.3/cert-manager.crds.yaml",
    "gateway-api.yaml": f"{GH}/kubernetes-sigs/gateway-api/releases/download/v1.7.0/standard-install.yaml",
    "velero-schedules.yaml": f"{RAW}/vmware-tanzu/velero/v1.18.4/config/crd/v1/bases/velero.io_schedules.yaml",
    "kyverno-validatingpolicies.yaml": f"{RAW}/kyverno/kyverno/v1.19.2/config/crds/policies.kyverno.io/policies.kyverno.io_validatingpolicies.yaml",
}
KEDA_SCALERS = f"{GH}/kedacore/keda/releases/download/v2.21.0/scalers-schema-2.21.0.json"
CORE_GROUPS = ["api/v1", "apis/apps/v1"]
NOT_K8S = {"prometheus/scrape-config.yaml"}  # a Prometheus config fragment, parsed only
PROM_PATH = "/api/v1/namespaces/monitoring/services/prometheus:9090/proxy/prometheus/api/v1/query"
failures: list[str] = []
skipped: list[str] = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  ({detail})"))
    if not ok:
        failures.append(name)


def skip(name, why):
    print(f"SKIP  {name}  ({why})")
    skipped.append(name)


def fetch(url, dest):
    if not dest.exists():  # curl, not urllib: python.org builds ship without a CA bundle
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["curl", "-fsSL", "-o", str(dest), url], check=True, timeout=120)
    return dest


def strict(node):
    """kubeconform-style strictness: unknown fields fail unless the schema preserves them."""
    if isinstance(node, dict):
        if node.get("format") == "int-or-string" or node.get("x-kubernetes-int-or-string"):
            node.pop("type", None)
            node["anyOf"] = [{"type": "integer"}, {"type": "string"}]
        # Only real object schemas: oneOf/anyOf branches that just list a required property must stay open.
        if node.get("type") == "object" and "properties" in node and "additionalProperties" not in node \
                and not node.get("x-kubernetes-preserve-unknown-fields"):
            node["additionalProperties"] = False
        for v in node.values():
            strict(v)
    elif isinstance(node, list):
        for v in node:
            strict(v)
    return node


def load_crd_schemas(cache):
    schemas = {}
    for name, url in CRDS.items():
        for doc in yaml.safe_load_all(fetch(url, cache / name).read_text()):
            if not doc or doc.get("kind") != "CustomResourceDefinition":
                continue
            spec = doc["spec"]
            for v in spec["versions"]:
                if v.get("served") and "schema" in v:
                    s = strict(v["schema"]["openAPIV3Schema"])
                    # Some CRDs (Istio) omit the envelope; ObjectMeta itself is the API server's job, not this check's.
                    s.setdefault("properties", {}).update(apiVersion={"type": "string"}, kind={"type": "string"},
                                                          metadata={"type": "object"})
                    schemas[(f"{spec['group']}/{v['name']}", spec["names"]["kind"])] = Draft202012Validator(s)
    return schemas


def load_core_schemas(context, cache):
    schemas = {}
    for group in CORE_GROUPS:
        out = subprocess.run(["kubectl", "--context", context, "--request-timeout=30s", "get", "--raw", f"/openapi/v3/{group}"],
                             capture_output=True, text=True, check=True).stdout
        (cache / f"openapi-{group.replace('/', '_')}.json").write_text(out)
        doc = strict(json.loads(out))
        uri = f"urn:k8s:{group}"
        registry = Registry().with_resource(uri, Resource.from_contents(doc, default_specification=DRAFT202012))
        for name, s in doc["components"]["schemas"].items():
            for gvk in s.get("x-kubernetes-group-version-kind", []):
                api = f"{gvk['group']}/{gvk['version']}" if gvk["group"] else gvk["version"]
                schemas[(api, gvk["kind"])] = Draft202012Validator({"$ref": f"{uri}#/components/schemas/{name}"}, registry=registry)
    return schemas


def validate_docs(label, docs, schemas, have_core):
    for i, doc in enumerate(docs):
        key = (doc.get("apiVersion"), doc.get("kind"))
        tag = f"{label} [{i}] {key[1]}"
        if key not in schemas:
            core = "." not in key[0].split("/")[0]  # v1, apps/v1
            if core and not have_core:
                skip(tag, "core schema needs --context")
            else:
                check(tag, False, f"no schema for {key}")
            continue
        errors = sorted(schemas[key].iter_errors(doc), key=lambda e: list(e.path))
        check(tag, not errors, "; ".join(f"{'/'.join(map(str, e.path))}: {e.message[-160:]}" for e in errors[:3]))


def keda_triggers(docs, scalers):
    params = {s["type"]: s["parameters"] for s in scalers["scalers"]}
    for doc in docs:
        if doc.get("kind") != "ScaledObject":
            continue
        for t in doc["spec"]["triggers"]:
            known = {p["name"]: p for p in params[t["type"]]}
            meta = t.get("metadata", {})
            unknown = sorted(set(meta) - set(known))
            missing = [n for n, p in known.items() if not p.get("optional") and "default" not in p and n not in meta
                       and not p.get("deprecated")
                       and not (t.get("authenticationRef") and p.get("triggerAuthenticationVariableReadable"))]
            check(f"KEDA {doc['metadata']['name']} {t['type']} metadata", not unknown and not missing,
                  f"unknown {unknown}, missing {missing}")


def kyverno_cel():
    try:
        import celpy
    except ImportError:
        skip("Kyverno CEL evaluation", "pip install cel-python")
        return
    env = celpy.Environment()
    pods = {name: yaml.safe_load((EXAMPLES / "tests" / f"{name}.yaml").read_text()) for name in ("pod-privileged", "pod-good")}
    expect = {"disallow-privileged.yaml": {"pod-privileged": False, "pod-good": True},
              "allowed-registries.yaml": {"pod-privileged": False, "pod-good": True}}
    for policy_file, cases in expect.items():
        spec = yaml.safe_load((EXAMPLES / "kyverno" / policy_file).read_text())["spec"]
        for pod_name, want in cases.items():
            act = {"object": celpy.json_to_cel(pods[pod_name])}
            variables = {}
            for v in spec.get("variables", []):
                variables[v["name"]] = env.program(env.compile(v["expression"])).evaluate({**act, "variables": celpy.json_to_cel(variables)})
            act["variables"] = celpy.celtypes.MapType({celpy.celtypes.StringType(k): v for k, v in variables.items()})
            got = all(bool(env.program(env.compile(r["expression"])).evaluate(act)) for r in spec["validations"])
            check(f"Kyverno {policy_file} on {pod_name} -> {'allow' if want else 'deny'}", got == want, f"got {got}")


def promql(context, articles_text):
    queries = []
    for block in re.findall(r"^```promql\n(.*?)^```", articles_text, re.S | re.M):
        for chunk in re.split(r"\n\s*\n", block):
            q = "\n".join(line for line in chunk.splitlines() if not line.lstrip().startswith("#")).strip()
            if q:
                queries.append(("article", q))
    for doc in yaml.safe_load_all((EXAMPLES / "prometheus/prometheusrule.yaml").read_text()):
        for group in doc["spec"]["groups"]:
            for rule in group["rules"]:
                queries.append((rule.get("alert") or rule.get("record"), rule["expr"].strip()))
    for label, q in queries:
        if not context:
            skip(f"PromQL {label}: {q.splitlines()[0][:60]}", "needs --context")
            continue
        url = PROM_PATH + "?query=" + urllib.parse.quote(q)
        out = subprocess.run(["kubectl", "--context", context, "--request-timeout=30s", "get", "--raw", url],
                             capture_output=True, text=True)
        ok = out.returncode == 0 and json.loads(out.stdout).get("status") == "success"
        series = len(json.loads(out.stdout)["data"]["result"]) if ok else 0
        check(f"PromQL parses and runs ({series} series): {label}: {q.splitlines()[0][:60]}", ok, out.stderr.strip()[:200])


def article_checks(path, example_texts):
    text = path.read_text()
    front, body = text.split("\n---\n", 1)
    meta = yaml.safe_load(front.lstrip("-\n"))
    check(f"{path.name}: title <= 110", len(meta["title"]) <= 110, str(len(meta["title"])))
    check(f"{path.name}: description 50-160", 50 <= len(meta["description"]) <= 160, str(len(meta["description"])))
    check(f"{path.name}: seoTitle <= 60", len(meta["seoTitle"]) <= 60, str(len(meta["seoTitle"])))
    check(f"{path.name}: seoDescription <= 160", len(meta["seoDescription"]) <= 160, str(len(meta["seoDescription"])))
    check(f"{path.name}: featured image exists", (WWW / "public" / meta["featuredImage"]["src"].lstrip("/")).exists())
    for ref in meta["related"]:
        check(f"{path.name}: related {ref} exists", (WWW / "content" / f"{ref}.mdx").exists())
    for img in re.findall(r"!\[[^\]]*\]\((/images/[^)]+)\)", body):
        check(f"{path.name}: image {img}", (WWW / "public" / img.lstrip("/")).exists())
    for slug in set(re.findall(r"\]\(/blog/([a-z0-9-]+)\)", body)):
        check(f"{path.name}: link /blog/{slug}", (WWW / "content/blog" / f"{slug}.mdx").exists())
    for block in re.findall(r"^```yaml\n(.*?)^```", body, re.S | re.M):
        match = [name for name, t in example_texts.items() if t == block]
        check(f"{path.name}: YAML block equals an example file ({match[0] if match else block.splitlines()[0]})", len(match) == 1)
    for i, block in enumerate(re.findall(r"^```bash\n(.*?)^```", body, re.S | re.M)):
        res = subprocess.run(["bash", "-n"], input=block, capture_output=True, text=True)
        check(f"{path.name}: bash block {i + 1} passes bash -n", res.returncode == 0, res.stderr.strip())
    prose = re.sub(r"```[\s\S]*?```", " ", body)
    prose = re.sub(r"<\/?[A-Za-z][^>\n]*>", " ", prose)
    words = len(re.sub(r"[#>*_`\[\]()!-]", " ", prose).split())
    check(f"{path.name}: reading time {round(words / 220)} min within 10-15", 10 <= round(words / 220) <= 15, str(words))
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--context", help="kubectl context for core schemas and PromQL (read-only)")
    ap.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "k8s-tools-schemas")
    args = ap.parse_args()

    schemas = load_crd_schemas(args.cache)
    have_core = bool(args.context)
    if have_core:
        schemas.update(load_core_schemas(args.context, args.cache))

    example_texts = {str(p.relative_to(EXAMPLES)): p.read_text() for p in sorted(EXAMPLES.rglob("*.yaml"))}
    all_docs = []
    for name, text in example_texts.items():
        docs = [d for d in yaml.safe_load_all(text) if d]
        if name in NOT_K8S:
            check(f"{name} parses with scrape_configs", "scrape_configs" in docs[0])
            continue
        if name.startswith("kustomize/") and name.endswith(("kustomization.yaml", "replicas.yaml")):
            continue  # Kustomization files and the strategic-merge patch are checked through the build below
        all_docs += docs
        validate_docs(name, docs, schemas, have_core)

    with tempfile.TemporaryDirectory() as tmp:
        out = subprocess.run(["kubectl", "kustomize", str(EXAMPLES / "kustomize/overlays/production")],
                             capture_output=True, text=True, cwd=tmp)
        check("kubectl kustomize overlays/production builds", out.returncode == 0, out.stderr[:300])
        built = [d for d in yaml.safe_load_all(out.stdout) if d]
        validate_docs("kustomize build", built, schemas, have_core)
        by_kind = {d["kind"]: d for d in built}
        dep, cm = by_kind.get("Deployment", {}), by_kind.get("ConfigMap", {})
        check("overlay: 3 replicas, tag 1.5.0, namespace shop",
              dep.get("spec", {}).get("replicas") == 3 and dep["spec"]["template"]["spec"]["containers"][0]["image"].endswith(":1.5.0")
              and all(d["metadata"].get("namespace") == "shop" for d in built))
        ref = dep["spec"]["template"]["spec"]["containers"][0]["envFrom"][0]["configMapRef"]["name"]
        check("overlay: hashed ConfigMap referenced, LOG_LEVEL=warn",
              ref == cm["metadata"]["name"] and ref != "shop-web-config" and cm["data"]["LOG_LEVEL"] == "warn", ref)

    keda_triggers(all_docs, json.loads(fetch(KEDA_SCALERS, args.cache / "keda-scalers.json").read_text()))
    kyverno_cel()
    texts = "".join(article_checks(a, {k: v for k, v in example_texts.items() if not k.startswith("tests/")}) for a in ARTICLES)
    used = {n for n, t in example_texts.items() if t in texts}
    unused = [n for n in example_texts if n not in used and not n.startswith(("tests/", "kustomize/base/deployment", "kustomize/base/service"))]
    check("every example file appears in an article", not unused, str(unused))
    promql(args.context, texts)

    print(f"\n{len(failures)} failed, {len(skipped)} skipped")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
