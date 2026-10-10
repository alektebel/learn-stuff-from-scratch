"""Tests for agent-evals #2: shadow routing comparator (BUILD: eval infrastructure).

Real checks for the promise that matters — the primary never sees the shadow — plus the
determinism of the sample and the shape of the report.

Map to README.md / tree.toml:
    primary byte-identical  -> test_primary_byte_identical
    deterministic sample    -> test_sampling_is_order_independent
    cost vs quality apart   -> test_report_separates_cost_and_quality
    slow shadow isolated    -> test_slow_shadow_isolated_to_its_column
    disagreements           -> test_fixed_and_broke
    edges                   -> test_is_sampled_bounds / test_empty_traffic / test_cli_smoke
"""

import sys
from types import SimpleNamespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import shadow_routing  # noqa: E402
from shadow_routing import ShadowConfig, compare, is_sampled, sampled_ids, shadow_run  # noqa: E402
from simulated_service import SimulatedService  # noqa: E402


class StubService:
    """A tiny deterministic service: primary always passes, shadow fails even ids."""

    def serve(self, request, model):
        if model == "primary":
            return SimpleNamespace(request_id=request.id, success=True, cost_eur=1.0, latency_ms=10.0)
        n = int(request.id[1:])
        return SimpleNamespace(request_id=request.id, success=(n % 2 == 1), cost_eur=5.0, latency_ms=99.0)

    def run(self, requests, model):
        return [self.serve(r, model) for r in requests]


def stub_requests(n=10):
    return [SimpleNamespace(id=f"r{i:05d}") for i in range(n)]


def test_primary_byte_identical():
    svc = SimulatedService(seed=4)
    reqs = svc.traffic(per_segment=60, segments=5)
    assert shadow_run(svc, reqs, ShadowConfig(fraction=0.0))[0] == \
        shadow_run(svc, reqs, ShadowConfig(fraction=0.4))[0]


def test_sampling_is_order_independent():
    svc = SimulatedService(seed=1)
    reqs = svc.traffic(per_segment=40, segments=4)
    a = sampled_ids(reqs, 0.3, seed=2)
    b = sampled_ids(list(reversed(reqs)), 0.3, seed=2)
    assert a == list(reversed(b))
    assert sampled_ids(reqs, 0.3, seed=2) == a  # deterministic


def test_is_sampled_bounds():
    assert is_sampled("x", 1.0, 0)
    assert not is_sampled("x", 0.0, 0)
    # a full fraction mirrors every request, an empty one mirrors none
    assert sampled_ids(stub_requests(7), 1.0, 0) == [f"r{i:05d}" for i in range(7)]
    assert sampled_ids(stub_requests(7), 0.0, 0) == []


def test_fixed_and_broke():
    cfg = ShadowConfig(primary="primary", shadow="shadow", fraction=1.0)
    cmp = compare(StubService(), stub_requests(10), cfg)
    assert cmp.n_total == 10 and cmp.n_sampled == 10
    assert cmp.primary["success"] == 1.0
    assert cmp.shadow["success"] == 0.5
    assert cmp.broke == 5 and cmp.fixed == 0
    assert len(cmp.disagreements) == 5


def test_report_separates_cost_and_quality():
    cfg = ShadowConfig(primary="primary", shadow="shadow", fraction=1.0)
    cmp = compare(StubService(), stub_requests(10), cfg)
    text = cmp.report()
    assert "success" in text and "cost EUR" in text and "latency ms" in text
    assert cmp.delta_cost_eur == 40.0  # 10 runs x (5.0 - 1.0), apart from the success drop
    assert cmp.delta_success == -0.5


def test_slow_shadow_isolated_to_its_column():
    svc = SimulatedService(seed=5)
    reqs = svc.traffic(per_segment=60, segments=4)
    slow = compare(svc, reqs, ShadowConfig(fraction=1.0, shadow="large"))
    fast = compare(svc, reqs, ShadowConfig(fraction=1.0, shadow="small"))
    assert slow.primary["latency_ms"] == fast.primary["latency_ms"]
    assert slow.shadow["latency_ms"] > fast.shadow["latency_ms"]


def test_empty_traffic():
    cmp = compare(SimulatedService(), [], ShadowConfig(fraction=0.5))
    assert cmp.n_total == 0 and cmp.n_sampled == 0
    assert "0/0 mirrored" in cmp.report()


def test_cli_smoke(capsys):
    assert shadow_routing.main(["--per-segment", "20", "--segments", "3", "--fraction", "0.2"]) == 0
    out = capsys.readouterr().out
    assert "shadow routing:" in out and "delta" in out
