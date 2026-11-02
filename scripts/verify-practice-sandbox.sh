#!/usr/bin/env bash
# Prove the sandbox isolation on mk4 before enabling code execution. Starts a throwaway sandbox pod in
# namespace jithendar with RuntimeClass gvisor-nonet and checks, from inside:
#   1. the kernel is gVisor's (dmesg / uname), not the host's;
#   2. there is no network: only loopback, DNS and TCP to the API server, the metadata address and the
#      public internet all fail;
#   3. no service-account token is mounted;
#   4. the admission policies: a sandbox pod without gVisor is rejected, the dispatcher cannot start a pod that
#      mounts the site's Secret and cannot delete the site's pods (server-side dry runs, impersonating it).
# Prints PASS/FAIL per check; exits non-zero on any failure. Creates and deletes only its own probe pod.
set -uo pipefail
CTX="${KUBE_CONTEXT:-mk4}"
NS=jithendar
IMAGE="${SANDBOX_IMAGE:-python:3.13-slim}"
k() { kubectl --context "$CTX" "$@"; }
fail=0
check() { if eval "$2"; then echo "PASS  $1"; else echo "FAIL  $1"; fail=1; fi; }

probe='
import os, socket, subprocess, urllib.request
print("KERNEL", open("/proc/version").read().strip())
print("IFACES", sorted(os.listdir("/sys/class/net")) if os.path.exists("/sys/class/net") else "none")
print("TOKEN", os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token"))
def tcp(host, port):
    try:
        socket.create_connection((host, port), timeout=3).close(); return "open"
    except Exception as e:
        return type(e).__name__
print("APISERVER", tcp(os.environ.get("KUBERNETES_SERVICE_HOST", "10.96.0.1"), 443))
print("METADATA", tcp("169.254.169.254", 80))
print("INTERNET", tcp("1.1.1.1", 443))
try:
    socket.gethostbyname("example.com"); print("DNS resolved")
except Exception as e:
    print("DNS", type(e).__name__)
'
pod=verify-$RANDOM
no_runtime=
cat <<YAML | k apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: { name: $pod, namespace: $NS, labels: { app.kubernetes.io/name: practice-sandbox, practice.jithendar.com/verify: "true" } }
spec:
  runtimeClassName: gvisor-nonet
  serviceAccountName: practice-sandbox
  automountServiceAccountToken: false
  restartPolicy: Never
  activeDeadlineSeconds: 120
  securityContext: { runAsNonRoot: true, runAsUser: 65532, seccompProfile: { type: RuntimeDefault } }
  containers:
    - name: probe
      image: $IMAGE
      command: ["python", "-c", $(printf '%s' "$probe" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')]
      resources: { limits: { cpu: "500m", memory: 256Mi } }
      securityContext: { allowPrivilegeEscalation: false, readOnlyRootFilesystem: true, capabilities: { drop: ["ALL"] } }
YAML
echo "Starting probe pod $NS/$pod with RuntimeClass gvisor-nonet (up to 2 minutes)..."
for ((i = 0; i < 60; i++)); do
  phase=$(k -n $NS get pod "$pod" -o jsonpath='{.status.phase}' 2>/dev/null)
  [[ "$phase" == Succeeded || "$phase" == Failed ]] && break
  why=$(k -n $NS get events --field-selector "involvedObject.name=$pod,reason=FailedCreatePodSandBox" -o jsonpath='{.items[-1:].message}' 2>/dev/null)
  if [[ "$why" == *"no runtime for"* ]]; then
    node=$(k -n $NS get pod "$pod" -o jsonpath='{.spec.nodeName}')
    echo "FAIL  node $node has no gVisor runtime: run scripts/install-gvisor-mk4.sh --apply on the mk4 host"
    fail=1
    no_runtime=1
    break
  fi
  sleep 2
done
echo "      probe pod phase: ${phase:-unknown}"
out=$(k -n $NS logs $pod 2>&1)
k -n $NS delete pod $pod --wait=false >/dev/null 2>&1
if [[ -n "${no_runtime:-}" ]]; then
  echo "SKIP  in-sandbox checks (gVisor kernel, loopback only, no token, API/metadata/internet/DNS unreachable): the probe pod could not start"
else
  echo "$out" | sed 's/^/      /'
  check "gVisor kernel"               'grep -q "KERNEL.*\(gVisor\|Linux version 4.4.0\)" <<<"$out"'
  check "loopback only"               'grep -q "IFACES \[.lo.\]\|IFACES none" <<<"$out"'
  check "no service-account token"    'grep -q "TOKEN False" <<<"$out"'
  check "API server unreachable"      '! grep -q "APISERVER open" <<<"$out" && grep -q APISERVER <<<"$out"'
  check "metadata endpoint unreachable" '! grep -q "METADATA open" <<<"$out" && grep -q METADATA <<<"$out"'
  check "internet unreachable"        '! grep -q "INTERNET open" <<<"$out" && grep -q INTERNET <<<"$out"'
  check "DNS does not resolve"        '! grep -q "DNS resolved" <<<"$out" && grep -q DNS <<<"$out"'
fi

rejected=$(cat <<YAML | k apply --dry-run=server -f - 2>&1
apiVersion: v1
kind: Pod
metadata: { name: should-be-rejected, namespace: $NS, labels: { app.kubernetes.io/name: practice-sandbox } }
spec:
  restartPolicy: Never
  containers: [{ name: c, image: $IMAGE, command: ["true"] }]
YAML
)
check "admission rejects sandbox pods without gvisor-nonet" 'grep -q "gvisor-nonet" <<<"$rejected"'

DISPATCHER=system:serviceaccount:$NS:practice-dispatcher
stolen=$(cat <<YAML | k apply --dry-run=server --as="$DISPATCHER" -f - 2>&1
apiVersion: v1
kind: Pod
metadata: { name: should-be-rejected, namespace: $NS }
spec:
  restartPolicy: Never
  containers: [{ name: c, image: $IMAGE, command: ["true"], envFrom: [{ secretRef: { name: jithendar-com-env } }] }]
YAML
)
check "dispatcher cannot start a pod reading the site's Secret" 'grep -qi "denied\|forbidden" <<<"$stolen"'
site_pod=$(k -n $NS get pods -l app=jithendar-com -o name | head -1)
deleted=$(k -n $NS delete "$site_pod" --dry-run=server --as="$DISPATCHER" 2>&1)
check "dispatcher cannot delete the site's pods" 'grep -q "only sandbox pods" <<<"$deleted"'
# A policy expression that does not type-check errors at admission and, with failurePolicy Fail, rejects pods.
for policy in practice-sandbox-pods practice-dispatcher-deletes; do
  warnings=$(k get validatingadmissionpolicy "$policy" -o jsonpath='{.status.typeChecking.expressionWarnings}' 2>&1)
  check "policy $policy type-checks cleanly" '[[ -z "$warnings" ]]'
  [[ -z "$warnings" ]] || echo "      $warnings"
done
exit $fail
