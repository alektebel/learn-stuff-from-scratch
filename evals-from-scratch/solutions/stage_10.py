"""Evals From Scratch — stage 10: the gate, and the report you can diff

SOLUTION. Pair by id (never by position), compute every rate over the paired
rows, let a per-slice floor outrank the overall interval, and keep the reasons
that produced the decision next to the decision itself.
"""

import json

from stage_08 import paired_bootstrap


def _index(rows, label):
    out = {}
    for row in rows:
        rid = row.get("id")
        if not rid:
            raise ValueError(f"{label} run has a row without an id: {row!r}")
        if rid in out:
            raise ValueError(f"{label} run has two rows with id {rid!r}")
        out[rid] = row
    return out


def _mean(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def gate(baseline, candidate, key="tenant", floors=None, alpha=0.05, seed=0):
    floors = dict(floors or {})
    base = _index(baseline, "baseline")
    cand = _index(candidate, "candidate")
    shared = sorted(set(base) & set(cand))
    n_dropped = (len(base) - len(shared)) + (len(cand) - len(shared))

    reasons = []
    a = [bool(base[rid]["passed"]) for rid in shared]
    b = [bool(cand[rid]["passed"]) for rid in shared]

    slices = {}
    for rid in shared:
        base_slice, cand_slice = base[rid].get(key), cand[rid].get(key)
        if base_slice != cand_slice:
            reasons.append(f"row {rid} moved from {base_slice!r} to "
                           f"{cand_slice!r} between the two runs")
        bucket = slices.setdefault(cand_slice, [0, 0, 0])
        bucket[0] += 1
        bucket[1] += bool(base[rid]["passed"])
        bucket[2] += bool(cand[rid]["passed"])

    table = {}
    for name, (n, base_passes, cand_passes) in slices.items():
        base_rate, cand_rate = base_passes / n, cand_passes / n
        table[name] = {"n": n, "baseline": base_rate, "candidate": cand_rate,
                       "diff": cand_rate - base_rate,
                       "breach": name in floors and cand_rate < floors[name]}
    for name, floor in floors.items():
        if name not in table:
            table[name] = {"n": 0, "baseline": 0.0, "candidate": 0.0,
                           "diff": 0.0, "breach": True}
            reasons.append(f"slice {name!r} has a floor of {floor} and does not "
                           f"appear in the candidate run at all: a slice that "
                           f"vanished is not a slice that passed")
    breaches = sorted(name for name, row in table.items() if row["breach"])

    if len(shared) < 2:
        overall = {"n": len(shared), "baseline": _mean(a), "candidate": _mean(b),
                   "diff": _mean(a) - _mean(b), "lo": 0.0, "hi": 0.0}
        reasons.append(f"only {len(shared)} row(s) appear in both runs "
                       f"({n_dropped} dropped): fewer than two paired rows "
                       f"cannot support an interval")
        decision = "regress" if breaches else "inconclusive"
    else:
        # diff is CANDIDATE minus BASELINE, matching the per-slice table: a
        # positive number means the candidate is better.
        ci = paired_bootstrap(b, a, seed=seed, alpha=alpha)
        overall = {"n": len(shared), "baseline": _mean(a), "candidate": _mean(b),
                   "diff": ci["mean_diff"], "lo": ci["lo"], "hi": ci["hi"]}
        if breaches:
            decision = "regress"
        elif ci["hi"] < 0:
            decision = "regress"
        elif ci["lo"] > 0:
            decision = "pass"
        else:
            decision = "inconclusive"
            reasons.append(f"the paired difference {ci['mean_diff']:+.4f} has "
                           f"an interval [{ci['lo']:+.4f}, {ci['hi']:+.4f}] that "
                           f"contains zero")

    for name in breaches:
        row = table[name]
        reasons.append(f"slice {name!r} is below its floor: "
                       f"{row['candidate']:.4f} < {floors[name]}")
    if n_dropped:
        reasons.append(f"{n_dropped} row(s) dropped: they appear in only one of "
                       f"the two runs")

    return {"decision": decision, "reasons": reasons, "n_paired": len(shared),
            "n_dropped": n_dropped, "overall": overall, "slices": table}


def report_json(result):
    def clean(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, float):
            return round(value, 4)
        if isinstance(value, dict):
            return {str(k): clean(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [clean(v) for v in value]
        return value

    return json.dumps(clean(result), indent=2, sort_keys=True) + "\n"
