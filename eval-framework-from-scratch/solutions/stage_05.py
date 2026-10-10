"""Eval Framework From Scratch — stage 5: the unit of aggregation is the case.

DESIGN DECISION — why is the unit of aggregation the case, and not the record?
    A repeat measures stability; it is not extra evidence. A case that was run
    five times would otherwise carry five times the weight of a case that was run
    once, so the published mean would be a statement about how the suite was
    configured rather than about how well the system did — and `repeats` is
    exactly the knob a worried author turns. One case, one value, one vote: the
    case's value is the mean over its repeats, and the suite's mean is the mean
    of those values.

DESIGN DECISION — why is a case's weight applied to its mean rather than to each
    of its records?
    The weight says how much the case matters, not how many times it ran. Applied
    per record it is silently multiplied by the repeat count, so a heavy case run
    three times counts nine times a light one run once, and the two knobs —
    weight and repeats — stop being independent. The weight belongs to the case,
    at the single moment the case's value enters the mean.

DESIGN DECISION — why does a metric that is `None` on a case disappear from `n`
    instead of counting as 0.0?
    `None` from a plugin means "not applicable to this case", which is
    information; 0.0 means "measured, and it failed", which is a verdict.
    Counting the first as the second invents a failure: it drags the mean down
    and, worse, it hides the case from `n`, so a metric that cannot measure a
    third of the suite looks like a healthy metric over all of it. A metric with
    no value anywhere reports `None` for every statistic, never a flattering
    zero.

DESIGN DECISION — why is `stable` a conjunction, and why must the verdict name
    the missing metric?
    A mean over one case is a coin flip, and a spread wider than the effect
    anyone is looking for cannot support a comparison, so `stable` needs both
    enough cases (`MIN_N`) and a spread inside `MAX_SPREAD` — inclusive, because
    every number in the rollup is rounded to `METRIC_DP` and a boundary that is
    not reproducible is not a rule. And a metric with no data must be refused by
    name: `missing`, `thin` and `noisy` are three different reasons to withhold a
    number, and a gate that cannot say which one it hit is a gate nobody can
    debug.
"""

from stage_03 import METRIC_DP, STATUSES

#: How many cases a metric needs before its mean may be published.
MIN_N = 3

#: The widest spread (`max - min` over the case values) that still supports a
#: comparison. Inclusive: a spread of exactly `MAX_SPREAD` is stable.
MAX_SPREAD = 0.35


def _case_weight(record):
    """The declared weight of the case the record came from (1.0 by default).

    The weight is a property of the case, and stage 3's record has no room for
    it, so the rollup reads it off the record the runner handed over and treats
    a record that does not carry one as a weight of 1.0.
    """
    return float(record.get("weight", 1.0))


def _metric_names(records):
    """Every metric the records mention, in first-seen order.

    A name mentioned with a `None` value is a name the run knows about: it has to
    appear in the rollup, or "we could not measure this" would be invisible.
    """
    names = []
    for record in records:
        for name in record.get("metrics", {}):
            if name not in names:
                names.append(name)
    return names


def case_values(records):
    """The case-level rollup: one entry per case id, keyed in first-seen order.

    `{case_id: {"weight": w, "repeats": n, "values": {metric: mean}}}` — the
    weight is the case's declared weight, `repeats` counts the records seen for
    the case, and each value is the mean over the case's repeats that produced
    one (a `None` produces nothing), rounded to `METRIC_DP`. A record that
    carries no weight weighs 1.0, so a plain stage 3 record aggregates as an
    unweighted case mean.
    """
    per_case = {}
    for record in records:
        case_id = record["case"]
        entry = per_case.get(case_id)
        if entry is None:
            entry = per_case[case_id] = {"weight": _case_weight(record),
                                         "repeats": 0, "values": {}}
        entry["repeats"] += 1
        for name, value in record.get("metrics", {}).items():
            if value is None:
                continue
            entry["values"].setdefault(name, []).append(value)
    return {
        case_id: {"weight": entry["weight"], "repeats": entry["repeats"],
                  "values": {name: round(sum(values) / len(values),
                                         METRIC_DP) + 0.0
                             for name, values in entry["values"].items()}}
        for case_id, entry in per_case.items()
    }


def aggregate(records):
    """A whole run as one mapping.

    `{"records", "cases", "status_counts", "metrics", "case_errors"}`: the counts
    are of records and of distinct cases, `status_counts` zero-fills every status
    of `stage_03.STATUSES`, `case_errors` counts the records whose status is
    `case_error` (our bug, not the plugin's), and `metrics[name]` is
    `{"n", "mean", "min", "max", "spread", "stable"}` computed on the CASE values
    — `n` counts cases, the mean is weighted by the cases' weights, and a metric
    with nothing to measure reports `None` for every statistic and
    `stable: False`.
    """
    per_case = case_values(records)
    status_counts = {status: 0 for status in STATUSES}
    for record in records:
        status = record["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
    metrics = {}
    for name in _metric_names(records):
        points = [(entry["weight"], entry["values"][name])
                  for entry in per_case.values() if name in entry["values"]]
        n = len(points)
        if n == 0:
            metrics[name] = {"n": 0, "mean": None, "min": None, "max": None,
                             "spread": None, "stable": False}
            continue
        total_weight = sum(weight for weight, _ in points)
        low = min(value for _, value in points)
        high = max(value for _, value in points)
        spread = round(high - low, METRIC_DP) + 0.0
        metrics[name] = {
            "n": n,
            "mean": round(sum(weight * value for weight, value in points)
                          / total_weight, METRIC_DP) + 0.0,
            "min": round(low, METRIC_DP) + 0.0,
            "max": round(high, METRIC_DP) + 0.0,
            "spread": spread,
            "stable": n >= MIN_N and spread <= MAX_SPREAD,
        }
    return {"records": len(records), "cases": len(per_case),
            "status_counts": status_counts, "metrics": metrics,
            "case_errors": sum(1 for record in records
                               if record["status"] == "case_error")}


def stability_verdict(agg, name):
    """`"stable"`, `"thin"`, `"noisy"` or `"missing"` for one metric of an aggregate.

    `missing` when the aggregate has no entry for the name or the entry has no
    data, `thin` when fewer than `MIN_N` cases produced the metric, `noisy` when
    its spread is wider than `MAX_SPREAD`, else `stable`.
    """
    entry = agg["metrics"].get(name)
    if entry is None:
        return "missing"
    if entry["n"] == 0:
        return "missing"
    if entry["n"] < MIN_N:
        return "thin"
    if entry["spread"] > MAX_SPREAD:
        return "noisy"
    return "stable"
