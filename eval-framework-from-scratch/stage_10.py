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

DESIGN DECISION — why is a truncated last line tolerated, and nothing else?
    A process that dies while writing leaves a partial line, and losing the whole
    run to that is absurd: the prefix before it is complete and its records are
    valid. But a *malformed* line in the middle is not a crash artefact — it is a
    log somebody edited or a writer that wrote garbage — and quietly skipping it
    would hide the corruption the resume is supposed to notice.

TODO: implement `suite_hash`, `write_checkpoint`, `read_checkpoint` and
`resume_run`.
"""


def suite_hash(suite):
    """The identity of a suite: `sha256` of its canonical form, first 16 hex chars."""
    raise NotImplementedError("stage 10: implement suite_hash()")


def write_checkpoint(path, *, suite):
    """Write `{"hash", "suite"}` to `path` (creating the parent directory) and
    return it. Called before the run, so a resume can tell which suite the log
    belongs to."""
    raise NotImplementedError("stage 10: implement write_checkpoint()")


def read_checkpoint(path):
    """The checkpoint at `path`, or `None` when there is no file.

    A file that is not a JSON object, or one without the two keys, is a
    `lab.ConfigError`: somebody wrote it by hand, and guessing is worse than
    refusing.
    """
    raise NotImplementedError("stage 10: implement read_checkpoint()")


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
    raise NotImplementedError("stage 10: implement resume_run()")
