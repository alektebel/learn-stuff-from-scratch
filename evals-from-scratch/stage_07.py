"""Evals From Scratch — stage 7: what the judge is worth (kappa, and the threshold)

DESIGN DECISION — agreement is not accuracy, and the base rate is why.
    A judge that answers "pass" to everything agrees with 85% of a label set
    that is 85% passes, and it is worthless: it has learned nothing and it
    cannot find the 15% that matter. Cohen's kappa subtracts the agreement you
    would get by chance from both the observed agreement and the ceiling, which
    is what makes it the number to report. Report agreement too, because kappa
    is unstable when one class is rare.

DESIGN DECISION — the pass/fail threshold is a decision with a cost.
    A judge that returns 1-5 is a scorer; the pipeline needs a decision. Where
    to put the cut is not a matter of taste: it trades false passes against
    false failures on the labelled set, and that trade has a price in your
    product. Sweep it and look at the confusion matrix instead of defaulting to
    the midpoint because it looks neutral.

TODO: implement

    confusion(judgments, labels) -> dict
        Both are iterables of booleans (True = pass). Returns
        {"tp", "fp", "tn", "fn"} counting judgment vs label.

    agreement(judgments, labels) -> float      (tp + tn) / n, 0.0 when n == 0

    cohen_kappa(judgments, labels) -> float
        (p_observed - p_chance) / (1 - p_chance), where p_chance is the
        agreement expected from the two marginals. A constant judge scores ~0.0
        whatever its accuracy; a perfect judge scores 1.0. When p_chance == 1
        (both raters constant and identical) return 1.0: there was no room to
        disagree. When n == 0 return 0.0.

    threshold_for(scores, labels, thresholds=None) -> dict
        `scores` are floats (a judge's 1-5), `labels` the human booleans. For
        every threshold in the sweep (default 1.5, 2.5, 3.5, 4.5), decide
        pass = score >= threshold, and compute the confusion matrix and the F1
        of the PASS class. Returns
        {"threshold", "f1", "precision", "recall", "confusion", "sweep": [...]}
        for the threshold with the best F1, ties to the smallest threshold.
        F1 of a class with no predicted positives and no actual positives is
        1.0; with none of either, 0.0.
        An empty calibration set, or two sequences of different lengths, is a
        ValueError: a sweep over no labels reports a perfect score over no data.
"""


def confusion(judgments, labels):
    raise NotImplementedError("stage 7: implement confusion()")


def agreement(judgments, labels):
    raise NotImplementedError("stage 7: implement agreement()")


def cohen_kappa(judgments, labels):
    raise NotImplementedError("stage 7: implement cohen_kappa()")


def threshold_for(scores, labels, thresholds=None):
    raise NotImplementedError("stage 7: implement threshold_for()")
