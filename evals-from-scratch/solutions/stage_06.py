"""Evals From Scratch — stage 6: the judge, and the order you showed it in

SOLUTION. Two calls per pair, the second with the arguments swapped, and a
mapping that knows which answer was presented first. The flip counter is the
measurement; the win rate is the debiased side effect.
"""


def _verdict(answer, swapped=False):
    if answer == "first":
        return "b" if swapped else "a"
    if answer == "second":
        return "a" if swapped else "b"
    if answer == "tie":
        return "tie"
    raise ValueError(
        f"judge returned {answer!r}; expected 'first', 'second' or 'tie'")


def run_pairwise(judge, pairs, swap=True):
    pairs = list(pairs)
    n = len(pairs)
    a_wins = b_wins = ties = 0.0
    flips = 0

    for pair in pairs:
        verdict = _verdict(judge(pair["a"], pair["b"]))
        if not swap:
            if verdict == "a":
                a_wins += 1
            elif verdict == "b":
                b_wins += 1
            else:
                ties += 1
            continue
        back = _verdict(judge(pair["b"], pair["a"]), swapped=True)
        for winner in (verdict, back):
            if winner == "a":
                a_wins += 0.5
            elif winner == "b":
                b_wins += 0.5
            else:
                ties += 0.5
        if verdict != "tie" and back != "tie" and verdict != back:
            flips += 1

    if not n:
        return {"n": 0, "a_wins": 0.0, "b_wins": 0.0, "ties": 0.0, "flips": 0,
                "position_bias": 0.0, "agreement": 1.0, "win_rate_a": 0.5}
    position_bias = flips / n
    return {"n": n, "a_wins": a_wins, "b_wins": b_wins, "ties": ties,
            "flips": flips, "position_bias": position_bias,
            "agreement": 1.0 - position_bias,
            "win_rate_a": (a_wins + 0.5 * ties) / n}
