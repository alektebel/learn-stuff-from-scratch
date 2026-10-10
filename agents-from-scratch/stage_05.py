"""Agents From Scratch — stage 5: retries, timeouts, and the effect that must
not happen twice

DESIGN DECISION — retry the condition, not the symptom.
    A timeout is a statement about the network; a bad argument is a statement
    about the request, and no amount of waiting changes it. Retrying everything
    with the same policy is how an agent burns its whole step budget on a call
    that cannot succeed, and the run then reports "tool kept failing" — which is
    true and useless. The taxonomy is the point: a retryable error is one where
    the same request may work later.

DESIGN DECISION — sleep is an injected dependency.
    An agent that really sleeps for 30 seconds cannot be tested, and a retry
    schedule nobody tests drifts. `sleep` and the backoff function are arguments:
    the run's timing becomes a value the check can assert, and there is no
    sleeping after the LAST attempt, because a caller that is about to give up
    does not need to wait first.

DESIGN DECISION — a retry is a second chance for the network, not for the
effect.
    The failure this stage exists for is the quiet one: the request reached the
    tool and the response was lost, so the caller retries and the effect lands
    twice — two charges, two emails, two rows. It cannot be fixed by the
    retrying caller, because only the tool knows whether it already applied
    something; it is fixed by giving the call a stable KEY and letting the
    effect run once per key. That is `Effect.once`, and its count is the
    assertion.

TODO: implement

    class ToolError(Exception): retryable = False
    class Timeout(ToolError): retryable = True
    class RateLimited(ToolError): retryable = True
    class BadArgs(ToolError): retryable = False
    class NotFound(ToolError): retryable = False

    classify(error) -> "retry" | "fatal"
        By type, never by matching the message: Timeout and RateLimited retry;
        every other ToolError is fatal; anything that is not a ToolError at all
        (a TypeError in your own code) is fatal, because a bug is not a
        transient condition.

    backoff(attempt, base=0.5, factor=2.0, cap=30.0) -> float
        The delay before retry number `attempt + 1` (attempt starts at 1):
        base * factor ** (attempt - 1), never above `cap`.

    with_retry(fn, attempts=3, base=0.5, factor=2.0, cap=30.0, sleep=None,
               classify=classify) -> dict
        Calls fn() and returns
            {"ok": bool, "attempts": int, "value": ... | None,
             "error": Exception | None, "slept": [float, ...]}
        - a fatal error, or a successful call, is never retried: attempts is 1;
        - a retryable error is retried up to `attempts` calls in total;
        - sleep is called with the backoff delay BEFORE each retry and not after
          the last failure (attempts=3 -> at most 2 entries in `slept`);
        - `sleep=None` means a real sleep (that is the production default) — the
          tests pass a recorder, which is why it is a parameter at all;
        - it returns; it does not raise, because a caller deciding what to do
          with a failed tool call is the next stage's problem.

    request_key(tool, args) -> str
        A canonical key for one call: the same tool with the same arguments
        (whatever the dict order) gives the same key, and a different argument
        value gives a different one. JSON with sorted keys is a fine body.

    class Effect:
        .applied -> dict[key, value]     the effects that landed
        .reused  -> int                  how many calls were answered from it
        once(key, fn) -> value
            Runs fn() the first time this key is seen, stores and returns its
            value; every later call with the same key returns the stored value
            WITHOUT calling fn again. If fn raises, nothing is stored and the
            next call with that key runs fn again (a failure is not an effect).
"""


class ToolError(Exception):
    raise NotImplementedError("stage 5: implement ToolError")


class Timeout(ToolError):
    raise NotImplementedError("stage 5: implement Timeout")


class RateLimited(ToolError):
    raise NotImplementedError("stage 5: implement RateLimited")


class BadArgs(ToolError):
    raise NotImplementedError("stage 5: implement BadArgs")


class NotFound(ToolError):
    raise NotImplementedError("stage 5: implement NotFound")


def classify(error):
    raise NotImplementedError("stage 5: implement classify()")


def backoff(attempt, base=0.5, factor=2.0, cap=30.0):
    raise NotImplementedError("stage 5: implement backoff()")


def with_retry(fn, attempts=3, base=0.5, factor=2.0, cap=30.0, sleep=None,
               classify=classify):
    raise NotImplementedError("stage 5: implement with_retry()")


def request_key(tool, args):
    raise NotImplementedError("stage 5: implement request_key()")


class Effect:
    def __init__(self):
        raise NotImplementedError("stage 5: implement Effect")

    def once(self, key, fn):
        raise NotImplementedError("stage 5: implement Effect.once()")
