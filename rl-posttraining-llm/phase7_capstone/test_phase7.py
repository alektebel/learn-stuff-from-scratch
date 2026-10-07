"""
Phase 7 tests — run this to check your `template_ablation.py`.

    python test_phase7.py

Requires Phase 4 to be implemented (the graph configs import it).
Trains four configurations, so this takes a few seconds.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from test_harness import Checker, assert_between, load_student_module  # noqa: E402
from tiny_sql_env import TASKS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
m = load_student_module(HERE, "template_ablation")

_rows: dict = {}


def rows() -> dict:
    if not _rows:
        for r in m.run_ablation(steps=200, seed=0):
            _rows[r.name] = r
    return _rows


def test_all_configs_present():
    got = rows()
    for config in m.CONFIGS:
        assert config in got, f"ablation is missing the '{config}' row"


def test_rows_well_formed():
    for name, r in rows().items():
        assert isinstance(r.reward, str) and r.reward, f"{name}: empty reward description"
        assert isinstance(r.executes_during_training, bool), (
            f"{name}: executes_during_training must be a bool"
        )
        assert_between(r.accuracy, 0.0, 1.0, f"{name}.accuracy")
        assert_between(r.q5_prob_correct, 0.0, 1.0, f"{name}.q5_prob_correct")


def test_execution_flags_are_honest():
    got = rows()
    for config in ("exec_only", "phased"):
        assert got[config].executes_during_training is True, (
            f"{config} uses execution accuracy — the flag must be True"
        )
    for config in ("graph_only", "phased_plus_graph"):
        assert got[config].executes_during_training is False, (
            f"{config} must not execute generated SQL during training"
        )


def test_exec_only_reproduces_blind_spot():
    r = rows()["exec_only"]
    assert r.q5_prob_correct < 0.5, (
        f"exec_only q5 P(correct) = {r.q5_prob_correct:.3f}; execution accuracy "
        "cannot distinguish q5's candidates, so this must stay near chance"
    )


def test_phased_fixes_q5():
    r = rows()["phased"]
    assert r.q5_prob_correct > 0.8, (
        f"phased q5 P(correct) = {r.q5_prob_correct:.3f}, expected > 0.8"
    )


def test_graph_only_fixes_q5():
    r = rows()["graph_only"]
    assert r.q5_prob_correct > 0.8, (
        f"graph_only q5 P(correct) = {r.q5_prob_correct:.3f}, expected > 0.8 — "
        "structural comparison should separate SUM(price*quantity) from COUNT(*)"
    )


def test_graph_only_never_executes_during_training():
    """Instrument the executor and count calls while training."""
    import tiny_sql_env

    calls = {"n": 0}
    original = tiny_sql_env.SQLEnv.execute

    def counting_execute(self, sql):
        calls["n"] += 1
        return original(self, sql)

    tiny_sql_env.SQLEnv.execute = counting_execute
    try:
        m.train_config("graph_only", steps=25, seed=0)
    finally:
        tiny_sql_env.SQLEnv.execute = original

    assert calls["n"] == 0, (
        f"graph_only executed SQL {calls['n']} times during training. The "
        "execution-free configuration must never run a generated query."
    )


def test_graph_only_matches_baseline_accuracy():
    got = rows()
    assert got["graph_only"].accuracy >= got["exec_only"].accuracy, (
        f"graph_only accuracy {got['graph_only'].accuracy:.2f} < exec_only "
        f"{got['exec_only'].accuracy:.2f}"
    )


def test_every_config_reaches_full_accuracy():
    bad = {n: r.accuracy for n, r in rows().items() if r.accuracy < 1.0}
    assert not bad, f"configs below full accuracy: {bad}"


def test_headline_result():
    """An execution-free config matches the best accuracy AND fixes q5."""
    got = rows()
    best_acc = max(r.accuracy for r in got.values())
    free = [r for r in got.values() if not r.executes_during_training]
    assert free, "no execution-free configuration in the table"
    winner = max(free, key=lambda r: (r.accuracy, r.q5_prob_correct))
    assert winner.accuracy >= best_acc, (
        f"best execution-free accuracy {winner.accuracy:.2f} < best overall {best_acc:.2f}"
    )
    assert winner.q5_prob_correct > 0.8, (
        f"execution-free config left q5 unsolved ({winner.q5_prob_correct:.3f})"
    )


if __name__ == "__main__":
    c = Checker("Phase 7 — capstone ablation")
    c.check("all configs present", test_all_configs_present)
    c.check("rows are well-formed", test_rows_well_formed)
    c.check("execution flags are honest", test_execution_flags_are_honest)
    c.check("exec_only reproduces the q5 blind spot", test_exec_only_reproduces_blind_spot)
    c.check("phased fixes q5", test_phased_fixes_q5)
    c.check("graph_only fixes q5", test_graph_only_fixes_q5)
    c.check("graph_only NEVER executes during training",
            test_graph_only_never_executes_during_training)
    c.check("graph_only matches baseline accuracy", test_graph_only_matches_baseline_accuracy)
    c.check("every config reaches full accuracy", test_every_config_reaches_full_accuracy)
    c.check("HEADLINE: execution-free matches the best", test_headline_result)
    sys.exit(c.summary())
