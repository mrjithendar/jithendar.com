"""Payload for the sandbox runner and parsing of its output (the runner lives in sandbox/runner.py)."""

from __future__ import annotations

import base64
import json
import secrets
from typing import Any

from .config import Settings
from .models import JobRequest

RESULT_PREFIX = "<<<RESULT:"


class InfraError(Exception):
    """The job could not be run (sandbox did not start, crashed, or answered nonsense). Not the code's fault."""


class PayloadTooLarge(ValueError):
    pass


def clamp_limits(req: JobRequest, s: Settings) -> dict[str, Any]:
    lim = req.limits
    return {
        "per_test_seconds": max(0.1, min(lim.per_test_seconds, s.max_per_test_seconds)),
        "total_seconds": max(0.5, min(lim.total_seconds, s.max_total_seconds)),
        "memory_mb": max(32, min(lim.memory_mb, s.max_memory_mb)),
        "output_bytes": max(1024, min(lim.output_bytes, s.max_output_bytes)),
    }


def build_payload(req: JobRequest, s: Settings) -> tuple[str, str]:
    """(nonce, base64 payload) for one sandbox run. Raises PayloadTooLarge."""
    if len(req.code.encode()) > s.max_code_bytes or len(req.prelude.encode()) > s.max_code_bytes:
        raise PayloadTooLarge(f"code is larger than {s.max_code_bytes} bytes")
    if len(req.tests) > s.max_tests:
        raise PayloadTooLarge(f"more than {s.max_tests} test cases")
    nonce = secrets.token_hex(16)
    payload = {
        "nonce": nonce,
        "code": req.code,
        "entrypoint": req.entrypoint,
        "prelude": req.prelude,
        "tests": [t.model_dump() for t in req.tests],
        "limits": clamp_limits(req, s),
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    if len(raw) > s.max_payload_bytes:
        raise PayloadTooLarge(f"job is larger than {s.max_payload_bytes} bytes")
    return nonce, base64.b64encode(raw).decode()


def parse_output(log: str, nonce: str) -> dict[str, Any]:
    """The runner's result line. Submitted code cannot write to the real stdout (see runner.py), but match the
    nonce and take the last such line anyway."""
    marker = f"{RESULT_PREFIX}{nonce}>>>"
    for line in reversed(log.splitlines()):
        if line.startswith(marker):
            try:
                result = json.loads(line[len(marker) :])
            except ValueError as exc:
                raise InfraError("runner output was not valid JSON") from exc
            if not isinstance(result, dict) or "status" not in result:
                raise InfraError("runner output had no status")
            return result
    raise InfraError("runner produced no result line")
