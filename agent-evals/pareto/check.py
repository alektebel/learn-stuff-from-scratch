"""Runnable check for pareto (standard library only).

    python3 agent-evals/pareto/check.py

Asserts that the frontier drops only strictly dominated configurations and keeps a cheaper
configuration that is not actually worse. Exits non-zero on failure.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # agent-evals/

from pareto import frontier, pareto, points  # noqa: E402


def make(config, wins, n, cost, tenant="acme"):
    rows = [SimpleNamespace(model=config, success=i < wins, cost_eur=cost, tenant=tenant)
            for i in range(n)]
    return rows


def check() -> None:
    rows = (
        make("budget", 70, 100, 0.005)     # cheapest; beats small on cost, equal success
        + make("small", 70, 100, 0.010)
        + make("large", 85, 100, 0.100)    # dearer but better: a real trade-off
        + make("mid", 80, 100, 0.200)      # dearer AND worse than large: dominated
    )
    pts = {p.config: p for p in points(rows)}
    assert pts["large"].success > pts["small"].success
    assert pts["large"].cost_eur > pts["small"].cost_eur

    front = [p.config for p in frontier(list(pts.values()))]
    assert "mid" not in front, "a dominated config stayed on the frontier"
    assert "small" not in front, "a dearer-equal config stayed on the frontier"
    assert "budget" in front, "a cheaper-not-worse config was wrongly dropped"
    assert "large" in front, "the quality-buying config was wrongly dropped"
    assert front == sorted(front) or set(front) == {"budget", "large"}

    # per-tenant frontiers are computed, not eyeballed
    per = pareto(rows, by="model", group="tenant")
    assert set(per) == {"acme"} and per["acme"]


if __name__ == "__main__":
    try:
        check()
    except AssertionError as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
    print("pareto: OK (frontier drops only dominated points; a cheaper-not-worse config stays)")
