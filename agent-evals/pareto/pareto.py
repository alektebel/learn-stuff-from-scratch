"""pareto — the cost-quality frontier per tenant (project #10).

Project #10 (BUILD: eval infrastructure). Given run records for several model
configurations, this computes the **Pareto frontier**: the configurations that are not
beaten on both cost *and* quality by another. An expensive config is worth keeping only
while it buys quality; the moment a cheaper one matches it, it belongs off the chart.

The numbers come from run records, never from eyeballing. Reads the trace store of the
[simulated service](../simulated_service/); each point is a `(mean cost per request,
success rate)` with a Wilson interval on the success, because at these sample sizes a
half-point of success is noise and a frontier should say so.

Standard library only.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

from simulated_service import SimulatedService


def _get(row, key):
    return row[key] if isinstance(row, dict) else getattr(row, key)


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial rate (kept inside [0, 1])."""
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


@dataclass(frozen=True)
class Point:
    config: str
    cost_eur: float          # mean cost per request
    success: float
    n: int
    ci: tuple[float, float]  # 95% interval on success

    def __str__(self) -> str:
        return (f"{self.config:<8} cost {self.cost_eur:.5f}/req  success {self.success:.3f} "
                f"[{self.ci[0]:.3f}, {self.ci[1]:.3f}]  n={self.n}")


def points(rows: Sequence, by: str = "model") -> list[Point]:
    groups: dict[str, list] = defaultdict(list)
    for r in rows:
        groups[_get(r, by)].append(r)
    out = []
    for config, rs in sorted(groups.items()):
        n = len(rs)
        wins = sum(int(bool(_get(r, "success"))) for r in rs)
        p = wins / n if n else 0.0
        cost = sum(float(_get(r, "cost_eur")) for r in rs) / n if n else 0.0
        out.append(Point(str(config), round(cost, 8), round(p, 4), n, wilson(wins, n)))
    return out


def dominates(a: Point, b: Point) -> bool:
    """`a` beats `b`: no dearer and no worse, and strictly better on at least one."""
    no_dearer = a.cost_eur <= b.cost_eur
    no_worse = a.success >= b.success
    strictly = a.cost_eur < b.cost_eur or a.success > b.success
    return no_dearer and no_worse and strictly


def frontier(pts: Sequence[Point]) -> list[Point]:
    """The non-dominated points, cheapest first; ties on cost go to the better success."""
    kept = [p for p in pts if not any(dominates(q, p) for q in pts if q is not p)]
    return sorted(kept, key=lambda p: (p.cost_eur, -p.success))


def pareto(rows: Sequence, by: str = "model", group: str | None = None):
    """Overall frontier, or one per `group` value (e.g. per tenant)."""
    if group is None:
        return frontier(points(rows, by))
    buckets: dict[str, list] = defaultdict(list)
    for r in rows:
        buckets[_get(r, group)].append(r)
    return {g: frontier(points(rs, by)) for g, rs in sorted(buckets.items())}


def render(result) -> str:
    def line(title, pts):
        body = "\n".join("  " + str(p) for p in pts) or "  (empty)"
        return f"{title}\n{body}"

    if isinstance(result, dict):
        return "\n".join(line(f"frontier for {g}:", pts) for g, pts in result.items())
    return line("cost-quality frontier (cheapest first):", result)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pareto",
                                 description="Cost-quality frontier over synthetic run records.")
    ap.add_argument("--per-segment", type=int, default=100)
    ap.add_argument("--segments", type=int, default=4)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--configs", default="small,large")
    ap.add_argument("--group", default="tenant", choices=["tenant", "category", "none"])
    args = ap.parse_args(argv)

    service = SimulatedService(seed=args.seed)
    traffic = service.traffic(per_segment=args.per_segment, segments=args.segments)
    rows = [r for model in args.configs.split(",") for r in service.run(traffic, model)]
    group = None if args.group == "none" else args.group
    print(render(pareto(rows, "model", group)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
