"""Agent Harness From Scratch — stage 8: the trace, the artifact you can replay.

DESIGN DECISION — the trace keeps the SHAPE of the run, never a copy of it.
    The obvious artifact to keep is the conversation: the prompt, the arguments
    the model asked for, the result the tool handed back. It is also the artifact
    you cannot keep. Every one of those is somebody's data, and it lands in the
    one place nobody guards — a log file, a dashboard, a ticket — with no expiry
    and no access check. What a trace has to answer is *which turn called which
    tool, and what did it cost*: the six keys below answer exactly that, and
    nothing else. The payloads stay where they already are (the conversation the
    run built, with its own lifetime), so the trace is safe to hand to anybody.
    That is also why there is no payload channel: `step` takes the six fields and
    no `**extra`, and `tool` is the tool's NAME, so a caller cannot smuggle a
    call into the artifact and call it debugging.

DESIGN DECISION — the clock is injected, or the step is not timed; never read.
    `time.time()` in a trace is a duration nobody can assert (two runs of the
    same script disagree by a millisecond), a line that cannot be merged or
    diffed, and a test that has to sleep to prove anything. So a step's duration
    is the gap since the PREVIOUS step, read from the clock the caller handed in
    — `ManualClock` in this course, whose ticks are seconds, so the gap is
    converted to milliseconds. A step with no clock and no given duration is
    recorded as `None`: "nobody measured this" is a fact about the run, and
    writing `0.0` there would be the trace inventing an instant step.

DESIGN DECISION — the first timed step is 0.0, and that is not a bug.
    There is no previous step to measure from, so the reading it takes becomes the
    BASELINE and the gap is zero. The alternative was to take the baseline in
    `__init__`, which makes a trace's first line depend on how long the caller
    happened to hold the object; the other alternative is for the caller to pass
    `duration_ms` for a first step it timed itself, and that is what the parameter
    is for. So: a clock times the gaps between recorded steps, and nothing else.

DESIGN DECISION — `.lines` hands out a copy, in both directions.
    The trace is the artifact and the caller is not its only author. A caller that
    "just annotates the last line" must not be able to rewrite what the run
    recorded, and a `step` that returned its own dict would let one mutation
    corrupt the audit. So both hand out fresh dicts — and `.lines` builds a new
    LIST of new dicts, because a shallow copy of the list still hands out the
    trace's own lines.

DESIGN DECISION — summary() and replay() are folds over `.lines`.
    One source of truth. Running totals kept beside the lines drift from them, and
    then the audit needs an audit. Every trap is in the fold: `turns` counts
    `kind == "model"` and a RETRY is not a turn (the model was asked twice; the
    turn is one), `calls` counts tool steps, `tokens` is the SUM (a replaced total
    is the last step's bill wearing the run's name), `errors` counts `ok is False`
    of any kind, and `duration_ms` totals what was measured and skips the steps
    nobody timed.

DESIGN DECISION — replay needs the shape, not the content.
    `[(turn, kind, tool)]` is everything it takes to re-read a run: which turn,
    what the step was, which tool it touched. If replay needed the argument dicts,
    the trace would have to keep them — and the trace that keeps the payloads is
    the leak you were auditing. The turn number belongs to the CALLER (the loop
    numbers the model calls it makes); the trace does not invent one, because a
    trace that guessed would disagree with the run it recorded.

TODO: implement `Trace`.

    KINDS = ("model", "tool", "retry", "compact", "end")
        The vocabulary of a step. `model` and `tool` are the run; `retry` is the
        same turn asked again; `compact` is the context being rewritten; `end` is
        the run finishing. A kind outside it is a HarnessError.

    class Trace
        KEYS = ("turn", "kind", "tokens", "duration_ms", "tool", "ok")
            The shape of a line, in this order. Nothing else goes in a line: not
            the prompt, not a tool's arguments, not a result, not a clock.

        __init__(*, clock=None)
            `clock` is the run's default clock; a caller may also hand one to a
            single `step`. Held as `.clock`. The trace keeps no other state but
            the lines and the last clock reading it took.

        step(*, kind, turn=None, tokens=0, tool=None, ok=True, duration_ms=None,
             clock=None) -> line
            Records ONE step and returns it — a COPY, like `.lines`, so the caller
            cannot edit the trace through what it was handed.
            - `kind` must be one of KINDS.
            - `turn` is None or an int >= 0: the caller's numbering.
            - `tokens` is a non-negative int (a bool is not one): the summary's
              total is money, and a string there adds up to nothing.
            - `ok` is a real bool; `summary()["errors"]` counts `ok is False`.
            - `tool` is a tool's NAME (str) or None. A call dict is the
              arguments, and the arguments are the payload this stage exists to
              keep out.
            - `duration_ms`:
                given (a number) -> recorded as given; a clock, if any, only
                  moves the baseline;
                not given, and there is a clock (the step's, else the trace's)
                  -> the gap since the previous timed step in MILLISECONDS,
                  `(clock.now() - previous reading) * 1000`; the first timed step
                  records 0.0 and takes the reading as its baseline;
                neither -> None.
            The recorded line is `{key: ...}` for exactly KEYS, in KEYS order.

        .lines -> [dict, ...]
            A COPY of every line recorded, oldest first: a fresh list of fresh
            dicts, so neither the list nor a line can be edited into the trace.

        summary() -> {"turns", "calls", "tokens", "errors", "duration_ms"}
            `turns` — steps of kind "model" (a retry is not a turn);
            `calls` — steps of kind "tool";
            `tokens` — the sum of every line's tokens;
            `errors` — how many lines have `ok is False`;
            `duration_ms` — the sum of the durations that were measured.

        replay() -> [(turn, kind, tool), ...]
            One tuple per line, in order, and no payloads: the shape is what
            makes a trace replayable.
"""

from tiny_env import HarnessError

# The vocabulary of a step. `model` and `tool` are the run; `retry` is the same
# turn asked again; `compact` is the context being rewritten; `end` is the run
# finishing. Anything else is a HarnessError: a kind nobody can count is a
# summary nobody can trust.
KINDS = ("model", "tool", "retry", "compact", "end")


class Trace:
    KEYS = ("turn", "kind", "tokens", "duration_ms", "tool", "ok")

    def __init__(self, *, clock=None):
        raise NotImplementedError("stage 8: implement Trace.__init__")

    @property
    def lines(self):
        raise NotImplementedError("stage 8: implement Trace.lines")

    def step(self, *, kind, turn=None, tokens=0, tool=None, ok=True,
             duration_ms=None, clock=None):
        raise NotImplementedError("stage 8: implement Trace.step()")

    def summary(self):
        raise NotImplementedError("stage 8: implement Trace.summary()")

    def replay(self):
        raise NotImplementedError("stage 8: implement Trace.replay()")
