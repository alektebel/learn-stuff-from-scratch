"""Tests for the shared simulated production service (BUILD: eval infrastructure).

The service is not a LEARN core; it is the deterministic double that #2, #9 and #10 run
against, so these are real checks, not xfails. They pin the properties the projects rely
on: reproducibility, per-request independence from mirroring, an injectable drift, a trace
store, and a cost/quality trade-off between the models.

Map to README.md:
    reproducible            -> test_reproducible_under_seed
    traffic shape           -> test_traffic_shape / test_per_segment_override / test_empty
    order independence      -> test_shadow_never_moves_primary
    drift is real + scoped  -> test_drift_lowers_success / test_drift_misses_other_tenant
    trace store             -> test_trace_roundtrip / test_drift_not_in_trace
    aggregations            -> test_success_rate_groups / test_totals
    cost vs quality         -> test_large_better_and_dearer
    CLI                     -> test_cli_writes_trace
"""

import json
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import simulated_service  # noqa: E402
from simulated_service import (  # noqa: E402
    Drift,
    SimulatedService,
    read_jsonl,
    success_rate,
    totals,
    write_jsonl,
)


def test_reproducible_under_seed():
    a, b = SimulatedService(seed=7), SimulatedService(seed=7)
    reqs = a.traffic(per_segment=25, segments=4)
    assert a.run(reqs) == b.run(b.traffic(per_segment=25, segments=4))


def test_traffic_shape():
    reqs = SimulatedService(seed=1).traffic(n=40, segments=4)
    assert len(reqs) == 40
    assert sorted({r.segment for r in reqs}) == [0, 1, 2, 3]
    assert all(0.0 <= r.difficulty <= 1.0 for r in reqs)
    assert all(r.prompt_tokens > 0 for r in reqs)
    assert len({r.tenant for r in reqs}) == len(simulated_service.TENANTS)


def test_per_segment_override():
    assert len(SimulatedService(seed=1).traffic(per_segment=10, segments=5)) == 50


def test_empty_traffic():
    assert SimulatedService(seed=1).traffic(n=0) == []


def test_serve_accounts_cost_and_tokens():
    svc = SimulatedService(seed=2)
    r = svc.serve(svc.traffic(n=1)[0], "large")
    assert r.cost_eur > 0
    assert r.output_tokens >= 1
    assert 0.0 <= r.quality <= 1.0


def test_shadow_never_moves_primary():
    svc = SimulatedService(seed=3)
    req = svc.traffic(n=1)[0]
    primary = svc.serve(req, "small")
    svc.serve(req, "large")  # the shadow, before or after, must not matter
    assert svc.serve(req, "small") == primary
    assert svc.serve(req, "small") == primary


def test_drift_lowers_success():
    svc = SimulatedService(seed=3, drift=[Drift(after_segment=3, penalty=3.0, tenant="acme")])
    rows = svc.run(svc.traffic(per_segment=120, segments=6))
    before = totals([r for r in rows if r.tenant == "acme" and r.segment < 3])["success"]
    after = totals([r for r in rows if r.tenant == "acme" and r.segment >= 3])["success"]
    assert after < before


def test_drift_misses_other_tenant():
    svc = SimulatedService(seed=3, drift=[Drift(after_segment=3, penalty=3.0, tenant="acme")])
    rows = svc.run(svc.traffic(per_segment=120, segments=6))
    acme_after = totals([r for r in rows if r.tenant == "acme" and r.segment >= 3])["success"]
    other_after = totals([r for r in rows if r.tenant != "acme" and r.segment >= 3])["success"]
    assert other_after > acme_after


def test_drift_not_in_trace():
    # a monitor must find the drop from success alone; the planted rule is not a field
    svc = SimulatedService(seed=0, drift=[Drift(after_segment=1, penalty=1.0)])
    row = asdict(svc.run(svc.traffic(n=1))[0])
    assert "drift" not in row and "penalty" not in row


def test_drift_schedule_is_returned():
    d = Drift(after_segment=2, penalty=1.5)
    assert SimulatedService(drift=[d]).drift_schedule() == [d]


def test_trace_roundtrip(tmp_path):
    svc = SimulatedService(seed=5)
    rows = svc.run(svc.traffic(per_segment=15, segments=2))
    path = write_jsonl(rows, tmp_path / "nested" / "run.jsonl")
    assert path.exists()
    back = read_jsonl(path)
    assert back == [asdict(r) for r in rows]
    assert json.loads(path.read_text().splitlines()[0])["request_id"] == rows[0].request_id


def test_success_rate_groups():
    rows = [
        {"success": True, "segment": 0},
        {"success": False, "segment": 0},
        {"success": True, "segment": 1},
    ]
    assert success_rate(rows, "segment") == {0: 0.5, 1: 1.0}


def test_totals():
    rows = [{"success": True, "cost_eur": 0.25, "latency_ms": 100.0}]
    t = totals(rows)
    assert t["runs"] == 1 and t["success"] == 1.0
    assert t["cost_eur"] == pytest.approx(0.25)


def test_large_better_and_dearer():
    svc = SimulatedService(seed=11)
    traffic = svc.traffic(per_segment=80, segments=3)
    small, large = svc.run(traffic, "small"), svc.run(traffic, "large")
    assert totals(large)["success"] >= totals(small)["success"]
    assert totals(large)["cost_eur"] > totals(small)["cost_eur"]


def test_cli_writes_trace(tmp_path):
    out = tmp_path / "cli.jsonl"
    rc = simulated_service.main(["--out", str(out), "--seed", "1",
                                 "--per-segment", "10", "--segments", "3",
                                 "--drift", "2:2.0:acme"])
    assert rc == 0
    rows = read_jsonl(out)
    assert len(rows) == 30


def test_drift_parser():
    from simulated_service.simulated_service import _parse_drift
    assert _parse_drift("7:1.4") == Drift(7, 1.4, None, None)
    assert _parse_drift("7:1.4:acme") == Drift(7, 1.4, "acme", None)
    assert _parse_drift("7:1.4:acme:lookup") == Drift(7, 1.4, "acme", "lookup")
