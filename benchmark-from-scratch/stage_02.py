"""Benchmark From Scratch — stage 2: the match loop.

DESIGN DECISION — why is the as-dealt snapshot taken before the hand is played?
    Because a hand is not its deal. The mus exchange replaces cards, so a
    snapshot taken when the hand is over records hands that were never dealt:
    two runs of the same seed then look like two different deals and the whole
    point of seeding is gone. What paired analysis compares must be the cards as
    dealt, saved the moment the hand starts, before any seat can touch them.

DESIGN DECISION — why is a retry not a turn?
    A turn is one decision that changed the position. A seat that answers with
    nonsense three times before finding a legal move took one turn and made three
    calls, and stage 1 already counts the refusals in their own bucket. If the
    loop charged each attempt as a turn, the same seat would look three times
    busier and — because a turn count is a denominator elsewhere — quietly better
    behaved, and the record would contain three lines for one decision.

DESIGN DECISION — why does the fallback come from the engine, and never from
    the legal action names?
    `legal_actions` returns NAMES: "descartar" is legal and carries no payload,
    so a fallback built out of a name is refused the moment a real payload is
    required, and the refusal is filed against the seat that never made it. The
    engine already knows what a reasonable legal action looks like in each phase
    (`default_action`), so the harness asks it — the same rule as stage 1: never
    re-derive what the table already knows.

DESIGN DECISION — why does a degraded match stop instead of finishing?
    A match whose turns are mostly the harness's own defaults is measuring the
    harness. Letting it run to the last hand produces a complete-looking row
    whose numbers are the loader's, and the loader is not in the comparison. So
    the rail trips (a hand that has taken more actions than `turn_limit`, or more
    fallbacks than the warmup allows), the row says `degraded`, and its numbers
    are what the match actually managed — the analysis gate decides separately
    whether a match that did finish is publishable.

DESIGN DECISION — why does a harness bug get its own status instead of being
    swallowed?
    `IllegalAction` is the seat misbehaving: data. Anything else is our program
    broken: a missing field, a table that cannot answer, a policy that raised.
    Reporting that as `done` puts a harness bug into the results as a data point,
    and the first sign of trouble would be a metric nobody can explain. It gets
    `status: "error"` and the exception's words in `note` — labelled, excluded,
    and visible.

DESIGN DECISION — why does `llm_turns` count the seats that are models?
    Because the fallback rate is a statement about a MODEL, and its denominator
    has to be that model's own decisions. Counting every seat's turns lets a
    baseline that never falls back dilute a model that mostly does, until the
    model's quarter of the decisions looks healthy. The counter that the
    fallback rate divides by must be the counter of the thing being judged.

The row is the frozen shape plus `teams` (the two team labels, from `names`) and
`note` (why a degraded or errored match stopped). Call it once per match.

TODO: implement `DegradedMatch` and `run_match`.
"""

FALLBACK_WARMUP = 10


class DegradedMatch(Exception):
    """The match stopped being about the seats: the turn or fallback rail fired.

    Carries `rail` ("turn_limit" or "fallbacks") and the engine's `note`.
    """

    def __init__(self, rail, note=""):
        super().__init__("%s: %s" % (rail, note))
        self.rail = rail
        self.note = note


def run_match(table, seats, *, names, llm=None, hands, turn_limit=200, retries=4,
              on_hand=None, log=None):
    """Play `hands` hands at `table` and return the match's row.

    - `seats` is one callable `(table, seat, legal) -> decision` for everybody,
      or four of them in seat order. A decision is what `Table.apply` accepts,
      plus an optional `confidence` (a probability, or None).
    - `names` are the four seat labels; `llm` marks which seats are models,
      defaulting to none of them.
    - `retries` is how many times a seat is asked again in one turn after the
      engine refused it; a turn that never produces a legal action gets the
      engine's own default and is counted as a fallback.
    - `on_hand(record)` is called with each finished hand's record.
    - `log.record(line)` receives one decision record per turn (stage 3's
      `DecisionLog`).

    Returns the row: the match's identity, its counters, the per-hand records'
    totals, and the deals as dealt — with `status` "done", or "degraded"
    (a rail fired) or "error" (a failure that was not the engine refusing).
    """
    raise NotImplementedError("stage 2: implement run_match()")
