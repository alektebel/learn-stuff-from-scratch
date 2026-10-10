"""Benchmark From Scratch (Mus) — stage 7: the low-variance outcome — the piedras
the hands awarded, not the vaca the match happened to end on.

DESIGN DECISION — why is the outcome the piedras PER HAND, and not the vaca count?
    The vaca is a THRESHOLD: the match stops the moment a team crosses forty
    points, so "who took the vaca" is one bit decided by whichever hand ran last,
    and a team that outplayed the other for nine hands loses that bit to a
    one-point swing. Sum the piedras the hands awarded and divide by the hands
    played and the noise averages out; that is what makes the number joinable
    across seeds, and it is why a scorecard keeps hundreds of hands instead of
    one bit. The vacas and the hand wins are still REPORTED here — they are the
    shape of the match — but they are not the outcome.

DESIGN DECISION — why `hand_gain_*` and NEVER `points_a`/`points_b`?
    Because the point counters are WIPED, and that is what a vaca is: the forty
    points a team reached get banked in `vacas_a` and the counter goes back to
    zero — both counters, the loser's included. So a match with a vaca in it has
    counters that read LESS the better a team played: in this stage's fixture the
    six hands awarded team A 42 piedras and left a counter reading 2, because one
    vaca's worth (forty points) was removed on the way. `hand_gain_*` is
    incremented next to the counter and is never reset, so it is the only column
    that remembers what each hand was worth. A rate summed from `points_*` is not
    a noisier outcome, it is a wrong one, and it is wrong in the direction that
    punishes the team that banked the vaca.

DESIGN DECISION — why do the vacas come from the LAST record and the wins from the
    records?
    `vacas_a`/`vacas_b` on a record are a RUNNING TOTAL, not that hand's delta: the
    records of a match where the vaca fires at hand 4 read 0, 0, 0, 1, 1, 1 — the
    same vaca printed once per hand that followed it. Adding them up counts it five
    times, and only the LAST record holds where the running total ended.
    `hand_winner` is the opposite: it is per hand — 0 for team A, 1 for team B, and
    None when the two teams took the same number of piedras, which is a TIE, so a
    win for neither side.

DESIGN DECISION — why is the per-hand divisor the hands in the LIST?
    Because the list is whatever the caller hands over, and the paired design hands
    over the hand records of BOTH orientations of a matchup: two matches, whose hand
    indexes both start at 1. The divisor is the number of hands in the list — never
    the last record's `hand`, which is one match's count (48 piedras over 8 hands
    reads 24.0 instead of 6.0), and never the number of records, because the log
    holds the per-decision rows too.

PINNED — an empty list returns `{}`.
    A match with no hand records has NO outcome, and `{}` is how this stage says so.
    A dict of zeros is indistinguishable from a match where both teams really scored
    nothing, and a caller that prints it reports 0.000 piedras per hand for a match
    that never ran. This stage reports the absence; the caller decides what to print.

TODO: implement `outcome`.
"""


def outcome(hand_records):
    """The low-variance outcome of the hands in `hand_records`, or `{}` if none.

    `hand_records` is a log's rows and only the rows whose `kind` is `"hand"` are
    hands (the per-decision rows sit in the same log). A hand record carries
    `hand_gain_a`, `hand_gain_b` — what that hand awarded each team — plus
    `hand_winner` (0, 1, or None for a tie), `vacas_a`, `vacas_b` (the running vaca
    total after that hand) and `hand` (the hand's index within its match).

    Returns, over the hand records only:

        hands                  how many hand records the list holds
        piedras_a / piedras_b  the sum of the hands' `hand_gain_a` / `hand_gain_b`
        piedras_per_hand_a/_b  piedras / hands, to three decimals
        piedras_diff_per_hand  (piedras_a - piedras_b) / hands, to three decimals
        vacas_a / vacas_b      the running vaca totals, read from the LAST record
        hand_wins_a/_b         how many hands `hand_winner` gives A / B; a tie
                               (None) counts for neither side

    An empty list returns `{}`.
    """
    raise NotImplementedError("stage 7: implement outcome()")
