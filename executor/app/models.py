"""Request and result shapes of the executor API (mirrored by www/src/lib/practice/executor-client.ts)."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ID = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")


class TestInput(BaseModel):
    # Opaque id chosen by the caller; the sandbox never learns whether a test is public or hidden.
    id: str
    args: list[Any] = Field(default_factory=list)
    kwargs: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        if not ID.match(v):
            raise ValueError("invalid test id")
        return v


class Limits(BaseModel):
    per_test_seconds: float = 2.0
    total_seconds: float = 10.0
    memory_mb: int = 256
    output_bytes: int = 16_384


class JobRequest(BaseModel):
    # Caller-chosen idempotency key: a retried request returns the existing job instead of running twice.
    idempotency_key: str
    # Pseudonymous user id (the web app sends an HMAC of its user id); used for quotas and abuse detection only.
    user: str
    runtime: str
    code: str
    entrypoint: str
    # Problem-provided helper code run before the submission (fakes, harness); see sandbox/runner.py.
    prelude: str = ""
    tests: list[TestInput]
    limits: Limits = Field(default_factory=Limits)
    purpose: Literal["run", "submit", "validate"] = "run"

    @field_validator("idempotency_key", "user")
    @classmethod
    def _ids(cls, v: str) -> str:
        if not ID.match(v):
            raise ValueError("must be 1-64 characters of A-Z, a-z, 0-9, _ or -")
        return v

    @field_validator("entrypoint")
    @classmethod
    def _entry(cls, v: str) -> str:
        if not IDENT.match(v):
            raise ValueError("entrypoint must be a Python identifier")
        return v


JobStatus = Literal["queued", "running", "done", "failed", "cancelled"]


class JobView(BaseModel):
    id: str
    status: JobStatus
    created_at: float
    started_at: float | None = None
    finished_at: float | None = None
    queue_position: int | None = None
    # Present when status is done: the runner's result (see sandbox/runner.py).
    result: dict[str, Any] | None = None
    # Present when status is failed: an infrastructure problem, not a problem with the submitted code.
    error: str | None = None
