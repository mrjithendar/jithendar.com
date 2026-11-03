"""
Where a job runs.

KubernetesBackend (production): one short-lived pod per job in the sandbox namespace, under the gVisor
RuntimeClass whose runsc is configured with network=none. The pod has no service-account token, no volumes
except a small in-memory /tmp, a read-only root filesystem, no capabilities, a non-root user and a hard
deadline. The dispatcher talks to the API server with its own service account, which may only create, read
and delete pods (and read pod logs) in the sandbox namespace.

LocalBackend (development only): runs the runner as a subprocess on this machine. No isolation at all;
config.validate() refuses it in production and without an explicit opt-in.
"""

from __future__ import annotations

import asyncio
import os
import secrets
import ssl
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable, Protocol

import httpx

from .config import Settings
from .models import JobRequest
from .protocol import InfraError, build_payload, clamp_limits, parse_output

Cancelled = Callable[[], Awaitable[bool]]

SA_DIR = Path("/var/run/secrets/kubernetes.io/serviceaccount")
RUNNER = Path(__file__).resolve().parent.parent / "sandbox" / "runner.py"


class JobCancelled(Exception):
    pass


class Backend(Protocol):
    async def execute(self, job_id: str, attempt: int, req: JobRequest, still_wanted: Cancelled) -> dict[str, Any]: ...

    async def cleanup(self) -> int: ...


def pod_spec(name: str, job_id: str, image: str, payload: str, deadline: int, s: Settings) -> dict[str, Any]:
    """The sandbox pod. Kept as a pure function so tests can assert every hardening field."""
    spec: dict[str, Any] = {
        "runtimeClassName": s.runtime_class,
        "serviceAccountName": s.sandbox_service_account,
        "automountServiceAccountToken": False,
        "enableServiceLinks": False,
        "restartPolicy": "Never",
        "activeDeadlineSeconds": deadline,
        "terminationGracePeriodSeconds": 0,
        "hostNetwork": False,
        "hostPID": False,
        "hostIPC": False,
        "shareProcessNamespace": False,
        # No cluster DNS: the sandbox has no network (runsc network=none), and nothing should even look names up.
        "dnsPolicy": "None",
        "dnsConfig": {"nameservers": ["127.0.0.1"]},
        "securityContext": {
            "runAsNonRoot": True,
            "runAsUser": 65532,
            "runAsGroup": 65532,
            "seccompProfile": {"type": "RuntimeDefault"},
        },
        "containers": [
            {
                "name": "run",
                "image": image,
                "imagePullPolicy": "Always",
                "env": [{"name": "JOB_PAYLOAD", "value": payload}, {"name": "PYTHONHASHSEED", "value": "0"}],
                "resources": {
                    "limits": {"cpu": s.sandbox_cpu, "memory": s.sandbox_memory, "ephemeral-storage": "32Mi"},
                    "requests": {"cpu": "100m", "memory": "128Mi", "ephemeral-storage": "16Mi"},
                },
                "securityContext": {
                    "allowPrivilegeEscalation": False,
                    "privileged": False,
                    "readOnlyRootFilesystem": True,
                    "runAsNonRoot": True,
                    "capabilities": {"drop": ["ALL"]},
                },
                "volumeMounts": [{"name": "tmp", "mountPath": "/tmp"}],
            }
        ],
        "volumes": [{"name": "tmp", "emptyDir": {"medium": "Memory", "sizeLimit": "16Mi"}}],
    }
    if s.image_pull_secret:
        spec["imagePullSecrets"] = [{"name": s.image_pull_secret}]
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": name,
            "namespace": s.sandbox_namespace,
            "labels": {"app.kubernetes.io/name": "practice-sandbox", "practice.jithendar.com/job": job_id},
        },
        "spec": spec,
    }


class KubernetesBackend:
    def __init__(self, s: Settings, client: httpx.AsyncClient | None = None):
        self.s = s
        if client is None:
            host = os.environ["KUBERNETES_SERVICE_HOST"]
            port = os.environ.get("KUBERNETES_SERVICE_PORT", "443")
            ctx = ssl.create_default_context(cafile=str(SA_DIR / "ca.crt"))
            client = httpx.AsyncClient(base_url=f"https://{host}:{port}", verify=ctx, timeout=15.0)
        self.http = client
        self.ns = s.sandbox_namespace

    def _headers(self) -> dict[str, str]:
        # Re-read every time: projected tokens are rotated by the kubelet.
        token_file = SA_DIR / "token"
        return {"Authorization": f"Bearer {token_file.read_text().strip()}"} if token_file.exists() else {}

    async def execute(self, job_id: str, attempt: int, req: JobRequest, still_wanted: Cancelled) -> dict[str, Any]:
        image = self.s.runtimes.get(req.runtime)
        if not image:
            raise InfraError(f"runtime {req.runtime} is not configured")
        nonce, payload = build_payload(req, self.s)
        limits = clamp_limits(req, self.s)
        # Load + one run per test, each bounded by per_test_seconds, plus the overall budget and slack.
        run_budget = min(limits["total_seconds"] + 2 * limits["per_test_seconds"], self.s.max_total_seconds + 10)
        name = f"run-{job_id[:12]}-{attempt}-{secrets.token_hex(3)}"
        body = pod_spec(name, job_id, image, payload, int(run_budget + self.s.pod_start_timeout), self.s)
        base = f"/api/v1/namespaces/{self.ns}/pods"
        res = await self.http.post(base, json=body, headers=self._headers())
        if res.status_code == 403 and "exceeded quota" in res.text:
            raise InfraError("sandbox capacity reached")
        if res.status_code >= 300:
            raise InfraError(f"pod create failed: HTTP {res.status_code}")
        try:
            phase = await self._wait(name, run_budget, still_wanted)
            log = await self.http.get(f"{base}/{name}/log", params={"container": "run", "limitBytes": 4 * 1024 * 1024}, headers=self._headers())
            if log.status_code >= 300:
                raise InfraError(f"log read failed: HTTP {log.status_code}")
            try:
                return parse_output(log.text, nonce)
            except InfraError:
                if phase == "DeadlineExceeded":
                    return {"status": "completed", "tests": [{"id": t.id, "status": "timeout"} for t in req.tests], "note": "sandbox deadline exceeded"}
                if phase == "OOMKilled":
                    return {"status": "completed", "tests": [{"id": t.id, "status": "memory"} for t in req.tests], "note": "sandbox memory limit exceeded"}
                raise
        finally:
            await self.http.delete(f"{base}/{name}", params={"gracePeriodSeconds": 0}, headers=self._headers())

    async def _wait(self, name: str, run_budget: float, still_wanted: Cancelled) -> str:
        """Poll until the pod finishes. Returns Succeeded, Failed, DeadlineExceeded or OOMKilled."""
        loop = asyncio.get_running_loop()
        start_deadline = loop.time() + self.s.pod_start_timeout
        run_deadline: float | None = None
        delay = 0.15
        while True:
            if not await still_wanted():
                raise JobCancelled()
            res = await self.http.get(f"/api/v1/namespaces/{self.ns}/pods/{name}", headers=self._headers())
            if res.status_code == 404:
                raise InfraError("sandbox pod disappeared")
            pod = res.json()
            status = pod.get("status", {})
            phase = status.get("phase")
            if status.get("reason") == "DeadlineExceeded":
                return "DeadlineExceeded"
            for cs in status.get("containerStatuses", []) or []:
                term = (cs.get("state") or {}).get("terminated")
                if term and term.get("reason") == "OOMKilled":
                    return "OOMKilled"
                waiting = (cs.get("state") or {}).get("waiting") or {}
                if waiting.get("reason") in ("ErrImagePull", "ImagePullBackOff", "CreateContainerConfigError", "InvalidImageName"):
                    raise InfraError(f"sandbox could not start: {waiting.get('reason')}")
                if cs.get("state", {}).get("running") and run_deadline is None:
                    run_deadline = loop.time() + run_budget
            if phase in ("Succeeded", "Failed"):
                return phase
            now = loop.time()
            if run_deadline is None and now > start_deadline:
                raise InfraError("sandbox did not start in time (is the gVisor RuntimeClass installed?)")
            if run_deadline is not None and now > run_deadline:
                return "DeadlineExceeded"
            await asyncio.sleep(delay)
            delay = min(delay * 1.5, 1.0)

    async def cleanup(self) -> int:
        """Delete sandbox pods left behind by a crashed dispatcher (finished, or older than any job can run)."""
        res = await self.http.get(f"/api/v1/namespaces/{self.ns}/pods", params={"labelSelector": "app.kubernetes.io/name=practice-sandbox"}, headers=self._headers())
        if res.status_code >= 300:
            return 0
        from datetime import datetime, timezone

        removed = 0
        now = datetime.now(timezone.utc)
        max_age = self.s.pod_start_timeout + self.s.max_total_seconds * 2 + 60
        for pod in res.json().get("items", []):
            created = datetime.fromisoformat(pod["metadata"]["creationTimestamp"].replace("Z", "+00:00"))
            if pod.get("status", {}).get("phase") in ("Succeeded", "Failed") or (now - created).total_seconds() > max_age:
                await self.http.delete(f"/api/v1/namespaces/{self.ns}/pods/{pod['metadata']['name']}", params={"gracePeriodSeconds": 0}, headers=self._headers())
                removed += 1
        return removed


class LocalBackend:
    """Development only. Runs the runner on this machine with no isolation (see module docstring)."""

    def __init__(self, s: Settings):
        if s.production or not s.allow_insecure_local:
            raise RuntimeError("LocalBackend is for development only")
        self.s = s

    async def execute(self, job_id: str, attempt: int, req: JobRequest, still_wanted: Cancelled) -> dict[str, Any]:
        nonce, payload = build_payload(req, self.s)
        env = {"JOB_PAYLOAD": payload, "PYTHONHASHSEED": "0", "PATH": "/usr/bin:/bin"}
        proc = await asyncio.create_subprocess_exec(sys.executable, "-I", str(RUNNER), env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        limits = clamp_limits(req, self.s)
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=limits["total_seconds"] + 2 * limits["per_test_seconds"] + 5)
        except asyncio.TimeoutError as exc:
            proc.kill()
            raise InfraError("local runner timed out") from exc
        return parse_output(out.decode("utf-8", "replace"), nonce)

    async def cleanup(self) -> int:
        return 0


def make_backend(s: Settings) -> Backend:
    return LocalBackend(s) if s.backend == "local" else KubernetesBackend(s)
