"""Eval Framework From Scratch — stage 4: the run.

DESIGN DECISION — why is the budget checked BEFORE the call, and with `+ 1`?
    A budget that is checked after the call is a receipt, not a limit: the point
    of `max_calls` is that the call that would exceed it does not happen, because
    the thing being spent may be somebody else's money. So the check is
    `calls + 1 > max_calls`, before the case runs, and the reason it stopped is
    recorded as `stopped` while the cases that were never reached simply do not
    appear in the log.

DESIGN DECISION — why is a case that was never reached absent from the log
instead of a `skipped` record?
    A record is a measurement. Aggregation (stage 5) rolls records up by case and
    a `skipped` line would either be counted — inflating `n` with a case that was
    never run — or need special-casing in every metric, gate and diff downstream.
    The log keeps what happened; the run's own summary says what did not, and
    which budget stopped it.

DESIGN DECISION — why are a case's repeats adjacent, and why is the log order
the run's identity?
    The resume (stage 10) reuses a PREFIX of the log and appends the rest: it
    needs to know that the records up to a point are exactly the first N units of
    this run and nothing else. With the cases in declared order and each case's
    repeats together, "the first N (case, repeat) units" is a prefix, so a
    resumed run can produce the same bytes as an uninterrupted one. Interleaving
    repeats across cases would make the log's shape depend on the schedule.

DESIGN DECISION — why does the runner catch nothing from a case?
    Because everything that can go wrong inside a case is already a status in its
    record (stage 3): the solver's exception, the timeout, the missing answer.
    An exception that escapes `run_case` is either a broken plugin (stage 2
    records metric failures itself) or our own bug, and a runner that converts it
    into "the suite finished with fewer records" has hidden the only fact that
    mattered. The one thing the runner owns is the config: `registry.bind` runs
    before the first case, so a missing metric plugin fails the whole run instead
    of failing it twice per case.

DESIGN DECISION — why are the summary's ticks and calls summed from the RECORDS?
    Because the log is the account. A second counter maintained by the loop is a
    number that can drift from the records it claims to summarise, and then two
    reports of one run disagree and nobody can tell which one lied.
"""

from stage_03 import STATUSES, run_case

#: The keys of a run's summary: exact and complete.
RUN_KEYS = ("suite", "cases", "records", "status_counts", "metric_errors", "ticks",
            "calls", "stopped")


def run_suite(suite, solver, *, clock, registry, sink=None):
    """Run every case of `suite` and return the run's counters.

    Cases run in the suite's declared order, and a case's repeats are adjacent.
    `registry.bind(suite.metrics)` happens first, so an unknown plugin raises
    `lab.ConfigError` before any case runs. Before each case the call budget
    (`calls + 1 > suite.max_calls`) and then the clock budget
    (`clock.now() - started > suite.max_ticks`) are checked; a stop records
    `stopped` as `"calls"` or `"ticks"` and emits no further records.

    `status_counts` carries all five statuses, zero-filled. `cases` counts the
    cases the suite declares, `records` the records emitted, and `ticks`/`calls`
    are the sums over the records. `sink(record)`, when given, is called once per
    record, in the order the run produced them.
    """
    bound = registry.bind(getattr(suite, "metrics", ()))
    started = clock.now()
    cases = tuple(getattr(suite, "cases", ()))
    counts = {status: 0 for status in STATUSES}
    records = ticks = calls = failed_metrics = 0
    stopped = None
    for case in cases:
        for repeat in range(getattr(case, "repeats", 1)):
            max_calls = getattr(suite, "max_calls", None)
            if max_calls is not None and calls + 1 > max_calls:
                stopped = "calls"
                break
            max_ticks = getattr(suite, "max_ticks", None)
            if max_ticks is not None and clock.now() - started > max_ticks:
                stopped = "ticks"
                break
            record = run_case(case, solver, clock=clock, bound=bound, repeat=repeat)
            records += 1
            counts[record["status"]] += 1
            failed_metrics += 1 if record["metric_errors"] else 0
            ticks += record["ticks"]
            calls += record["calls"]
            if sink is not None:
                sink(record)
        if stopped is not None:
            break
    return {"suite": suite.id, "cases": len(cases), "records": records,
            "status_counts": counts, "metric_errors": failed_metrics,
            "ticks": ticks, "calls": calls, "stopped": stopped}
