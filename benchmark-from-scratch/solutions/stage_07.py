"""Benchmark From Scratch (Mus) — stage 7 solution: the low-variance outcome.

The reasoning lives in `stage_07.py`'s docstring; this file is the implementation.
"""


def outcome(hand_records):
    """The piedras per hand of the hand records in `hand_records`, plus the vacas
    and the hand wins. `{}` when there is no hand record at all.

    `hand_gain_*` is the per-hand award and it survives the vaca's reset of the
    point counters, so it is the column the outcome is summed from; the vaca
    counters are a running total and only the last record holds its end.
    """
    hands = [r for r in hand_records if r.get("kind") == "hand"]
    if not hands:
        return {}
    ga = sum(h["hand_gain_a"] for h in hands)
    gb = sum(h["hand_gain_b"] for h in hands)
    n = len(hands)
    return {
        "hands": n,
        "piedras_a": ga,
        "piedras_b": gb,
        "piedras_per_hand_a": round(ga / n, 3),
        "piedras_per_hand_b": round(gb / n, 3),
        "piedras_diff_per_hand": round((ga - gb) / n, 3),
        "vacas_a": hands[-1]["vacas_a"],
        "vacas_b": hands[-1]["vacas_b"],
        "hand_wins_a": sum(1 for h in hands if h["hand_winner"] == 0),
        "hand_wins_b": sum(1 for h in hands if h["hand_winner"] == 1),
    }
