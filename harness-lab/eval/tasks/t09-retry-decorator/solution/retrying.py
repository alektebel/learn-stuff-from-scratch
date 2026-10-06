import functools
import time


def retry(attempts=3, base_delay=0.5, factor=2.0, retry_on=(Exception,), sleep=time.sleep):
    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for k in range(1, attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except retry_on:
                    if k == attempts:
                        raise
                    sleep(base_delay * factor ** (k - 1))
        return wrapper
    return decorator
