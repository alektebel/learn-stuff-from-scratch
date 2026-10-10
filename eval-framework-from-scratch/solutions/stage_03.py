"""Eval Framework From Scratch — stage 3: one case, one record.

DESIGN DECISION — why is the deadline checked after the call, and against an
injected clock?
    A runner cannot preempt a callable: there is no way to stop a solver that
    decided to loop forever, and a signal or a thread would make the framework's
    behaviour depend on the machine it ran on. So the budget is measured where it
    can be measured honestly — how much of the CLOCK the code under test spent —
    and the verdict arrives after the fact. A stopwatch here would measure the
    load average, the garbage collector and the neighbour's build job, and two
    runs of the same suite would not produce the same log.

DESIGN DECISION — why is the answer of a timed-out call discarded?
    Because it is not an answer under the budget. Keeping it lets a metric be
    computed on work the budget forbade, so a run that blew its limit reports a
    quality number anyway and nobody notices the limit was meaningless. The
    record says `timeout`, the answer is `None`, no metric runs, and the cost
    that caused it is in the record.

DESIGN DECISION — why are `solver_error` and `case_error` different statuses?
    Attribution. An exception from the solver is data about the system under
    test: it is counted, and the note carries the type and the message so a run
    can be read without the traceback. An exception from OUR code — a case
    object that came from somewhere else with a missing prompt or a `max_ticks`
    that is a string — is a bug in the harness, and a harness that files its own
    crash as a model failure has poisoned its own benchmark. `case_error` is
    recorded rather than raised so one bad case cannot destroy the other nine,
    and the gate (stage 8) refuses to publish a run that has any.

DESIGN DECISION — why is `metric_errors` separate from the status?
    The status describes the answer ("did we get one, in budget?"); the metric
    errors describe the measurement ("could we turn it into a number?"). A case
    can be answered perfectly and measured not at all, and merging the two would
    turn "our metric plugin raised" into "the model failed" — the same
    attribution mistake, one layer down.

DESIGN DECISION — why does the record carry the case's weight?
    Because aggregation happens later, over records, and the weight lives on the
    case. A rollup that reads the log cannot know what the suite declared unless
    the declaration travelled with the measurement, and a suite whose weights are
    silently read as 1.0 reports a mean that no author asked for — with every
    wrong number still looking plausible. The weight is part of the record, and
    it is normalised to a float where the record is built.

DESIGN DECISION — why is every metric value rounded where the record is built?
    The log is diffed byte for byte: by the resume (stage 10), by the baseline
    diff (stage 9) and by a human with `diff` at three in the morning. A float
    that reached the record through a different but equivalent path — 0.1 + 0.2
    against 0.3 — would make two identical runs differ in bytes, and `-0.0` is a
    different string from `0.0`.
"""

from lab import ConfigError
from stage_02 import apply_metrics

#: What a case record may say about itself, in the only vocabulary there is.
STATUSES = ("ok", "no_answer", "solver_error", "timeout", "case_error")

#: The keys of a case record: exact and complete, in this order.
CASE_RECORD_KEYS = ("case", "repeat", "weight", "status", "answer", "metrics",
                    "metric_errors", "ticks", "calls", "note")

#: How many decimal places a metric value keeps in the log.
METRIC_DP = 6


def _case_id(case):
    """The id a record can carry even when the case itself is broken."""
    value = getattr(case, "id", None)
    return value if isinstance(value, str) else ""


def _prepare(case):
    """The three fields a run needs, validated: our failures, not the solver's."""
    case_id = _case_id(case)
    if not case_id.strip():
        raise ConfigError("case %r: id must be a non-empty string" % (case_id,))
    prompt = getattr(case, "prompt", None)
    if not isinstance(prompt, str) or not prompt.strip():
        raise ConfigError("case %r: prompt must be a non-empty string, got %r"
                          % (case_id, prompt))
    max_ticks = getattr(case, "max_ticks", None)
    if isinstance(max_ticks, bool) or not isinstance(max_ticks, int) or max_ticks < 1:
        raise ConfigError("case %r: max_ticks must be an int >= 1, got %r"
                          % (case_id, max_ticks))
    weight = getattr(case, "weight", 1.0)
    if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not weight > 0:
        raise ConfigError("case %r: weight must be a number > 0, got %r" % (case_id, weight))
    return case_id, prompt, max_ticks, float(weight)


def round_metrics(record):
    """The same record with every metric value rounded to `METRIC_DP`.

    A copy: the record handed in is not modified. `-0.0` rounds to `0.0`, because
    the log is compared as text.
    """
    rounded = dict(record)
    rounded["metrics"] = {
        name: (value if value is None else round(value, METRIC_DP) + 0.0)
        for name, value in record["metrics"].items()
    }
    return rounded


def run_case(case, solver, *, clock, bound, repeat=0):
    """Run one case once and return its record.

    The solver is called as `solver(case.prompt, clock=clock)` and the ticks it
    spent are `clock.now()` before and after that call. The status is the first
    that applies: `case_error` (our own preparation of the case failed, so the
    call did not happen and the note says why), `solver_error` (the call raised,
    or answered with something that is not a `str` and not `None`), `timeout`
    (the clock ran past `case.max_ticks`; the answer is discarded), `no_answer`
    (`None`), else `ok`.

    Metrics run only for `ok`, through `stage_02.apply_metrics`; their failures
    land in `metric_errors` and do not change the status.
    """
    started = clock.now()
    if isinstance(repeat, bool) or not isinstance(repeat, int) or repeat < 0:
        raise ConfigError("run_case(repeat): repeat must be an int >= 0, got %r" % (repeat,))
    try:
        case_id, prompt, max_ticks, weight = _prepare(case)
    except ConfigError as exc:
        return round_metrics({
            "case": _case_id(case), "repeat": repeat, "weight": 1.0,
            "status": "case_error", "answer": None, "metrics": {}, "metric_errors": {},
            "ticks": 0, "calls": 0, "note": str(exc)})

    status, answer, calls, note = "ok", None, 0, ""
    try:
        calls = 1                     # a call that raised is still a call: it was spent
        answer = solver(prompt, clock=clock)
    except Exception as exc:                                    # noqa: BLE001
        status = "solver_error"
        note = "%s: %s" % (type(exc).__name__, exc)

    ticks = clock.now() - started
    metrics, metric_errors = {}, {}
    if status == "ok":
        if ticks > max_ticks:
            status = "timeout"
            note = "took %d ticks of %d" % (ticks, max_ticks)
            answer = None
        elif answer is None:
            status = "no_answer"
        elif not isinstance(answer, str):
            status = "solver_error"
            note = "the solver answered with %s, not a str" % (type(answer).__name__,)
            answer = None
        else:
            measured = apply_metrics(case, answer, bound)
            metrics, metric_errors = measured["values"], measured["errors"]

    return round_metrics({
        "case": case_id, "repeat": repeat, "weight": weight, "status": status,
        "answer": answer, "metrics": metrics, "metric_errors": metric_errors,
        "ticks": ticks, "calls": calls, "note": note})
