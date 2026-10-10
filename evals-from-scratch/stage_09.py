"""Evals From Scratch — stage 9: ten configs, one winner, no correction

DESIGN DECISION — the best of many tests is not a test.
    Ten variants, each compared against the baseline at alpha = 0.05, will hand
    you a "significant" winner about 40% of the time when none of them is
    different: 1 - (1 - 0.05) ** 10. The number that comes out of the winner's
    row is the same number either way, which is why this ships. Holm's step-down
    is the correction to apply: it controls the probability of ANY false
    rejection across the family, and it is uniformly more powerful than
    Bonferroni's divide-by-m.

    The rule of thumb that costs nothing: decide the family before you look at
    the p-values. Choosing which tests count (and which variant is "the"
    comparison) after seeing the results is the other half of this bug, and no
    correction fixes it.

TODO: implement

    holm(p_values) -> list[float]
        Adjusted p-values in the input order, by the step-down procedure:
        sort ascending; the i-th smallest (1-based) is multiplied by (m - i + 1);
        the result is passed through a running maximum (so adjusted values are
        non-decreasing in the sorted order, never above 1.0).

    significant(p_values, alpha=0.05) -> dict
        {"rejected": [bool, ...] in input order, "adjusted": [...],
         "thresholds": [...]}
        Step-down: the i-th smallest p-value is rejected when it is <= alpha /
        (m - i + 1), and the moment one fails, everything larger fails too.
        The first result must agree with `holm`: rejected[i] is
        adjusted[i] <= alpha.
"""


def holm(p_values):
    raise NotImplementedError("stage 9: implement holm()")


def significant(p_values, alpha=0.05):
    raise NotImplementedError("stage 9: implement significant()")
