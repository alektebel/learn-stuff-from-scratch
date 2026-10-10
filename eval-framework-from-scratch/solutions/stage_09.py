"""Eval Framework From Scratch — stage 9: the baseline diff.

DESIGN DECISION — why must a difference beat the noise before it is news?
    Two runs of the same suite do not produce the same mean: a case that was
    answered on one repeat and missed on another moves it, and so does a metric
    that only applied to two of the three cases. A diff that reported every
    nonzero delta would report a change every single time, and a report that
    always fires is a report nobody reads. So a difference is only called a
    difference when it is larger than the instability the two runs already show:
    `abs(delta) > noise + eps`. The eps is not decoration — it is the resolution
    of the numbers being compared (values are rounded to `METRIC_DP`), and two
    means that differ by less than one rounding step may differ by nothing at
    all. The comparison is STRICT: a difference exactly at the noise is the
    noise.

DESIGN DECISION — why is the noise the larger of the two spreads, and not a
mean or a sigma?
    The spreads are what the aggregation already measured about its own data —
    the distance between the best and the worst case value on each side. Taking
    the LARGER of the two sides is the conservative choice: if either run was
    jumpy, the jumpiness is the standard the difference must beat. Reading the
    noise from a single side would let a quiet baseline on one side hide a noisy
    candidate on the other, and reporting `mean + sigma`-style intervals is a
    different lesson (C1 owns significance); here the framework only has to
    avoid calling noise a result.

DESIGN DECISION — why is a metric on one side only `added`/`removed`, and why is
a missing side `None` rather than 0.0?
    A metric that nobody measured is not a measurement of zero. Filling a missing
    side with 0.0 turns "we did not measure this" into "we measured a disaster":
    a metric that appeared in the candidate becomes an enormous improvement, and
    one that disappeared becomes a regression, both of them fabricated. So the
    absent side is `None`, the delta cannot exist without two numbers, and the
    verdict is `added` / `removed` — a change in what was measured, never a claim
    about how much better or worse anything got.

DESIGN DECISION — why does an unstable side stop the comparison?
    `stable` is the aggregation's own admission that this number is not solid:
    too few cases, or a spread wider than the metric's noise floor. A verdict
    computed on top of an unstable number inherits its instability and hides it,
    so the diff refuses: a side that is not stable makes the comparison
    `unstable`, which is a fact about the data and not a claim about quality.
"""

from stage_03 import METRIC_DP

#: The slack a difference must beat on top of the noise: one rounding step.
EPS = 10 ** -METRIC_DP


def _entry(agg, name):
    """The metric's entry on one side, or `None` when that side never saw it."""
    metrics = agg.get("metrics") if isinstance(agg, dict) else None
    if not isinstance(metrics, dict):
        return None
    return metrics.get(name)


def _number(value):
    """`value` when it is a real number, else `None` (`bool` is not a number)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _value(agg, name):
    """The mean one side reports for a metric, or `None` when it has no data."""
    entry = _entry(agg, name)
    if entry is None:
        return None
    return _number(entry.get("mean"))


def _spread(agg, name):
    """The spread one side reports for a metric, or `None` when it has no data."""
    entry = _entry(agg, name)
    if entry is None:
        return None
    return _number(entry.get("spread"))


def _stable(agg, name):
    """Whether one side called its own measurement stable."""
    entry = _entry(agg, name)
    return bool(entry is not None and entry.get("stable") is True)


def _noise(base_agg, cand_agg, name):
    """The largest spread among the sides that have data, or `None`."""
    spreads = [value for value in (_spread(base_agg, name), _spread(cand_agg, name))
               if value is not None]
    return max(spreads) if spreads else None


def diff_metrics(base_agg, cand_agg, *, eps=EPS):
    """Compare two aggregations metric by metric.

    Returns `{metric: {"base", "cand", "delta", "noise", "verdict"}}`: the two
    means (or `None` for a side with no data), `delta = cand - base` (or `None`
    when a side has no number), the `noise` (the largest spread among the sides
    that have data) and the `verdict`.
    """
    base_metrics = base_agg.get("metrics") or {}
    cand_metrics = cand_agg.get("metrics") or {}
    diff = {}
    for name in sorted(set(base_metrics) | set(cand_metrics)):
        base_entry = base_metrics.get(name)
        cand_entry = cand_metrics.get(name)
        base = _value(base_agg, name)
        cand = _value(cand_agg, name)
        noise = _noise(base_agg, cand_agg, name)
        delta = None if base is None or cand is None else cand - base
        if base_entry is None:
            verdict = "added"
        elif cand_entry is None:
            verdict = "removed"
        elif not (_stable(base_agg, name) and _stable(cand_agg, name)):
            verdict = "unstable"
        elif abs(delta) > noise + eps:
            verdict = "improvement" if delta > 0 else "regression"
        else:
            verdict = "stable"
        diff[name] = {"base": base, "cand": cand, "delta": delta, "noise": noise,
                      "verdict": verdict}
    return diff


def regressions(diff):
    """The metrics whose verdict is `"regression"`, sorted by metric name."""
    names = [name for name, row in diff.items() if row["verdict"] == "regression"]
    return tuple(sorted(names))
