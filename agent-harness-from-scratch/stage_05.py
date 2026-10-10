"""Agent Harness From Scratch — stage 5: streaming, and the timings of a turn

DESIGN DECISION — why a SINK and not a list of events?
    A harness that returns the events has already read all of them: the caller
    learns the model was slow only after the answer arrived, and a person waiting
    for the first token stares at a spinner while a buffer fills. A sink is the
    one shape that fits both a provider that pushes (call it from the callback)
    and one the harness pulls from (call it from the loop), and it is what a UI
    actually needs. So `stream` owns the iteration, the sink owns the delivery,
    and neither owns the other's buffer — the events are handed on one at a time
    and the sink is never handed the finished turn.

DESIGN DECISION — why does `end` close the SINK but not the iteration?
    "Nothing after `end`" and "nothing after `end` reaches collect" are two
    different rules, and conflating them loses information both ways. The sink is
    the human-facing surface: an event that arrives after the turn was declared
    over is not part of the answer, so it is not shown (a UI that appends it
    shows text nobody can attribute to a turn). The iterator is the harness-facing
    surface: a provider that keeps talking after `end` is a bug the harness
    REFUSES (stage 1 raises `HarnessError` for it), not one it papers over by
    quietly dropping the tail. So the loop keeps pulling after `end` and forwards
    every event to `collect`; only the sink is closed.

DESIGN DECISION — why is TTFT the first TEXT event, and not the first event?
    Time to first token is the number a user feels: how long until something
    readable appeared. The first event of a turn is very often a `tool_call` or a
    `usage` chunk — the model has started working long before it has started
    saying anything — so measuring from "the first event of any type" reports a
    number that is too small and flatters the provider exactly when it is slowest
    to say anything. A turn with no text at all has no time to first token:
    `None`, not `0.0` (a zero claims the token arrived instantly).

DESIGN DECISION — why does the arrival log ride ON the turn?
    `timings(turn)` is specified as a pure function of a turn, and a turn of text,
    tool calls, usage and a reason has no clock in it. So `stream` records the
    arrival stamps — `{"started": <seconds>, "stamps": [(type, <seconds>), ...]}`
    — under `turn["timings"]` while it consumes the stream, and then replaces that
    value with `timings(turn)`. The returned turn is stage 1's `collect` result
    plus exactly one key, and `timings` can be called on it again (it reduces the
    log once and copies the summary after that). The alternative — keeping the
    stamps in a side channel — leaves `timings` unable to answer the only question
    it exists for.

DESIGN DECISION — why is a mid-stream failure never turned into a turn?
    A stream that dies after two deltas and a stream that finished after two
    deltas are the same bytes; the difference is that one of them is a lie. A
    harness that catches the failure and returns "the turn is over" hands a half
    answer to a person and, worse, tells a retry layer that there is nothing to
    retry: stage 6 retries a `ModelError` only when NOTHING was forwarded yet, and
    it can only know that if stage 5 lets the error out. So the error propagates
    as it is, `retryable` and all, and the sink keeps whatever partial events it
    already saw (a caller that streamed a prefix must know it streamed a prefix).

The clock is injected (`tiny_env.ManualClock` in the tests) and NEVER read from
the wall: `clock=None` means nobody injected one, so every delta is 0.0. A harness
that calls `time.time()` cannot be tested, and an untested latency number is a
number nobody checks.

TODO: implement `stream` and `timings`. `collect` from stage 1 is imported below:
the turn this stage returns is that turn plus timings, and re-deriving it here
would give the harness two owners of the same facts.
"""

from stage_01 import collect


def stream(model, messages, tools=None, *, sink=None, clock=None):
    """One model call, delivered to `sink` as it arrives, returned as a turn.

        stream(model, messages, tools=None, *, sink=None, clock=None) -> turn

    The turn is exactly `collect(model(messages, tools))` plus one key:

        {"text", "tool_calls", "usage", "reason",   # stage 1's turn
         "timings": {"ttft_ms", "itl_ms", "events"}}  # = timings(turn)

    Invariants, each one a mistake somebody has shipped:

    - `sink(event)` is called exactly ONCE per event, in order, AS IT ARRIVES —
      before the next event is pulled, and before the turn exists. Buffering the
      stream and calling the sink at the end is a stream nobody can watch.
    - nothing is sent to the sink after the `end` event; the `end` event itself
      is sent. The iteration does NOT stop at `end`: the events after it still go
      to `collect`, which is where "the turn was over" is enforced.
    - the error of a stream that dies mid-way propagates unchanged (its
      `retryable` flag included): the sink keeps the partial events, and the
      caller is never told the turn finished.
    - the clock is only ever `clock.now()`; `clock=None` means the deltas are 0.0.
      `time.time()` is never read.

    `tools` is forwarded to the model as the caller gave it (`None` included): the
    harness does not invent an empty tool list a provider may not accept.
    """
    raise NotImplementedError("stage 5: implement stream()")


def timings(turn):
    """The turn's arrival log, in milliseconds.

        timings(turn) -> {"ttft_ms": float | None,
                          "itl_ms": [float, ...],
                          "events": int}

    - `ttft_ms` is `(first text event - the call) * 1000`, from the STAMPED log
      the stream left on the turn; the clock is in seconds and the turn is in
      milliseconds, so a `ManualClock` delta of 0.25 is 250.0. `None` when the
      turn had no text event: there is no time to a first token that never came.
    - `itl_ms` is the gap between CONSECUTIVE TEXT events, in ms, in order. A
      usage or tool_call event between two text events is bookkeeping, not the
      model pausing. A turn with fewer than two text events has no gaps: `[]`.
    - `events` is how many events the stream delivered, `end` included.

    Given the turn `stream` returned (already reduced), it answers the same
    numbers again — a copy, so a caller that mutates what it got back cannot
    rewrite the turn's own timings.
    """
    raise NotImplementedError("stage 5: implement timings()")
