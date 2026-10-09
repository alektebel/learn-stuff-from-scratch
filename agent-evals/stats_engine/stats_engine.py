"""stats_engine: paired comparison of two agent variants, bootstrapped over TASKS.

agent-evals #7. The design correction this module exists to teach (see
agent-evals/README.md, row #7): when two variants are evaluated on the SAME
task set, their outcomes are PAIRED by task, and the task -- not the run or
episode -- is the resampling unit. Several runs of the same task (seeds,
retries) are correlated, not independent evidence; resampling runs instead of
tasks inflates the effective sample size and yields confidence intervals that
are too narrow (anti-conservative) and p-values that are too small.

LEARN-mode file: parse_jsonl and summarise_by_task are provided as TEST
INFRASTRUCTURE and are implemented. The four statistical entry points
(paired_bootstrap_ci, paired_bootstrap_p, compare, main) are deliberately
unwritten; the tests in tests/test_stats_engine.py define what the learner
must make true.

Determinism: every stochastic entry point takes an explicit ``seed`` and uses
its own random.Random; nothing depends on global RNG state or PYTHONHASHSEED.
Standard library only (no numpy, no pip in this environment).
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any, Sequence

REQUIRED_FIELDS = ("agent", "task_id", "success")

__all__ = [
    "REQUIRED_FIELDS",
    "parse_jsonl",
    "summarise_by_task",
    "paired_bootstrap_ci",
    "paired_bootstrap_p",
    "compare",
    "main",
]


# --------------------------------------------------------------------------
# Test infrastructure (implemented on purpose; its tests pass today)
# --------------------------------------------------------------------------


def _field(record: Any, name: str) -> Any:
    """Read ``name`` from a mapping-style or attribute-style run record."""
    if isinstance(record, Mapping):
        if name not in record:
            raise ValueError(f"run record is missing field {name!r}: {record!r}")
        return record[name]
    try:
        return getattr(record, name)
    except AttributeError:
        raise ValueError(f"run record is missing field {name!r}: {record!r}") from None


def parse_jsonl(lines: Iterable[str]) -> list[dict[str, Any]]:
    """Parse JSONL run records of the harness-lab shape (eval/contract.py):
    one JSON object per line with fields ``agent``, ``task_id``, ``success``.

    Blank lines are skipped. Raises ValueError on a line that is not valid
    JSON, on an object missing a required field, or on a ``success`` that is
    neither a bool nor the ints 0/1 (a string like "yes" is rejected, not
    coerced). 0/1 are coerced to False/True.
    """
    records: list[dict[str, Any]] = []
    for lineno, raw in enumerate(lines, start=1):
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {lineno}: not valid JSON: {exc}") from exc
        if not isinstance(obj, dict):
            raise ValueError(
                f"line {lineno}: expected a JSON object, got {type(obj).__name__}"
            )
        for name in REQUIRED_FIELDS:
            if name not in obj:
                raise ValueError(f"line {lineno}: run record is missing field {name!r}")
        ok = obj["success"]
        if isinstance(ok, bool):
            pass
        elif isinstance(ok, int) and ok in (0, 1):
            obj["success"] = bool(ok)
        else:
            raise ValueError(
                f"line {lineno}: 'success' must be a bool (or 0/1), got {ok!r}"
            )
        records.append(obj)
    return records


def summarise_by_task(records: Iterable[Any]) -> dict[str, dict[str, bool]]:
    """Group run records into the paired shape: task_id -> {agent_name: success}.

    This is the mapping every statistic below consumes. It is strict on
    purpose:

    - the same agent may appear at most once per task. A second run of the
      same task (a seed/retry) is a duplicate: reduce seed-level data to one
      per-task outcome yourself and say how -- this function refuses to guess
      an aggregation rule -> ValueError;
    - every task must carry the SAME set of agents. If one variant is missing
      on some task, the two runs are not on a common task set and nothing is
      paired -> ValueError.

    Accepts dict records and attribute-style records (see _field).
    """
    by_task: dict[str, dict[str, bool]] = {}
    for record in records:
        agent = str(_field(record, "agent"))
        task_id = str(_field(record, "task_id"))
        success = bool(_field(record, "success"))
        per_task = by_task.setdefault(task_id, {})
        if agent in per_task:
            raise ValueError(
                f"duplicate run: agent {agent!r} appears twice on task {task_id!r}"
            )
        per_task[agent] = success
    agent_sets = {frozenset(per_task) for per_task in by_task.values()}
    if len(agent_sets) > 1:
        raise ValueError(
            "agents differ across tasks; the comparison is not paired "
            f"(per-task agent sets: {sorted(map(sorted, agent_sets))})"
        )
    return by_task


# --------------------------------------------------------------------------
# The core (LEARN: not implemented yet; the tests define it)
# --------------------------------------------------------------------------


def paired_bootstrap_ci(
    a_passes: Sequence[bool],
    b_passes: Sequence[bool],
    *,
    n_resamples: int = 10000,
    confidence: float = 0.95,
    seed: int = 0,
) -> tuple[float, float]:
    """Percentile CI for mean(a) - mean(b), resampling TASKS (paired).

    ``a_passes`` / ``b_passes`` are per-task outcomes of the two variants on
    the SAME task set: equal lengths, index i = task i. Each resample draws
    n task indices WITH replacement and computes the mean difference over the
    SAME indices for both variants (the pairing is preserved: one draw feeds
    both variants). The returned interval is the ``confidence`` percentile
    band of the resampled mean differences.

    Raises ValueError if the two sequences differ in length (never silently
    zip-truncates) or if ``confidence`` is not in (0, 1).

    LEARN: not implemented yet -- tests/test_stats_engine.py defines it.
    """
    raise NotImplementedError("paired_bootstrap_ci is the learner's core (agent-evals #7)")


def paired_bootstrap_p(
    a_passes: Sequence[bool],
    b_passes: Sequence[bool],
    *,
    n_resamples: int = 10000,
    seed: int = 0,
) -> float:
    """Two-sided bootstrap p-value for the paired mean difference.

    Resample tasks exactly as in paired_bootstrap_ci. Over the n_resamples
    resampled mean differences d*, the p-value is

        min(1, 2 * min(#{d* <= 0}, #{d* >= 0}) / n_resamples)

    Resampled differences of exactly 0 count on BOTH sides, so two identical
    variants give p = 1.0. The result is a float in [0, 1].

    LEARN: not implemented yet -- tests/test_stats_engine.py defines it.
    """
    raise NotImplementedError("paired_bootstrap_p is the learner's core (agent-evals #7)")


def compare(a_records: Iterable[Any], b_records: Iterable[Any], *, seed: int = 0) -> dict:
    """Compare two variants' run records on a shared task set.

    ``a_records`` / ``b_records``: iterables of harness-lab run records (dicts
    or attribute objects with fields agent, task_id, success; see
    harness-lab/eval/contract.py), one variant each. They are reduced with
    summarise_by_task, which enforces the pairing (equal task sets, one run
    per task and agent).

    Returns a report dict with EXACTLY these keys:

        n_tasks   -- int, number of paired tasks
        mean_diff -- float, mean(success_a) - mean(success_b) over tasks
        ci        -- (lo, hi) percentile bootstrap CI of mean_diff, task-level
        p         -- float, two-sided bootstrap p-value, task-level
        unit      -- "task" (what was resampled; never "run")
    """
    raise NotImplementedError("compare is the learner's core (agent-evals #7)")


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: python -m stats_engine --a a.jsonl --b b.jsonl [options].

    Flags: --a PATH and --b PATH (JSONL run-record files, one variant each),
    --n-resamples INT (default 10000), --confidence FLOAT (default 0.95),
    --seed INT (default 0). Reads both files with parse_jsonl, calls compare,
    prints the report as JSON on stdout, and returns 0.

    LEARN: not implemented yet -- tests/test_stats_engine.py defines it.
    """
    raise NotImplementedError("main is the learner's core (agent-evals #7)")
