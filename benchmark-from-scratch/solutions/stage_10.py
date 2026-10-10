"""Benchmark From Scratch — stage 10 solution: the mirrored pair.

The reasoning lives in `stage_10.py`'s docstring; this file is the code. The two
functions are deliberately dumb: the schedule is a nested loop, the pairing is a
group-by over a dictionary keyed by `(sorted matchup, seed)`, and the only
arithmetic in the file is one sum and one division.
"""


def build_jobs(pairings, seeds, *, mirror=True):
    """The schedule: one job per (model_a, model_b, seed)."""
    pairings = [tuple(pairing) for pairing in pairings]
    for pairing in pairings:
        if len(pairing) != 2:
            raise ValueError("a pairing is two model labels, got %r" % (pairing,))
    if len({frozenset(pairing) for pairing in pairings}) != len(pairings):
        raise ValueError("a pairing is unordered: the same matchup twice, in "
                         "either orientation, would run the same job twice")
    seeds = list(seeds)
    jobs = []
    for seed in seeds:
        for model_a, model_b in pairings:
            jobs.append((model_a, model_b, seed))
            if mirror:
                jobs.append((model_b, model_a, seed))
    return jobs


def paired_rows(entries):
    """The paired comparison: one entry per matchup per seed."""
    groups = {}
    for entry in entries:
        if entry.get("status") != "done":
            # A degraded match measured the harness's fallback, not the model.
            continue
        teams = tuple(entry["teams"])
        if len(teams) != 2:
            raise ValueError("a row names its two teams, got %r" % (teams,))
        seen = groups.setdefault((tuple(sorted(teams)), entry["seed"]), {})
        if teams in seen:
            raise ValueError("the same orientation ran twice for %r at seed %r: "
                             "the schedule is broken, not the model"
                             % (teams, entry["seed"]))
        seen[teams] = entry

    pairs = []
    for (models, seed), halves in sorted(groups.items()):
        if len(halves) != 2:
            # One orientation is the biased number this stage exists to cancel.
            continue
        (a, b) = models
        seat_a = halves.get((a, b))
        seat_b = halves.get((b, a))
        if seat_a is None or seat_b is None:
            continue
        diff_a = seat_a["hand_gain_a"] - seat_a["hand_gain_b"]
        diff_b = seat_b["hand_gain_b"] - seat_b["hand_gain_a"]
        hands = seat_a["hands"] + seat_b["hands"]
        pairs.append({
            "models": [a, b],
            "seed": seed,
            "seat_a": seat_a,
            "seat_b": seat_b,
            "piedra_diff_seat_a": diff_a,
            "piedra_diff_seat_b": diff_b,
            "paired_diff": diff_a + diff_b,
            "hands": hands,
            "per_hand": None if hands == 0 else round((diff_a + diff_b) / hands, 3),
        })
    return pairs
