"""
Dispatcher: takes jobs from the Redis queue and runs each one in a fresh sandbox (app/backends.py).

  python -m app.dispatcher

Runs EXECUTOR_DISPATCHER_CONCURRENCY jobs at a time. Each running job's lease is renewed every few seconds;
if this process dies, another dispatcher's reaper requeues the job (at most EXECUTOR_MAX_ATTEMPTS runs in
total). Orphaned sandbox pods are deleted by the cleanup loop.
"""

from __future__ import annotations

import asyncio
import os
import signal
import socket
import time
from typing import Any

from redis.asyncio import Redis

from . import config
from .backends import Backend, JobCancelled, make_backend
from .main import audit
from .protocol import InfraError, PayloadTooLarge
from .queue import JobQueue


def summarize(result: dict[str, Any]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for t in result.get("tests", []):
        counts[t.get("status", "?")] = counts.get(t.get("status", "?"), 0) + 1
    return {"status": result.get("status"), "tests": counts}


async def run_one(queue: JobQueue, backend: Backend, job_id: str, req, attempt: int) -> None:
    started = time.monotonic()
    stop_renew = asyncio.Event()
    wanted = {"value": True}

    async def renew() -> None:
        while not stop_renew.is_set():
            wanted["value"] = await queue.renew(job_id)
            try:
                await asyncio.wait_for(stop_renew.wait(), timeout=5)
            except asyncio.TimeoutError:
                pass

    async def still_wanted() -> bool:
        return wanted["value"]

    renewer = asyncio.create_task(renew())
    try:
        result = await backend.execute(job_id, attempt, req, still_wanted)
        await queue.complete(job_id, result)
        audit("job.finished", job=job_id, user=req.user, attempt=attempt, ms=round((time.monotonic() - started) * 1000), **summarize(result))
    except JobCancelled:
        await queue.mark_cancelled(job_id)
        audit("job.cancelled", job=job_id, user=req.user)
    except PayloadTooLarge as exc:
        await queue.fail(job_id, str(exc), attempts=10**6)
        audit("job.rejected", job=job_id, user=req.user, reason=str(exc))
    except InfraError as exc:
        requeued = await queue.fail(job_id, str(exc), attempt)
        audit("job.infra_error", job=job_id, user=req.user, attempt=attempt, error=str(exc), requeued=requeued)
    except Exception as exc:  # noqa: BLE001 - never lose a job silently
        requeued = await queue.fail(job_id, f"unexpected dispatcher error: {type(exc).__name__}", attempt)
        audit("job.dispatcher_error", job=job_id, error=repr(exc)[:300], requeued=requeued)
    finally:
        stop_renew.set()
        await renewer


async def worker(queue: JobQueue, backend: Backend, stopping: asyncio.Event) -> None:
    while not stopping.is_set():
        taken = await queue.take(timeout=2.0)
        if taken:
            await run_one(queue, backend, *taken)


async def housekeeping(queue: JobQueue, backend: Backend, dispatcher_id: str, stopping: asyncio.Event) -> None:
    last_cleanup = 0.0
    while not stopping.is_set():
        await queue.heartbeat(dispatcher_id)
        for job_id in await queue.reap():
            audit("job.lease_expired", job=job_id)
        if time.monotonic() - last_cleanup > 60:
            last_cleanup = time.monotonic()
            removed = await backend.cleanup()
            if removed:
                audit("sandbox.cleanup", removed=removed)
        try:
            await asyncio.wait_for(stopping.wait(), timeout=10)
        except asyncio.TimeoutError:
            pass


async def main() -> None:
    s = config.load()
    redis = Redis.from_url(s.redis_url)
    queue = JobQueue(redis, s)
    backend = make_backend(s)
    dispatcher_id = f"{socket.gethostname()}-{os.getpid()}"
    stopping = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stopping.set)
    audit("dispatcher.started", id=dispatcher_id, backend=s.backend, concurrency=s.dispatcher_concurrency, runtimes=sorted(s.runtimes))
    tasks = [asyncio.create_task(worker(queue, backend, stopping)) for _ in range(s.dispatcher_concurrency)]
    tasks.append(asyncio.create_task(housekeeping(queue, backend, dispatcher_id, stopping)))
    await asyncio.gather(*tasks)
    await redis.aclose()
    audit("dispatcher.stopped", id=dispatcher_id)


if __name__ == "__main__":
    asyncio.run(main())
