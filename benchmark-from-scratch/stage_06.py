"""Benchmark From Scratch (Mus) — stage 6: the risk half of the scorecard — does
this seat BET well?

A scorecard that only counted wins would call every bold player good and every
cautious one bad. The interesting question is not what the seat won, it is what
it was WILLING to risk and whether the risk was priced: did it push from weak
hands (bluff), did weak hands fold to it (bluff success), did it fold lances it
was winning (fold error) and pay off lances it was losing? Those numbers are this
stage.

DESIGN DECISION — a bluff is a BET FROM A WEAK HAND, never a bet that lost.
    The tempting proxy — "bet and then lost the lance" — measures the BASE RATE
    of the game, not the player: with two hands a team wins any lance about half
    the time, so under that definition every seat bluffs about 50% and the metric
    cannot tell the random policy from the disciplined one. A seat that bets
    eight strong hands and loses all eight has bluffed ZERO times. The band comes
    from stage 5, so "weak" means "weak among the hands that faced this same
    betting choice in this same lance", not "a number I chose".

DESIGN DECISION — the answer to a bet is stage 4's LINK, keyed by the
    aggressor's own identity.
    Two ways to be wrong here. Scanning forward inside this stage would re-derive
    a rule stage 4 already owns, and re-deriving it is how a partner's pass gets
    counted as the answer to your envite (the aggressor's own team answering
    itself). Keying the link by MODEL or by seat would also collapse two seats of
    one model that bet in the same lance into one answer. The key is
    `(hand, lance, aggressor_turn)` — the aggressor, exactly.

DESIGN DECISION — a called bluff is only PAID when the lance is lost.
    `bluff_called` counts every time the opposition called or raised a weak-hand
    bet. That is a fact about the bettor's risk, not yet about its cost: a call
    to a bluff that WOULD have won is a pot the bettor collects. So the stake
    leaves the bettor's pocket only when `would_win is False`, and that is the
    number `stake_lost_called_bluffs` sums — the loss side of `fold_equity`.
    Charging every call reports a profitable bluff as a loss.

DESIGN DECISION — fold_error and payoff need a bet from the OTHER team.
    Folding to the PARTNER's envite is not a fold error: the team's points are
    the team's points, and the seat was never paying an opponent. So both numbers
    require `holder_team is not None and holder_team != decision["team"]`, and a
    decision whose truth is unknown (`would_win is None`, a drawn lance) is
    neither a mistake nor a payoff.

DESIGN DECISION — a rate with no denominator is None, never 0.0.
    A seat that never faced a bet has no fold_error_rate; reporting 0.0 says it
    never made a fold error, which is what a perfect player reports, and a table
    sorted on that column puts the seat that was never tested at the top. Every
    rate here is `float | None`, and None means "was never asked" — the same rule
    stage 5 lays down for a cut it cannot measure.

DESIGN DECISION — `weak_hand_bet_rate` divides by the WEAK OPPORTUNITIES.
    The question is "when this seat held a weak hand and COULD bet, how often did
    it push?" — so the denominator is the weak slices of its own `bet_chances`,
    not `aggressive` (which answers "of my bets, how many were weak?" — that is
    `bluff_rate`) and not `bet_chances` (which mixes the weak hands with the
    strong ones, so a seat that never held a weak hand scores 0). Three different
    questions, three different denominators, and this is the one that separates
    the heuristic policy from the random one.

TODO: implement `scorecard`.
"""

#: Stage 4 owns which verbs are bets and stage 5 owns what "weak" means; this
#: stage only reads them, so the three stages can never disagree about a bet.
from stage_04 import AGGRESSIVE, link_responses
from stage_05 import can_bet, strength_band, strength_terciles


def scorecard(decisions, key="model"):
    """One risk metric dict per distinct `str(decision.get(key))`, in log order.

    `decisions` is the frozen decision log (contract §2), in log order, possibly
    spanning several hands, lances and models; `key="seat"` buckets by
    `str(decision["seat"])` instead. Every counter in the returned dict is an
    int and every rate a `float | None`:

        decisions, aggressive (an aggressive verb AND a named lance), bet_chances
        (stage 5's `can_bet`), aggression_rate = aggressive / bet_chances,
        bluffs (a bet from the WEAK band), value_bets (a bet from the STRONG
        band), bluff_rate = bluffs / aggressive, weak_hand_bet_rate = bluffs /
        the weak slices of bet_chances, value_bet_rate = value_bets / aggressive,
        avg_strength_when_betting (mean over the aggressive decisions with a
        measured strength, rounded to 3dp),
        bluff_folded / bluff_called / bluff_success = folded / (folded + called),
        value_folded / value_called / value_bet_fold_rate,
        stake_won_folds, stake_lost_called_bluffs, fold_equity (their difference),
        faced_winning / fold_error / fold_error_rate,
        faced_losing / payoff / payoff_rate.

    `bluff_called` and `value_called` count stage 4's `"call"` AND `"raise"` — a
    raise is the opposition declining to fold, which is the same news to the
    bettor, and lumping it into nothing would drop the loudest answers out of
    every success rate.
    """
    raise NotImplementedError("stage 6: implement scorecard()")
