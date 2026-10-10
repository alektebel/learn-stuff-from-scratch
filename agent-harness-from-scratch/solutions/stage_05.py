"""Agent Harness From Scratch — stage 5 solution: streaming, and the timings of a
turn.

The reasoning lives in `stage_05.py`'s docstring (the design decisions are the
lesson); this file is the implementation.
"""

from stage_01 import collect


def _ms(seconds):
    """The clock's unit is seconds; the turn reports milliseconds."""
    return round(seconds * 1000.0, 6)


def timings(turn):
    """The arrival log the stream left on `turn`, reduced to milliseconds."""
    log = turn.get("timings") if isinstance(turn, dict) else None
    if isinstance(log, dict) and "stamps" in log:
        started = float(log.get("started", 0.0))
        stamps = list(log["stamps"])
        # Only a TEXT event is a token: a tool call is the model asking a question,
        # not the first token of an answer, and measuring from it reports a TTFT
        # that is too small exactly when the model is slowest to say anything.
        text_times = [at for kind, at in stamps if kind == "text"]
        return {
            "ttft_ms": None if not text_times else _ms(text_times[0] - started),
            # Text to text: a usage event between two deltas is bookkeeping, not
            # the model pausing, and it must not open a gap in the middle.
            "itl_ms": [_ms(later - earlier)
                       for earlier, later in zip(text_times, text_times[1:])],
            "events": len(stamps),
        }
    if isinstance(log, dict):
        # Already reduced: this is the turn `stream` returned. A copy, so a caller
        # mutating what it got back cannot rewrite the turn's own numbers.
        return {"ttft_ms": log.get("ttft_ms"),
                "itl_ms": list(log.get("itl_ms") or []),
                "events": int(log.get("events", 0))}
    return {"ttft_ms": None, "itl_ms": [], "events": 0}


def stream(model, messages, tools=None, *, sink=None, clock=None):
    """One model call, forwarded to `sink` as it arrives, returned as a turn."""
    # `clock=None` means nobody injected a clock: the deltas are 0.0. It never
    # means "read the wall clock" — a harness with time.time() in it is a harness
    # whose latency numbers no test can assert.
    started = clock.now() if clock is not None else 0.0
    log = {"started": started, "stamps": []}
    raw = model(messages, tools)

    def forwarded():
        ended = False
        for event in raw:
            kind = event.get("type") if isinstance(event, dict) else None
            # Stamped when it ARRIVES (the model's generator has just advanced the
            # clock to this event's time), not when the turn is assembled.
            log["stamps"].append((kind, clock.now() if clock is not None else 0.0))
            # One call per event, in order, before the turn exists. The `end` event
            # reaches the sink; what comes after it does not.
            if not ended and sink is not None:
                sink(event)
            if kind == "end":
                ended = True
            # Every event, after `end` included, still goes to collect: that is
            # where stage 1 refuses a stream that kept talking after the turn was
            # over. Dropping it here would hide the provider's bug from the caller.
            yield event

    turn = collect(forwarded())
    turn["timings"] = log          # the arrival log rides on the turn, so ...
    turn["timings"] = timings(turn)  # ... `timings` stays a pure function of it
    return turn
