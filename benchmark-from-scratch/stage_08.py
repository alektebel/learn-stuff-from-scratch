"""Benchmark From Scratch (Mus) — stage 8: calibration and discrimination — a
probability is graded against what happened, a ranking against the order things
happened in.

The read channel is the only place a model's own number can be checked against
the world on the spot: `read={"p_win_lance": 0.7}` is a claim, and the hand is
either won or lost a moment later. Two DIFFERENT questions are asked of a list of
such claims:

- **calibration** — of the hands a model called 70% wins, how many did it win?
  `brier` and `logloss` are the two proper scores, and `reliability` is the table
  that shows the shape of the error bin by bin instead of collapsing it to one
  number;
- **discrimination** — does the model rank the hands it won above the hands it
  lost, even if every number it emits is miscalibrated? `auc`.

`pairs` is the shared input of all four: a list of `(p, y)`, `p` a number in
[0, 1], `y` the outcome as `True`/`False` (or `1`/`0`). Stage 6's read channel
produces them — `(read["p_win_lance"], would_win)` and
`(read["p_opp_fold"], opponent folded)` — and nothing else about this stage knows
where they came from.

DESIGN DECISION — why refuse a bad probability here, when the reference clamps
    silently?
    The reference's own `_prob` turns a read that is not a number into `None` and
    clamps a `1.4` to `1.0`, both without saying so. A score is a statement about
    ONE model's prediction, and a clamp applied before the score means the number
    scored is not the number the model produced; two models' scores then rest on
    different inputs and nobody can tell by looking at the table. The `bool` is
    the sharpest case: `True` IS `1` to Python, so `p=True` sails through every
    arithmetic check as a perfect prediction and a read of `True` scores as if the
    model had said 100%. An out-of-range `p` is a bug in OUR caller — a percentage
    that was never divided by 100, a logit, a probability of 1.2 — and a score
    computed after silencing that bug is worse than a crash. So validation
    happens once, up front, and raises `ValueError` naming the pair. Same reason
    an outcome that is not `True`/`False`/`1`/`0` is refused: a probabilistic
    LABEL belongs in `p`, and a `y` of 0.5 is a category error the score would
    silently average into a number.

DESIGN DECISION — why is the Brier error SQUARED?
    `mean((p - y)**2)` punishes the confident miss far harder than the hedged one:
    0.9 on a hand that lost costs 0.81 while 0.6 costs 0.36, where the mean
    ABSOLUTE error scores them 0.9 and 0.6 — nearly the same. A calibration score
    exists to expose the model that is confident and wrong, because that is the
    model that bets three piedras too many. The second half of the choice is the
    base rate: a coin-flip read against a half-and-half outcome is **0.25**, not
    0.5, because it is the squared error that is averaged. A mean absolute error
    of 0.5 for a coin flip is the same number as the outcome's own spread, so it
    cannot tell the coin apart from a model that learned nothing — which is the
    number a reader would use to decide whether the read channel works at all.

DESIGN DECISION — why clip the log-loss at `EPS`, and is that not a lie?
    `ln(0)` is `-inf` and the mean of a list containing `-inf` is `-inf`, so ONE
    pair at `p = 0.0` with `y = True` erases every other pair in the same score.
    `p` of 0.0 or 1.0 is not exotic: it is exactly what a read the model rounds to
    "certain" produces, and `logloss([(0.0, True)])` would raise a `math domain
    error` on a console-facing key. Clipping to `[EPS, 1 - EPS]` first makes the
    worst possible prediction cost a large FINITE number, `-ln(1e-6) ~= 13.8155`
    nats, and leaves the order of the scores unchanged (`-ln` is monotone), so a
    better-calibrated model still scores lower. The number reported is the score
    of a clipped probability and it is finite; the alternative is not a score at
    all. The clip is per pair and only for the log-loss: `0.0` and `1.0` are legal
    probabilities for Brier and for a ranking.

DESIGN DECISION — why is no data `None` instead of `0.0`?
    Brier of an empty list is not 0.0 ("never wrong") and log-loss of it is not
    0.0 ("no loss"): both readings put a model that was never asked anything at
    the top of a table that is used to rank models on this exact channel. `None`
    says what is true — there is no data — and forces the caller to print `--`
    rather than a number nobody measured. A `auc` with no pairs is `None` for the
    same reason and one more: with no pairs there is also no pair to order, so the
    probability is not estimable at all. `reliability([])` is `[]`: nothing
    measured, nothing shown.

DESIGN DECISION — why is the AUC undefined with one class present?
    The AUC is `P(the score of a positive exceeds the score of a negative)`. With
    every hand won there is no negative to compare against, so the probability is
    not estimable — and reporting 0.5 would claim the model's ordering of two
    classes it never had to separate was a coin flip, a statement about a game
    that was not played. In a small sample this is the common case (a model that
    wins four hands in a row has no losing hand to rank), and a table that shows
    `0.50` there reads as "uninformative" when the truth is "unmeasured". `None`.

DESIGN DECISION — why the `O(n*m)` all-pairs form instead of sorting?
    `(#(pos, neg) pairs correctly ordered) / (|pos| * |neg|)` IS the definition
    (the Mann-Whitney U statistic), ties counting one half: a tie is not a win,
    because a model whose read is a single constant orders nothing and would
    otherwise score 1.0 — a perfect ranker that ranks nothing. The sort-based
    `O(n log n)` form is an optimisation whose tie handling is easy to get wrong
    by half a comparison, and at the scale of a match (tens of reads per seat) it
    buys nothing while hiding the definition. Count the pairs, don't sort.

DESIGN DECISION — why clamp the bin index, and why skip empty bins?
    `p == 1.0` computes `int(1.0 * bins) == bins`, one past the last bin: without
    `min(..., bins - 1)` the model's most confident predictions raise
    `IndexError`, or get dropped in a `try` — and the top of the reliability table
    is precisely where a model's overconfidence lives. With the clamp, `1.0` is
    the last bin and its label says so (`0.8-1` at five bins); the interval is
    left-closed, so `0.2` is in the 0.2-0.4 bin and `0.0` is in the first. Empty
    bins are SKIPPED rather than reported as `{"n": 0, "actual": 0.0}`: a row of
    zeros is a fabricated measurement — a reader cannot tell it from a bin whose
    predictions all missed — and in a ten-bin table over twenty reads the
    fabricated rows outnumber the real ones, which is how a calibration table
    starts lying with correct arithmetic.

TODO: implement `brier`, `logloss`, `auc` and `reliability`.

    EPS                       # the clip bound: 1e-6, and it is public because
                              # the reported loss of a certain-but-wrong read is
                              # `-ln(EPS)` and a reader has to be able to check it

    brier(pairs) -> float | None
        `mean((p - float(y))**2)`, and `None` for an empty list. Squared, because
        the mistake that matters is being confident and wrong (see above).

    logloss(pairs) -> float | None
        `mean(-ln(p) if y else -ln(1 - p))` with each `p` clipped to
        `[EPS, 1 - EPS]` BEFORE the log, and `None` for an empty list. `y` is the
        outcome: the loss is taken on the probability of what happened.

    auc(pairs) -> float | None
        The share of `(positive, negative)` pairs the model ordered correctly,
        with a tie counting 0.5. `None` when either class is empty — including the
        empty input, where both are. The all-pairs form is the definition.

    reliability(pairs, *, bins=5) -> [ {"bin", "n", "mean_p", "actual"}, ... ]
        Bucket index `min(int(p * bins), bins - 1)`; a bucket is
        `{"bin": "%g-%g" % (i / bins, (i + 1) / bins), "n": len(bucket),
        "mean_p": round(mean of the p's, 3), "actual": round(share that is true, 3)}`.
        Buckets with nothing in them are skipped, the surviving rows are in
        ascending order, and `bins` below 1 is a `ValueError` (a bin width of 1/0
        is not a width).

All four validate their input the same way and refuse the same things: `p` must
be a number in [0, 1] and never a `bool`, and `y` must be `True`, `False`, `1` or
`0`. Factoring that check into one helper is part of the answer.
"""

import math

#: The clip bound for the log-loss. `-ln(EPS)` is the cost of the most confident
#: possible miss (13.815510557964274 nats), and keeping it in one named place is
#: what lets a reader check that number instead of trusting it.
EPS = 1e-6


def brier(pairs):
    """Mean squared error of the probabilities; `None` when there are no pairs."""
    raise NotImplementedError("stage 8: implement brier()")


def logloss(pairs):
    """Mean negative log-likelihood, each `p` clipped to `[EPS, 1 - EPS]` first."""
    raise NotImplementedError("stage 8: implement logloss()")


def auc(pairs):
    """Mann-Whitney ranking quality in `[0, 1]`; `None` when a class is missing."""
    raise NotImplementedError("stage 8: implement auc()")


def reliability(pairs, *, bins=5):
    """Predicted probability against the realised rate, per bin, ascending."""
    raise NotImplementedError("stage 8: implement reliability()")
