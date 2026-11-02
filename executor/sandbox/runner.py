"""
Sandbox runner: the entrypoint of the sandbox image (one pod per job, see docs/PYTHON_PRACTICE_EXECUTOR.md).

It receives the submitted code and the *inputs* of the test cases (never the expected outputs) in the
JOB_PAYLOAD environment variable (base64 JSON), runs the code once per test case in a forked child process
and prints one result line, `<<<RESULT:{nonce}>>>{json}`, to stdout. Grading happens outside the sandbox.

The parent process never executes submitted code. Each child:
  - gets fresh copies of the inputs (decoded from JSON per test, so one test cannot mutate another's input),
  - has its stdout/stderr redirected to pipes the parent drains and truncates (it cannot write to the pod log),
  - runs under RLIMIT_AS / RLIMIT_CPU / RLIMIT_FSIZE / RLIMIT_NOFILE,
  - is killed (SIGKILL, whole process group) when its wall-clock budget runs out.

The trust boundary is the pod (gVisor, no network, no credentials), not this process: a child running as the
same user could interfere with the parent, which can only spoil its own result. Standard library only, and
compatible with Python 3.11+.
"""

from __future__ import annotations

import base64
import json
import math
import os
import platform
import resource
import selectors
import signal
import sys
import time
import traceback
from typing import Any

RESULT_PREFIX = "<<<RESULT:"
MAX_DEPTH = 64
MAX_ITEMS = 100_000
SAFE_INT = 2**53 - 1


class Unserializable(Exception):
    pass


def normalize(value: Any, depth: int = 0, budget: list[int] | None = None) -> Any:
    """Lossless, deterministic JSON form of a return value (the grader compares these)."""
    if budget is None:
        budget = [MAX_ITEMS]
    budget[0] -= 1
    if budget[0] < 0:
        raise Unserializable("return value is too large")
    if depth > MAX_DEPTH:
        raise Unserializable("return value is nested too deeply")
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int):
        return value if -SAFE_INT <= value <= SAFE_INT else {"__int__": str(value)}
    if isinstance(value, float):
        if math.isnan(value):
            return {"__float__": "nan"}
        if math.isinf(value):
            return {"__float__": "inf" if value > 0 else "-inf"}
        return value
    if isinstance(value, (list, tuple)):
        return [normalize(v, depth + 1, budget) for v in value]
    if isinstance(value, dict):
        if all(isinstance(k, str) for k in value):
            return {k: normalize(v, depth + 1, budget) for k, v in value.items()}
        pairs = [[normalize(k, depth + 1, budget), normalize(v, depth + 1, budget)] for k, v in value.items()]
        return {"__map__": sorted(pairs, key=lambda p: json.dumps(p, sort_keys=True))}
    if isinstance(value, (set, frozenset)):
        items = [normalize(v, depth + 1, budget) for v in value]
        return {"__set__": sorted(items, key=lambda v: json.dumps(v, sort_keys=True))}
    if isinstance(value, (bytes, bytearray)):
        return {"__bytes__": base64.b64encode(bytes(value)).decode()}
    import dataclasses

    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {"__dataclass__": type(value).__name__, "fields": {f.name: normalize(getattr(value, f.name), depth + 1, budget) for f in dataclasses.fields(value)}}
    raise Unserializable(f"cannot compare a value of type {type(value).__name__}")


def safe_repr(value: Any, limit: int = 2000) -> str:
    try:
        text = repr(value)
    except Exception as exc:  # noqa: BLE001 - user objects may raise anything from __repr__
        text = f"<unrepresentable {type(value).__name__}: {type(exc).__name__}>"
    return text if len(text) <= limit else text[:limit] + "…"


def clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + "…"


def user_traceback(exc: BaseException, limit: int = 4000) -> str:
    """Traceback frames from the submitted file only (no runner internals)."""
    frames = [f for f in traceback.extract_tb(exc.__traceback__) if f.filename == "solution.py"]
    lines = traceback.format_list(frames) + traceback.format_exception_only(type(exc), exc)
    text = "".join(lines)
    return text if len(text) <= limit else text[-limit:]


def maxrss_kb(ru: resource.struct_rusage) -> int:
    # Linux reports kilobytes, macOS bytes.
    return int(ru.ru_maxrss // 1024) if sys.platform == "darwin" else int(ru.ru_maxrss)


# --- child ------------------------------------------------------------------------------------------


def child_main(payload: dict, test: dict | None, result_fd: int) -> None:
    """Runs in the forked child: load the module, optionally call the entrypoint, write one JSON result."""
    limits = payload["limits"]
    mem = int(limits["memory_mb"]) * 1024 * 1024
    for res, val in (
        (resource.RLIMIT_AS, mem),
        (resource.RLIMIT_CPU, int(math.ceil(limits["per_test_seconds"])) + 1),
        (resource.RLIMIT_FSIZE, 1024 * 1024),
        (resource.RLIMIT_NOFILE, 64),
        (resource.RLIMIT_CORE, 0),
    ):
        try:
            resource.setrlimit(res, (val, val))
        except (ValueError, OSError):
            pass  # not supported on this platform (e.g. RLIMIT_AS on macOS)

    out: dict[str, Any] = {}
    try:
        try:
            code = compile(payload["code"], "solution.py", "exec", dont_inherit=True)
        except SyntaxError as exc:
            out = {"status": "syntax_error", "error": {"type": type(exc).__name__, "message": str(exc.msg), "line": exc.lineno, "offset": exc.offset}}
            return
        namespace: dict[str, Any] = {"__name__": "solution", "__file__": "solution.py", "__builtins__": __builtins__}
        harness = None
        if payload.get("prelude"):
            # Problem-provided helpers (fake clients, clocks) and an optional __harness__(fn, *args) that calls
            # the submitted function. Trusted problem content, but it runs inside the sandbox like everything else.
            try:
                exec(compile(payload["prelude"], "prelude.py", "exec", dont_inherit=True), namespace)  # noqa: S102
            except BaseException as exc:  # noqa: BLE001
                out = {"status": "crash", "error": {"type": "PreludeError", "message": clip(f"{type(exc).__name__}: {exc}", 500)}}
                return
            harness = namespace.get("__harness__")
        try:
            exec(code, namespace)  # noqa: S102 - this is the sandbox; isolation is the pod's job
        except MemoryError:
            out = {"status": "memory"}
            return
        except BaseException as exc:  # noqa: BLE001
            out = {"status": "error", "phase": "import", "error": {"type": type(exc).__name__, "message": clip(str(exc), 1000), "traceback": user_traceback(exc)}}
            return
        fn = namespace.get(payload["entrypoint"])
        if not callable(fn):
            out = {"status": "missing_entrypoint", "error": {"type": "NameError", "message": f"Define a function named {payload['entrypoint']}()."}}
            return
        if test is None:
            out = {"status": "ok"}
            return
        args = test.get("args", [])
        kwargs = test.get("kwargs", {})
        start = time.perf_counter()
        try:
            value = harness(fn, *args, **kwargs) if callable(harness) else fn(*args, **kwargs)
            import inspect

            if inspect.isawaitable(value):
                import asyncio

                async def _await(v: Any) -> Any:
                    return await v

                value = asyncio.run(_await(value))
        except MemoryError:
            out = {"status": "memory"}
            return
        except RecursionError as exc:
            out = {"status": "error", "error": {"type": "RecursionError", "message": clip(str(exc), 300), "traceback": user_traceback(exc)}}
            return
        except BaseException as exc:  # noqa: BLE001 - SystemExit, KeyboardInterrupt etc. are failures too
            out = {"status": "error", "error": {"type": type(exc).__name__, "message": clip(str(exc), 1000), "traceback": user_traceback(exc)}}
            return
        elapsed = (time.perf_counter() - start) * 1000
        try:
            out = {"status": "ok", "output": normalize(value), "output_repr": safe_repr(value), "duration_ms": round(elapsed, 3)}
        except Unserializable as exc:
            out = {"status": "ok", "unserializable": str(exc), "output_repr": safe_repr(value), "duration_ms": round(elapsed, 3)}
        except MemoryError:
            out = {"status": "memory"}
    finally:
        try:
            data = json.dumps(out).encode()
        except (TypeError, ValueError, MemoryError):
            data = b'{"status":"crash","error":{"type":"RunnerError","message":"result could not be encoded"}}'
        try:
            view = memoryview(data)
            while view:
                n = os.write(result_fd, view)
                view = view[n:]
        finally:
            os._exit(0)


# --- parent -----------------------------------------------------------------------------------------


def run_child(payload: dict, test: dict | None, timeout: float, output_limit: int) -> dict:
    """Fork one child, drain its pipes with a wall-clock deadline, and return its result plus measurements."""
    r_res, w_res = os.pipe()
    r_out, w_out = os.pipe()
    r_err, w_err = os.pipe()
    started = time.monotonic()
    pid = os.fork()
    if pid == 0:  # child
        try:
            os.setsid()  # own process group, so a timeout kills everything it started
            os.close(r_res)
            os.close(r_out)
            os.close(r_err)
            devnull = os.open(os.devnull, os.O_RDONLY)
            os.dup2(devnull, 0)
            os.dup2(w_out, 1)
            os.dup2(w_err, 2)
            sys.stdout = os.fdopen(1, "w", buffering=1, closefd=False)
            sys.stderr = os.fdopen(2, "w", buffering=1, closefd=False)
            child_main(payload, test, w_res)
        finally:
            os._exit(70)
    os.close(w_res)
    os.close(w_out)
    os.close(w_err)

    bufs = {r_res: bytearray(), r_out: bytearray(), r_err: bytearray()}
    caps = {r_res: 8 * 1024 * 1024, r_out: output_limit, r_err: output_limit}
    truncated = {r_out: False, r_err: False}
    sel = selectors.DefaultSelector()
    for fd in bufs:
        os.set_blocking(fd, False)
        sel.register(fd, selectors.EVENT_READ)
    deadline = started + timeout
    timed_out = False
    flooded = False
    open_fds = set(bufs)
    while open_fds:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
            break
        for key, _ in sel.select(timeout=min(remaining, 0.25)):
            fd = key.fd
            try:
                chunk = os.read(fd, 65536)
            except BlockingIOError:
                continue
            if not chunk:
                sel.unregister(fd)
                open_fds.discard(fd)
                continue
            room = caps[fd] - len(bufs[fd])
            if room > 0:
                bufs[fd].extend(chunk[:room])
            if len(chunk) > room:
                if fd in truncated:
                    truncated[fd] = True
                if fd == r_res or sum(len(b) for b in bufs.values()) >= caps[r_res]:
                    flooded = True
        if flooded:
            break
    if open_fds:
        try:
            os.killpg(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    sel.close()
    _, status, ru = os.wait4(pid, 0)
    for fd in bufs:
        os.close(fd)
    wall_ms = round((time.monotonic() - started) * 1000, 3)

    result: dict[str, Any]
    if timed_out:
        result = {"status": "timeout"}
    elif flooded:
        result = {"status": "error", "error": {"type": "OutputLimitExceeded", "message": "The program produced too much output."}}
    else:
        try:
            result = json.loads(bytes(bufs[r_res]).decode() or "null") or {}
        except (ValueError, UnicodeDecodeError):
            result = {}
        if not result:
            sig = os.WTERMSIG(status) if os.WIFSIGNALED(status) else None
            if sig == signal.SIGXCPU:
                result = {"status": "timeout"}
            elif sig == signal.SIGKILL:
                # The kernel's OOM killer (or gVisor's) ends a process that exceeds the memory limit.
                result = {"status": "memory"}
            else:
                code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else None
                result = {"status": "crash", "error": {"type": "ProcessExited", "message": f"The process exited unexpectedly (exit={code}, signal={sig})."}}
    result["stdout"] = bufs[r_out].decode("utf-8", "replace")
    result["stderr"] = bufs[r_err].decode("utf-8", "replace")
    if truncated[r_out] or truncated[r_err]:
        result["output_truncated"] = True
    result["wall_ms"] = wall_ms
    result["memory_kb"] = maxrss_kb(ru)
    return result


def run(payload: dict) -> dict:
    limits = payload["limits"]
    per_test = float(limits["per_test_seconds"])
    total = float(limits["total_seconds"])
    output_limit = int(limits.get("output_bytes", 65536))
    started = time.monotonic()
    base = {"python": platform.python_version()}

    load = run_child(payload, None, per_test, output_limit)
    if load["status"] != "ok":
        status = load["status"] if load["status"] in ("syntax_error", "missing_entrypoint") else "load_error"
        return {**base, "status": status, "load": load, "tests": []}

    tests = []
    for test in payload["tests"]:
        if time.monotonic() - started > total:
            tests.append({"id": test["id"], "status": "skipped", "reason": "total time limit reached"})
            continue
        res = run_child(payload, test, per_test, output_limit)
        res["id"] = test["id"]
        tests.append(res)
    return {**base, "status": "completed", "tests": tests, "elapsed_ms": round((time.monotonic() - started) * 1000, 3)}


def main() -> int:
    raw = os.environ.pop("JOB_PAYLOAD", None)
    if raw is None and len(sys.argv) > 1 and sys.argv[1] == "-":
        raw = base64.b64encode(sys.stdin.buffer.read()).decode()
    if not raw:
        print("JOB_PAYLOAD is not set", file=sys.stderr)
        return 2
    payload = json.loads(base64.b64decode(raw))
    nonce = str(payload.get("nonce", ""))
    try:
        result = run(payload)
    except Exception as exc:  # noqa: BLE001 - always answer with a parseable line
        result = {"status": "internal_error", "error": {"type": type(exc).__name__, "message": str(exc)[:500]}}
    sys.stdout.write(f"{RESULT_PREFIX}{nonce}>>>{json.dumps(result)}\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
