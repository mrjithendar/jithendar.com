# Python practice: code execution sandbox

How submitted Python is run for `/python-practice`, why it is built this way, and how to switch it on.
Status (2026-11-02): **built, tested locally, not deployed. Execution is off.** mk4 has no sandbox runtime yet.

## Threat model

Anyone with a free account can submit arbitrary Python. Assume every submission is hostile.

| Attacker goal | Example | Control |
|---|---|---|
| Escape to the node | kernel exploit, container breakout | gVisor (`runsc`): submissions talk to gVisor's user-space kernel, not the host kernel. One fresh sandbox (pod) per job. Non-root, no capabilities, seccomp, read-only root, no privilege escalation |
| Reach internal services | Postgres, Redis, the Kubernetes API, the site, Argo CD | `runsc` with `network = "none"`: the sandbox has only loopback. No DNS (`dnsPolicy: None` → 127.0.0.1). NetworkPolicies are present too, but **mk4's kindnet does not enforce them**, so they are not relied on |
| Steal credentials | service-account token, cloud metadata, env secrets | `automountServiceAccountToken: false`; no network (so no metadata endpoint); the only env var is the job payload; the sandbox service account has no permissions anyway |
| Read hidden tests / expected outputs | read files, inspect memory | The sandbox receives **inputs only**. Expected outputs never leave the web app; grading happens there (`lib/practice/evaluator.ts`). Hidden-test details (inputs, outputs, stdout) are never shown to users |
| Forge a passing result | print a fake result line, tamper with the runner | User code runs in a forked child with stdout/stderr redirected to pipes; it cannot write to the pod log. Even a forged result only contains outputs, which are compared server-side against values the code never saw |
| Exhaust resources | fork bombs, infinite loops, memory, output floods | per-test wall-clock kill (process group), `RLIMIT_AS/CPU/FSIZE/NOFILE`, pod CPU/memory limits, `activeDeadlineSeconds`, output caps, a namespace ResourceQuota (8 pods), per-user concurrency and rate limits, queue length limit, automatic 15-minute block after repeated resource-limit hits |
| Weaken the sandbox via the dispatcher | create a privileged pod | The dispatcher's Role allows only pods in `practice-sandbox`; a ValidatingAdmissionPolicy rejects any pod there that lacks the gVisor runtime, mounts a token, uses host namespaces, non-emptyDir volumes, privileges or missing limits |
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
browser ─► jithendar-com (Next.js)                       practice-exec                     practice-sandbox
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
3. **Apply the manifests:** `kubectl --context mk4 apply -k k8s/practice-executor`, then
   `scripts/create-practice-executor-secrets.sh mk4`. `ecr-pull` appears in both namespaces on its own (the
   `ecr-refresh` CronJob covers every namespace).
4. **Verify isolation:** `scripts/verify-practice-sandbox.sh` must print PASS for every check (gVisor kernel,
   loopback only, no token, API server / metadata / internet / DNS unreachable, admission rejects a plain pod).
5. **Let CI deploy:** `scripts/setup-practice-ci-deployer.sh` (stores secret `PRACTICE_CI_TOKEN`; it checks the
   token can patch the executor and cannot read Secrets, create pods or touch the site), then
   `gh variable set PRACTICE_EXECUTOR_DEPLOY --body true` and re-run the workflow on `master`. From then on
   every push that touches `executor/` or the practice catalog deploys: the `deploy` job pins both executor
   Deployments and the sandbox runtime to the digests it just pushed and waits for the rollout. It never applies
   manifests, so changes to `k8s/practice-executor/` (RBAC, admission, quota, network policy) are still applied
   by hand — then re-run the workflow, because a manual apply resets the images to `:latest`.
6. **Connect the site:** add `PRACTICE_EXECUTOR_URL=http://practice-executor.practice-exec` and
   `PRACTICE_EXECUTOR_TOKEN=…` to Secret `jithendar/jithendar-com-env`, run `./deploy.sh` (it also applies the
   site's egress rule to `practice-exec`), then switch on
   *Admin → Python practice → Settings → Allow running and submitting code*.
7. Optional: validate a problem from the admin editor (“Validate”) to see an end-to-end run.

To stop CI deploying, set `PRACTICE_EXECUTOR_DEPLOY` to anything but `true`; to revoke its access, delete Secret
`practice-exec/practice-ci-deployer-token`.

Rollback: switch execution off in the admin (instant; pages keep working), or delete the
`practice-exec`/`practice-sandbox` namespaces.

## Operating it

- Admin → Python practice shows executor reachability, queue depth, live dispatchers, verdicts in the last
  24 h and abuse signals. The executor logs one JSON line per job (`job.submitted`, `job.finished`, …) with a
  pseudonymous user id and the code's SHA-256 — never the code.
- Capacity: the dispatcher runs 4 jobs at a time; the quota allows 8 sandbox pods. A run costs one pod start
  (gVisor ≈ 1–3 s) plus the tests. Scale the dispatcher replicas and the quota together.
- Failed infrastructure (pod could not start, image pull error) is retried once, then reported to the user as
  “Could not run” without affecting their progress.
