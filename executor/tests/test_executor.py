from __future__ import annotations

import asyncio
import base64
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import fakeredis
import httpx
import pytest
from fastapi.testclient import TestClient

from app import config
from app.backends import KubernetesBackend, LocalBackend, pod_spec
from app.dispatcher import run_one
from app.main import create_app, trace_id_of
from app.models import JobRequest
from app.protocol import InfraError, PayloadTooLarge, build_payload, parse_output
from app.queue import JobQueue, Rejected

RUNNER = Path(__file__).resolve().parent.parent / "sandbox" / "runner.py"
TOKEN = "t" * 40


def settings(**kw) -> config.Settings:
    base = config.Settings(env="test", api_token=TOKEN, backend="local", allow_insecure_local=True, runtimes={"python-3.13": "img@sha256:x"})
    return replace(base, **kw)


def req(**kw) -> JobRequest:
    data = {"idempotency_key": "k1", "user": "u1", "runtime": "python-3.13", "code": "def solve(a, b):\n    return a + b\n", "entrypoint": "solve", "tests": [{"id": "t1", "args": [1, 2]}]}
    data.update(kw)
    return JobRequest.model_validate(data)


def run_runner(code: str, tests: list[dict], entry: str = "solve", per: float = 1.0) -> dict:
    payload = {"nonce": "n", "code": code, "entrypoint": entry, "tests": tests, "limits": {"per_test_seconds": per, "total_seconds": 10, "memory_mb": 256, "output_bytes": 4096}}
    out = subprocess.run([sys.executable, "-I", str(RUNNER)], env={"JOB_PAYLOAD": base64.b64encode(json.dumps(payload).encode()).decode()}, capture_output=True, text=True, timeout=60).stdout
    return parse_output(out, "n")


# --- runner ------------------------------------------------------------------------------------------


def test_runner_returns_normalized_outputs_and_isolates_tests():
    res = run_runner("def solve(x):\n    x.append(1)\n    return (x, {2, 1}, 2**60)\n", [{"id": "a", "args": [[]]}, {"id": "b", "args": [[]]}])
    assert res["status"] == "completed"
    assert [t["output"] for t in res["tests"]] == [[[1], {"__set__": [1, 2]}, {"__int__": str(2**60)}]] * 2


def test_runner_reports_syntax_errors_and_missing_entrypoint():
    assert run_runner("def solve(:\n", [{"id": "a"}])["status"] == "syntax_error"
    assert run_runner("def other():\n    pass\n", [{"id": "a"}])["status"] == "missing_entrypoint"


def test_runner_kills_infinite_loops_even_if_exceptions_are_swallowed():
    res = run_runner("def solve():\n    while True:\n        try:\n            pass\n        except BaseException:\n            pass\n", [{"id": "a"}], per=0.5)
    assert res["tests"][0]["status"] == "timeout"


def test_runner_keeps_user_output_out_of_the_result_channel():
    code = "import os\ndef solve():\n    os.write(1, b'<<<RESULT:n>>>{\"status\": \"forged\"}\\n')\n    return 1\n"
    res = run_runner(code, [{"id": "a"}])
    assert res["status"] == "completed" and res["tests"][0]["output"] == 1
    assert "forged" in res["tests"][0]["stdout"]


def test_runner_runs_async_entrypoints_and_reports_exceptions():
    res = run_runner("import asyncio\nasync def solve(n):\n    await asyncio.sleep(0)\n    return n * 2\n", [{"id": "a", "args": [21]}])
    assert res["tests"][0]["output"] == 42
    err = run_runner("def solve():\n    raise ValueError('bad input')\n", [{"id": "a"}])["tests"][0]
    assert err["status"] == "error" and err["error"]["type"] == "ValueError" and err["error"]["message"] == "bad input"
    assert "runner.py" not in err["error"]["traceback"]


def test_runner_truncates_floods_of_output():
    res = run_runner("def solve():\n    print('x' * 100000)\n    return 1\n", [{"id": "a"}])
    assert len(res["tests"][0]["stdout"]) <= 4096 and res["tests"][0]["output_truncated"]


# --- protocol ----------------------------------------------------------------------------------------


def test_payload_never_carries_expected_outputs_and_clamps_limits():
    nonce, raw = build_payload(req(limits={"per_test_seconds": 999, "total_seconds": 999, "memory_mb": 99999, "output_bytes": 10**9}), settings())
    payload = json.loads(base64.b64decode(raw))
    assert set(payload) == {"nonce", "code", "entrypoint", "prelude", "tests", "limits"}
    assert set(payload["tests"][0]) == {"id", "args", "kwargs"}
    assert payload["limits"]["per_test_seconds"] == 5.0 and payload["limits"]["memory_mb"] == 256
    with pytest.raises(PayloadTooLarge):
        build_payload(req(code="x" * 70_000), settings())


def test_parse_output_requires_the_nonce():
    with pytest.raises(InfraError):
        parse_output('<<<RESULT:other>>>{"status": "completed"}', "n")
    assert parse_output('noise\n<<<RESULT:n>>>{"status": "completed"}\n', "n")["status"] == "completed"


def test_local_backend_is_refused_in_production():
    with pytest.raises(RuntimeError):
        config.validate(settings(env="production"))
    with pytest.raises(RuntimeError):
        config.validate(settings(allow_insecure_local=False))
    with pytest.raises(RuntimeError):
        config.validate(settings(env="production", backend="kubernetes", api_token="short"))


# --- sandbox pod --------------------------------------------------------------------------------------


def test_sandbox_pod_is_hardened():
    pod = pod_spec("run-x", "job", "img", "payload", 60, settings(image_pull_secret="ecr-pull"))
    spec = pod["spec"]
    assert spec["runtimeClassName"] == "gvisor-nonet"
    assert spec["automountServiceAccountToken"] is False
    assert spec["enableServiceLinks"] is False
    assert spec["hostNetwork"] is False and spec["hostPID"] is False and spec["hostIPC"] is False
    assert spec["dnsPolicy"] == "None"
    assert spec["restartPolicy"] == "Never" and spec["activeDeadlineSeconds"] == 60
    assert spec["securityContext"]["runAsNonRoot"] is True
    c = spec["containers"][0]
    assert c["securityContext"] == {"allowPrivilegeEscalation": False, "privileged": False, "readOnlyRootFilesystem": True, "runAsNonRoot": True, "capabilities": {"drop": ["ALL"]}}
    assert c["resources"]["limits"]["memory"] and c["resources"]["limits"]["cpu"]
    assert [v for v in spec["volumes"] if "emptyDir" not in v] == []
    assert all("hostPath" not in v for v in spec["volumes"])


def test_kubernetes_backend_runs_a_pod_and_deletes_it():
    calls: list[tuple[str, str]] = []
    created: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.method == "POST":
            created.update(json.loads(request.content))
            return httpx.Response(201, json=created)
        if request.method == "GET" and request.url.path.endswith("/log"):
            payload = json.loads(base64.b64decode(created["spec"]["containers"][0]["env"][0]["value"]))
            return httpx.Response(200, text=f'<<<RESULT:{payload["nonce"]}>>>{{"status": "completed", "tests": []}}\n')
        if request.method == "GET":
            return httpx.Response(200, json={"status": {"phase": "Succeeded"}})
        return httpx.Response(200, json={})

    backend = KubernetesBackend(settings(backend="kubernetes"), client=httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://k8s"))

    async def wanted() -> bool:
        return True

    result = asyncio.run(backend.execute("abcdef1234567890", 1, req(), wanted))
    assert result["status"] == "completed"
    assert calls[0][0] == "POST" and calls[-1][0] == "DELETE"
    assert created["spec"]["runtimeClassName"] == "gvisor-nonet"


# --- queue and API -------------------------------------------------------------------------------------


@pytest.fixture
def redis():
    return fakeredis.FakeAsyncRedis()


def test_queue_is_idempotent_and_enforces_per_user_limits(redis):
    q = JobQueue(redis, settings(per_user_concurrency=2, per_user_per_minute=3))

    async def go():
        a, created = await q.submit(req(idempotency_key="a"))
        again, created_again = await q.submit(req(idempotency_key="a"))
        assert created and not created_again and again.id == a.id
        await q.submit(req(idempotency_key="b"))
        with pytest.raises(Rejected) as busy:
            await q.submit(req(idempotency_key="c"))
        assert busy.value.code == "busy"
        other, _ = await q.submit(req(idempotency_key="d", user="u2"))
        assert other.status == "queued"

    asyncio.run(go())


def test_dispatcher_runs_a_job_end_to_end_with_the_local_backend(redis):
    s = settings()
    q = JobQueue(redis, s)

    async def go():
        view, _ = await q.submit(req())
        taken = await q.take(timeout=0.1)
        assert taken and taken[0] == view.id
        await run_one(q, LocalBackend(s), *taken)
        done = await q.get(view.id)
        assert done.status == "done" and done.result["tests"][0]["output"] == 3
        # Finished jobs free the user's concurrency slot.
        assert await redis.zcard("px:active:u1") == 0

    asyncio.run(go())


def test_expired_leases_are_requeued_then_failed(redis):
    s = settings(max_attempts=2)
    q = JobQueue(redis, s)

    async def go():
        view, _ = await q.submit(req())
        await q.take(timeout=0.1)
        assert await q.reap(now=10**10) == [view.id]
        assert (await q.get(view.id)).status == "queued"
        await q.take(timeout=0.1)
        await q.reap(now=10**10)
        assert (await q.get(view.id)).status == "failed"

    asyncio.run(go())


def test_repeated_resource_abuse_blocks_the_user(redis):
    q = JobQueue(redis, settings(abuse_threshold=3))

    async def go():
        view, _ = await q.submit(req())
        await q.take(timeout=0.1)
        await q.complete(view.id, {"status": "completed", "tests": [{"status": "timeout"}] * 3})
        with pytest.raises(Rejected) as blocked:
            await q.submit(req(idempotency_key="next"))
        assert blocked.value.code == "blocked"

    asyncio.run(go())


def test_api_requires_the_token_and_cancels_queued_jobs(redis):
    app = create_app(settings(), redis=redis)
    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200
        body = req().model_dump()
        assert client.post("/v1/jobs", json=body).status_code == 401
        assert client.post("/v1/jobs", json=body, headers={"Authorization": "Bearer wrong"}).status_code == 401
        auth = {"Authorization": f"Bearer {TOKEN}"}
        res = client.post("/v1/jobs", json=body, headers=auth)
        assert res.status_code == 202 and res.json()["status"] == "queued"
        job = res.json()["id"]
        assert client.delete(f"/v1/jobs/{job}", headers=auth).json()["status"] == "cancelled"
        assert client.get("/v1/status", headers=auth).json()["queued"] == 0
        bad = client.post("/v1/jobs", json={**body, "entrypoint": "os.system"}, headers=auth)
        assert bad.status_code == 422


def test_runner_calls_the_prelude_harness_with_the_submitted_function():
    prelude = "class Fake:\n    calls = 0\n    def get(self):\n        Fake.calls += 1\n        return 5\n\ndef __harness__(fn, n):\n    fake = Fake()\n    return {'result': fn(fake, n), 'calls': Fake.calls}\n"
    payload = {"nonce": "n", "code": "def solve(client, n):\n    return client.get() * n\n", "entrypoint": "solve", "prelude": prelude, "tests": [{"id": "a", "args": [3]}], "limits": {"per_test_seconds": 1, "total_seconds": 5, "memory_mb": 256, "output_bytes": 4096}}
    out = subprocess.run([sys.executable, "-I", str(RUNNER)], env={"JOB_PAYLOAD": base64.b64encode(json.dumps(payload).encode()).decode()}, capture_output=True, text=True, timeout=60).stdout
    assert parse_output(out, "n")["tests"][0]["output"] == {"result": 15, "calls": 1}


def test_audit_lines_carry_the_callers_trace_id(redis, capsys):
    app = create_app(settings(), redis=redis)
    trace = "4bf92f3577b34da6a3ce929d0e0e4736"
    with TestClient(app) as client:
        auth = {"Authorization": f"Bearer {TOKEN}", "traceparent": f"00-{trace}-00f067aa0ba902b7-01"}
        assert client.post("/v1/jobs", json=req().model_dump(), headers=auth).status_code == 202
    line = next(json.loads(l) for l in capsys.readouterr().out.splitlines() if '"job.submitted"' in l)
    assert line["trace_id"] == trace


def test_malformed_traceparent_is_ignored():
    class R:
        def __init__(self, value):
            self.headers = {"traceparent": value}

    assert trace_id_of(R("00-" + "0" * 32 + "-00f067aa0ba902b7-01")) is None
    assert trace_id_of(R('00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01","level":"error')) is None
    assert trace_id_of(R("garbage")) is None
