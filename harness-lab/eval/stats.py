"""Statistics for comparing agents: confidence intervals, paired tests, power.

Why paired: two variants run on the same tasks. Most of the variance in success is
between tasks (some are easy for everyone, some impossible for everyone), and pairing
cancels it. Only *discordant* tasks (one variant passes, the other fails) carry
information about the difference. McNemar's test is built on exactly those.

    python -m eval.stats power        # minimum detectable effect for this suite
"""

from __future__ import annotations

import argparse
import math
from statistics import NormalDist

_Z = NormalDist()


def wilson_interval(successes: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Wilson score interval. Unlike the normal approximation, it stays inside [0, 1]
    and behaves at 0/n and n/n, which the null and oracle controls hit by design."""
    if n == 0:
        return (0.0, 1.0)
    z = _Z.inv_cdf(1 - (1 - confidence) / 2)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    # round away float noise so 0/n reports a lower bound of exactly 0
    return (round(max(0.0, centre - half), 12), round(min(1.0, centre + half), 12))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value. b = pairs only A passed, c = only B passed.
    Under H0 each discordant pair is a fair coin, so this is a binomial test."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def paired_n_required(delta: float, discordance: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Tasks needed to detect a paired difference `delta` in success rate.

    `discordance` = P(the two variants disagree on a task), which must be >= |delta|.
    Normal approximation for McNemar's test (Connor 1987, Biometrics 43:207-211):
        n = (z_{a/2} sqrt(psi) + z_b sqrt(psi - delta^2))^2 / delta^2
    """
    if not 0 < abs(delta) <= discordance <= 1:
        raise ValueError("need 0 < |delta| <= discordance <= 1")
    za = _Z.inv_cdf(1 - alpha / 2)
    zb = _Z.inv_cdf(power)
    n = (za * math.sqrt(discordance) + zb * math.sqrt(discordance - delta ** 2)) ** 2 / delta ** 2
    return math.ceil(n)


def paired_mde(n: int, discordance: float, alpha: float = 0.05, power: float = 0.8) -> float:
    """Smallest |delta| detectable with `n` paired tasks (inverse of the above, by bisection)."""
    lo, hi = 1e-6, discordance
    if paired_n_required(hi, discordance, alpha, power) > n:
        return math.inf  # not even the maximum possible effect is detectable
    for _ in range(100):
        mid = (lo + hi) / 2
        if paired_n_required(mid, discordance, alpha, power) <= n:
            hi = mid
        else:
            lo = mid
    return hi


def power_table(ns=(20, 50, 70, 150), discordances=(0.1, 0.2, 0.3, 0.4)) -> str:
    head = "n tasks | " + " | ".join(f"psi={d:.1f}" for d in discordances)
    lines = [head, "-" * len(head)]
    for n in ns:
        cells = []
        for d in discordances:
            m = paired_mde(n, d)
            cells.append("  none  " if math.isinf(m) else f"{100 * m:5.1f} pp")
        lines.append(f"{n:7d} | " + " | ".join(cells))
    lines.append("")
    lines.append("Cells: minimum detectable paired difference in success rate (alpha=0.05, power=0.8).")
    lines.append("psi: share of tasks on which the two variants disagree. 'none': undetectable at any effect.")
    lines.append("Seeds of the same task are not independent tasks: n counts tasks, not runs.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["power"])
    ap.parse_args(argv)
    print(power_table())


if __name__ == "__main__":
    main()
