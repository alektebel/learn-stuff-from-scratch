"""Benchmark From Scratch (Mus) — stage 5: the reference distribution a betting
threshold is measured against

A scorecard wants to say "this model bluffs" — it bet from a weak hand. Weak
compared to WHAT? There is no absolute hand strength in Mus: 0.62 is a good hand
for Pares and an average one for Grande, and any fixed number is a threshold
somebody invented. So the reference is measured from the logs themselves, per
lance, out of the hands that were in the same situation as the hand being
judged.

DESIGN DECISION — the pool is the BET-CAPABLE decisions, not every decision.
    Only a seat whose `legal` actions included an aggressive verb was choosing
    under pressure; the rest passed because the engine let them do nothing else
    at that moment. Pooling every decision mixes the hands that faced a bet with
    the hands that never had the chance to make one, and since who gets the
    option depends on the table (a seat in front of an envite, a mano holding
    the lance), the resulting threshold measures the deal, not the hands. The
    reference must be the same for every model being compared, so it can only be
    built out of the situations all of them faced.

DESIGN DECISION — `MIN_REFERENCE` hands or no cut at all.
    A tercile of five hands is one hand of noise: the "bottom third" is a single
    hand, and every hand below it is compared against that. A cut of `None`
    means the band is `None` — no claim is made. This is the same instinct as
    stage 9's data-poor model and the course's other floors: an unmeasured
    number is reported as unmeasured, never as 0.0, and never as a threshold
    cooked from whatever happened to be in the log.

DESIGN DECISION — the cut is positional on the SORTED pool, and the boundary is
    inclusive at the bottom and exclusive at the top.
    `(vals[n // 3], vals[2 * n // 3])` is a tercile read off the data: the
    bottom third ends at the value that is a third of the way in, the top third
    starts after the value two thirds of the way in — and both cut values are
    hands that were actually played. That is why `s <= lo` is weak (the hand ON
    the bottom cut is the last hand of the bottom third) and `s > hi` is strong
    (the hand ON the top cut is still the last hand of the middle). An
    off-by-one here moves exactly one hand between two bands, every time, which
    is invisible in a single scorecard and biases every rate in stage 6.
    The pool is sorted first: the order the hands arrived in is an artefact of
    the deal, and a cut that depends on it moves between runs.

DESIGN DECISION — `AGGRESSIVE` is imported from stage 4.
    The course is cumulative: stage 4 owns which verbs are bets ("envido",
    "y-yo", "reenvido", "ordago" — a response like "quiero" is not one), and a
    second copy of that tuple here is a threshold that silently drifts the day
    stage 4 learns a new verb.

DESIGN DECISION — a lance is present in the dict as soon as one of its decisions
    was bet-capable, with a cut of `None` until enough hands were measured.
    "No cut" and "no lance" are different facts: the first says the reference is
    too thin to read, the second says this lance never presented a betting
    choice at all. Collapsing them into a missing key throws away the
    information a report needs ("Grande: 4 hands so far, no cut yet").

TODO: implement `can_bet`, `strength_terciles` and `strength_band`.
"""

# Stage 4's own tuple — see the design decision above. The course is cumulative;
# do not restate the verbs here.
from stage_04 import AGGRESSIVE

# The smallest pool that splits into three non-empty thirds. Five hands give a
# third of one hand.
MIN_REFERENCE = 6


def can_bet(decision):
    """Did this seat hold a live betting option at this decision?

    True only when the decision names a lance AND one of stage 4's aggressive
    verbs is in `decision["legal"]` — the engine's own answer to "what may this
    seat do right now?". A response ("quiero", "no-quiero") is not a bet.
    """
    raise NotImplementedError("stage 5: implement can_bet()")


def strength_terciles(decisions):
    """Per-lance cut points, `{lance: (lo, hi) | None}`.

    Pool `decision["strength"]` for every decision where `can_bet(decision)` and
    the strength was measured; sort each lance's pool; a pool shorter than
    `MIN_REFERENCE` yields `None` for that lance. A lance with no bet-capable
    decision is absent from the dict entirely. The result depends on the hands
    only — never on the model name, never on the order the decisions arrived in.
    """
    raise NotImplementedError("stage 5: implement strength_terciles()")


def strength_band(decision, cuts):
    """`"weak"`, `"medium"`, `"strong"`, or `None` when nothing can be said.

    `None` when `decision["strength"]` is None or the lance has no cut. `"weak"`
    when `strength <= lo`, `"strong"` when `strength > hi`, `"medium"`
    otherwise — the boundary is deliberate, and a check pins both ends.
    """
    raise NotImplementedError("stage 5: implement strength_band()")
