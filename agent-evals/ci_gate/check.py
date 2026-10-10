"""Runnable check for ci_gate (standard library only).

    python3 agent-evals/ci_gate/check.py

Asserts the gate's contract: a deterministic regression and a low-variance metric
regression block, while a small success drop within noise only warns. Exits non-zero on
failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # agent-evals/

from ci_gate import GateConfig, evaluate  # noqa: E402


def rec(task, seed, success, cost=0.01, wall=1.0):
    return {"task_id": task, "seed": seed, "success": success, "cost_eur": cost,
            "wall_time_s": wall}


def check() -> None:
    config = GateConfig()

    # 1. A deterministic regression — the same (task, seed) flips pass -> fail — blocks.
    base = [rec("t1", 0, True), rec("t2", 0, True), rec("t3", 0, True)]
    cand = [rec("t1", 0, False), rec("t2", 0, True), rec("t3", 0, True)]
    v = evaluate(base, cand, config)
    assert v.blocked and v.metrics["deterministic_regressions"] == 1, v.render()

    # 2. A low-variance metric regression (cost x2) blocks.
    base = [rec(f"t{i}", 0, True, cost=0.01) for i in range(10)]
    cand = [rec(f"t{i}", 0, True, cost=0.02) for i in range(10)]
    assert evaluate(base, cand, config).blocked, "cost regression did not block"

    # 3. A small success drop within noise only warns: different seeds, so no flip to blame.
    base = [rec(f"t{i}", 0, i < 40, cost=0.01) for i in range(50)]
    cand = [rec(f"t{i}", 1, i < 39, cost=0.01) for i in range(50)]
    v = evaluate(base, cand, config)
    assert not v.blocked, v.render()
    assert v.warnings and "success" in v.warnings[0]

    # 4. A clean candidate passes with no blocks.
    same = [rec(f"t{i}", 0, i < 40) for i in range(50)]
    v = evaluate(same, [dict(r) for r in same], config)
    assert not v.blocked and not v.blocks


if __name__ == "__main__":
    try:
        check()
    except AssertionError as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
    print("ci_gate: OK (deterministic and metric regressions block; noise only warns)")
