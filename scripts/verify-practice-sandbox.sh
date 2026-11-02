#!/usr/bin/env bash
# Prove the sandbox isolation on mk4 before enabling code execution. Starts throwaway pods in
# practice-sandbox with RuntimeClass gvisor-nonet and checks, from inside:
#   1. the kernel is gVisor's (dmesg / uname), not the host's;
#   2. there is no network: only loopback, DNS and TCP to the API server, the metadata address and the
#      public internet all fail;
#   3. no service-account token is mounted;
#   4. the admission policy rejects a pod without the sandbox runtime.
# Prints PASS/FAIL per check; exits non-zero on any failure. Read-only for everything outside practice-sandbox.
set -uo pipefail
CTX="${KUBE_CONTEXT:-mk4}"
NS=practice-sandbox
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
cat <<YAML | k apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: { name: $pod, namespace: $NS, labels: { app.kubernetes.io/name: practice-sandbox-verify } }
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
k -n $NS wait --for=jsonpath='{.status.phase}'=Succeeded pod/$pod --timeout=120s >/dev/null 2>&1
out=$(k -n $NS logs $pod 2>&1)
k -n $NS delete pod $pod --wait=false >/dev/null 2>&1
echo "$out" | sed 's/^/      /'
check "gVisor kernel"               'grep -q "KERNEL.*\(gVisor\|Linux version 4.4.0\)" <<<"$out"'
check "loopback only"               'grep -q "IFACES \[.lo.\]\|IFACES none" <<<"$out"'
check "no service-account token"    'grep -q "TOKEN False" <<<"$out"'
check "API server unreachable"      '! grep -q "APISERVER open" <<<"$out" && grep -q APISERVER <<<"$out"'
check "metadata endpoint unreachable" '! grep -q "METADATA open" <<<"$out" && grep -q METADATA <<<"$out"'
check "internet unreachable"        '! grep -q "INTERNET open" <<<"$out" && grep -q INTERNET <<<"$out"'
check "DNS does not resolve"        '! grep -q "DNS resolved" <<<"$out" && grep -q DNS <<<"$out"'

rejected=$(cat <<YAML | k apply --dry-run=server -f - 2>&1
apiVersion: v1
kind: Pod
metadata: { name: should-be-rejected, namespace: $NS }
spec:
  restartPolicy: Never
  containers: [{ name: c, image: $IMAGE, command: ["true"] }]
YAML
)
check "admission rejects pods without gvisor-nonet" 'grep -q "gvisor-nonet" <<<"$rejected"'
exit $fail
