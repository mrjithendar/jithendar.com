"""Executor settings, from environment variables only (see executor/README.md for the full list)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    env: str = "development"
    api_token: str = ""
    redis_url: str = "redis://localhost:6379/0"
    # kubernetes (production) or local (development only: runs code on this machine without isolation).
    backend: str = "kubernetes"
    allow_insecure_local: bool = False
    # runtime id → sandbox image (e.g. {"python-3.13": "…/practice-sandbox:latest"}).
    runtimes: dict[str, str] = field(default_factory=dict)
    sandbox_namespace: str = "practice-sandbox"
    runtime_class: str = "gvisor-nonet"
    sandbox_service_account: str = "practice-sandbox"
    image_pull_secret: str = ""
    sandbox_cpu: str = "1"
    sandbox_memory: str = "512Mi"
    # Limits a caller may ask for (requests above them are clamped).
    max_per_test_seconds: float = 5.0
    max_total_seconds: float = 20.0
    max_memory_mb: int = 256
    max_output_bytes: int = 65_536
    max_code_bytes: int = 64_000
    max_payload_bytes: int = 256_000
    max_tests: int = 60
    # Admission control.
    max_queue: int = 200
    per_user_concurrency: int = 2
    per_user_per_minute: int = 30
    abuse_window_seconds: int = 600
    abuse_threshold: int = 25
    abuse_block_seconds: int = 900
    # Dispatcher.
    dispatcher_concurrency: int = 4
    pod_start_timeout: float = 60.0
    result_ttl_seconds: int = 3600
    lease_seconds: int = 120
    max_attempts: int = 2

    @property
    def production(self) -> bool:
        return self.env == "production"


def load() -> Settings:
    runtimes_raw = os.environ.get("EXECUTOR_RUNTIMES", "{}")
    try:
        runtimes = {str(k): str(v) for k, v in json.loads(runtimes_raw).items()}
    except (ValueError, AttributeError):
        runtimes = {}
    s = Settings(
        env=os.environ.get("EXECUTOR_ENV", "development"),
        api_token=os.environ.get("EXECUTOR_API_TOKEN", ""),
        redis_url=os.environ.get("EXECUTOR_REDIS_URL", "redis://localhost:6379/0"),
        backend=os.environ.get("EXECUTOR_BACKEND", "kubernetes"),
        allow_insecure_local=os.environ.get("EXECUTOR_ALLOW_INSECURE_LOCAL") == "yes-i-understand",
        runtimes=runtimes,
        sandbox_namespace=os.environ.get("EXECUTOR_SANDBOX_NAMESPACE", "practice-sandbox"),
        runtime_class=os.environ.get("EXECUTOR_RUNTIME_CLASS", "gvisor-nonet"),
        sandbox_service_account=os.environ.get("EXECUTOR_SANDBOX_SERVICE_ACCOUNT", "practice-sandbox"),
        image_pull_secret=os.environ.get("EXECUTOR_IMAGE_PULL_SECRET", ""),
        sandbox_cpu=os.environ.get("EXECUTOR_SANDBOX_CPU", "1"),
        sandbox_memory=os.environ.get("EXECUTOR_SANDBOX_MEMORY", "512Mi"),
        max_per_test_seconds=_float("EXECUTOR_MAX_PER_TEST_SECONDS", 5.0),
        max_total_seconds=_float("EXECUTOR_MAX_TOTAL_SECONDS", 20.0),
        max_memory_mb=_int("EXECUTOR_MAX_MEMORY_MB", 256),
        max_queue=_int("EXECUTOR_MAX_QUEUE", 200),
        per_user_concurrency=_int("EXECUTOR_PER_USER_CONCURRENCY", 2),
        per_user_per_minute=_int("EXECUTOR_PER_USER_PER_MINUTE", 30),
        abuse_threshold=_int("EXECUTOR_ABUSE_THRESHOLD", 25),
        dispatcher_concurrency=_int("EXECUTOR_DISPATCHER_CONCURRENCY", 4),
    )
    validate(s)
    return s


def validate(s: Settings) -> None:
    if s.backend not in ("kubernetes", "local"):
        raise RuntimeError(f"EXECUTOR_BACKEND must be kubernetes or local, not {s.backend!r}")
    if s.backend == "local" and (s.production or not s.allow_insecure_local):
        raise RuntimeError(
            "The local backend runs submitted code on this machine without isolation. It is refused in production and "
            "needs EXECUTOR_ALLOW_INSECURE_LOCAL=yes-i-understand elsewhere."
        )
    if s.production and len(s.api_token) < 32:
        raise RuntimeError("EXECUTOR_API_TOKEN (32+ characters) is required in production.")
    if s.production and not s.runtime_class:
        raise RuntimeError("EXECUTOR_RUNTIME_CLASS is required in production (sandbox pods must not use the default runtime).")
