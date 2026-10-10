"""Evals From Scratch — stage 6: the judge, and the order you showed it in

DESIGN DECISION — every pair is judged twice, in both orders.
    A judge has a position bias: shown (A, B) it prefers A more often than it
    would prefer A if it were shown second. Zheng et al. measured it, and it is
    large enough to invent a winner out of two identical answers. The correction
    costs one extra call per pair and consists of exactly this: swap the order,
    and count only what survives the swap.

DESIGN DECISION — a judge with no human label is a hypothesis, not a metric.
    `win_rate` is a number about a model you have not calibrated (stage 7 does
    that). What this stage must deliver is the bias measurement, because that is
    the part that is decided by the data rather than by the judge's opinion:
    when the same answer wins in both positions, that is a preference; when the
    first-presented answer wins, that is the prompt layout.

TODO: implement

    run_pairwise(judge, pairs, swap=True) -> dict
        `judge` is a callable taking (first, second) and returning "first",
        "second" or "tie" — a stand-in for a model, so this stage needs no API.
        `pairs` is an iterable of {"id", "a", "b"}.
        With swap=True each pair is judged twice: as (a, b) and as (b, a).

        Returns:
            {"n", "a_wins", "b_wins", "ties", "flips", "position_bias",
             "agreement", "win_rate_a"}
        a_wins / b_wins: the DEBIASED counts — each judged order contributes
        half a win, so a judge that always answers "first" produces a_wins ==
        b_wins and a win rate of 0.5.
        flips: pairs whose winner changed with the order (ties excluded on
        either side) — the raw evidence of position bias. The first-presented
        answer winning both times IS a flip.
        win_rate_a = (a_wins + 0.5 * ties) / n, so a judge with no opinion and
        a judge with a pure position bias both land at 0.5.
        position_bias = flips / n. agreement = 1 - position_bias.
        With swap=False the same keys are returned, but the counts are the raw
        single-order ones and flips/position_bias are 0 — which is exactly the
        report that invents winners, and why the check compares the two.
"""


def run_pairwise(judge, pairs, swap=True):
    raise NotImplementedError("stage 6: implement run_pairwise()")
