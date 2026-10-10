"""drift_monitor — find a quality regression in a traffic trace (project #9).

Project #9 (BUILD: eval infrastructure). A deployed model does not fail loudly; it decays
while the success rate stays "fine" on average. This reads a trace and, for each time
segment, compares the **realised** success rate to the **predicted** one, alerting only
when the shortfall is both large and unlikely to be sampling noise.

The separation that makes it honest is the comparison itself. Every trace row carries a
`quality` — the pass rate the model predicts for that request, computed before any drift
(see [simulated_service](../simulated_service/)). Realised `success` is drawn from the
*drift-adjusted* rate. So:

- a **traffic shift** (a harder mix: more hard categories, higher difficulty) lowers
  `quality` too, and the gap `quality − success` stays near zero — no alert;
- a **regression** leaves `quality` where it was and pulls `success` down — a gap, and an
  alert.

A monitor that chased the raw success rate would fire on every seasonal change. That is the
limit case #9 exists to teach.

Standard library only.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

from simulated_service import Drift, SimulatedService


def _get(row, key):
    return row[key] if isinstance(row, dict) else getattr(row, key)


@dataclass(frozen=True)
class MonitorConfig:
    """`baseline` is the inclusive segment range treated as known-good.

    `min_drop` is the smallest `quality − success` gap worth reporting; `min_n` the
    smallest segment to judge; `z` the standard deviations before it counts as real.
    """

    baseline: tuple[int, int] = (0, 2)
    min_drop: float = 0.05
    min_n: int = 40
    z: float = 3.0


@dataclass(frozen=True)
class Alert:
    segment: int
    group: str | None          # the tenant/category, or None for the whole segment
    observed: float            # realised success
    expected: float            # mean predicted quality
    drop: float                # expected - observed
    n: int
    z: float

    def __str__(self) -> str:
        who = f" [{self.group}]" if self.group is not None else ""
        return (f"segment {self.segment}{who}: success {self.observed:.3f} vs predicted "
                f"{self.expected:.3f} — drop {self.drop:+.3f} (n={self.n}, z={self.z:.1f})")


def _judge(rows: Sequence, config: MonitorConfig, segment: int, group: str | None) -> Alert | None:
    n = len(rows)
    if n < config.min_n:
        return None
    observed = sum(int(bool(_get(r, "success"))) for r in rows) / n
    qualities = [float(_get(r, "quality")) for r in rows]
    expected = sum(qualities) / n
    # variance of the realised rate under the per-request predicted probabilities
    var = sum(q * (1.0 - q) for q in qualities) / (n * n)
    drop = expected - observed
    z = drop / math.sqrt(var) if var > 0 else 0.0
    if drop >= config.min_drop and z >= config.z:
        return Alert(segment, group, round(observed, 4), round(expected, 4), round(drop, 4),
                     n, round(z, 2))
    return None


def _segments_after(rows: Sequence, baseline: tuple[int, int]) -> list[int]:
    lo, hi = baseline
    return sorted({_get(r, "segment") for r in rows if _get(r, "segment") > hi})


def monitor(rows: Sequence, config: MonitorConfig | None = None) -> list[Alert]:
    """Alerts over the whole trace, one per segment after the baseline."""
    config = config or MonitorConfig()
    alerts = []
    for seg in _segments_after(rows, config.baseline):
        alert = _judge([r for r in rows if _get(r, "segment") == seg], config, seg, None)
        if alert:
            alerts.append(alert)
    return alerts


def monitor_by(rows: Sequence, config: MonitorConfig | None = None,
               key: str = "tenant") -> dict[str, list[Alert]]:
    """The same alert, computed inside each `key` group (e.g. per tenant)."""
    config = config or MonitorConfig()
    from dataclasses import replace

    groups: dict[str, list] = defaultdict(list)
    for r in rows:
        groups[_get(r, key)].append(r)
    return {g: [replace(a, group=g) for a in monitor(rs, config)]
            for g, rs in sorted(groups.items())}


def all_alerts(rows: Sequence, config: MonitorConfig | None = None,
               key: str = "tenant") -> list[Alert]:
    """Overall alerts plus per-group ones, overall first."""
    return monitor(rows, config) + [a for alerts in monitor_by(rows, config, key).values()
                                    for a in alerts]


def render(alerts: Sequence[Alert]) -> str:
    if not alerts:
        return "no drift detected"
    return "\n".join(str(a) for a in alerts)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="drift_monitor",
                                 description="Detect a quality regression in a synthetic trace.")
    ap.add_argument("--per-segment", type=int, default=120)
    ap.add_argument("--segments", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--model", default="small")
    ap.add_argument("--baseline", default="0:2", metavar="LO:HI")
    ap.add_argument("--drift", action="append", default=[], metavar="AFTER:PENALTY[:TENANT[:CATEGORY]]")
    args = ap.parse_args(argv)

    from simulated_service.simulated_service import _parse_drift
    drift = [_parse_drift(d) for d in args.drift]
    lo, hi = (int(x) for x in args.baseline.split(":"))
    config = MonitorConfig(baseline=(lo, hi))
    service = SimulatedService(seed=args.seed, drift=drift)
    rows = service.run(service.traffic(per_segment=args.per_segment, segments=args.segments),
                       args.model)
    alerts = all_alerts(rows, config)
    print(render(alerts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
