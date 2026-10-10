"""Agents From Scratch — stage 5: retries, timeouts, and the effect that must
not happen twice

SOLUTION. Three small pieces that only look like one: a taxonomy that decides
whether waiting can help, a loop that sleeps between attempts and not after the
last one, and a memo keyed by the request so a lost response cannot charge twice.
"""

import json
import time


class ToolError(Exception):
    retryable = False

    def __init__(self, message="", *, retryable=None):
        super().__init__(message)
        if retryable is not None:
            self.retryable = retryable


class Timeout(ToolError):
    retryable = True


class RateLimited(ToolError):
    retryable = True


class BadArgs(ToolError):
    retryable = False


class NotFound(ToolError):
    retryable = False


def classify(error):
    if isinstance(error, ToolError):
        return "retry" if error.retryable else "fatal"
    # A crash in the tool, a TypeError in the caller, a bug in the schema: none
    # of those get better by asking again, and retrying them hides the bug.
    return "fatal"


def backoff(attempt, base=0.5, factor=2.0, cap=30.0):
    if attempt < 1:
        raise ValueError(f"attempt starts at 1, got {attempt}")
    return min(cap, base * factor ** (attempt - 1))


def with_retry(fn, attempts=3, base=0.5, factor=2.0, cap=30.0, sleep=None,
               classify=classify):
    if attempts < 1:
        raise ValueError(f"attempts must be at least 1, got {attempts}")
    do_sleep = time.sleep if sleep is None else sleep
    slept = []
    error = None

    for attempt in range(1, attempts + 1):
        try:
            return {"ok": True, "attempts": attempt, "value": fn(),
                    "error": None, "slept": slept}
        except Exception as exc:                        # noqa: BLE001 - classified
            error = exc
            if classify(exc) == "fatal" or attempt == attempts:
                break
            delay = backoff(attempt, base=base, factor=factor, cap=cap)
            slept.append(delay)
            do_sleep(delay)

    return {"ok": False, "attempts": len(slept) + 1 if error else 0, "value": None,
            "error": error, "slept": slept}


def request_key(tool, args):
    return json.dumps({"tool": tool, "args": args}, sort_keys=True,
                      separators=(",", ":"), default=repr)


class Effect:
    def __init__(self):
        self.applied = {}
        self.reused = 0

    def once(self, key, fn):
        if key in self.applied:
            self.reused += 1
            return self.applied[key]
        value = fn()                       # a raise here stores nothing
        self.applied[key] = value
        return value
