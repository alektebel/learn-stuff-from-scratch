"""Runnable check for simulated_service (standard library only).

    python3 agent-evals/simulated_service/check.py

Asserts the properties the three projects depend on: reproducibility, per-request
independence from mirroring, a planted drift that actually lowers success, and a trace
round-trip. Exits non-zero with a message on the first failure.
"""

from __future__ import annotations

import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # agent-evals/, so `import simulated_service` works

from simulated_service import (  # noqa: E402
    Drift,
    SimulatedService,
    read_jsonl,
    totals,
    write_jsonl,
)


def rate(rows) -> float:
    return totals(rows)["success"]


def check() -> None:
    # 1. A run is reproducible for a fixed seed.
    a = SimulatedService(seed=7)
    b = SimulatedService(seed=7)
    reqs = a.traffic(per_segment=50, segments=6)
    assert a.run(reqs) == b.run(b.traffic(per_segment=50, segments=6)), "not reproducible"

    # 2. Traffic is spread evenly over the segments.
    segs = sorted({r.segment for r in reqs})
    assert segs == list(range(6)), f"segments {segs}"

    # 3. Mirroring cannot move the primary: serve alone == serve after a shadow.
    svc = SimulatedService(seed=3)
    req = reqs[0]
    primary = svc.serve(req, "small")
    svc.serve(req, "large")  # the shadow
    assert svc.serve(req, "small") == primary, "shadow changed the primary"
    assert svc.serve(req, "small") == primary, "not idempotent"

    # 4. A planted drift lowers observed success for the affected tenant only.
    drift = SimulatedService(seed=3, drift=[Drift(after_segment=3, penalty=3.0, tenant="acme")])
    rows = drift.run(drift.traffic(per_segment=120, segments=6))
    before = rate([r for r in rows if r.tenant == "acme" and r.segment < 3])
    after = rate([r for r in rows if r.tenant == "acme" and r.segment >= 3])
    control = rate([r for r in rows if r.tenant != "acme"])
    assert after < before, f"drift did not lower success: {before:.3f} -> {after:.3f}"
    assert control > after, f"control tenant also dropped: {control:.3f} vs {after:.3f}"

    # 5. A trace survives a round-trip, and cost/quality are sane.
    with tempfile.TemporaryDirectory() as tmp:
        path = write_jsonl(rows, Path(tmp) / "traces" / "run.jsonl")
        back = read_jsonl(path)
    assert back == [asdict(r) for r in rows], "trace round-trip changed the records"
    assert totals(rows)["cost_eur"] > 0, "cost is not accounted"

    # 6. The expensive model is at least as good and strictly dearer on the same traffic.
    svc2 = SimulatedService(seed=11)
    traffic = svc2.traffic(per_segment=80, segments=3)
    small, large = svc2.run(traffic, "small"), svc2.run(traffic, "large")
    assert rate(large) >= rate(small), f"large not better: {rate(large):.3f} < {rate(small):.3f}"
    assert totals(large)["cost_eur"] > totals(small)["cost_eur"], "large is not dearer"


if __name__ == "__main__":
    try:
        check()
    except AssertionError as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
    print("simulated_service: OK (reproducible, order-independent, drift injectable, trace round-trips)")
