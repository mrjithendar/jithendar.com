"""
Executor API (FastAPI). Callers: the jithendar.com web app only, authenticated with EXECUTOR_API_TOKEN.

  POST   /v1/jobs        submit (idempotent per user + idempotency_key) → 202 job
  GET    /v1/jobs/{id}   job status and, when done, the runner's result
  DELETE /v1/jobs/{id}   cancel
  GET    /v1/status      queue depth, live dispatchers, counters, configured runtimes
  GET    /healthz        process is up;  GET /readyz  Redis answers

This process never runs code and holds no Kubernetes credentials; the dispatcher (app/dispatcher.py) does the work.
Audit lines (JSON on stdout) record who ran what, by code hash and size, never the code itself. They carry the
caller's W3C trace id (the site sends `traceparent` to this service only), so Loki finds them next to the site's
lines for the same request.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import sys
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from . import config
from .models import JobRequest, JobView
from .queue import JobQueue, Rejected


def audit(event: str, **fields: Any) -> None:
    sys.stdout.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "level": "info", "service": "practice-executor", "event": event, **fields}) + "\n")
    sys.stdout.flush()


TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-[0-9a-f]{16}-[0-9a-f]{2}$")


def trace_id_of(request: Request) -> str | None:
    """The trace id from a well-formed `traceparent` header (never an all-zero id), else None."""
    m = TRACEPARENT.match(request.headers.get("traceparent", ""))
    return m.group(1) if m and m.group(1) != "0" * 32 else None


def create_app(settings: config.Settings | None = None, redis: Redis | None = None) -> FastAPI:
    s = settings or config.load()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.redis = redis or Redis.from_url(s.redis_url)
        app.state.queue = JobQueue(app.state.redis, s)
        yield
        if redis is None:
            await app.state.redis.aclose()

    app = FastAPI(title="practice-executor", version="1.0.0", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    def require_token(authorization: str = Header(default="")) -> None:
        expected = s.api_token
        given = authorization.removeprefix("Bearer ").strip()
        if not expected or not hmac.compare_digest(given.encode(), expected.encode()):
            raise HTTPException(status_code=401, detail="unauthorized")

    def q(request: Request) -> JobQueue:
        return request.app.state.queue

    @app.exception_handler(Rejected)
    async def _rejected(_: Request, exc: Rejected):
        headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else {}
        return JSONResponse({"error": exc.code, "message": exc.message}, status_code=exc.status, headers=headers)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz(request: Request) -> dict[str, str]:
        try:
            await request.app.state.redis.ping()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=503, detail="redis unavailable") from exc
        return {"status": "ready"}

    @app.post("/v1/jobs", status_code=202, dependencies=[Depends(require_token)])
    async def submit(req: JobRequest, request: Request) -> JobView:
        if len(req.code.encode()) > s.max_code_bytes:
            raise HTTPException(status_code=413, detail=f"code is larger than {s.max_code_bytes} bytes")
        if len(req.tests) > s.max_tests:
            raise HTTPException(status_code=413, detail=f"more than {s.max_tests} test cases")
        view, created = await q(request).submit(req)
        if created:
            audit(
                "job.submitted",
                job=view.id,
                user=req.user,
                purpose=req.purpose,
                runtime=req.runtime,
                tests=len(req.tests),
                code_sha256=hashlib.sha256(req.code.encode()).hexdigest(),
                code_bytes=len(req.code.encode()),
                trace_id=trace_id_of(request),
            )
        return view

    @app.get("/v1/jobs/{job_id}", dependencies=[Depends(require_token)])
    async def get_job(job_id: str, request: Request) -> JobView:
        view = await q(request).get(job_id)
        if not view:
            raise HTTPException(status_code=404, detail="not found")
        return view

    @app.delete("/v1/jobs/{job_id}", dependencies=[Depends(require_token)])
    async def cancel_job(job_id: str, request: Request) -> JobView:
        view = await q(request).cancel(job_id)
        if not view:
            raise HTTPException(status_code=404, detail="not found")
        audit("job.cancel_requested", job=job_id, trace_id=trace_id_of(request))
        return view

    @app.get("/v1/status", dependencies=[Depends(require_token)])
    async def status(request: Request) -> dict[str, Any]:
        return {
            **(await q(request).status()),
            "backend": s.backend,
            "runtimes": sorted(s.runtimes),
            "runtime_class": s.runtime_class,
            "limits": {"per_test_seconds": s.max_per_test_seconds, "total_seconds": s.max_total_seconds, "memory_mb": s.max_memory_mb},
        }

    return app


def run() -> None:
    import os

    import uvicorn

    uvicorn.run(create_app(), host="0.0.0.0", port=int(os.environ.get("PORT", "8080")), log_level="warning", access_log=False)  # noqa: S104


if __name__ == "__main__":
    run()
