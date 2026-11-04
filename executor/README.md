# practice-executor

Sandboxed Python execution for jithendar.com/python-practice. Threat model, architecture and the deployment
runbook: [../www/docs/PYTHON_PRACTICE_EXECUTOR.md](../www/docs/PYTHON_PRACTICE_EXECUTOR.md).

| Path | What |
|---|---|
| `app/main.py` | FastAPI API (`/v1/jobs`, `/v1/status`, `/healthz`, `/readyz`); token auth; never runs code |
| `app/queue.py` | Redis queue: idempotency, per-user concurrency and rate limits, leases, abuse blocking |
| `app/dispatcher.py` | Takes jobs, runs each in a fresh sandbox, renews leases, requeues on dispatcher death |
| `app/backends.py` | `KubernetesBackend` (pod per job, gVisor, hardened spec) and `LocalBackend` (development only) |
| `sandbox/runner.py` | Runs inside the sandbox: forks per test, limits, captures output, prints one result line |
| `tools/build_problems.py` | Builds and validates `www/content/python-practice/catalog.generated.json` |

## Configuration (environment)

| Variable | Default | |
|---|---|---|
| `EXECUTOR_ENV` | development | `production` enforces a 32+ character token and refuses the local backend |
| `EXECUTOR_API_TOKEN` | — | shared with the site (`PRACTICE_EXECUTOR_TOKEN`) |
| `EXECUTOR_REDIS_URL` | redis://localhost:6379/0 | |
| `EXECUTOR_BACKEND` | kubernetes | `local` runs code on this machine **without isolation**; needs `EXECUTOR_ALLOW_INSECURE_LOCAL=yes-i-understand` |
| `EXECUTOR_RUNTIMES` | `{}` | JSON: runtime id → sandbox image |
| `EXECUTOR_RUNTIME_CLASS` | gvisor-nonet | |
| `EXECUTOR_SANDBOX_NAMESPACE` | practice-sandbox | mk4 sets `jithendar` (`minikube/practice-executor-40-executor.yaml`) |
| `EXECUTOR_MAX_PER_TEST_SECONDS` / `_TOTAL_SECONDS` / `_MEMORY_MB` | 5 / 20 / 256 | caps on what callers may request |
| `EXECUTOR_PER_USER_CONCURRENCY` / `_PER_MINUTE` | 2 / 30 | |
| `EXECUTOR_MAX_QUEUE` | 200 | 503 above this |
| `EXECUTOR_ABUSE_THRESHOLD` | 25 | resource-limit hits per 10 min before a 15-minute block |
| `EXECUTOR_DISPATCHER_CONCURRENCY` | 4 | jobs per dispatcher |

## Development

```sh
python -m venv .venv && .venv/bin/pip install ".[test]" pyyaml
.venv/bin/python -m pytest -q                       # 17 tests, uses fakeredis and the real runner
python tools/build_problems.py --check              # validate the problem catalog (from the repository root: executor/tools/…)
```
