"""Retry a flaky call with capped exponential backoff and full jitter."""
import functools
import random
import time


def retry(attempts=5, base=0.2, cap=5.0, retry_on=(ConnectionError, TimeoutError), sleep=time.sleep):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on:
                    if attempt == attempts:
                        raise  # out of budget: surface the real error
                    # Full jitter: random wait in [0, min(cap, base * 2^n)].
                    sleep(random.uniform(0, min(cap, base * 2 ** (attempt - 1))))
        return wrapper
    return decorator
