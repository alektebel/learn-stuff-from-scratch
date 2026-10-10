"""Benchmark From Scratch (Mus) — stage 5 solution: the reference distribution a
betting threshold is measured against.

The reasoning lives in `stage_05.py`'s docstring (the design decisions are the
lesson); this file is the implementation. One sentence each:

    * a hand belongs in the reference only if its seat actually faced a betting
      choice, and only if the engine measured it;
    * a tercile is read from at least `MIN_REFERENCE` such hands, and a lance
      with fewer gets no cut rather than a threshold invented from a handful;
    * the cut is a sorted positional one -- `vals[n // 3]` and `vals[2 * n // 3]`
      -- with the bottom cut inclusive (`s <= lo` is weak) and the top cut
      exclusive (`s > hi` is strong).
"""

# The betting verbs are stage 4's, not a second copy: the course is cumulative,
# and a reference threshold that drifts the day stage 4 learns a new verb is a
# threshold nothing else agrees with.
from stage_04 import AGGRESSIVE

# Six hands is the smallest reference that splits into three non-empty thirds:
# with five, one third of the distribution is a single hand.
MIN_REFERENCE = 6


def can_bet(decision):
    """Did this seat hold a live betting option at this decision?

    Two conditions, and both are needed: the engine's `legal` list has to offer
    an aggressive action (so a seat that could only pass is not in the
    reference), and the decision has to name a lance (a bet with no lance has no
    distribution to be compared against).
    """
    if decision.get("lance") is None:
        return False
    return any(name in (decision.get("legal") or []) for name in AGGRESSIVE)


def strength_terciles(decisions):
    """Per-lance cut points for weak / medium / strong hands.

    The pool is the strength of every decision where the seat COULD have bet and
    the engine measured a strength, per lance. A lance enters the reference as
    soon as one of its decisions was bet-capable; if fewer than `MIN_REFERENCE`
    hands were measured its cut is `None` -- never a threshold invented from a
    handful of hands. The pool is sorted first, so the cut does not depend on
    the order the hands arrived in.
    """
    pools = {}
    for decision in decisions:
        if not can_bet(decision):
            continue
        pool = pools.setdefault(decision.get("lance"), [])
        if decision.get("strength") is not None:
            pool.append(decision["strength"])
    cuts = {}
    for lance, vals in pools.items():
        vals.sort()
        n = len(vals)
        if n < MIN_REFERENCE:
            cuts[lance] = None
            continue
        cuts[lance] = (vals[n // 3], vals[2 * n // 3])
    return cuts


def strength_band(decision, cuts):
    """`"weak" | "medium" | "strong" | None` for one decision against the cuts.

    None when there is nothing to compare: no strength was measured, or the
    lance has no cut (too few hands, or no bet-capable decision at all). The
    boundary is deliberate -- `s <= lo` is weak (the bottom cut is one of the
    hands the cut was read from) and `s > hi` is strong (medium keeps the hand
    sitting on the top cut).
    """
    lance = decision.get("lance")
    strength = decision.get("strength")
    if lance is None or strength is None:
        return None
    cut = cuts.get(lance)
    if cut is None:
        return None
    lo, hi = cut
    if strength <= lo:
        return "weak"
    if strength > hi:
        return "strong"
    return "medium"
