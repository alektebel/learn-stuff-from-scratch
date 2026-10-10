"""Tests for agent-evals #9: drift monitor (BUILD: eval infrastructure).

Map to README.md / tree.toml:
    planted drop caught       -> test_detects_planted_drop / test_localises_to_tenant
    seasonal no false alarm   -> test_seasonal_shift_is_not_an_alert
    quiet trace is quiet      -> test_clean_trace_has_no_alerts
    noise control             -> test_small_segment_is_not_judged / test_threshold_blocks_noise
    report + CLI              -> test_render / test_cli_smoke
"""

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import drift_monitor  # noqa: E402
from drift_monitor import Alert, MonitorConfig, all_alerts, monitor, monitor_by, render  # noqa: E402
from simulated_service import Drift, SimulatedService  # noqa: E402

CFG = MonitorConfig(baseline=(0, 2), min_drop=0.05, min_n=40, z=3.0)


def drifted():
    svc = SimulatedService(seed=0, drift=[Drift(after_segment=4, penalty=3.0, tenant="acme")])
    return svc.run(svc.traffic(per_segment=150, segments=7))


def test_detects_planted_drop():
    segs = [a.segment for a in monitor(drifted(), CFG)]
    assert segs and min(segs) == 4
    assert 3 not in segs


def test_localises_to_tenant():
    by = monitor_by(drifted(), CFG, key="tenant")
    assert by["acme"] and not by["globex"] and not by["initech"]


def test_all_alerts_prepends_overall():
    alerts = all_alerts(drifted(), CFG)
    assert alerts[0].group is None
    assert any(a.group == "acme" for a in alerts)


def test_seasonal_shift_is_not_an_alert():
    svc = SimulatedService(seed=0)
    traffic = [replace(r, difficulty=min(1.0, r.difficulty + 0.35)) if r.segment >= 4 else r
               for r in svc.traffic(per_segment=150, segments=7)]
    assert monitor(svc.run(traffic), CFG) == []


def test_clean_trace_has_no_alerts():
    svc = SimulatedService(seed=3)
    assert monitor(svc.run(svc.traffic(per_segment=150, segments=6)), CFG) == []


def test_small_segment_is_not_judged():
    svc = SimulatedService(seed=0, drift=[Drift(after_segment=4, penalty=3.0, tenant="acme")])
    rows = svc.run(svc.traffic(per_segment=10, segments=7))  # 10 < min_n
    assert monitor(rows, CFG) == []


def test_threshold_blocks_noise():
    # a trace whose realised rate is above predicted cannot alert: the drop is negative
    svc = SimulatedService(seed=1)
    assert monitor(svc.run(svc.traffic(per_segment=80, segments=4)), CFG) == []


def test_render():
    assert render([]) == "no drift detected"
    text = render([Alert(4, "acme", 0.5, 0.8, 0.3, 100, 6.0)])
    assert "segment 4" in text and "acme" in text and "drop +0.300" in text


def test_cli_smoke(capsys):
    assert drift_monitor.main(["--per-segment", "100", "--segments", "7",
                               "--drift", "4:3.0:acme"]) == 0
    out = capsys.readouterr().out
    assert "segment 4" in out
