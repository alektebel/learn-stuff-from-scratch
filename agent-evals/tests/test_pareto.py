"""Tests for agent-evals #10: cost-quality Pareto (BUILD: eval infrastructure).

Map to README.md / tree.toml:
    frontier from records     -> test_points_from_records / test_frontier_drops_dominated
    cheaper-not-worse stays   -> test_cheaper_equal_is_kept
    a real trade-off stays    -> test_trade_off_is_kept
    per-tenant                -> test_pareto_by_group
    intervals                 -> test_wilson_bounds
    report + CLI              -> test_render / test_cli_smoke
"""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pareto  # noqa: E402
from pareto import Point, dominates, frontier, pareto as frontier_by, points, render, wilson  # noqa: E402
from simulated_service import SimulatedService  # noqa: E402


def make(config, wins, n, cost, tenant="acme"):
    return [SimpleNamespace(model=config, success=i < wins, cost_eur=cost, tenant=tenant)
            for i in range(n)]


def sample_rows():
    return (make("budget", 70, 100, 0.005) + make("small", 70, 100, 0.010)
            + make("large", 85, 100, 0.100) + make("mid", 80, 100, 0.200))


def test_points_from_records():
    pts = {p.config: p for p in points(sample_rows())}
    assert pts["small"].success == 0.7 and pts["small"].cost_eur == 0.01
    assert pts["small"].n == 100
    assert pts["large"].ci[0] < pts["large"].success < pts["large"].ci[1]


def test_frontier_drops_dominated():
    front = {p.config for p in frontier(points(sample_rows()))}
    assert front == {"budget", "large"}


def test_cheaper_equal_is_kept():
    # budget is cheaper than small at equal success: budget dominates, small is dropped
    pts = points(sample_rows())
    budget = next(p for p in pts if p.config == "budget")
    small = next(p for p in pts if p.config == "small")
    assert dominates(budget, small)
    assert not dominates(small, budget)


def test_trade_off_is_kept():
    pts = points(sample_rows())
    large = next(p for p in pts if p.config == "large")
    small = next(p for p in pts if p.config == "small")
    assert not dominates(large, small)  # large is better but dearer
    assert not dominates(small, large)


def test_identical_points_neither_dominates():
    a = Point("a", 0.1, 0.8, 100, (0.7, 0.9))
    b = Point("b", 0.1, 0.8, 100, (0.7, 0.9))
    assert not dominates(a, b) and not dominates(b, a)


def test_pareto_by_group():
    rows = sample_rows() + make("large", 90, 100, 0.100, tenant="globex") \
        + make("small", 60, 100, 0.010, tenant="globex")
    per = frontier_by(rows, by="model", group="tenant")
    assert set(per) == {"acme", "globex"}
    assert {p.config for p in per["acme"]} == {"budget", "large"}


def test_wilson_bounds():
    lo, hi = wilson(80, 100)
    assert lo < 0.8 < hi
    assert wilson(0, 10)[0] == 0.0 and wilson(10, 10)[1] == 1.0
    assert wilson(0, 0) == (0.0, 0.0)


def test_render():
    text = render(frontier(points(sample_rows())))
    assert "frontier" in text and "budget" in text and "large" in text
    assert "frontier for globex" in render({"globex": []})


def test_cli_smoke(capsys):
    assert pareto.main(["--per-segment", "50", "--segments", "3"]) == 0
    assert "frontier" in capsys.readouterr().out
