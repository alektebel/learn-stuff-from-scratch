"""Eval Framework From Scratch — stage 8: the gate and the exit status.

DESIGN DECISION — why does a gate refuse to judge a number it cannot trust?
    A gate is a promise about a MEASUREMENT: "the mean of `em` is at least 0.5".
    A mean over two cases is not that measurement, it is a rumour with a decimal
    point, and a spread of half the scale means the metric is not one number at
    all. A gate that compares a bound against such a number is not lenient, it
    is lying: the run is published green and the number behind it moves on the
    next run. So the gate reads the entry's own stability first and answers
    `missing`, `thin`, `noisy` or `unstable` instead of a bound comparison. The
    bound itself is inclusive — a threshold is the value the author wrote down,
    and 0.5 is at least 0.5 — so `>=`/`<=`, never `>`/`<`.

DESIGN DECISION — why is an empty gate list NOT a pass?
    "Everything passed" and "nothing was checked" are different sentences, and a
    suite with no gates must not be able to say the first. A config typo that
    drops the gates — an empty list, a bound that was never spelled right —
    would otherwise be the cheapest road to a green run in the whole framework.
    The same reason makes an unknown key a refusal: a typo'd `minimum` silently
    ignored is a gate that means something other than what its author wrote.

DESIGN DECISION — why is the exit status ordered config -> invalid -> gate?
    The gate answers "is this measurement good enough to publish?", and that
    question is meaningless while the measurement is missing or broken. A run
    that stopped on its call or tick budget, or that recorded a `case_error`
    (our bug, not the model's), or whose metric plugin raised, holds numbers
    that mean nothing; a green gate over it is precisely the accident this
    ordering exists to prevent. So: the run never happened -> EXIT_CONFIG; the
    run happened but is not a valid measurement -> EXIT_RUN_INVALID; only then
    does a refused gate get to be EXIT_GATE_FAILED, and only a valid run that
    cleared every gate is EXIT_OK. The four numbers are distinct because a
    caller — CI, the CLI, the resume — reads the number, not a message.

DESIGN DECISION — why import MIN_N/MAX_SPREAD from stage 5 instead of calling
`stability_verdict`?
    Because the numbers are the contract and the function is the convenience.
    Importing the two constants lets this stage be checked against hand-built
    `agg` dicts — no run, no registry, no record — while calling
    `stability_verdict(agg, name)` would drag stage 5's aggregation into every
    gate verdict and let one stage's bug read as the other's. The gate reads the
    metric's entry (the same row stage 5 publishes) and applies the same two
    rules to it.
"""

from lab import ConfigError
from stage_05 import MAX_SPREAD, MIN_N

#: The keys a gate may carry: the metric, and exactly one bound.
GATE_KEYS = ("metric", "min_mean", "max_mean")

#: What the process exits with. Four distinct numbers, in this order: 0 green,
#: 1 a gate refused a valid run, 2 the run is not a valid measurement, 3 the run
#: never happened. A caller reads the number.
EXIT_OK, EXIT_GATE_FAILED, EXIT_RUN_INVALID, EXIT_CONFIG = 0, 1, 2, 3

#: The keys stage 4's run SUMMARY carries: `records` and `metric_errors` are
#: counts, never logs. A dict without them is not a run.
_RUN_KEYS = ("suite", "cases", "records", "status_counts", "metric_errors", "ticks",
             "calls", "stopped")


def _bound(spec):
    """Which bound the gate declared: `min_mean` or `max_mean`, or a refusal."""
    has_min = "min_mean" in spec
    has_max = "max_mean" in spec
    if has_min and has_max:
        raise ConfigError("gate: exactly one of min_mean/max_mean, got both (%r, %r)"
                          % (spec["min_mean"], spec["max_mean"]))
    if not has_min and not has_max:
        raise ConfigError("gate: exactly one of min_mean/max_mean, got neither of them "
                          "in %r" % (sorted(spec),))
    return "min_mean" if has_min else "max_mean"


def _bound_value(value, where):
    """A finite real bound, or a refusal naming where the offender came from."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError("%s: a gate bound must be a number, got %r" % (where, value))
    if value != value or value in (float("inf"), float("-inf")):
        raise ConfigError("%s: a gate bound must be finite, got %r" % (where, value))
    return float(value)


def parse_gate(spec):
    """The gate a spec describes, or a `ConfigError` naming the mistake.

    Exactly one bound: `{"metric": m, "min_mean": v}` says higher is better,
    `{"metric": m, "max_mean": v}` says lower is better. A spec that carries
    both is ambiguous, a spec that carries neither cannot fail, and an unknown
    key is a typo that must not be silently ignored.
    """
    if not isinstance(spec, dict):
        raise ConfigError("gate: a gate must be a mapping, got %s" % (type(spec).__name__,))
    unknown = sorted(key for key in spec if key not in GATE_KEYS)
    if unknown:
        raise ConfigError("gate: unknown key %r (a gate carries %s)"
                          % (unknown[0], ", ".join(GATE_KEYS)))
    metric = spec.get("metric")
    if not isinstance(metric, str) or not metric:
        raise ConfigError("gate: metric must be a non-empty string, got %r" % (metric,))
    bound = _bound(spec)
    return {"metric": metric,
            bound: _bound_value(spec[bound], "gate(%s).%s" % (metric, bound))}


def evaluate_gate(gate, agg):
    """One gate's verdict against an aggregate: `{"ok", "value", "reason"}`.

    Reads `agg["metrics"][gate["metric"]]` and applies stage 5's two rules to
    the entry — never a stage 5 call — then compares the bound. The reason is
    the first that applies: `missing` (no entry, or no mean to judge), `thin`
    (`n < MIN_N`), `noisy` (`spread > MAX_SPREAD`), `unstable` (the entry's
    `stable` is falsy for a reason the two above do not name), `below` /
    `above` (the bound failed), else `ok`. `value` is the metric's mean, or
    `None` when there is no mean to report. A gate that carries no bound at all
    is refused: a gate that cannot fail is not a gate.
    """
    entry = (agg.get("metrics") or {}).get(gate["metric"])
    if entry is None or not entry.get("n") or entry.get("mean") is None:
        return {"ok": False, "value": None, "reason": "missing"}
    mean = entry["mean"]
    if entry["n"] < MIN_N:
        return {"ok": False, "value": mean, "reason": "thin"}
    spread = entry.get("spread")
    if spread is not None and spread > MAX_SPREAD:
        return {"ok": False, "value": mean, "reason": "noisy"}
    if not entry.get("stable"):
        return {"ok": False, "value": mean, "reason": "unstable"}
    if "min_mean" in gate:
        if mean >= gate["min_mean"]:
            return {"ok": True, "value": mean, "reason": "ok"}
        return {"ok": False, "value": mean, "reason": "below"}
    if "max_mean" in gate:
        if mean <= gate["max_mean"]:
            return {"ok": True, "value": mean, "reason": "ok"}
        return {"ok": False, "value": mean, "reason": "above"}
    raise ConfigError("gate(%s): neither min_mean nor max_mean — a gate that cannot "
                      "fail is not a gate" % (gate["metric"],))


def evaluate_gates(gates, agg):
    """Every gate's verdict, in the declared order: `{"ok", "gates"}`.

    An empty gate list is NOT a pass: it is `{"ok": False, "gates": (),
    "reason": "no_gates"}`, because nothing was checked is not the same sentence
    as everything passed. With at least one gate, `ok` is False as soon as one
    verdict failed and `gates` holds one verdict per gate, in order.
    """
    if not gates:
        return {"ok": False, "gates": (), "reason": "no_gates"}
    verdicts = tuple(evaluate_gate(gate, agg) for gate in gates)
    return {"ok": all(verdict["ok"] for verdict in verdicts), "gates": verdicts}


def run_exit(run, gates_result):
    """The process status for a run summary and its gate verdict.

    `EXIT_CONFIG` when the run itself never happened (a run that is not a dict,
    or that lacks any of its keys), `EXIT_RUN_INVALID` when the run happened but
    is not a valid measurement — all three read from the SUMMARY, never by
    scanning a log: it stopped on a budget (`stopped is not None`), or it
    counted a `case_error` (`status_counts["case_error"] > 0`), or it counted a
    record whose metric plugin raised (`metric_errors > 0`). Then
    `EXIT_GATE_FAILED` when the run is valid and a gate refused it — or when the
    gates were never evaluated at all — else `EXIT_OK`. The order is the point:
    a green gate over an invalid run is the bug this function exists to prevent.
    """
    if not isinstance(run, dict) or any(key not in run for key in _RUN_KEYS):
        return EXIT_CONFIG
    if run["stopped"] is not None:
        return EXIT_RUN_INVALID
    if run["status_counts"].get("case_error", 0):
        return EXIT_RUN_INVALID
    if run["metric_errors"]:
        return EXIT_RUN_INVALID
    if not gates_result or not gates_result.get("ok"):
        return EXIT_GATE_FAILED
    return EXIT_OK
