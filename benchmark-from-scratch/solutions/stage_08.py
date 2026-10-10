"""Benchmark From Scratch (Mus) — stage 8 solution: calibration and discrimination.

The reasoning lives in `stage_08.py`'s docstring (the design decisions are the
lesson); this file is the implementation.
"""

import math

#: The clip bound for the log-loss: the cost of the most confident possible miss
#: is `-ln(1e-6) = 13.815510557964274` nats. Kept public so that number can be
#: checked by a reader instead of trusted.
EPS = 1e-6


def _checked(pairs, caller):
    """The pairs as `(float(p), bool(y))`, or `ValueError` naming the first bad one.

    The reference's `_prob` returns `None` for a read that is not a number and
    clamps a `1.4` to `1.0`; both are silent, and a score computed after a silent
    clamp is a score for a prediction the model never made. Here a `bool` is not a
    probability (`True` is `1` to Python, so it would pass every arithmetic test as
    a perfect prediction), an out-of-range `p` is a bug in the caller, and an
    outcome that is not `True`/`False`/`1`/`0` is a category error.
    """
    out = []
    for index, pair in enumerate(pairs):
        try:
            p, y = pair
        except (TypeError, ValueError):
            raise ValueError("%s: pair %d is not a (p, y) pair: %r"
                             % (caller, index, pair))
        if isinstance(p, bool) or not isinstance(p, (int, float)):
            raise ValueError(
                "%s: pair %d: p=%r is not a probability — a probability is a "
                "number in [0, 1] and never a bool, because `True` is 1 to Python "
                "and would score as a model that was certain and right"
                % (caller, index, p))
        if not 0.0 <= p <= 1.0:
            raise ValueError(
                "%s: pair %d: p=%r is outside [0, 1] — a probability outside the "
                "unit interval is a bug in the caller (a percentage never divided "
                "by 100, a logit), and clamping it here would hide that bug from "
                "every number this stage prints" % (caller, index, p))
        if isinstance(y, bool):
            outcome = y
        elif isinstance(y, int) and y in (0, 1):
            outcome = bool(y)
        else:
            raise ValueError(
                "%s: pair %d: y=%r is not an outcome — an outcome is True/False "
                "(or 1/0), and a probabilistic label belongs in `p`"
                % (caller, index, y))
        out.append((float(p), outcome))
    return out


def brier(pairs):
    """Mean squared error of the probabilities; `None` when there are no pairs."""
    pairs = _checked(pairs, "brier")
    if not pairs:
        return None
    return sum((p - float(y)) ** 2 for p, y in pairs) / len(pairs)


def logloss(pairs):
    """Mean negative log-likelihood, each `p` clipped to `[EPS, 1 - EPS]` first."""
    pairs = _checked(pairs, "logloss")
    if not pairs:
        return None
    total = 0.0
    for p, y in pairs:
        # The clip is not decoration: ln(0) is -inf and one such pair turns the
        # mean into -inf, erasing every other prediction in the same score.
        p = min(max(p, EPS), 1.0 - EPS)
        total -= math.log(p) if y else math.log(1.0 - p)
    return total / len(pairs)


def auc(pairs):
    """Mann-Whitney ranking quality in `[0, 1]`; `None` when a class is missing."""
    pairs = _checked(pairs, "auc")
    if not pairs:
        # No data at all: `None`, exactly like Brier and the log-loss. There is no
        # pair to order and a 0.0 would read as the worst possible ranking of a
        # sample that does not exist.
        return None
    pos = [p for p, y in pairs if y]
    neg = [p for p, y in pairs if not y]
    if not pos or not neg:
        # One class present is a DIFFERENT kind of no-data, and the same answer:
        # with no negative to compare against, `P(positive > negative)` is not
        # estimable, and 0.5 would be a claim about a game that was never played.
        return None
    # The all-pairs sum IS the definition (Mann-Whitney U). A tie counts a half:
    # counting it as a win scores a model whose read is one constant at 1.0.
    wins = sum(1.0 if a > b else 0.5 if a == b else 0.0
               for a in pos for b in neg)
    return wins / (len(pos) * len(neg))


def reliability(pairs, *, bins=5):
    """Predicted probability against the realised rate, per bin, ascending."""
    if bins < 1:
        raise ValueError("reliability: bins=%r — a table with no bins holds no "
                         "information, and a bin width of 1/0 is not a width"
                         % (bins,))
    pairs = _checked(pairs, "reliability")
    if not pairs:
        return []
    buckets = [[] for _ in range(bins)]
    for p, y in pairs:
        # p == 1.0 computes int(bins) == bins, one past the last bin; the clamp is
        # what keeps the most confident predictions in the table.
        buckets[min(int(p * bins), bins - 1)].append((p, y))
    out = []
    for i, bucket in enumerate(buckets):
        if not bucket:
            # A bucket with nothing in it is not a measurement: `n: 0, actual:
            # 0.0` cannot be told apart from a bin whose predictions all missed.
            continue
        out.append({
            "bin": "%g-%g" % (i / bins, (i + 1) / bins),
            "n": len(bucket),
            "mean_p": round(sum(p for p, _ in bucket) / len(bucket), 3),
            "actual": round(sum(1 for _, y in bucket if y) / len(bucket), 3),
        })
    return out
