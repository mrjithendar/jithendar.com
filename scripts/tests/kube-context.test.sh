#!/usr/bin/env bash
# Tests for scripts/lib/kube-context.sh with a stub `kubectl` on PATH (no cluster needed). Plain bash, no bats:
#   bash scripts/tests/kube-context.test.sh
# Exits non-zero on the first failure. CI runs it in .github/workflows/check.yml (job "scripts").
set -uo pipefail

ROOT="$(cd "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
LIB="$ROOT/scripts/lib/kube-context.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fail=0
pass() { echo "PASS  $1"; }
nope() {
  echo "FAIL  $1" >&2
  fail=1
}

# Stub kubectl: knows contexts ctx-a (current) and ctx-b; logs every call's arguments.
mkdir -p "$TMP/bin"
cat >"$TMP/bin/kubectl" <<'STUB'
#!/usr/bin/env bash
echo "$*" >>"$KUBECTL_LOG"
# take --context X out wherever it is (the wrapper puts it first; the guard's own `config view` puts it later)
ctx="${STUB_CURRENT:-}"
args=()
while (($#)); do
  if [[ "$1" == "--context" ]]; then ctx="$2"; shift 2; else args+=("$1"); shift; fi
done
case "${args[*]}" in
  "config current-context") [[ -n "${STUB_CURRENT:-}" ]] && echo "$STUB_CURRENT" || exit 1 ;;
  # pause after the first name so a `kubectl … | grep -q` under pipefail reliably hits SIGPIPE (regression guard)
  "config get-contexts -o name") printf 'ctx-a\n'; sleep 0.2; printf 'ctx-b\n' ;;
  config\ view*) echo "https://$ctx.example:8443" ;;
  *) echo "ran against $ctx: ${args[*]}" ;;
esac
STUB
chmod +x "$TMP/bin/kubectl"
export PATH="$TMP/bin:$PATH" KUBECTL_LOG="$TMP/log"

# A tiny "cluster script" that sources the guard and runs one command.
cat >"$TMP/script.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail
source "$LIB"
kubectl -n jithendar get pods
EOF
chmod +x "$TMP/script.sh"

run() { : >"$KUBECTL_LOG"; env "$@" bash "$TMP/script.sh" </dev/null >"$TMP/out" 2>"$TMP/err"; }

# 1. The current context is resolved and passed to every call.
if run -u KUBE_CONTEXT -u YES STUB_CURRENT=ctx-a && grep -qx -- "--context ctx-a -n jithendar get pods" "$KUBECTL_LOG"; then
  pass "current context is passed (--context ctx-a)"
else nope "current context is passed"; fi

# 2. KUBE_CONTEXT overrides the current context.
if run KUBE_CONTEXT=ctx-b STUB_CURRENT=ctx-a && grep -qx -- "--context ctx-b -n jithendar get pods" "$KUBECTL_LOG" && ! grep -q -- "--context ctx-a" "$KUBECTL_LOG"; then
  pass "KUBE_CONTEXT overrides the current context"
else nope "KUBE_CONTEXT overrides the current context"; fi

# 3. A context that does not exist stops the script before any command runs.
if run KUBE_CONTEXT=ctx-missing STUB_CURRENT=ctx-a; then
  nope "missing context exits non-zero"
elif grep -q "get pods" "$KUBECTL_LOG"; then
  nope "missing context: no command may run"
else pass "missing context exits non-zero and runs nothing"; fi

# 3b. No current context and no KUBE_CONTEXT.
if run -u KUBE_CONTEXT -u STUB_CURRENT; then nope "no context at all exits non-zero"; else pass "no context at all exits non-zero"; fi

# 4. No prompt without a TTY (stdin is /dev/null here), even with KUBE_CONTEXT unset and YES unset.
if run -u KUBE_CONTEXT -u YES STUB_CURRENT=ctx-a && ! grep -q "Continue against" "$TMP/out" "$TMP/err"; then
  pass "no prompt without a TTY"
else nope "no prompt without a TTY"; fi

# 5. The context and API server are printed (stderr).
if run KUBE_CONTEXT=ctx-b && grep -q "Kube context: ctx-b (KUBE_CONTEXT), API server: https://ctx-b.example:8443" "$TMP/err"; then
  pass "prints the context and API server"
else nope "prints the context and API server"; fi

# 6. With a TTY and no KUBE_CONTEXT it asks, and anything but yes aborts. A python pty driver answers 'n' only once the
#    prompt has appeared (no sleep-based timing, which flaked with `script` fed from a pipe). Skipped without python3.
if command -v python3 >/dev/null 2>&1; then
  : >"$KUBECTL_LOG"
  env -u KUBE_CONTEXT -u YES STUB_CURRENT=ctx-a python3 - "$TMP/script.sh" >"$TMP/tty" 2>&1 <<'PY'
import os, pty, select, signal, sys, time
pid, fd = pty.fork()
if pid == 0:
    os.execvp("bash", ["bash", sys.argv[1]])
out, answered, deadline = b"", False, time.time() + 15
while time.time() < deadline:
    if not select.select([fd], [], [], 0.2)[0]:
        continue
    try:
        chunk = os.read(fd, 4096)
    except OSError:  # Linux: EIO once the child has exited
        break
    if not chunk:
        break
    out += chunk
    if not answered and b"Continue against" in out:
        os.write(fd, b"n\n")
        answered = True
else:
    os.kill(pid, signal.SIGKILL)
    out += b"\n[driver] timed out\n"
_, status = os.waitpid(pid, 0)
sys.stdout.write(out.decode(errors="replace"))
sys.exit(os.waitstatus_to_exitcode(status) if hasattr(os, "waitstatus_to_exitcode") else status >> 8)
PY
  rc=$?
  if ((rc != 0)) && grep -q "Continue against 'ctx-a'" "$TMP/tty" && grep -q "Aborted" "$TMP/tty" && ! grep -q "get pods" "$KUBECTL_LOG"; then
    pass "TTY without KUBE_CONTEXT prompts; 'n' aborts"
  else
    nope "TTY without KUBE_CONTEXT prompts; 'n' aborts (exit $rc)"
    sed 's/^/      /' "$TMP/tty" >&2
  fi
else
  echo "SKIP  TTY prompt (no python3)"
fi

# 7. Every script that changes the cluster sources the guard (manifests.sh only prints).
for f in "$ROOT"/scripts/*.sh; do
  base="$(basename "$f")"
  [[ "$base" == manifests.sh ]] && continue
  grep -Eq '^[^#]*\bkubectl\b' "$f" || grep -Eq '^\s*k\(\)' "$f" || continue
  if grep -q 'lib/kube-context.sh' "$f"; then pass "$base sources the guard"; else nope "$base runs kubectl without the guard"; fi
  if grep -Eq '^[^#]*[^d] kubectl --kubeconfig' "$f"; then nope "$base: use 'command kubectl --kubeconfig' (the wrapper adds --context)"; fi
done

exit "$fail"
