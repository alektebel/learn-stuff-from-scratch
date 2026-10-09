"""Tests for agent-evals #7: paired bootstrap over tasks (stats_engine).

LEARN mode: the statistical core (paired_bootstrap_ci, paired_bootstrap_p,
compare, main) is not written yet; every test that needs it is decorated
``xfail(raises=NotImplementedError, reason="core not implemented")`` and
turns into a real check once the learner implements it. The record-parsing
and grouping helpers are provided infrastructure and their tests pass today.

Map to SPEC.md:
    A1 -> test_parse_jsonl_*                        A6 -> test_ci_length_mismatch_raises_value_error
    A2 -> test_summarise_by_task_maps/accepts_...   A7 -> test_p_value_matches_sign_of_effect
    A3 -> test_summarise_by_task_unequal/rejects    A8 -> test_compare_report_shape
    A4 -> test_ci_identical/separated               A9 -> test_main_cli_smoke
    A5 -> test_deterministic_under_fixed_seed       A10 -> test_mcnemar_cross_check_with_eval_stats
    L1 -> test_task_ci_is_wider_than_naive_run_resampling
    L2 -> test_single_task_degenerate_no_crash
    L3 -> test_ci_length_mismatch_raises_value_error (shared with A6)
    L4 -> test_summarise_by_task_unequal/rejects (shared with A3)
"""

import json
import math
import random
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# Make the agent-evals project importable no matter where pytest is rooted.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import stats_engine  # noqa: E402

XFAIL_CORE = pytest.mark.xfail(
    raises=NotImplementedError, reason="core not implemented"
)

A_NAME, B_NAME = "alpha", "beta"


# --------------------------------------------------------------------------
# record helpers (test infrastructure)
# --------------------------------------------------------------------------


def rec(agent, task_id, success):
    return {"agent": agent, "task_id": task_id, "success": success}


def one_agent_records(agent, passes, tasks=None):
    tasks = tasks or [f"task-{i:03d}" for i in range(len(passes))]
    return [rec(agent, t, bool(s)) for t, s in zip(tasks, passes)]


def _naive_run_resample_ci(a_runs, b_runs, *, n_resamples, confidence, seed):
    """WRONG ON PURPOSE: a run-level (row-level) bootstrap.

    Resamples the n_runs rows instead of the tasks, ignoring that the runs
    are clustered (and correlated) within tasks. Lives in the TEST, not in
    the core, so that limit case L1 can measure how much too narrow this is.
    """
    rng = random.Random(seed)
    n = len(a_runs)
    assert n == len(b_runs)
    diffs = []
    for _ in range(n_resamples):
        idx = [rng.randrange(n) for _ in range(n)]
        mean_a = sum(a_runs[i] for i in idx) / n
        mean_b = sum(b_runs[i] for i in idx) / n
        diffs.append(mean_a - mean_b)
    diffs.sort()

    def quantile(p):
        pos = p * (len(diffs) - 1)
        lo = int(pos)
        hi = min(lo + 1, len(diffs) - 1)
        frac = pos - lo
        return diffs[lo] * (1.0 - frac) + diffs[hi] * frac

    alpha = (1.0 - confidence) / 2.0
    return quantile(alpha), quantile(1.0 - alpha)


# --------------------------------------------------------------------------
# A1: record parsing (infrastructure — passes today)
# --------------------------------------------------------------------------


def test_parse_jsonl_reads_records():
    lines = [
        json.dumps(rec("alpha", "task-000", True)),
        "",  # blank lines are skipped
        json.dumps(rec("beta", "task-000", False)),
        json.dumps({"agent": "alpha", "task_id": "task-001", "success": 1}),  # 0/1 coerced
    ]
    assert stats_engine.parse_jsonl(lines) == [
        rec("alpha", "task-000", True),
        rec("beta", "task-000", False),
        rec("alpha", "task-001", True),
    ]


def test_parse_jsonl_missing_field_raises():
    with pytest.raises(ValueError):
        stats_engine.parse_jsonl(['{"agent": "alpha", "task_id": "task-000"}'])  # no "success"


def test_parse_jsonl_rejects_non_boolean_success():
    with pytest.raises(ValueError):
        stats_engine.parse_jsonl([json.dumps(rec("alpha", "task-000", "yes"))])


# --------------------------------------------------------------------------
# A2/A3/L4: grouping and pairing enforcement (infrastructure — passes today)
# --------------------------------------------------------------------------


def test_summarise_by_task_maps_task_to_agent_success():
    records = one_agent_records(A_NAME, [True, False]) + one_agent_records(
        B_NAME, [False, True]
    )
    assert stats_engine.summarise_by_task(records) == {
        "task-000": {A_NAME: True, B_NAME: False},
        "task-001": {A_NAME: False, B_NAME: True},
    }


def test_summarise_by_task_accepts_attribute_records():
    records = [
        SimpleNamespace(agent="alpha", task_id="task-000", success=True),
        SimpleNamespace(agent="beta", task_id="task-000", success=False),
    ]
    assert stats_engine.summarise_by_task(records) == {
        "task-000": {"alpha": True, "beta": False}
    }


def test_summarise_by_task_unequal_task_sets_raises():
    # beta is missing on task-002: not a paired comparison
    records = one_agent_records(A_NAME, [1, 0, 1]) + one_agent_records(B_NAME, [1, 0])
    with pytest.raises(ValueError):
        stats_engine.summarise_by_task(records)


def test_summarise_by_task_rejects_duplicate_run():
    records = one_agent_records(A_NAME, [1, 0]) + one_agent_records(
        A_NAME, [1], tasks=["task-000"]
    )
    with pytest.raises(ValueError):
        stats_engine.summarise_by_task(records)


# --------------------------------------------------------------------------
# A4/A5/A6: paired_bootstrap_ci (core — xfail until implemented)
# --------------------------------------------------------------------------


@XFAIL_CORE
def test_ci_identical_variants_covers_zero():
    a = [1, 0, 1, 1, 0, 1, 0, 0, 1, 1]
    lo, hi = stats_engine.paired_bootstrap_ci(a, a, n_resamples=500, seed=0)
    assert isinstance(lo, float) and isinstance(hi, float)
    assert lo <= hi
    assert lo <= 0.0 <= hi


@XFAIL_CORE
def test_ci_identical_variants_is_exactly_zero():
    """Pairing, sharply: with identical per-task outcomes every resampled
    difference is 0, so the CI is the single point (0, 0). An implementation
    that resamples the two variants independently (unpaired) returns a
    non-degenerate interval and fails here."""
    a = [1, 0, 1, 1, 0, 1, 0, 0, 1, 1]
    assert stats_engine.paired_bootstrap_ci(a, a, n_resamples=500, seed=0) == (0.0, 0.0)


@XFAIL_CORE
def test_ci_separated_variants_excludes_zero():
    a = [1] * 18 + [0] * 2
    b = [1] * 2 + [0] * 18
    lo, hi = stats_engine.paired_bootstrap_ci(a, b, n_resamples=1000, seed=0)
    assert isinstance(lo, float) and isinstance(hi, float)
    assert lo <= hi
    assert lo > 0.0


@XFAIL_CORE
def test_deterministic_under_fixed_seed():
    a = [1, 0, 1, 1, 0, 0, 1, 1, 0, 1]
    b = [1, 0, 0, 1, 0, 1, 1, 0, 0, 0]
    ci1 = stats_engine.paired_bootstrap_ci(a, b, n_resamples=300, seed=42)
    ci2 = stats_engine.paired_bootstrap_ci(a, b, n_resamples=300, seed=42)
    assert ci1 == ci2
    p1 = stats_engine.paired_bootstrap_p(a, b, n_resamples=300, seed=42)
    p2 = stats_engine.paired_bootstrap_p(a, b, n_resamples=300, seed=42)
    assert p1 == p2


@XFAIL_CORE
def test_ci_length_mismatch_raises_value_error():
    with pytest.raises(ValueError):
        stats_engine.paired_bootstrap_ci([1, 0], [1, 0, 1], seed=0)


# --------------------------------------------------------------------------
# A7: paired_bootstrap_p (core — xfail until implemented)
# --------------------------------------------------------------------------


@XFAIL_CORE
def test_p_value_matches_sign_of_effect():
    identical = [1, 0, 1, 1, 0, 1, 0, 1]
    p_same = stats_engine.paired_bootstrap_p(identical, identical, n_resamples=1000, seed=0)
    assert 0.5 <= p_same <= 1.0  # the SPEC tie rule makes this exactly 1.0
    a = [1] * 10 + [0] * 30  # 10 discordant pairs, all favouring a
    b = [0] * 40
    p_diff = stats_engine.paired_bootstrap_p(a, b, n_resamples=1000, seed=0)
    assert 0.0 <= p_diff < 0.05


# --------------------------------------------------------------------------
# A8: compare() report shape (core — xfail until implemented)
# --------------------------------------------------------------------------


@XFAIL_CORE
def test_compare_report_shape():
    a = [1] * 18 + [0] * 2
    b = [1] * 2 + [0] * 18
    report = stats_engine.compare(
        one_agent_records(A_NAME, a), one_agent_records(B_NAME, b), seed=0
    )
    assert set(report) == {"n_tasks", "mean_diff", "ci", "p", "unit"}
    assert report["unit"] == "task"
    assert report["n_tasks"] == 20
    assert report["mean_diff"] == pytest.approx(0.8)
    lo, hi = report["ci"]
    assert isinstance(lo, float) and isinstance(hi, float)
    assert lo <= hi
    assert 0.0 <= report["p"] <= 1.0


# --------------------------------------------------------------------------
# L1: the project's point — the resampling unit is the task (core — xfail)
# --------------------------------------------------------------------------


@XFAIL_CORE
def test_task_ci_is_wider_than_naive_run_resampling():
    n_tasks, seeds = 40, 5
    # Perfectly correlated seeds within a task: the task is solved or not,
    # for both variants (a solves 30 tasks, b solves 25 of the same set).
    a_task = [1 if t < 30 else 0 for t in range(n_tasks)]
    b_task = [1 if t < 25 else 0 for t in range(n_tasks)]
    a_runs = [s for s in a_task for _ in range(seeds)]
    b_runs = [s for s in b_task for _ in range(seeds)]

    task_ci = stats_engine.paired_bootstrap_ci(a_task, b_task, n_resamples=2000, seed=0)
    run_ci = _naive_run_resample_ci(
        a_runs, b_runs, n_resamples=2000, confidence=0.95, seed=0
    )
    task_width = task_ci[1] - task_ci[0]
    run_width = run_ci[1] - run_ci[0]
    assert run_width > 0.0
    # theory says ~sqrt(5) wider; keep a conservative margin
    assert task_width > run_width * 1.1


# --------------------------------------------------------------------------
# L2: degenerate input (core — xfail until implemented)
# --------------------------------------------------------------------------


@XFAIL_CORE
def test_single_task_degenerate_no_crash():
    lo, hi = stats_engine.paired_bootstrap_ci([1], [0], n_resamples=100, seed=0)
    assert isinstance(lo, float) and isinstance(hi, float)
    assert lo <= hi
    p = stats_engine.paired_bootstrap_p([1], [0], n_resamples=100, seed=0)
    assert 0.0 <= p <= 1.0


# --------------------------------------------------------------------------
# A9: CLI (core — xfail until implemented)
# --------------------------------------------------------------------------


@XFAIL_CORE
def test_main_cli_smoke(tmp_path, capsys, monkeypatch):
    a = one_agent_records(A_NAME, [1, 0, 1, 1])
    b = one_agent_records(B_NAME, [0, 0, 1, 0])
    file_a = tmp_path / "a.jsonl"
    file_b = tmp_path / "b.jsonl"
    file_a.write_text("\n".join(json.dumps(r) for r in a) + "\n")
    file_b.write_text("\n".join(json.dumps(r) for r in b) + "\n")

    calls = {}

    def fake_compare(a_records, b_records, **kwargs):
        calls["a"] = a_records
        calls["b"] = b_records
        calls["kwargs"] = kwargs
        return {
            "n_tasks": 4,
            "mean_diff": 0.5,
            "ci": (0.0, 1.0),
            "p": 0.5,
            "unit": "task",
        }

    monkeypatch.setattr(stats_engine.stats_engine, "compare", fake_compare)

    rc = stats_engine.main(
        ["--a", str(file_a), "--b", str(file_b), "--seed", "3"]
    )
    assert rc == 0
    assert len(calls["a"]) == 4 and len(calls["b"]) == 4
    assert calls["kwargs"].get("seed") == 3
    report = json.loads(capsys.readouterr().out)
    assert report["unit"] == "task"


# --------------------------------------------------------------------------
# A10: optional integration cross-check with harness-lab's McNemar
# --------------------------------------------------------------------------


@XFAIL_CORE
def test_mcnemar_cross_check_with_eval_stats():
    """The bootstrap p must agree with exact McNemar's verdict on the pairs.

    Skipped unless harness-lab's eval package is importable from this
    checkout. The exact McNemar p is recomputed here with math.comb so the
    significance verdict does not depend on eval.stats' API; if eval.stats
    exposes a mcnemar helper we additionally require the same verdict.
    """
    eval_stats = pytest.importorskip("eval.stats")
    a = [1] * 10 + [0] * 30  # 10 discordant pairs, all favouring a
    b = [0] * 40  # 30 concordant failures: McNemar discards them
    n01, n10 = 0, 10  # tasks only b wins / only a wins
    p_exact = 2.0 * sum(math.comb(n01 + n10, k) for k in range(n01 + 1)) / 2.0 ** (n01 + n10)
    assert p_exact < 0.05

    p_boot = stats_engine.paired_bootstrap_p(a, b, n_resamples=2000, seed=0)
    assert p_boot < 0.05

    # eval.stats exposes mcnemar_exact(b, c) -> float (two-sided exact p on
    # the two discordant counts); fall back to name discovery if it moves.
    helper = getattr(eval_stats, "mcnemar_exact", None)
    if helper is None:
        helpers = [
            getattr(eval_stats, name)
            for name in dir(eval_stats)
            if "mcnemar" in name.lower() and callable(getattr(eval_stats, name))
        ]
        helper = helpers[0] if helpers else None
    if helper is None:
        pytest.skip("eval.stats exposes no mcnemar helper with a discoverable name")
    try:
        p_lib = helper(n01, n10)
    except (TypeError, ValueError):
        pytest.skip("eval.stats mcnemar helper has an unexpected call signature")
    if isinstance(p_lib, tuple):
        p_lib = p_lib[0]
    assert (p_lib < 0.05) == (p_boot < 0.05)
