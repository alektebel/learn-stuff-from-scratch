"""Evals From Scratch — stage 8: is the difference real? Paired, always paired

DESIGN DECISION — the same examples, or you are measuring the examples.
    Two systems evaluated on the same 200 items differ only in how the items
    interact with each system; that shared difficulty is what a paired test
    cancels. Resampling the two sides independently throws that structure away
    and returns an interval several times wider — wide enough that most real
    improvements stop being visible. The pairing is not a refinement, it is
    what makes a 5-point difference detectable on a few hundred items.

DESIGN DECISION — an interval that contains zero is not a win.
    The output of this stage is not a p-value to quote but a decision with
    three outcomes: A is better, B is better, or the data does not say. Anything
    that reports the third as the first is how a leaderboard becomes a
    coin flip with a change log.

TODO: implement

    binom_two_sided(k, n) -> float
        The exact two-sided binomial p-value for k successes in n trials at
        p = 0.5 (the convention for McNemar's exact test): 2 * min(P(X <= k),
        P(X >= k)), capped at 1.0. Use the standard library only — no SciPy.

    mcnemar(a, b) -> dict
        `a` and `b` are booleans per example, the SAME examples in the same
        order (pass = True). Only the discordant pairs carry information:
            {"a_only": count(a pass, b fail), "b_only": count(a fail, b pass),
             "p": binom_two_sided(a_only, a_only + b_only)}
        With no discordant pairs p is 1.0 — identical systems, on this data.

    paired_bootstrap(a, b, seed=0, n=2000, alpha=0.05) -> dict
        mean(a) - mean(b) over the same items, with a percentile interval from
        resampling ITEMS (with replacement, both sides of an item together):
            {"mean_diff", "lo", "hi", "n"}
        random.Random(seed), so the same seed returns the same interval.

    independent_ci(a, b, seed=0, n=2000, alpha=0.05) -> dict
        The same difference, resampled independently per side — the wrong
        analysis, kept here so the check can show how much wider it is.

    decide(a, b, alpha=0.05, seed=0) -> "a" | "b" | "inconclusive"
        "a" when the paired interval lies entirely above zero, "b" when
        entirely below, "inconclusive" when it contains zero. This is a
        one-sided reading of a two-sided interval, and that is on purpose: the
        question a gate asks is "is it better", not "is it different".
"""


def binom_two_sided(k, n):
    raise NotImplementedError("stage 8: implement binom_two_sided()")


def mcnemar(a, b):
    raise NotImplementedError("stage 8: implement mcnemar()")


def paired_bootstrap(a, b, seed=0, n=2000, alpha=0.05):
    raise NotImplementedError("stage 8: implement paired_bootstrap()")


def independent_ci(a, b, seed=0, n=2000, alpha=0.05):
    raise NotImplementedError("stage 8: implement independent_ci()")


def decide(a, b, alpha=0.05, seed=0):
    raise NotImplementedError("stage 8: implement decide()")
