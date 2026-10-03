"""
Step 4 — Deploying safely: health checks, canaries and rollback. Complete Solution.

Deployment is not "the new version is running". It is "the new version is
running AND you found out fast if it is worse AND you could get back".
"""

import math
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from metrics import SLO, burn_rate, percentile


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------

class HealthCheck:
    """Liveness and readiness are different questions. Conflating them is the
    single most common way a deploy turns a degradation into an outage.

      LIVENESS  — "is this process wedged?" Failing it RESTARTS the container.
      READINESS — "should this replica get traffic right now?" Failing it
                  removes the replica from the load balancer, no restart.

    A model server loading 16GB of weights is ALIVE but NOT READY for two
    minutes. If that period fails your liveness probe, Kubernetes kills it
    mid-load, forever, and you have built a crash loop that looks like a bad
    build. Give liveness a generous timeout and a startup probe; put the real
    checks in readiness.

    A replica whose KV cache is full should fail READINESS (shed traffic, let
    it drain) and pass LIVENESS (it is working fine, just busy).
    """

    def __init__(self, name: str, kind: str, timeout_s: float,
                 failure_threshold: int = 3):
        if kind not in ("liveness", "readiness", "startup"):
            raise ValueError(f"unknown probe kind {kind!r}")
        self.name = name
        self.kind = kind
        self.timeout_s = timeout_s
        self.failure_threshold = failure_threshold
        self.consecutive_failures = 0

    def record(self, healthy: bool) -> str:
        """Returns the action: 'none', 'remove_from_lb' or 'restart'."""
        if healthy:
            self.consecutive_failures = 0
            return "none"
        self.consecutive_failures += 1
        if self.consecutive_failures < self.failure_threshold:
            return "none"
        return "restart" if self.kind == "liveness" else "remove_from_lb"


def probe_plan(model_load_seconds: float) -> Dict[str, Dict[str, float]]:
    """Probe timings that will not kill a slow-loading model server.

    The startup probe is what buys the load time. Once it passes, liveness
    takes over with a tight timeout — which is what you actually want, because
    from then on a hang IS a bug.
    """
    return {
        "startup": {"period_s": 10, "failure_threshold":
                    math.ceil(model_load_seconds / 10) + 6, "timeout_s": 5},
        "readiness": {"period_s": 5, "failure_threshold": 2, "timeout_s": 3},
        "liveness": {"period_s": 20, "failure_threshold": 3, "timeout_s": 10},
    }


# ---------------------------------------------------------------------------
# Canary analysis
# ---------------------------------------------------------------------------

def compare_versions(baseline_latencies: Sequence[float],
                     canary_latencies: Sequence[float],
                     baseline_errors: int = 0,
                     canary_errors: int = 0) -> Dict[str, float]:
    """Compare a canary against the running version on the metrics that matter."""
    base_p99 = percentile(baseline_latencies, 0.99)
    canary_p99 = percentile(canary_latencies, 0.99)
    base_rate = baseline_errors / max(len(baseline_latencies) + baseline_errors, 1)
    canary_rate = canary_errors / max(len(canary_latencies) + canary_errors, 1)
    return {
        "baseline_p99": base_p99,
        "canary_p99": canary_p99,
        "p99_ratio": canary_p99 / base_p99 if base_p99 else 0.0,
        "baseline_error_rate": base_rate,
        "canary_error_rate": canary_rate,
        "error_rate_delta": canary_rate - base_rate,
        "canary_samples": len(canary_latencies) + canary_errors,
    }


def enough_samples(canary_samples: int, baseline_rate: float,
                   detectable_increase: float = 2.0) -> bool:
    """Is the canary carrying enough traffic to conclude anything?

    Rough rule of thumb: to see a `detectable_increase`x change in a rate, you
    need on the order of 10 / baseline_rate samples. At a 0.1% baseline error
    rate that is ~10,000 requests — so a canary running for 90 seconds at 1%
    of traffic has seen nothing and its clean metrics prove nothing.

    Shipping on an underpowered canary is worse than not canarying: it
    manufactures confidence.
    """
    if baseline_rate <= 0:
        baseline_rate = 0.001
    return canary_samples >= 10 / baseline_rate / detectable_increase


def canary_verdict(comparison: Dict[str, float],
                   p99_tolerance: float = 1.20,
                   error_tolerance: float = 0.005) -> Tuple[str, str]:
    """Returns (verdict, reason): 'promote', 'rollback' or 'hold'.

    'hold' is a real answer and the most commonly missing one. If the canary
    has not seen enough traffic, neither promoting nor rolling back is
    justified — wait.
    """
    if not enough_samples(comparison["canary_samples"],
                          comparison["baseline_error_rate"]):
        return "hold", (f"only {comparison['canary_samples']:.0f} canary "
                        "requests — not enough to detect a regression")

    if comparison["error_rate_delta"] > error_tolerance:
        return "rollback", (f"error rate up "
                            f"{comparison['error_rate_delta']:.2%} "
                            f"(tolerance {error_tolerance:.2%})")

    if comparison["p99_ratio"] > p99_tolerance:
        return "rollback", (f"p99 is {comparison['p99_ratio']:.2f}x baseline "
                            f"(tolerance {p99_tolerance:.2f}x)")

    return "promote", (f"p99 {comparison['p99_ratio']:.2f}x baseline, "
                       f"error delta {comparison['error_rate_delta']:+.3%}")


# ---------------------------------------------------------------------------
# Progressive rollout
# ---------------------------------------------------------------------------

class Rollout:
    """A staged rollout that can stop itself.

    Stages exist so the blast radius grows only after evidence. 1% -> 5% ->
    25% -> 100% is common; each stage must both PASS and have seen enough
    traffic before the next begins.
    """

    def __init__(self, stages: Optional[List[float]] = None,
                 p99_tolerance: float = 1.20,
                 error_tolerance: float = 0.005):
        self.stages = stages or [0.01, 0.05, 0.25, 1.00]
        self.p99_tolerance = p99_tolerance
        self.error_tolerance = error_tolerance
        self.history: List[Dict[str, object]] = []

    def run(self, observe: Callable[[float], Dict[str, float]]) -> Dict[str, object]:
        """Advance through the stages, calling observe(fraction) at each.

        `observe` stands in for "wait, then scrape the canary's metrics".
        """
        for fraction in self.stages:
            comparison = observe(fraction)
            verdict, reason = canary_verdict(comparison, self.p99_tolerance,
                                             self.error_tolerance)
            self.history.append({"fraction": fraction, "verdict": verdict,
                                 "reason": reason, "comparison": comparison})
            if verdict == "rollback":
                return {"outcome": "rolled_back", "failed_at": fraction,
                        "reason": reason, "history": self.history}
            if verdict == "hold":
                return {"outcome": "held", "at": fraction, "reason": reason,
                        "history": self.history}
        return {"outcome": "promoted", "history": self.history}


def rollback_triggers(slo: SLO, budget_used: float,
                      window_hours: float) -> Tuple[bool, str]:
    """Should an automated system roll back right now?

    Tie the trigger to the error BUDGET, not the raw error rate. A 2% error
    rate for 30 seconds is noise; 0.5% sustained for six hours eats a month's
    budget. Burn rate is the metric that tells these apart.
    """
    rate = burn_rate(budget_used, window_hours, slo.window_days)
    if rate > 14.4:
        return True, (f"burn rate {rate:.1f}x — the 30-day budget is gone in "
                      "~2 days at this rate")
    if rate > 6:
        return False, f"burn rate {rate:.1f}x — page, but do not auto-revert yet"
    return False, f"burn rate {rate:.1f}x — within budget"


def _demo() -> None:
    import random as _random

    print("=== Liveness vs readiness ===")
    print("A model server takes 100s to load weights. Probe plan:")
    for kind, settings in probe_plan(100).items():
        budget = settings["period_s"] * settings["failure_threshold"]
        print(f"  {kind:<10} period {settings['period_s']:>3.0f}s  "
              f"threshold {settings['failure_threshold']:>3.0f}  "
              f"-> tolerates {budget:>4.0f}s")
    print("The startup probe covers the load; liveness only takes over after.")
    print("Without it, a 100s load fails a 60s liveness probe, Kubernetes")
    print("restarts the pod mid-load, and you get an infinite crash loop that")
    print("looks exactly like a bad image.\n")

    liveness = HealthCheck("llm", "liveness", timeout_s=10, failure_threshold=3)
    readiness = HealthCheck("llm", "readiness", timeout_s=3, failure_threshold=2)
    print("KV cache full — which probe should fail?")
    readiness.record(False)
    print(f"  readiness (2 failures) -> {readiness.record(False):<16}"
          "drain it, do not kill it")
    for _ in range(3):
        liveness_action = liveness.record(True)
    print(f"  liveness  (passing)    -> {liveness_action:<16}"
          "the process is fine, just busy")

    print("\n=== Canary analysis ===")
    rng = _random.Random(3)
    baseline = [rng.gauss(120, 25) for _ in range(20000)]

    scenarios = {
        "identical build": ([rng.gauss(120, 25) for _ in range(20000)], 20, 20),
        "20% slower p99": ([rng.gauss(120, 45) for _ in range(20000)], 20, 20),
        "new error path": ([rng.gauss(121, 25) for _ in range(20000)], 20, 220),
        "canary too small": ([rng.gauss(500, 25) for _ in range(90)], 20, 0),
    }
    print(f"{'scenario':<20}{'p99 ratio':>11}{'err delta':>12}{'verdict':>11}  why")
    for name, (canary, base_err, canary_err) in scenarios.items():
        comparison = compare_versions(baseline, canary, base_err, canary_err)
        verdict, reason = canary_verdict(comparison)
        print(f"{name:<20}{comparison['p99_ratio']:>11.2f}"
              f"{comparison['error_rate_delta']:>+12.3%}{verdict:>11}  {reason[:38]}")
    print("\nThe last row matters most: the canary is 4x SLOWER and the verdict")
    print("is still 'hold', because 90 requests cannot establish anything. A")
    print("canary that ships on 90 requests is not a safety mechanism, it is a")
    print("ritual.")

    print("\n=== Progressive rollout that stops itself ===")

    def observe_regression(fraction: float) -> Dict[str, float]:
        """A build that is fine at low load and falls over at 25%."""
        degraded = fraction >= 0.25
        canary = [rng.gauss(300 if degraded else 122, 30) for _ in range(20000)]
        return compare_versions(baseline, canary, 20, 400 if degraded else 21)

    result = Rollout().run(observe_regression)
    for entry in result["history"]:
        print(f"  {entry['fraction']:>5.0%}  {entry['verdict']:<9} "
              f"{entry['reason'][:52]}")
    print(f"outcome: {result['outcome']} at {result.get('failed_at', 1.0):.0%}")
    print("Staging is what kept this off 100% of traffic. A single 1% canary")
    print("would have passed and shipped the regression.")

    print("\n=== When to auto-roll-back ===")
    slo = SLO("api", threshold_ms=500, target=0.999)
    print(f"{'budget used':>13}{'window':>9}{'auto-revert':>13}  reason")
    for used, hours in [(0.002, 1), (0.015, 1), (0.05, 1), (0.30, 24)]:
        should, reason = rollback_triggers(slo, used, hours)
        print(f"{used:>13.1%}{hours:>8.1f}h{str(should):>13}  {reason[:46]}")


if __name__ == "__main__":
    _demo()
