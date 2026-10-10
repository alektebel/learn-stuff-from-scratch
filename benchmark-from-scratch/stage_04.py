"""Benchmark From Scratch (Mus) — stage 4: linking an aggressive action to the
answer it got.

An envite is the one moment in mus where a model has to commit: it pushes a
stake onto the table and somebody — sooner or later — says quiero or no-quiero.
Every risk metric in the course (bluff rate, fold equity, bluff success, whether
the model's push was answered) is a question about ONE thing: this aggression,
and the response it got. Nothing else in the log carries that pairing, so this
stage is where the noise of "who won the vaca" becomes a decision that either
got a fold or got called.

DESIGN DECISION — why a LINK and not a field written back onto the decision?
    The reference implementation mutates each decision record in place
    (`rec["response"] = "fold"`). It works, and it is one line shorter. It also
    means the log stops being a log: a second pass sees a `response` key it did
    not write, "what the model did" and "what we decided about it" end up in the
    same dict, and stage 6's scorecard can only be run if you remember that
    you have to link first. So this stage returns a LIST of links — each one
    naming the aggression by (hand, lance, turn) and the answer by turn — and
    the decision log stays exactly the frozen wire shape stage 3 recorded. The
    reading can then be recomputed, filtered by lance or by model, or thrown
    away and rebuilt, none of which mutating the input allows.

DESIGN DECISION — the answer is the first RIVAL *response* later in the SAME
    hand and SAME lance, and the scan skips whatever is neither.
    Three things can sit between an envite and its answer, and every one of
    them is a real regression:
      - the aggressor's own PARTNER, who may well speak next (a y-yo, a paso).
        It is skipped, never a match and never a stop: the partner is the
        attacker's own team answering itself, and stopping there would report
        that nobody ever answered an envite that was folded two turns later.
      - a rival action that is not an answer at all (a paso in another phase).
        It is not the response either; a `break` here loses the real answer.
      - the next hand, and the next lance of the same hand. A response lives in
        ONE hand and ONE lance: a Chica fold in hand 2 does not answer an envite
        made in hand 1, and it does not answer hand 1's Grande either. Hand
        numbers repeat across matches in one log, which is exactly why the
        pairing has to be keyed by all of it and not by "the next rival line".

DESIGN DECISION — why the FIRST rival response, and why each aggression gets
    its OWN answer?
    The first one is the answer: it is the sentence the table said back to the
    stake that was on the table. A later fold, after the stake has changed, is
    a different decision about a different bet. And two aggressions in the same
    hand and lance — a seat raises, its partner y-yo's — are each answered by
    that same rival sentence: the response is counted once per aggression, not
    consumed by the first one it explained.

DESIGN DECISION — why read `stake` and `previous` off the RESPONDER's line, and
    why floor them at 1?
    The stakes that matter are the ones the SEAT FACING the bet had in front of
    it: what a call puts at risk, and what a fold collects. Those are exactly
    the `stake` and `previous` stage 3 snapshotted for the responder's own
    decision (its snapshot is taken before it acts). Reading them off the
    aggressor's line gives the numbers of the wrong moment. Both are floored at
    1 because the floor is a floor: when `previous` is 0 the folder still
    collects the deje — the minimum — and reporting `fold_gain: 0` says a fold
    won nothing. The same edge in `stake` says a call risks nothing.

`decisions` is the frozen decision log (contract §2) in play order, possibly
spanning several hands, several lances and several models. The action name of a
decision lives one level down, in `decision["action"]["action"]` — the wire dict
`Table.apply` took. Returned links come back in the order the aggressions
happened:

    {"hand": int, "lance": str,
     "aggressor_turn": int, "responder_turn": int,
     "model": str, "responder": str, "team": int,
     "kind": "fold" | "call" | "raise",
     "stake": int, "fold_gain": int}

`AGGRESSIVE` and `RESPONSES` are the two tuples the rest of the course reads:
the four actions that put a stake on the table, and every answer to one (a fold,
a call, or a raise back).

TODO: implement `link_responses` below.
"""

AGGRESSIVE = ("envido", "y-yo", "reenvido", "ordago")
RESPONSES = ("quiero", "no-quiero") + AGGRESSIVE


def link_responses(decisions):
    """One link per aggressive decision the opposition answered.

    Every decision whose action is in `AGGRESSIVE` and whose `lance` is not None
    is paired with the FIRST later decision that is in the same hand and the
    same lance, belongs to the other team, and whose action is in `RESPONSES`.
    The aggressor's own team is skipped, never a match and never a stop. A
    decision with no `lance` is skipped entirely, and an aggression nobody
    answered yields no link at all — not a link with `kind` None.

    `kind` is "fold" for no-quiero, "call" for quiero, and "raise" for any other
    name in `RESPONSES`. `stake` is `max(responder's snapshot stake, 1)` — what a
    call puts at risk — and `fold_gain` is `max(responder's snapshot previous,
    1)`, the deje the responder collects by folding.
    """
    raise NotImplementedError("stage 4: implement link_responses()")
