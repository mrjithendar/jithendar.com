"""Check many HTTP endpoints in parallel with a per-request timeout."""
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


def check(url, timeout=3.0):
    start = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            status = resp.status
    except urllib.error.HTTPError as exc:  # 4xx/5xx still answered
        status = exc.code
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return url, None, f"{type(exc).__name__}: {exc}"
    return url, status, f"{(time.monotonic() - start) * 1000:.0f} ms"


def check_all(urls, workers=20):
    # Threads are fine here: the GIL is released while waiting on sockets.
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(check, u) for u in urls]
        for future in as_completed(futures):
            yield future.result()


if __name__ == "__main__":
    failed = 0
    for url, status, detail in check_all(sys.argv[1:]):
        healthy = status is not None and 200 <= status < 400
        failed += not healthy
        print(f"{'OK  ' if healthy else 'FAIL'} {status or '---'} {url} ({detail})")
    sys.exit(1 if failed else 0)
