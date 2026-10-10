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
    gate verdict and let one stage's bug read as the other's.

TODO: implement `parse_gate`, `evaluate_gate`, `evaluate_gates` and `run_exit`.
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


def parse_gate(spec):
    """The gate a spec describes, or a `ConfigError` naming the mistake.

    Exactly one bound: `{"metric": m, "min_mean": v}` says higher is better,
    `{"metric": m, "max_mean": v}` says lower is better. A spec that carries
    both is ambiguous, a spec that carries neither cannot fail, and an unknown
    key is a typo that must not be silently ignored.
    """
    raise NotImplementedError("stage 8: implement parse_gate()")


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
    raise NotImplementedError("stage 8: implement evaluate_gate()")


def evaluate_gates(gates, agg):
    """Every gate's verdict, in the declared order: `{"ok", "gates"}`.

    An empty gate list is NOT a pass: it is `{"ok": False, "gates": (),
    "reason": "no_gates"}`, because nothing was checked is not the same sentence
    as everything passed. With at least one gate, `ok` is False as soon as one
    verdict failed and `gates` holds one verdict per gate, in order.
    """
    raise NotImplementedError("stage 8: implement evaluate_gates()")


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
    raise NotImplementedError("stage 8: implement run_exit()")
