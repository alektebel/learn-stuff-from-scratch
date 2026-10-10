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

TODO: implement `case_values`, `aggregate` and `stability_verdict`.
"""

#: How many cases a metric needs before its mean may be published.
MIN_N = 3

#: The widest spread (`max - min` over the case values) that still supports a
#: comparison. Inclusive: a spread of exactly `MAX_SPREAD` is stable.
MAX_SPREAD = 0.35


def case_values(records):
    """The case-level rollup: one entry per case id, keyed in first-seen order.

    `{case_id: {"weight": w, "repeats": n, "values": {metric: mean}}}` — the
    weight is the case's declared weight, `repeats` counts the records seen for
    the case, and each value is the mean over the case's repeats that produced
    one (a `None` produces nothing), rounded to `METRIC_DP`. A record that
    carries no weight weighs 1.0, so a plain stage 3 record aggregates as an
    unweighted case mean.
    """
    raise NotImplementedError("stage 5: implement case_values()")


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
    raise NotImplementedError("stage 5: implement aggregate()")


def stability_verdict(agg, name):
    """`"stable"`, `"thin"`, `"noisy"` or `"missing"` for one metric of an aggregate.

    `missing` when the aggregate has no entry for the name or the entry has no
    data, `thin` when fewer than `MIN_N` cases produced the metric, `noisy` when
    its spread is wider than `MAX_SPREAD`, else `stable`.
    """
    raise NotImplementedError("stage 5: implement stability_verdict()")
