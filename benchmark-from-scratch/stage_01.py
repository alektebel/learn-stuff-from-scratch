"""Benchmark From Scratch — stage 1: the turn gate.

DESIGN DECISION — why is the engine the only gate?
    A harness that re-checks "is this action legal" against its own copy of the
    rules has two rulebooks, and the second one is wrong. The engine already
    answers the question (`legal_actions`) and already refuses (`apply`), and its
    refusal is atomic. This stage's job is not to know the rules: it is to turn
    "the table accepted it" and "the table refused it" into two DIFFERENT
    outcomes, and to count them separately.

DESIGN DECISION — why is a rejection not a turn?
    A turn is a decision that changed the position. A model that answers with
    nonsense four times before finding a legal move did not take four turns, and a
    benchmark that counts rejections as turns reports a busier, better-behaved
    player than it has: the turn count is the denominator of a decision cost, and
    the rejection count is the numerator of a behaviour you want to see.

DESIGN DECISION — why does anything that is not `IllegalAction` propagate?
    `IllegalAction` means the SEAT misbehaved, which is data: it is counted and
    the reason is handed back so the seat can be told what went wrong. Any other
    exception means OUR program is broken — a missing field, a wrong type, a
    table that cannot answer. Converting that into "the model misbehaved" hides
    the bug behind a behaviour metric, and the metric is the thing you are trying
    to trust.

DESIGN DECISION — why is `stats` handed in instead of returned?
    One stats dict per match, mutated in place, because the accounting is
    match-scoped: a fresh dict per hand would silently reset the rejections a seat
    accumulated, and the number would look worse in every hand than it is.

TODO: implement `new_stats` and `gate`.
"""

#: The counters a match keeps. Every one of them is an int; `new_stats` returns a
#: fresh dict containing exactly these keys, at zero.
STATS_KEYS = ("turns", "rejections", "fallbacks", "llm_turns", "calls")


def new_stats():
    """A fresh, all-zero stats dict for one match."""
    raise NotImplementedError("stage 1: implement new_stats()")


def gate(table, seat, action, *, stats):
    """Offer one action to the table and report what happened.

    Returns `{"ok": bool, "reason": str | None, "turn": int}`:

    - the action was accepted: the table has advanced, `stats["turns"]` is one
      higher, `ok` is True, `reason` is None and `turn` is the new turn number;
    - the table refused it (`mus.IllegalAction`): nothing about the position has
      changed, `stats["rejections"]` is one higher, `ok` is False, `reason` is the
      engine's own words, and `turn` is still the last turn that happened;
    - anything else the call raises is a bug in our program and is NOT caught.
    """
    raise NotImplementedError("stage 1: implement gate()")
