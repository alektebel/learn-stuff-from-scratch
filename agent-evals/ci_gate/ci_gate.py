"""ci_gate — a regression gate for evaluation runs (project #4).

Project #4 (BUILD: eval infrastructure). Run evaluations on every change and **block the
ones that break something**, without blocking on noise. The correction to the original brief
(see [../README.md](../README.md)) is the whole design: a success-rate threshold as small as
2 % is below what 20-70 tasks can detect, so gating on it blocks pull requests at random.

So the gate blocks on what is *low-variance and real*:

- a **deterministic regression** — the same `(task, seed)` that passed now fails;
- a **cost** or **latency** median that regresses past its budget.

and only *warns* on the **success rate**, always with a confidence interval so the reader
sees whether the drop clears the noise. `python -m ci_gate` exits non-zero when blocked, so
CI can use it directly.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence


def _get(row, key, default=0.0):
    return row[key] if isinstance(row, dict) else getattr(row, key, default)


def median(xs: Sequence[float]) -> float:
    ys = sorted(xs)
    n = len(ys)
    if n == 0:
        return 0.0
    mid = n // 2
    return ys[mid] if n % 2 else (ys[mid - 1] + ys[mid]) / 2


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def newcombe(b_wins: int, b_n: int, c_wins: int, c_n: int) -> tuple[float, float]:
    """Newcombe interval for `candidate_rate - baseline_rate` (independent samples)."""
    if b_n == 0 or c_n == 0:
        return (0.0, 0.0)
    p1, p2 = b_wins / b_n, c_wins / c_n
    l1, u1 = wilson(b_wins, b_n)
    l2, u2 = wilson(c_wins, c_n)
    d = p2 - p1
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return (max(-1.0, lo), min(1.0, hi))


@dataclass(frozen=True)
class GateConfig:
    max_cost_regression: float = 0.10     # relative, median
    max_latency_regression: float = 0.10
    cost_key: str = "cost_eur"
    latency_key: str = "wall_time_s"


@dataclass(frozen=True)
class Verdict:
    blocked: bool
    blocks: tuple[str, ...]
    warnings: tuple[str, ...]
    metrics: dict = field(default_factory=dict)

    def render(self) -> str:
        head = "BLOCKED" if self.blocked else "passed"
        lines = [f"ci gate: {head}"]
        for b in self.blocks:
            lines.append(f"  block: {b}")
        for w in self.warnings:
            lines.append(f"  warn:  {w}")
        m = self.metrics
        lines.append(f"  success {m['baseline_success']:.3f} -> {m['candidate_success']:.3f} "
                     f"({m['success_diff']:+.3f}, 95% CI [{m['success_ci'][0]:+.3f}, "
                     f"{m['success_ci'][1]:+.3f}])")
        lines.append(f"  cost median x{m['cost_ratio']:.3f} · latency median "
                     f"x{m['latency_ratio']:.3f}")
        return "\n".join(lines)


def _keyed(rows: Sequence) -> dict:
    return {(_get(r, "task_id"), _get(r, "seed")): r for r in rows}


def evaluate(baseline: Sequence, candidate: Sequence,
             config: GateConfig | None = None) -> Verdict:
    config = config or GateConfig()
    base_by = _keyed(baseline)
    cand_by = _keyed(candidate)
    shared = sorted(set(base_by) & set(cand_by))

    blocks: list[str] = []
    warnings: list[str] = []

    regressions = [k for k in shared if bool(_get(base_by[k], "success"))
                   and not bool(_get(cand_by[k], "success"))]
    if regressions:
        shown = ", ".join(f"{t}#{s}" for t, s in regressions[:5])
        blocks.append(f"{len(regressions)} deterministic regression(s): {shown}")

    b_cost = median([float(_get(r, config.cost_key)) for r in baseline])
    c_cost = median([float(_get(r, config.cost_key)) for r in candidate])
    b_lat = median([float(_get(r, config.latency_key)) for r in baseline])
    c_lat = median([float(_get(r, config.latency_key)) for r in candidate])
    cost_ratio = (c_cost / b_cost) if b_cost else 1.0
    lat_ratio = (c_lat / b_lat) if b_lat else 1.0
    if cost_ratio - 1.0 > config.max_cost_regression:
        blocks.append(f"cost median +{100 * (cost_ratio - 1):.1f}% "
                      f"(>{100 * config.max_cost_regression:.0f}%)")
    if lat_ratio - 1.0 > config.max_latency_regression:
        blocks.append(f"latency median +{100 * (lat_ratio - 1):.1f}% "
                      f"(>{100 * config.max_latency_regression:.0f}%)")

    b_n, c_n = len(baseline), len(candidate)
    b_wins = sum(int(bool(_get(r, "success"))) for r in baseline)
    c_wins = sum(int(bool(_get(r, "success"))) for r in candidate)
    b_rate = b_wins / b_n if b_n else 0.0
    c_rate = c_wins / c_n if c_n else 0.0
    diff = c_rate - b_rate
    ci = newcombe(b_wins, b_n, c_wins, c_n)
    if c_rate < b_rate:
        clears = "clears the noise" if ci[1] < 0 else "within noise, not a block"
        warnings.append(f"success {b_rate:.3f} -> {c_rate:.3f} ({diff:+.3f}); {clears}")

    metrics = {
        "baseline_success": round(b_rate, 4), "candidate_success": round(c_rate, 4),
        "success_diff": round(diff, 4), "success_ci": (round(ci[0], 4), round(ci[1], 4)),
        "cost_ratio": round(cost_ratio, 4), "latency_ratio": round(lat_ratio, 4),
        "deterministic_regressions": len(regressions),
    }
    return Verdict(bool(blocks), tuple(blocks), tuple(warnings), metrics)


def read_jsonl(path: str | Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()]


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ci_gate",
                                 description="Gate a candidate eval run against a baseline.")
    ap.add_argument("--baseline", required=True, help="baseline run records (JSONL)")
    ap.add_argument("--candidate", required=True, help="candidate run records (JSONL)")
    ap.add_argument("--max-cost-regression", type=float, default=0.10)
    ap.add_argument("--max-latency-regression", type=float, default=0.10)
    args = ap.parse_args(argv)

    config = GateConfig(args.max_cost_regression, args.max_latency_regression)
    verdict = evaluate(read_jsonl(args.baseline), read_jsonl(args.candidate), config)
    print(verdict.render())
    return 1 if verdict.blocked else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
