#!/usr/bin/env bash
# Install gVisor (runsc) on every node of the mk4 minikube cluster and register the containerd runtime
# handler `runsc-nonet` (gVisor with networking disabled) used by RuntimeClass gvisor-nonet
# (k8s/practice-executor/05-runtimeclass.yaml). Run ON THE mk4 HOST, by a person:
#
#   scripts/install-gvisor-mk4.sh            # dry run: shows what would change on each node
#   scripts/install-gvisor-mk4.sh --apply    # install, then restart containerd node by node
#
# Restarting containerd does not stop running containers (their shims keep running), but do it in a quiet
# period. Afterwards run scripts/verify-practice-sandbox.sh before turning execution on.
# Release: GVISOR_RELEASE=latest (default) or a dated release such as 20251020.0; checksums are verified.
set -euo pipefail
PROFILE="${MINIKUBE_PROFILE:-mk4}"
RELEASE="${GVISOR_RELEASE:-latest}"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

nodes=$(minikube -p "$PROFILE" node list | awk '{print $1}')
[[ -n "$nodes" ]] || { echo "No nodes found for profile $PROFILE" >&2; exit 1; }

read -r -d '' REMOTE <<'SCRIPT' || true
set -euo pipefail
ARCH=$(uname -m)
URL="https://storage.googleapis.com/gvisor/releases/release/${RELEASE}/${ARCH}"
CONFIG=/etc/containerd/config.toml
echo "  node arch: $ARCH; containerd: $(containerd --version | awk '{print $3}')"
if grep -q "runsc-nonet" "$CONFIG"; then echo "  runsc-nonet already configured"; exit 0; fi
if [[ "$APPLY" != 1 ]]; then echo "  would install runsc + containerd-shim-runsc-v1 from $URL and add runtime runsc-nonet to $CONFIG"; exit 0; fi
tmp=$(mktemp -d)
cd "$tmp"
for f in runsc containerd-shim-runsc-v1; do
  curl -fsSLO "$URL/$f" && curl -fsSLO "$URL/$f.sha512"
done
sha512sum -c runsc.sha512 -c containerd-shim-runsc-v1.sha512
sudo install -m 0755 runsc containerd-shim-runsc-v1 /usr/local/bin/
printf '[runsc_config]\n  network = "none"\n' | sudo tee /etc/containerd/runsc-nonet.toml >/dev/null
sudo cp "$CONFIG" "$CONFIG.bak-$(date +%Y%m%d%H%M%S)"
if grep -qE '^version *= *3' "$CONFIG"; then
  PLUGIN="plugins.'io.containerd.cri.v1.runtime'.containerd.runtimes.runsc-nonet"
else
  PLUGIN='plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runsc-nonet'
fi
sudo tee -a "$CONFIG" >/dev/null <<TOML

[$PLUGIN]
  runtime_type = "io.containerd.runsc.v1"
[$PLUGIN.options]
  TypeUrl = "io.containerd.runsc.v1.options"
  ConfigPath = "/etc/containerd/runsc-nonet.toml"
TOML
sudo systemctl restart containerd
sleep 3
sudo systemctl is-active containerd
runsc --version | head -1
SCRIPT

for node in $nodes; do
  echo "→ $node"
  minikube -p "$PROFILE" ssh -n "$node" -- "RELEASE=$RELEASE APPLY=$APPLY bash -s" <<<"$REMOTE"
done
[[ $APPLY == 1 ]] && echo "Done. Next: kubectl --context $PROFILE apply -f k8s/practice-executor/05-runtimeclass.yaml && scripts/verify-practice-sandbox.sh" || echo "Dry run only. Re-run with --apply."
