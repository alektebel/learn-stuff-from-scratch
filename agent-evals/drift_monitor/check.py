"""Runnable check for drift_monitor (standard library only).

    python3 agent-evals/drift_monitor/check.py

Asserts what #9 promises: a planted drop raises an alert at the segment it starts, and a
seasonal traffic shift (harder requests, no regression) does not. Exits non-zero on failure.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # agent-evals/

from drift_monitor import MonitorConfig, all_alerts, monitor, monitor_by  # noqa: E402
from simulated_service import Drift, SimulatedService  # noqa: E402

CONFIG = MonitorConfig(baseline=(0, 2), min_drop=0.05, min_n=40, z=3.0)


def check() -> None:
    service = SimulatedService(seed=0, drift=[Drift(after_segment=4, penalty=3.0, tenant="acme")])
    rows = service.run(service.traffic(per_segment=150, segments=7))

    # 1. The planted drop raises an alert at the segment it starts, and not before.
    segs = {a.segment for a in monitor(rows, CONFIG)}
    assert 4 in segs, f"drift at segment 4 not detected: {sorted(segs)}"
    assert 3 not in segs, "alerted on a clean segment"

    # 2. It localises to the affected tenant, not the others.
    by = monitor_by(rows, CONFIG, key="tenant")
    assert by["acme"] and not by["globex"] and not by["initech"], {k: len(v) for k, v in by.items()}

    # 3. A seasonal shift — harder requests, no drift — does not raise a false alert.
    clean = SimulatedService(seed=0)
    base = clean.traffic(per_segment=150, segments=7)
    seasonal = [replace(r, difficulty=min(1.0, r.difficulty + 0.35)) if r.segment >= 4 else r
                for r in base]
    assert not monitor(clean.run(seasonal), CONFIG), "false alarm on a seasonal shift"

    # 4. A trace with no change at all is quiet.
    assert not all_alerts(clean.run(base), CONFIG)


if __name__ == "__main__":
    try:
        check()
    except AssertionError as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
    print("drift_monitor: OK (planted drop caught and localised; seasonal shift not a false alarm)")
