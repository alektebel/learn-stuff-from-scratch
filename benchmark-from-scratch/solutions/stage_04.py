"""Benchmark From Scratch (Mus) — stage 4 solution: linking an aggressive action
to the answer it got.

See `stage_04.py` for the design decisions; this is the body.
"""

AGGRESSIVE = ("envido", "y-yo", "reenvido", "ordago")
RESPONSES = ("quiero", "no-quiero") + AGGRESSIVE

# How one rival answer reads. `quiero` and `no-quiero` are the only two ways to
# STOP a bet; every other name in RESPONSES pushes the stake higher, i.e. raises.
# The mapping is looked up by name, so a name added to RESPONSES reads as a
# raise instead of silently counting as a call.
_KIND = {"no-quiero": "fold", "quiero": "call"}


def _action_name(decision):
    """The name of the action a decision line is about, or None.

    The frozen shape carries the action as the wire dict `{"action": str, ...}`
    — the same dict `Table.apply` accepted — so the name is one level down.
    """
    action = decision.get("action")
    return action.get("action") if isinstance(action, dict) else None


def _floored(value):
    """A snapshot number as the table counts it: never below 1.

    A fold always collects the deje (the minimum) even when `previous` is 0, and
    a call always risks at least the minimum stake even when the snapshot says
    0 — the two edge cases where a raw 0 would report that nothing was at stake
    in a bet that was made.
    """
    return max(value or 0, 1)


def link_responses(decisions):
    """One link per aggressive decision the opposition answered."""
    links = []
    for index, decision in enumerate(decisions):
        lance = decision.get("lance")
        if lance is None:
            continue
        if _action_name(decision) not in AGGRESSIVE:
            continue
        hand = decision.get("hand")
        team = decision.get("team")
        response = None
        for later in decisions[index + 1:]:
            if later.get("hand") != hand or later.get("lance") != lance:
                continue
            if later.get("team") == team:
                continue
            if _action_name(later) not in RESPONSES:
                continue
            response = later
            break
        if response is None:
            continue
        links.append({
            "hand": hand,
            "lance": lance,
            "aggressor_turn": decision.get("turn"),
            "responder_turn": response.get("turn"),
            "model": decision.get("model"),
            "responder": response.get("model"),
            "team": team,
            "kind": _KIND.get(_action_name(response), "raise"),
            "stake": _floored(response.get("stake")),
            "fold_gain": _floored(response.get("previous")),
        })
    return links
