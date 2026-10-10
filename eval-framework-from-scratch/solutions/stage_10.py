"""Eval Framework From Scratch — stage 10: the resume, and the hash that decides
whether a resume is allowed.

DESIGN DECISION — why is the checkpoint keyed by a hash of the EFFECTIVE config?
    A log is only reusable by a run that would have produced it. The cheapest
    honest test is equality of the thing that determines every record: the
    validated suite, with its defaults materialised (stage 1). Hash the file's
    spelling and a resume is refused after somebody writes a default out
    explicitly; hash nothing and a resume silently mixes records from two
    different suites into one log, which is worse than losing the run.

DESIGN DECISION — why does the resume continue inside a case, and therefore not
through `run_suite`?
    Because `(case, repeat)` is the identity of a record, and `run_suite` starts
    every case at repeat zero. A run that died on the third repeat of a case has
    three good records; re-running the whole case would append a second copy of
    records the log already has, and the merged log would not be the log of one
    run — it would be two runs interleaved, with a case that voted twice in every
    metric. So the resume runs the remaining UNITS, in the same order and with
    the same budget rules, and the log it leaves behind is byte for byte the log
    an uninterrupted run would have produced.

DESIGN DECISION — why do the budgets carry over instead of restarting?
    `max_calls` is a property of the run, not of the process that happens to be
    executing it: a run that spent 900 of its 1000 calls, was killed and resumed
    must have 100 left, or the resume is a way to buy more budget by pulling the
    plug. The totals are read from the records themselves — the same account the
    summary uses (stage 5) — because a checkpoint file that failed to record a
    spend would otherwise launder it.

DESIGN DECISION — why does a run without a checkpoint start its log over?
    Because a checkpoint is what makes a log belonging to a run, and a resume is
    only ever allowed to append to the log of ITS run. Starting fresh next to an
    old log would splice two runs into one file — the second run's records after
    the first run's, with no boundary a reader could see — which is the exact
    failure the checkpoint exists to prevent. So no checkpoint means a new run:
    the log is truncated, and the records that were there are gone by design.

DESIGN DECISION — why is a truncated last line tolerated, and nothing else?
    A process that dies while writing leaves a partial line, and losing the whole
    run to that is absurd: the prefix before it is complete and its records are
    valid. But a *malformed* line in the middle is not a crash artefact — it is a
    log somebody edited or a writer that wrote garbage — and quietly skipping it
    would hide the corruption the resume is supposed to notice. The half-written
    tail is not merely ignored, it is REPAIRED: the file ends where the records
    end (or gets the terminator the crash ate), because the next append has to
    land exactly where it would have landed for the log to come out byte for byte
    the way an uninterrupted run would have written it.
"""

import hashlib
import json
import os

from lab import ConfigError
from stage_01 import canonical_suite
from stage_03 import STATUSES, run_case
from stage_07 import RunLog, read_records


def suite_hash(suite):
    """The identity of a suite: `sha256` of its canonical form, first 16 hex chars."""
    text = canonical_suite(suite)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def write_checkpoint(path, *, suite):
    """Write `{"hash", "suite"}` to `path` (creating the parent directory) and
    return it. Called before the run, so a resume can tell which suite the log
    belongs to."""
    state = {"hash": suite_hash(suite), "suite": suite.id}
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with open(path, "w") as handle:
        handle.write(json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n")
    return state


def read_checkpoint(path):
    """The checkpoint at `path`, or `None` when there is no file.

    A file that is not a JSON object, or one without the two keys, is a
    `lab.ConfigError`: somebody wrote it by hand, and guessing is worse than
    refusing.
    """
    if not os.path.exists(path):
        return None
    with open(path) as handle:
        text = handle.read()
    try:
        state = json.loads(text)
    except ValueError as exc:
        raise ConfigError("checkpoint %s: not JSON (%s)" % (path, exc))
    if not isinstance(state, dict) or "hash" not in state or "suite" not in state:
        raise ConfigError("checkpoint %s: expected an object with 'hash' and 'suite', got %r"
                          % (path, state))
    return state


def _repair_tail(path):
    """Cut a half-written record off the end of the log, or terminate a complete
    one that lost its newline.

    A crash in the middle of a write leaves bytes: a partial JSON object, which
    is dropped, or a complete object whose terminator never made it, which only
    needs the newline. Either way the file ends where the records end, because
    the next append has to land exactly where it would have landed.
    """
    if not os.path.exists(path):
        return
    with open(path, "rb") as handle:
        data = handle.read()
    if not data or data.endswith(b"\n"):
        return
    cut = data.rfind(b"\n")
    tail = data[cut + 1:]
    try:
        complete = isinstance(json.loads(tail.decode("utf-8")), dict)
    except (ValueError, UnicodeDecodeError):
        complete = False
    if complete:
        with open(path, "ab") as handle:
            handle.write(b"\n")
    else:
        with open(path, "r+b") as handle:
            handle.truncate(cut + 1 if cut >= 0 else 0)


def _units(suite):
    """Every `(case, repeat)` the suite declares, in the run's order."""
    for case in suite.cases:
        for repeat in range(getattr(case, "repeats", 1)):
            yield case, repeat


def resume_run(suite, solver, *, clock, registry, sink=None, state_path, log_path):
    """Continue a run from `log_path`, or start one.

    Returns `{"suite", "resumed", "reused", "cases", "records", "status_counts",
    "ticks", "calls", "stopped"}`: `reused` counts the records already on disk,
    `records` the total, the status counts and the ticks/calls sums cover the
    merged records, and `stopped` is whichever budget stopped the resumed work
    (the run's budgets minus what the records already show).

    A checkpoint that names a different suite raises `lab.ConfigError`; a missing
    one is written first and the whole suite runs.
    """
    state = read_checkpoint(state_path)
    if state is None:
        write_checkpoint(state_path, suite=suite)
        parent = os.path.dirname(os.path.abspath(log_path))
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        with open(log_path, "w"):
            pass
        resumed = False
        already = []
    else:
        expected = suite_hash(suite)
        if state["hash"] != expected:
            raise ConfigError(
                "checkpoint %s belongs to suite %r (hash %s), not to suite %r (hash %s): a "
                "resume may only reuse a log the same config would have produced"
                % (state_path, state["suite"], state["hash"], suite.id, expected))
        resumed = True
        already = read_records(log_path, tolerant=True)
        _repair_tail(log_path)

    bound = registry.bind(getattr(suite, "metrics", ()))
    done = {(record["case"], record["repeat"]) for record in already}
    spending = {"ticks": sum(record["ticks"] for record in already),
                "calls": sum(record["calls"] for record in already)}
    counts = {status: 0 for status in STATUSES}
    for record in already:
        counts[record["status"]] = counts.get(record["status"], 0) + 1

    max_calls = getattr(suite, "max_calls", None)
    max_ticks = getattr(suite, "max_ticks", None)
    log = RunLog(log_path)
    fresh = 0
    stopped = None
    for case, repeat in _units(suite):
        if (case.id, repeat) in done:
            continue
        if max_calls is not None and spending["calls"] + 1 > max_calls:
            stopped = "calls"
            break
        if max_ticks is not None and spending["ticks"] > max_ticks:
            stopped = "ticks"
            break
        record = run_case(case, solver, clock=clock, bound=bound, repeat=repeat)
        log.append(record)
        if sink is not None:
            sink(record)
        fresh += 1
        spending["ticks"] += record["ticks"]
        spending["calls"] += record["calls"]
        counts[record["status"]] = counts.get(record["status"], 0) + 1

    return {"suite": suite.id, "resumed": resumed, "reused": len(already),
            "cases": len(tuple(getattr(suite, "cases", ()))),
            "records": len(already) + fresh, "status_counts": counts,
            "ticks": spending["ticks"], "calls": spending["calls"], "stopped": stopped}
