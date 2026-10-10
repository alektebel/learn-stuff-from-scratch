"""Agent Harness From Scratch — stage 8 solution: the trace.

The reasoning lives in `stage_08.py`'s docstring (the design decisions are the
lesson); this file is the implementation. Six keys per line, no wall clock and no
payload, and `summary()`/`replay()` are folds over the lines the trace kept — so
the artifact and the digest of the artifact cannot disagree.
"""

from tiny_env import HarnessError

KINDS = ("model", "tool", "retry", "compact", "end")


def _index(value, field):
    """A turn number: None (the caller did not number this step) or an int >= 0.
    A bool is an int in Python, and `True` as a turn number is a bug, not a
    turn."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise HarnessError("%s must be an int or None, got %r (%s)"
                           % (field, value, type(value).__name__))
    if value < 0:
        raise HarnessError("%s cannot be negative, got %r" % (field, value))
    return value


def _count(value, field):
    """A non-negative count. Ints only: a bool is an int, a string count is a
    total that adds up to nothing, and a negative one un-bills a run."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise HarnessError("%s must be an int, got %r (%s)"
                           % (field, value, type(value).__name__))
    if value < 0:
        raise HarnessError("%s cannot be negative, got %r" % (field, value))
    return value


def _number(value, field):
    """A non-negative number: a duration the caller measured itself."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise HarnessError("%s must be a number, got %r (%s)"
                           % (field, value, type(value).__name__))
    if value < 0:
        raise HarnessError("%s cannot be negative, got %r" % (field, value))
    return value


class Trace:
    """One line per step, exactly KEYS, and nothing about the payloads."""

    KEYS = ("turn", "kind", "tokens", "duration_ms", "tool", "ok")

    def __init__(self, *, clock=None):
        self.clock = clock
        self._lines = []
        # The clock reading at the previous TIMED step: the gap to the next one
        # is what that step took. None until something has been timed, and it is
        # the only state the trace keeps besides the lines.
        self._mark = None

    @property
    def lines(self):
        # A fresh list of fresh dicts. `list(self._lines)` alone would still hand
        # out the trace's own line dicts, and one edited line is a rewritten
        # audit.
        return [dict(line) for line in self._lines]

    def step(self, *, kind, turn=None, tokens=0, tool=None, ok=True,
             duration_ms=None, clock=None):
        if kind not in KINDS:
            raise HarnessError(
                "unknown step kind %r (known: %s): a line nobody can count is a "
                "summary nobody can trust" % (kind, ", ".join(KINDS)))
        turn = _index(turn, "turn")
        tokens = _count(tokens, "tokens")
        if not isinstance(ok, bool):
            raise HarnessError("ok must be a bool, got %r (%s)"
                               % (ok, type(ok).__name__))
        if tool is not None and not isinstance(tool, str):
            raise HarnessError(
                "tool must be the tool's NAME (a string) or None, got %r (%s): a "
                "trace that records the call records its arguments"
                % (tool, type(tool).__name__))
        source = clock if clock is not None else self.clock
        if duration_ms is None:
            if source is not None:
                now = source.now()
                # The first timed step has no predecessor to measure from: the
                # reading it takes is the baseline, and 0.0 says "nothing was
                # measured before this", not "this was instant". ManualClock ticks
                # in seconds and a duration is milliseconds.
                duration_ms = 0.0 if self._mark is None \
                    else (now - self._mark) * 1000.0
                self._mark = now
        else:
            # The caller's own measurement wins; an available clock only moves
            # the baseline, so the next measured step is timed from here.
            duration_ms = _number(duration_ms, "duration_ms")
            if source is not None:
                self._mark = source.now()
        line = {"turn": turn, "kind": kind, "tokens": tokens,
                "duration_ms": duration_ms, "tool": tool, "ok": ok}
        self._lines.append(line)
        return dict(line)

    def summary(self):
        """The digest, folded over the lines — one source of truth."""
        lines = self._lines
        return {
            "turns": sum(1 for line in lines if line["kind"] == "model"),
            "calls": sum(1 for line in lines if line["kind"] == "tool"),
            "tokens": sum(line["tokens"] for line in lines),
            "errors": sum(1 for line in lines if line["ok"] is False),
            "duration_ms": sum(line["duration_ms"] for line in lines
                               if line["duration_ms"] is not None),
        }

    def replay(self):
        """The shape of the run: which turn, what the step was, which tool. No
        payloads — that is what makes a trace replayable and safe to keep."""
        return [(line["turn"], line["kind"], line["tool"])
                for line in self._lines]
