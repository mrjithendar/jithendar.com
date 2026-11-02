# Python practice: code execution sandbox

How submitted Python is run for `/python-practice`, why it is built this way, and how to switch it on.
Status (2026-11-02): **built, tested locally, not deployed. Execution is off.** mk4 has no sandbox runtime yet.

## Threat model

Anyone with a free account can submit arbitrary Python. Assume every submission is hostile.

| Attacker goal | Example | Control |
|---|---|---|
| Escape to the node | kernel exploit, container breakout | gVisor (`runsc`): submissions talk to gVisor's user-space kernel, not the host kernel. One fresh sandbox (pod) per job. Non-root, no capabilities, seccomp, read-only root, no privilege escalation |
| Reach internal services | Postgres, Redis, the Kubernetes API, the site, Argo CD | `runsc` with `network = "none"`: the sandbox has only loopback. No DNS (`dnsPolicy: None` → 127.0.0.1). NetworkPolicies (`k8s/practice-executor/50-networkpolicies.yaml`) are a second layer: mk4's kindnet enforces them, so the site's egress rule must allow `app=practice-executor-api` |
| Steal credentials | service-account token, cloud metadata, env secrets | `automountServiceAccountToken: false`; no network (so no metadata endpoint); the only env var is the job payload; the sandbox service account has no permissions anyway |
| Read hidden tests / expected outputs | read files, inspect memory | The sandbox receives **inputs only**. Expected outputs never leave the web app; grading happens there (`lib/practice/evaluator.ts`). Hidden-test details (inputs, outputs, stdout) are never shown to users |
| Forge a passing result | print a fake result line, tamper with the runner | User code runs in a forked child with stdout/stderr redirected to pipes; it cannot write to the pod log. Even a forged result only contains outputs, which are compared server-side against values the code never saw |
| Exhaust resources | fork bombs, infinite loops, memory, output floods | per-test wall-clock kill (process group), `RLIMIT_AS/CPU/FSIZE/NOFILE`, pod CPU/memory limits, `activeDeadlineSeconds`, output caps, a ResourceQuota for sandbox pods (8 pods), per-user concurrency and rate limits, queue length limit, automatic 15-minute block after repeated resource-limit hits |
| Weaken the sandbox via the dispatcher | create a privileged pod, or a pod that mounts the site's Secrets | Everything runs in namespace `jithendar` with the site (owner decision 2026-11-02), and pod-create rights there would normally reach every Secret. ValidatingAdmissionPolicy `practice-sandbox-pods` therefore checks every pod the dispatcher creates (and every pod labelled or running as `practice-sandbox`): gVisor runtime, no token, emptyDir volumes only, no env from Secrets/ConfigMaps, no host namespaces, non-root, unprivileged, limits and a deadline. `practice-dispatcher-deletes` lets it delete only sandbox pods. It can still list pods and read pod logs in `jithendar` |
| Abuse the executor API | submit jobs directly | Bearer token known only to the site; the API itself never runs code and holds no Kubernetes credentials |

**Why not plain Docker or Python-level sandboxing?** Containers share the host kernel; a kernel bug is a
host compromise. Restricted-Python approaches (`exec` with filtered builtins, audit hooks) are routinely
bypassed. **Why gVisor rather than Kata?** Kata needs nested virtualisation (KVM) inside minikube's node
containers on an arm64 host; gVisor's `systrap` platform runs without KVM. Kata or Firecracker remain the
stronger option on a host with KVM.

**Known residual risks.** gVisor bugs (a sandbox escape would still need a second bug to leave the pod's
seccomp/namespace confinement); denial of service within the quota; the public repository contains the
seed problems' hidden tests and solutions, so they are hidden *in the product* but not secret — add private
hidden tests through the admin for anything that matters.

## Architecture

```
           ────────────────────────────── all in namespace jithendar ──────────────────────────────
browser ─► jithendar-com (Next.js)                       executor                           sandbox pods
           • auth, quotas, idempotent submission row     • practice-executor-api (FastAPI)  • one pod per job
           • builds job: code + test INPUTS ─────────────►  token auth, Redis queue,          RuntimeClass gvisor-nonet
           • polls job, GRADES outputs vs expected ◄──────  per-user limits, abuse block      python -I runner.py
           • progress/XP/badges exactly once             • practice-dispatcher ─────────────►  inputs → outputs (stdout)
                                                           creates pod, reads log, deletes    no network, no token
```

- Executor code: `executor/` (`app/main.py` API, `app/dispatcher.py`, `app/backends.py`, `sandbox/runner.py`).
- Manifests: `k8s/practice-executor/` — separate from `k8s/kustomization.yaml`, so `./deploy.sh` never deploys it.
- Result protocol: the runner prints one line `<<<RESULT:{nonce}>>>{json}`; per test: status
  (ok/error/timeout/memory/crash/skipped), normalised output (sets, big ints, tuples encoded losslessly),
  repr, stdout/stderr (capped), exception type/message/traceback (user frames only), duration, peak memory.
- Problems may ship a **prelude** (fake Boto3/Kubernetes clients, fake clocks, a `__harness__(fn, *args)`
  that calls the user's function). It runs inside the sandbox too.

## Turning it on (manual steps, in order)

1. **Install gVisor on every mk4 node** (on the mk4 host): `scripts/install-gvisor-mk4.sh` (dry run), then
   `scripts/install-gvisor-mk4.sh --apply`. It verifies the release checksums, adds the containerd handler
   `runsc-nonet` with `network = "none"` and restarts containerd node by node. *Not run by the agent.*
2. **ECR repositories** `practice-executor` and `practice-sandbox` and CI's push rights come from Terraform
   (`infra/`, see [infra/README.md](../../infra/README.md)); once it has applied, merge to `master` so `.github/workflows/ci-practice-executor.yml` builds the images (it also moves
   `practice-executor:latest`, which the manifests start from).
3. **Apply the manifests:** `kubectl --context mk4 apply -k k8s/practice-executor` (namespace `jithendar`),
   `kubectl --context mk4 apply -f k8s/80-ci-deployer.yaml` (lets the site's CI account roll out the executor),
   then `scripts/create-practice-executor-secrets.sh mk4`: it creates `practice-executor-env` and writes
   `PRACTICE_EXECUTOR_URL`/`PRACTICE_EXECUTOR_TOKEN` into `jithendar-com-env` directly (nothing to copy by hand).
   `ecr-pull` already exists in `jithendar`.
4. **Verify isolation:** `scripts/verify-practice-sandbox.sh` must print PASS for every check (gVisor kernel,
   loopback only, no token, API server / metadata / internet / DNS unreachable, a sandbox pod without gVisor is
   rejected, the dispatcher cannot start a pod reading the site's Secret or delete the site's pods).
5. **Let CI deploy:** `gh variable set PRACTICE_EXECUTOR_DEPLOY --body true`, then re-run the workflow on `master`.
   The `deploy` job signs in with the site's existing CI credentials (`MK4_CI_TOKEN`), pins both executor
   Deployments and the sandbox runtime to the digests it just pushed and waits for the rollout. From then on every
   push that touches `executor/` or the practice catalog deploys. It never applies manifests, so changes to
   `k8s/practice-executor/` are still applied by hand — then re-run the workflow, because a manual apply resets
   the images to `:latest`.
6. **Connect the site:** `./deploy.sh` (applies the site's egress rule to the executor and restarts it), then
   switch on *Admin → Python practice → Settings → Allow running and submitting code*.
7. Optional: validate a problem from the admin editor (“Validate”) to see an end-to-end run.

To stop CI deploying, set `PRACTICE_EXECUTOR_DEPLOY` to anything but `true`.

Rollback: switch execution off in the admin (instant; pages keep working), or
`kubectl --context mk4 delete -k k8s/practice-executor` (removes only the executor's objects; the site, its
database and Secrets stay).

## Operating it

- Admin → Python practice shows executor reachability, queue depth, live dispatchers, verdicts in the last
  24 h and abuse signals. The executor logs one JSON line per job (`job.submitted`, `job.finished`, …) with a
  pseudonymous user id and the code's SHA-256 — never the code.
- Capacity: the dispatcher runs 4 jobs at a time; the quota allows 8 sandbox pods. A run costs one pod start
  (gVisor ≈ 1–3 s) plus the tests. Scale the dispatcher replicas and the quota together.
- Failed infrastructure (pod could not start, image pull error) is retried once, then reported to the user as
  “Could not run” without affecting their progress.
