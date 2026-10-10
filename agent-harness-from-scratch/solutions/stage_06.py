"""Agent Harness From Scratch — stage 6 solution: retry the model call, never the
tool call, and never re-send what was already streamed.

The reasoning lives in `stage_06.py`'s docstring (the design decisions are the
lesson); this file is the implementation.
"""

from tiny_env import HarnessError, ModelError

from stage_01 import EMPTY_USAGE, usage_add


class Retrying:
    """A transparent model wrapper that retries a retryable `ModelError`, but only
    while it has forwarded nothing, doubles the delay per retry, waits through the
    injected clock, and bills every attempt."""

    def __init__(self, model, *, attempts=3, backoff=0.5, clock=None, budget=None):
        if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 1:
            raise ValueError("attempts must be a positive int, got %r" % (attempts,))
        if isinstance(backoff, bool) or not isinstance(backoff, (int, float)):
            raise ValueError("backoff must be a number of seconds, got %r" % (backoff,))
        if budget is not None and (isinstance(budget, bool)
                                   or not isinstance(budget, int) or budget < 0):
            raise ValueError("budget must be None or a non-negative int, got %r"
                             % (budget,))
        self.model = model
        self.attempts = attempts
        self.backoff = backoff
        self.clock = clock
        self.budget = budget
        self.calls = 0
        self.retries = 0
        self.usage = dict(EMPTY_USAGE)

    def __call__(self, messages, tools=None):
        # A generator, not a list: the caller must see each event as it arrives,
        # which is what makes "was anything forwarded?" a question the wrapper can
        # answer.
        return self._stream(messages, tools)

    def _allowed(self):
        """How many attempts THIS call may make: `attempts`, capped by whatever is
        left of the whole-run `budget`."""
        if self.budget is None:
            return self.attempts
        return min(self.attempts, self.budget - self.calls)

    def _wait(self, index):
        """Sleep `backoff * 2**index` (`index` is the 0-based retry number) through
        the injected clock. `time.sleep` would make the backoff untestable: a check
        could not tell a real 0.5 second wait from no wait at all, and the suite
        would pay the wall clock."""
        if self.clock is None:
            return
        self.clock.sleep(self.backoff * (2 ** index))

    def _stream(self, messages, tools):
        allowed = self._allowed()
        if allowed <= 0:
            # There is no pending error to hand back: the caller asked for a turn
            # the budget does not cover, and papering over that would make the cap
            # advisory.
            raise HarnessError(
                "the retry budget is spent: %d attempt(s) made against budget=%r, "
                "so this call cannot be made"
                % (self.calls, self.budget))
        last_error = None
        for attempt in range(allowed):
            if attempt > 0:
                # The first attempt never waits; each retry waits twice the last,
                # and the wait is recorded by the clock.
                self._wait(attempt - 1)
                self.retries += 1
            self.calls += 1
            forwarded = False
            try:
                stream = self.model(messages, tools)
                for event in stream:
                    if isinstance(event, dict) and event.get("type") == "usage":
                        # Billed BEFORE forwarding: a stream that dies right after
                        # its usage event still cost money.
                        self.usage = usage_add(self.usage, event)
                    # The attempt is committed the moment an event reaches the
                    # caller; after this a failure may not be retried.
                    forwarded = True
                    yield event
                return
            except ModelError as exc:
                if not exc.retryable or forwarded:
                    # A permanent failure, or one the caller already has a prefix
                    # of: both propagate. Re-sending the prefix would deliver it
                    # twice.
                    raise
                last_error = exc
                # Nothing was forwarded: waiting and trying again cannot duplicate
                # anything the caller saw.
        # Every allowed attempt failed retryably. A retryable error that ran out of
        # attempts is still a failure, not a silently empty turn.
        raise last_error
