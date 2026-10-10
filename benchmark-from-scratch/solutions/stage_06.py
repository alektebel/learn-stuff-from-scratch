"""Benchmark From Scratch (Mus) — stage 6 solution: the risk half of the
scorecard.

See `stage_06.py` for the design decisions; this is the body. One sentence each:

    * a bluff is a bet from the WEAK band of its own lance, never a bet that
      lost — with two hands a team wins any lance about half the time, so "bet
      and lost" measures the base rate, not the player;
    * the answer to a bet is stage 4's link, and it is keyed by the aggressor's
      own identity (hand, lance, turn), so a partner's pass is not an answer and
      two aggressors in one lance each get their own;
    * a called bluff is only PAID when the lance is lost: a call to a winning
      lance is a call the bettor wins;
    * a rate with no denominator is `None` — an unmeasured number is reported as
      unmeasured, never as 0.0 (which reads as "never" and ranks a model that
      was never in the situation).
"""

from stage_04 import AGGRESSIVE, link_responses
from stage_05 import can_bet, strength_band, strength_terciles


def _action_name(decision):
    """The name of the action this decision line is about, or None.

    The frozen shape carries the action as the wire dict `{"action": str, ...}`;
    the name is one level down. Stage 4 reads it the same way — one rule, one
    place.
    """
    action = decision.get("action")
    return action.get("action") if isinstance(action, dict) else None


def _rate(numerator, denominator):
    """A rate, or None when nothing was measured.

    `0/0` is not "never did it": it is "was never asked", and a 0.0 there ranks a
    model that never faced a betting choice as the most disciplined one in the
    table.
    """
    if denominator == 0:
        return None
    return numerator / denominator


def _answer_index(decisions):
    """`{(hand, lance, aggressor_turn): link}` from stage 4's links.

    The key is the aggressor's own identity, not its model: two seats of one
    model can bet in the same lance, and each of them has its own answer.
    """
    answers = {}
    for link in link_responses(decisions):
        answers[(link["hand"], link["lance"], link["aggressor_turn"])] = link
    return answers


def _faces_a_bet(decision):
    """Is this seat answering a bet from the OTHER team right now?

    Three facts have to line up. It has to be facing a bet; the truth has to be
    known (`would_win is None` is a tie, and a fold to a drawn lance is neither
    an error nor a payoff); and the bet has to be held by an OPPONENT — the
    partner's envite is not something this seat can fold to or pay off.
    """
    if not decision.get("facing_bet"):
        return False
    if decision.get("would_win") is None:
        return False
    holder_team = decision.get("holder_team")
    return holder_team is not None and holder_team != decision.get("team")


def _bucket():
    """Every counter one key's scorecard accumulates."""
    return {
        "decisions": 0,
        "aggressive": 0,
        "bet_chances": 0,
        "bet_chances_weak": 0,
        "bluffs": 0,
        "value_bets": 0,
        "strength_sum": 0.0,
        "strength_n": 0,
        "bluff_folded": 0,
        "bluff_called": 0,
        "value_folded": 0,
        "value_called": 0,
        "stake_won_folds": 0,
        "stake_lost_called_bluffs": 0,
        "faced_winning": 0,
        "fold_error": 0,
        "faced_losing": 0,
        "payoff": 0,
    }


def _accumulate(bucket, decision, band, answer):
    """Fold one decision into its key's counters."""
    name = _action_name(decision)
    aggressive = name in AGGRESSIVE and decision.get("lance") is not None

    bucket["decisions"] += 1
    if can_bet(decision):
        bucket["bet_chances"] += 1
        if band == "weak":
            bucket["bet_chances_weak"] += 1

    if aggressive:
        bucket["aggressive"] += 1
        strength = decision.get("strength")
        if strength is not None:
            bucket["strength_sum"] += strength
            bucket["strength_n"] += 1

    kind = answer.get("kind") if answer else None
    if aggressive and band == "strong":
        bucket["value_bets"] += 1
        if kind == "fold":
            bucket["value_folded"] += 1
        elif kind in ("call", "raise"):
            bucket["value_called"] += 1
    elif aggressive and band == "weak":
        bucket["bluffs"] += 1
        if kind == "fold":
            bucket["bluff_folded"] += 1
            bucket["stake_won_folds"] += answer["fold_gain"]
        elif kind in ("call", "raise"):
            bucket["bluff_called"] += 1
            # A call only COSTS when the lance is lost. Calling a bluff that
            # would have won pays the bettor; charging it here would report a
            # profitable bluff as a loss.
            if decision.get("would_win") is False:
                bucket["stake_lost_called_bluffs"] += answer["stake"]

    if _faces_a_bet(decision):
        if decision.get("would_win"):
            bucket["faced_winning"] += 1
            if name == "no-quiero":
                bucket["fold_error"] += 1
        else:
            bucket["faced_losing"] += 1
            if name != "no-quiero":
                bucket["payoff"] += 1


def _finalise(bucket):
    """The counters as rates, with every empty denominator reported as None."""
    folded_and_called = bucket["bluff_folded"] + bucket["bluff_called"]
    value_answered = bucket["value_folded"] + bucket["value_called"]
    return {
        "decisions": bucket["decisions"],
        "aggressive": bucket["aggressive"],
        "bet_chances": bucket["bet_chances"],
        "aggression_rate": _rate(bucket["aggressive"], bucket["bet_chances"]),
        "bluffs": bucket["bluffs"],
        "value_bets": bucket["value_bets"],
        "bluff_rate": _rate(bucket["bluffs"], bucket["aggressive"]),
        "weak_hand_bet_rate": _rate(bucket["bluffs"], bucket["bet_chances_weak"]),
        "value_bet_rate": _rate(bucket["value_bets"], bucket["aggressive"]),
        "avg_strength_when_betting": (
            None if bucket["strength_n"] == 0
            else round(bucket["strength_sum"] / bucket["strength_n"], 3)),
        "bluff_folded": bucket["bluff_folded"],
        "bluff_called": bucket["bluff_called"],
        "bluff_success": _rate(bucket["bluff_folded"], folded_and_called),
        "value_folded": bucket["value_folded"],
        "value_called": bucket["value_called"],
        "value_bet_fold_rate": _rate(bucket["value_folded"], value_answered),
        "stake_won_folds": bucket["stake_won_folds"],
        "stake_lost_called_bluffs": bucket["stake_lost_called_bluffs"],
        "fold_equity": (bucket["stake_won_folds"]
                        - bucket["stake_lost_called_bluffs"]),
        "faced_winning": bucket["faced_winning"],
        "fold_error": bucket["fold_error"],
        "fold_error_rate": _rate(bucket["fold_error"], bucket["faced_winning"]),
        "faced_losing": bucket["faced_losing"],
        "payoff": bucket["payoff"],
        "payoff_rate": _rate(bucket["payoff"], bucket["faced_losing"]),
    }


def scorecard(decisions, key="model"):
    """One risk scorecard per distinct `str(decision[key])`."""
    if not isinstance(decisions, (list, tuple)):
        raise TypeError("scorecard takes the decision log, got %s"
                        % type(decisions).__name__)
    cuts = strength_terciles(decisions)
    answers = _answer_index(decisions)
    buckets = {}
    for decision in decisions:
        name = str(decision.get(key))
        bucket = buckets.setdefault(name, _bucket())
        band = strength_band(decision, cuts)
        answer = answers.get((decision.get("hand"), decision.get("lance"),
                              decision.get("turn")))
        _accumulate(bucket, decision, band, answer)
    return {name: _finalise(bucket) for name, bucket in buckets.items()}
