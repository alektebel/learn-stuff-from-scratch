"""Tests for agent-evals #4: CI regression gate (BUILD: eval infrastructure).

Map to README.md / tree.toml:
    deterministic regression blocks -> test_deterministic_regression_blocks
    low-variance metric blocks       -> test_cost_regression_blocks / test_latency_regression_blocks
    noise does not block             -> test_small_success_drop_only_warns
    clean passes                     -> test_clean_candidate_passes
    intervals                        -> test_newcombe / test_wilson
    report + CLI                     -> test_render / test_cli_exit_code / test_read_jsonl
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ci_gate  # noqa: E402
from ci_gate import GateConfig, evaluate, median, newcombe, read_jsonl, wilson  # noqa: E402

CFG = GateConfig()


def rec(task, seed, success, cost=0.01, wall=1.0):
    return {"task_id": task, "seed": seed, "success": success, "cost_eur": cost,
            "wall_time_s": wall}


def test_deterministic_regression_blocks():
    base = [rec("t1", 0, True), rec("t2", 0, True)]
    cand = [rec("t1", 0, False), rec("t2", 0, True)]
    v = evaluate(base, cand, CFG)
    assert v.blocked and v.metrics["deterministic_regressions"] == 1
    assert "deterministic" in v.blocks[0]


def test_cost_regression_blocks():
    base = [rec(f"t{i}", 0, True, cost=0.01) for i in range(10)]
    cand = [rec(f"t{i}", 0, True, cost=0.02) for i in range(10)]
    v = evaluate(base, cand, CFG)
    assert v.blocked and any("cost" in b for b in v.blocks)


def test_latency_regression_blocks():
    base = [rec(f"t{i}", 0, True, wall=1.0) for i in range(10)]
    cand = [rec(f"t{i}", 0, True, wall=1.5) for i in range(10)]
    v = evaluate(base, cand, CFG)
    assert v.blocked and any("latency" in b for b in v.blocks)


def test_small_success_drop_only_warns():
    base = [rec(f"t{i}", 0, i < 40, cost=0.01) for i in range(50)]
    cand = [rec(f"t{i}", 1, i < 39, cost=0.01) for i in range(50)]
    v = evaluate(base, cand, CFG)
    assert not v.blocked and v.warnings
    assert "within noise" in v.warnings[0]


def test_clean_candidate_passes():
    same = [rec(f"t{i}", 0, i < 40) for i in range(50)]
    v = evaluate(same, [dict(r) for r in same], CFG)
    assert not v.blocked and not v.blocks and not v.warnings


def test_thresholds_are_configurable():
    base = [rec(f"t{i}", 0, True, cost=0.01) for i in range(10)]
    cand = [rec(f"t{i}", 0, True, cost=0.015) for i in range(10)]  # +50%
    assert not evaluate(base, cand, GateConfig(max_cost_regression=0.60)).blocked
    assert evaluate(base, cand, GateConfig(max_cost_regression=0.10)).blocked


def test_newcombe():
    lo, hi = newcombe(80, 100, 79, 100)   # a 1-point drop: brackets zero
    assert lo < 0 < hi
    lo, hi = newcombe(90, 100, 30, 100)   # a large drop: entirely below zero
    assert hi < 0


def test_wilson_and_median():
    assert wilson(0, 10)[0] == 0.0
    assert median([]) == 0.0
    assert median([3, 1, 2]) == 2 and median([1, 2, 3, 4]) == 2.5


def test_render():
    v = evaluate([rec("t1", 0, True)], [rec("t1", 0, False)], CFG)
    text = v.render()
    assert "BLOCKED" in text and "success" in text and "cost median" in text


def test_read_jsonl(tmp_path):
    path = tmp_path / "r.jsonl"
    path.write_text("\n".join(json.dumps(rec("t1", 0, True)) for _ in range(3)) + "\n")
    assert len(read_jsonl(path)) == 3


def test_cli_exit_code(tmp_path, capsys):
    base = tmp_path / "b.jsonl"
    cand = tmp_path / "c.jsonl"
    base.write_text(json.dumps(rec("t1", 0, True)) + "\n")
    cand.write_text(json.dumps(rec("t1", 0, False)) + "\n")
    assert ci_gate.main(["--baseline", str(base), "--candidate", str(cand)]) == 1
    pass_cand = tmp_path / "p.jsonl"
    pass_cand.write_text(json.dumps(rec("t1", 0, True)) + "\n")
    assert ci_gate.main(["--baseline", str(base), "--candidate", str(pass_cand)]) == 0
