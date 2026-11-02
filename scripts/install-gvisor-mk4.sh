#!/usr/bin/env bash
# Install gVisor (runsc) on every node of the mk4 minikube cluster and register the containerd runtime
# handler `runsc-nonet` (gVisor with networking disabled) used by RuntimeClass gvisor-nonet
# (k8s/practice-executor/05-runtimeclass.yaml). Run ON THE mk4 HOST, by a person:
#
#   bash scripts/install-gvisor-mk4.sh            # dry run: shows what would change on each node
#   bash scripts/install-gvisor-mk4.sh --apply    # install, then restart containerd node by node
#
# Restarting containerd does not stop running containers (their shims keep running), but do it in a quiet
# period. Afterwards run scripts/verify-practice-sandbox.sh before turning execution on.
# Release: GVISOR_RELEASE=latest (default) or a dated release such as 20261026.0; the checksum is verified.
# Since late 2026 a release is one gvisor.tar.bz2 per arch (runsc, containerd-shim-runsc-v1 and a gvisor-bin/
# directory of sidecars that runsc requires next to itself); the old per-binary URLs return 404.
set -euo pipefail
PROFILE="${MINIKUBE_PROFILE:-mk4}"
RELEASE="${GVISOR_RELEASE:-latest}"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

dnf install -y bzip2

# Nodes are the docker-driver containers mk4, mk4-m02, ... found with docker, not `minikube node list`: a node
# added outside the profile (mk4-m05 shows as an "invalid profile") is missing from that list, and
# `minikube status` exits non-zero on InsufficientStorage even though the cluster runs.
if ! command -v docker >/dev/null; then
  echo "No docker here. Run this on the mk4 host (the machine where minikube runs)," >&2
  echo "for example from the Mac: scp scripts/install-gvisor-mk4.sh <user>@<mk4-host>:/tmp/ && ssh <user>@<mk4-host> bash /tmp/install-gvisor-mk4.sh" >&2
  exit 1
fi
nodes=$(docker ps --format '{{.Names}}' | grep -E "^${PROFILE}(-m[0-9]+)?\$" | sort || true)
[[ -n "$nodes" ]] || { echo "No running node containers named $PROFILE, $PROFILE-m02, ... on this host" >&2; exit 1; }
echo "Nodes: $(echo $nodes)"

# Download and verify once on the host, then copy into each node (the node image may lack bzip2).
ARCH=$(docker exec "${nodes%%$'\n'*}" uname -m)
URL="https://storage.googleapis.com/gvisor/releases/release/${RELEASE}/${ARCH}/gvisor.tar.bz2"
dl=""
if [[ $APPLY == 1 ]]; then
  command -v bzip2 >/dev/null || { echo "bzip2 is needed to unpack the release: dnf install -y bzip2" >&2; exit 1; }
  dl=$(mktemp -d)
  trap 'rm -rf "$dl"' EXIT
  echo "Downloading $URL"
  (cd "$dl" && curl -fsSLO "$URL" && curl -fsSLO "$URL.sha512" && sha512sum -c gvisor.tar.bz2.sha512)
  mkdir "$dl/x" && tar -xjf "$dl/gvisor.tar.bz2" -C "$dl/x"
  for f in runsc containerd-shim-runsc-v1 gvisor-bin; do
    [[ -e "$dl/x/$f" ]] || { echo "Release tarball has no $f; check $URL" >&2; exit 1; }
  done
  "$dl/x/runsc" --version 2>/dev/null | head -1 || true
fi

read -r -d '' REMOTE <<'SCRIPT' || true
set -euo pipefail
[[ $(id -u) == 0 ]] && sudo() { "$@"; }
CONFIG=/etc/containerd/config.toml
echo "  arch: $(uname -m); containerd: $(containerd --version | awk '{print $3}'); free: $(df -Pm /usr/local/bin | awk 'NR==2 {print $4}') MiB"
have_bin=0; have_cfg=0
[[ -x /usr/local/bin/runsc && -x /usr/local/bin/containerd-shim-runsc-v1 && -d /usr/local/bin/gvisor-bin ]] && have_bin=1
grep -q "runsc-nonet" "$CONFIG" && have_cfg=1
if [[ $have_bin == 1 && $have_cfg == 1 ]]; then echo "  already installed and configured: $(runsc --version | head -1)"; exit 0; fi
if [[ "$APPLY" != 1 ]]; then
  echo "  would install: binaries=$([[ $have_bin == 1 ]] && echo present || echo missing), runsc-nonet in $CONFIG=$([[ $have_cfg == 1 ]] && echo present || echo missing)"
  exit 0
fi
# Binaries were copied to /opt/gvisor-install by the host (not /tmp: the node mounts a tmpfs over /tmp, so
# `docker cp` lands underneath it, invisible here). Also drop any such hidden copy left by an older run.
if sudo mkdir -p /mnt/gvisor-rootfs && sudo mount --bind / /mnt/gvisor-rootfs 2>/dev/null; then
  sudo rm -rf /mnt/gvisor-rootfs/tmp/gvisor-install
  sudo umount /mnt/gvisor-rootfs
fi
sudo rmdir /mnt/gvisor-rootfs 2>/dev/null || true
sudo rm -rf /usr/local/bin/gvisor-bin
sudo cp -a /opt/gvisor-install/runsc /opt/gvisor-install/containerd-shim-runsc-v1 /opt/gvisor-install/gvisor-bin /usr/local/bin/
sudo chmod 0755 /usr/local/bin/runsc /usr/local/bin/containerd-shim-runsc-v1
sudo rm -rf /opt/gvisor-install
if [[ $have_cfg == 0 ]]; then
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
fi
sudo systemctl restart containerd
sleep 3
echo "  containerd: $(sudo systemctl is-active containerd)"
runsc --version | head -1
SCRIPT

failed=0
for node in $nodes; do
  echo "→ $node"
  if [[ $APPLY == 1 ]]; then
    docker exec "$node" rm -rf /opt/gvisor-install
    docker cp "$dl/x" "$node:/opt/gvisor-install"
  fi
  docker exec -i -e APPLY="$APPLY" "$node" bash -s <<<"$REMOTE" || { echo "  FAILED on $node" >&2; failed=1; }
done
if [[ $APPLY != 1 ]]; then echo "Dry run only. Re-run with --apply."
elif [[ $failed == 1 ]]; then echo "Some nodes FAILED (see above)." >&2; exit 1
else echo "Done. Next, on the Mac: scripts/verify-practice-sandbox.sh"
fi
