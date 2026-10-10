"""Benchmark From Scratch — stage 1 solution: the turn gate.

The reasoning lives in `stage_01.py`'s docstring (the design decisions are the
lesson); this file is the implementation. Fifteen lines, and every one of them is
a rule the rest of the benchmark rests on.
"""

from mus import IllegalAction

STATS_KEYS = ("turns", "rejections", "fallbacks", "llm_turns", "calls")


def new_stats():
    """A fresh, all-zero stats dict for one match."""
    return {key: 0 for key in STATS_KEYS}


def gate(table, seat, action, *, stats):
    """Offer one action to the table and report what happened."""
    if not isinstance(stats, dict):
        raise TypeError("stats must be the match's own dict, got %s"
                        % type(stats).__name__)
    try:
        table.apply(seat, action)
    except IllegalAction as exc:
        # The seat misbehaved: data, not a crash. The count is the numerator of a
        # behaviour, and it is NOT a turn — the position did not change.
        stats["rejections"] += 1
        return {"ok": False, "reason": str(exc), "turn": stats["turns"]}
    # Everything else propagates: our bug must not be filed as the model's.
    stats["turns"] += 1
    return {"ok": True, "reason": None, "turn": stats["turns"]}
