"""
Redis-backed job queue with admission control.

Keys (prefix px:):
  job:{id}            hash: status, request, result, error, created_at, started_at, finished_at, attempts, user, cancel
  idem:{user}:{key}   job id for an idempotency key (a retried request returns the same job)
  queue               list of queued job ids (LPUSH in, BLMOVE out to `processing`)
  processing          list of job ids a dispatcher has taken
  leases              zset job id → lease expiry; an expired lease means the dispatcher died, so the job is requeued
  active:{user}       zset job id → start time (per-user concurrency)
  rl:{user}:{minute}  counter (per-user rate limit)
  abuse:{user}        zset of timestamps of runs that hit a resource limit
  block:{user}        set while a user is temporarily blocked
  dispatchers         hash dispatcher id → last heartbeat
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from redis.asyncio import Redis

from .config import Settings
from .models import JobRequest, JobView

P = "px:"


class Rejected(Exception):
    def __init__(self, status: int, code: str, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.retry_after = retry_after


def _f(v: Any) -> float | None:
    return float(v) if v not in (None, "", b"") else None


class JobQueue:
    def __init__(self, redis: Redis, settings: Settings):
        self.r = redis
        self.s = settings

    # --- submission --------------------------------------------------------------------------------

    async def submit(self, req: JobRequest, now: float | None = None) -> tuple[JobView, bool]:
        """(job, created). Raises Rejected when the caller must back off."""
        now = now or time.time()
        user = req.user
        if req.runtime not in self.s.runtimes and self.s.backend == "kubernetes":
            raise Rejected(400, "unknown_runtime", f"Runtime {req.runtime!r} is not configured.")
        if await self.r.exists(f"{P}block:{user}"):
            ttl = await self.r.ttl(f"{P}block:{user}")
            raise Rejected(429, "blocked", "Too many runs hit resource limits. Try again later.", max(ttl, 1))

        idem = f"{P}idem:{user}:{req.idempotency_key}"
        existing = await self.r.get(idem)
        if existing:
            view = await self.get(existing.decode() if isinstance(existing, bytes) else existing)
            if view:
                return view, False

        minute = int(now // 60)
        rl = f"{P}rl:{user}:{minute}"
        count = await self.r.incr(rl)
        if count == 1:
            await self.r.expire(rl, 120)
        if count > self.s.per_user_per_minute:
            raise Rejected(429, "rate_limited", "Too many runs this minute.", 60 - int(now % 60))

        active = f"{P}active:{user}"
        await self.r.zremrangebyscore(active, 0, now - self.s.lease_seconds * self.s.max_attempts - 60)
        if await self.r.zcard(active) >= self.s.per_user_concurrency:
            raise Rejected(429, "busy", "Wait for your running code to finish.", 2)
        if await self.r.llen(f"{P}queue") >= self.s.max_queue:
            raise Rejected(503, "queue_full", "The execution queue is full. Try again shortly.", 5)

        job_id = uuid.uuid4().hex
        if not await self.r.set(idem, job_id, nx=True, ex=self.s.result_ttl_seconds):
            other = await self.r.get(idem)
            view = await self.get(other.decode() if isinstance(other, bytes) else other)
            if view:
                return view, False
        pipe = self.r.pipeline(transaction=True)
        pipe.hset(
            f"{P}job:{job_id}",
            mapping={"status": "queued", "request": req.model_dump_json(), "created_at": now, "attempts": 0, "user": user, "purpose": req.purpose},
        )
        pipe.expire(f"{P}job:{job_id}", self.s.result_ttl_seconds * 2)
        pipe.zadd(active, {job_id: now})
        pipe.expire(active, self.s.result_ttl_seconds)
        pipe.lpush(f"{P}queue", job_id)
        pipe.hincrby(f"{P}stats", "submitted", 1)
        await pipe.execute()
        view = await self.get(job_id)
        assert view is not None
        return view, True

    async def get(self, job_id: str) -> JobView | None:
        raw = await self.r.hgetall(f"{P}job:{job_id}")
        if not raw:
            return None
        h = {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in raw.items()}
        position = None
        if h["status"] == "queued":
            ids = await self.r.lrange(f"{P}queue", 0, -1)
            ids = [i.decode() if isinstance(i, bytes) else i for i in ids]
            # LPUSH in, taken from the right: the rightmost job runs next.
            position = len(ids) - ids.index(job_id) if job_id in ids else None
        return JobView(
            id=job_id,
            status=h["status"],  # type: ignore[arg-type]
            created_at=float(h["created_at"]),
            started_at=_f(h.get("started_at")),
            finished_at=_f(h.get("finished_at")),
            queue_position=position,
            result=json.loads(h["result"]) if h.get("result") else None,
            error=h.get("error") or None,
        )

    async def cancel(self, job_id: str) -> JobView | None:
        view = await self.get(job_id)
        if not view or view.status in ("done", "failed", "cancelled"):
            return view
        await self.r.hset(f"{P}job:{job_id}", "cancel", "1")
        if view.status == "queued" and await self.r.lrem(f"{P}queue", 0, job_id):
            await self._finish(job_id, "cancelled", error="cancelled before it started")
        return await self.get(job_id)

    # --- dispatcher side --------------------------------------------------------------------------

    async def take(self, timeout: float = 2.0) -> tuple[str, JobRequest, int] | None:
        raw = await self.r.blmove(f"{P}queue", f"{P}processing", timeout, "RIGHT", "LEFT")
        if raw is None:
            return None
        job_id = raw.decode() if isinstance(raw, bytes) else raw
        h = await self.r.hgetall(f"{P}job:{job_id}")
        h = {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in h.items()}
        if not h or h.get("cancel") == "1" or h.get("status") != "queued":
            await self.r.lrem(f"{P}processing", 0, job_id)
            if h and h.get("status") in ("queued", "running"):
                await self._finish(job_id, "cancelled", error="cancelled")
            return None
        attempts = int(h.get("attempts", 0)) + 1
        now = time.time()
        pipe = self.r.pipeline(transaction=True)
        pipe.hset(f"{P}job:{job_id}", mapping={"status": "running", "started_at": now, "attempts": attempts})
        pipe.zadd(f"{P}leases", {job_id: now + self.s.lease_seconds})
        await pipe.execute()
        return job_id, JobRequest.model_validate_json(h["request"]), attempts

    async def renew(self, job_id: str) -> bool:
        """Extend the lease; False when the job was cancelled meanwhile."""
        await self.r.zadd(f"{P}leases", {job_id: time.time() + self.s.lease_seconds}, xx=True)
        return (await self.r.hget(f"{P}job:{job_id}", "cancel")) not in (b"1", "1")

    async def complete(self, job_id: str, result: dict[str, Any]) -> None:
        await self._finish(job_id, "done", result=result)
        user = await self.r.hget(f"{P}job:{job_id}", "user")
        if user:
            await self._record_abuse(user.decode() if isinstance(user, bytes) else user, result)

    async def fail(self, job_id: str, error: str, attempts: int) -> bool:
        """Retry an infrastructure failure once more, or give up. True when requeued."""
        if attempts < self.s.max_attempts and (await self.r.hget(f"{P}job:{job_id}", "cancel")) not in (b"1", "1"):
            pipe = self.r.pipeline(transaction=True)
            pipe.hset(f"{P}job:{job_id}", mapping={"status": "queued", "error": error})
            pipe.zrem(f"{P}leases", job_id)
            pipe.lrem(f"{P}processing", 0, job_id)
            pipe.rpush(f"{P}queue", job_id)  # to the front: it has waited already
            pipe.hincrby(f"{P}stats", "retried", 1)
            await pipe.execute()
            return True
        await self._finish(job_id, "failed", error=error)
        return False

    async def mark_cancelled(self, job_id: str) -> None:
        await self._finish(job_id, "cancelled", error="cancelled while running")

    async def _finish(self, job_id: str, status: str, result: dict[str, Any] | None = None, error: str | None = None) -> None:
        key = f"{P}job:{job_id}"
        user = await self.r.hget(key, "user")
        pipe = self.r.pipeline(transaction=True)
        mapping: dict[str, Any] = {"status": status, "finished_at": time.time()}
        if result is not None:
            mapping["result"] = json.dumps(result)
        if error is not None:
            mapping["error"] = error
        pipe.hset(key, mapping=mapping)
        pipe.expire(key, self.s.result_ttl_seconds)
        pipe.zrem(f"{P}leases", job_id)
        pipe.lrem(f"{P}processing", 0, job_id)
        if user:
            pipe.zrem(f"{P}active:{user.decode() if isinstance(user, bytes) else user}", job_id)
        pipe.hincrby(f"{P}stats", status, 1)
        await pipe.execute()

    async def _record_abuse(self, user: str, result: dict[str, Any]) -> None:
        """Runs that hit the time or memory limit or flood output count towards a temporary block."""
        hits = sum(
            1
            for t in result.get("tests", [])
            if t.get("status") in ("timeout", "memory") or (t.get("error") or {}).get("type") == "OutputLimitExceeded"
        )
        if not hits:
            return
        now = time.time()
        key = f"{P}abuse:{user}"
        pipe = self.r.pipeline(transaction=True)
        pipe.zadd(key, {f"{now}:{i}": now for i in range(hits)})
        pipe.zremrangebyscore(key, 0, now - self.s.abuse_window_seconds)
        pipe.zcard(key)
        pipe.expire(key, self.s.abuse_window_seconds)
        *_, count, _ = await pipe.execute()
        if count >= self.s.abuse_threshold:
            await self.r.set(f"{P}block:{user}", "1", ex=self.s.abuse_block_seconds)
            await self.r.delete(key)
            await self.r.hincrby(f"{P}stats", "blocked_users", 1)

    async def reap(self, now: float | None = None) -> list[str]:
        """Requeue (or fail) jobs whose dispatcher stopped renewing the lease."""
        now = now or time.time()
        expired = await self.r.zrangebyscore(f"{P}leases", 0, now)
        out = []
        for raw in expired:
            job_id = raw.decode() if isinstance(raw, bytes) else raw
            attempts = int(await self.r.hget(f"{P}job:{job_id}", "attempts") or 0)
            await self.fail(job_id, "dispatcher stopped responding", attempts)
            out.append(job_id)
        return out

    async def heartbeat(self, dispatcher_id: str) -> None:
        await self.r.hset(f"{P}dispatchers", dispatcher_id, time.time())

    async def status(self) -> dict[str, Any]:
        now = time.time()
        beats = await self.r.hgetall(f"{P}dispatchers")
        alive = {}
        for k, v in beats.items():
            key = k.decode() if isinstance(k, bytes) else k
            age = now - float(v)
            if age > 3600:
                await self.r.hdel(f"{P}dispatchers", key)
            elif age < 30:
                alive[key] = round(age, 1)
        stats = {(k.decode() if isinstance(k, bytes) else k): int(v) for k, v in (await self.r.hgetall(f"{P}stats")).items()}
        return {
            "queued": await self.r.llen(f"{P}queue"),
            "running": await self.r.zcard(f"{P}leases"),
            "dispatchers": alive,
            "stats": stats,
        }
