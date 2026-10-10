"""Agent Harness From Scratch — stage 6: retries — the model call, never the
tool call.

DESIGN DECISION — a retry policy is an object that WRAPS the model, not a
    `for attempt in range(3)` written at every call site.
    The alternative is a loop in the agent run, and then every caller that wants
    a retry re-implements the backoff, the retryability rule and the accounting
    — and each of them gets one of the three wrong. A wrapper makes the policy
    one object with one set of counters (`.calls`, `.retries`, `.usage`), and
    the loop in stage 3 keeps calling "the model" without knowing it is a
    decorator. The wrapper is transparent: it re-emits the model's events,
    unchanged and in order, so stage 1's `collect` and stage 5's `stream` never
    learn that a retry happened.

DESIGN DECISION — the wait goes through the injected clock, never `time.sleep`.
    A backoff that sleeps for real is a backoff no test can observe: the check
    cannot tell a 0.5 second wait from no wait at all, and a suite that retries
    three times pays the wall-clock cost forever. `clock.sleep(seconds)` both
    advances the injected clock and records what it was asked to wait, so the
    delay is an assertion, not a delay. The delay doubles per retry
    (`backoff * 2**k`, `k` the 0-based retry number), which is the shape a
    provider's rate limit expects.

DESIGN DECISION — retry ONLY a `ModelError` with `retryable=True`.
    `ModelError` is the model's refusal; `retryable` is the provider's opinion
    about whether asking again can help. A permanent failure (a bad request, a
    schema the provider rejects) that is retried spends money to get the same
    answer, so it propagates on the first try. Anything else — an `EnvError`
    from a tool, a `TypeError` from a bug — is not caught: the wrapper is not a
    place to hide a harness defect behind a retry.

DESIGN DECISION — a retry happens only while NOTHING has been forwarded.
    This is the headline rule. The wrapper is a generator: it hands each event
    to its caller the moment it reads it. If the stream dies after one text
    delta has already reached the caller, a retry would hand that caller the
    prefix a second time — the answer "He" then "Hello", glued into "HeHello".
    So the moment an event is yielded the attempt is committed: a later
    `ModelError` propagates, and the partial stream the caller already has is
    the record of what happened. A stream that fails before its first event,
    though, cost the caller nothing, and that is exactly the case a retry is
    for.

DESIGN DECISION — usage accumulates over EVERY attempt, including failed ones.
    A failed attempt that emitted a usage event reported tokens the provider
    will bill, even though the turn never finished; dropping it makes a run
    that retried four times look cheap. So the wrapper adds each usage event to
    `.usage` as it reads it (before forwarding, so a mid-stream death still
    bills it) rather than summing the finished turn once. Summing is stage 1's
    `usage_add` — reusing it keeps the arithmetic in one file.

DESIGN DECISION — `attempts` is per call; `budget` is per whole run.
    `attempts` (default 3) is the most tries ONE `__call__` may make, because a
    single question that needed retries should not exhaust the allowance of the
    questions that follow. `budget` (default `None`) is the most model
    invocations the WHOLE wrapper may make, across every call: it is the
    operator's cost ceiling. With `budget=None` three questions may cost nine
    attempts; with `budget=2` the second question finds nothing left to spend
    and the wrapper refuses to make a call it cannot pay for (`HarnessError`).

TODO: implement

    class Retrying
        __init__(model, *, attempts=3, backoff=0.5, clock=None, budget=None)
            model is a callable `(messages, tools=None) -> iterator of events`
            (stage 1's contract; `tiny_env.ScriptedModel` fits). `attempts` is a
            positive int (how many tries one call may make); `backoff` is the
            first wait in seconds, doubling per retry; `clock` is the injected
            clock (a `.sleep(seconds)` is the only wait); `budget` is `None` or a
            non-negative int, the whole-run cap on model invocations. Bad
            arguments raise `ValueError` before anything is called.

        __call__(messages, tools=None) -> iterator of events
            Returns an iterator. It calls the model, forwards every event it
            produces, and, while NOTHING has been forwarded yet and the failure
            is a retryable `ModelError`, waits `backoff * 2**k` through the clock
            (`k` the 0-based retry number) and calls the model again with the
            SAME `messages` and `tools`. A non-retryable `ModelError`, a failure
            after an event was forwarded, or a spent budget propagates instead.
            When every allowed attempt fails retryably, the last `ModelError`
            propagates (never an empty iterator).

        .calls   -> int      # model invocations made, counting retries
        .retries -> int      # of those, the ones that were a retry
        .usage   -> dict     # {"input_tokens", "output_tokens"}, summed over
                             # every attempt, failed ones included

    Errors:
        ModelError(retryable=True)   the only thing retried
        ModelError(retryable=False)  propagates on the first try
        HarnessError                 a call started with the budget already spent
        ValueError                   bad `attempts`/`backoff`/`budget`
"""


class Retrying:
    def __init__(self, model, *, attempts=3, backoff=0.5, clock=None, budget=None):
        raise NotImplementedError("stage 6: implement Retrying")

    def __call__(self, messages, tools=None):
        raise NotImplementedError("stage 6: implement Retrying.__call__")
