#!/usr/bin/env bash
# Run once on the mk4 server as root, after the 2026-10-29 freezes (CI builds starved the cluster):
#
#   bash protect-host.sh            # apply (safe to rerun)
#   bash protect-host.sh status     # show what is in place
#
# 1. 8 GB swap file: memory pressure slows the host down instead of freezing it (SSH stays reachable).
# 2. Persistent journal: kernel messages (OOM kills) survive a reboot, so the next incident can be diagnosed.
# 3. minikube-mk4.service: starts the cluster after a reboot (it does not start by itself).
# 4. Every GitHub Actions runner service on the host goes into ci.slice, capped at half the CPUs, 6 GB of
#    memory and low disk priority, so a build can no longer take the machine from the cluster.
#    Limitation: `docker build` / `docker run` steps execute inside dockerd, outside the runner's cgroup, so
#    image builds are not capped by this; the real fix is building elsewhere (jithendar.com now uses
#    GitHub-hosted runners).
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "Run as root." >&2; exit 1; }

SWAP_FILE=${SWAP_FILE:-/swapfile}
SWAP_SIZE=${SWAP_SIZE:-8G}
CI_MEMORY=${CI_MEMORY:-6G}
CPUS=$(nproc)
CI_CPU_PERCENT=$(( (CPUS / 2 > 0 ? CPUS / 2 : 1) * 100 ))

runner_units() { systemctl list-unit-files --type=service --no-legend 'actions.runner.*' 2>/dev/null | awk '{print $1}'; }

status() {
  echo "Swap:";            swapon --show || true
  echo "Journal storage:"; [[ -d /var/log/journal ]] && echo "  persistent" || echo "  volatile (lost on reboot)"
  echo "minikube-mk4:";    systemctl is-enabled minikube-mk4 2>/dev/null || echo "  not installed"
  echo "ci.slice:";        systemctl show ci.slice -p MemoryMax -p CPUQuotaPerSecUSec -p IOWeight 2>/dev/null | sed 's/^/  /'
  echo "Runner services:"
  for u in $(runner_units); do printf '  %-60s %s\n' "$u" "$(systemctl show "$u" -p Slice --value)"; done
}

if [[ ${1:-} == status ]]; then status; exit 0; fi

# 1. Swap
if swapon --show=NAME --noheadings | grep -qx "$SWAP_FILE"; then
  echo "→ Swap $SWAP_FILE already active"
else
  echo "→ Creating $SWAP_SIZE swap at $SWAP_FILE"
  [[ -f $SWAP_FILE ]] || fallocate -l "$SWAP_SIZE" "$SWAP_FILE"
  chmod 600 "$SWAP_FILE"
  mkswap "$SWAP_FILE" >/dev/null
  swapon "$SWAP_FILE"
  grep -q "^$SWAP_FILE " /etc/fstab || echo "$SWAP_FILE none swap sw 0 0" >> /etc/fstab
fi
# Prefer keeping program code and page cache over swapping application memory early.
echo 'vm.swappiness=10' > /etc/sysctl.d/90-swappiness.conf
sysctl -q -p /etc/sysctl.d/90-swappiness.conf

# 2. Persistent journal
if [[ ! -d /var/log/journal ]]; then
  echo "→ Making the journal persistent"
  mkdir -p /var/log/journal
  systemd-tmpfiles --create --prefix /var/log/journal
  systemctl restart systemd-journald
fi

# 3. Start minikube at boot
MINIKUBE=$(command -v minikube || true)
if [[ -n $MINIKUBE ]]; then
  echo "→ Installing minikube-mk4.service ($MINIKUBE)"
  cat > /etc/systemd/system/minikube-mk4.service <<EOF
[Unit]
Description=minikube cluster mk4
After=docker.service network-online.target
Wants=network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
Environment=HOME=/root
ExecStart=$MINIKUBE start -p mk4 --driver=docker --force
ExecStop=$MINIKUBE stop -p mk4
TimeoutStartSec=1200

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable minikube-mk4 >/dev/null
else
  echo "! minikube not found in PATH; skipped the boot service"
fi

# 4. Cap CI runners
echo "→ ci.slice: CPUQuota=${CI_CPU_PERCENT}% (of ${CPUS} CPUs), MemoryMax=$CI_MEMORY, low I/O priority"
cat > /etc/systemd/system/ci.slice <<EOF
[Unit]
Description=GitHub Actions runners (capped so builds cannot starve the cluster)

[Slice]
CPUQuota=${CI_CPU_PERCENT}%
MemoryHigh=$(( ${CI_MEMORY%G} - 1 ))G
MemoryMax=$CI_MEMORY
IOWeight=20
EOF
for u in $(runner_units); do
  mkdir -p "/etc/systemd/system/$u.d"
  cat > "/etc/systemd/system/$u.d/50-ci-slice.conf" <<'EOF'
[Service]
Slice=ci.slice
Nice=10
IOSchedulingClass=idle
EOF
  echo "  $u → ci.slice"
done
systemctl daemon-reload
for u in $(runner_units); do systemctl is-active --quiet "$u" && systemctl restart "$u"; done

status
