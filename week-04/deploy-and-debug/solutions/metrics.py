"""
Step 2 — Metrics, percentiles and error budgets. Complete Solution.

The measurement layer. If you take one thing from this file: averages hide
exactly the failures your users notice.
"""

import math
from typing import Dict, List, Optional, Sequence, Tuple


def percentile(values: Sequence[float], q: float) -> float:
    """The q-th percentile (q in [0, 1]), nearest-rank."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(int(q * (len(ordered) - 1) + 0.5), len(ordered) - 1)
    return ordered[index]


def summarize(values: Sequence[float]) -> Dict[str, float]:
    """The summary worth putting on a dashboard."""
    if not values:
        return {"count": 0, "mean": 0.0, "p50": 0.0, "p90": 0.0,
                "p99": 0.0, "p999": 0.0, "max": 0.0}
    return {
        "count": len(values),
        "mean": sum(values) / len(values),
        "p50": percentile(values, 0.50),
        "p90": percentile(values, 0.90),
        "p99": percentile(values, 0.99),
        "p999": percentile(values, 0.999),
        "max": max(values),
    }


def why_not_the_mean(values: Sequence[float]) -> Dict[str, float]:
    """How much of the tail the mean is hiding."""
    stats = summarize(values)
    return {
        "mean": stats["mean"],
        "p99": stats["p99"],
        "p99_over_mean": stats["p99"] / stats["mean"] if stats["mean"] else 0.0,
        "fraction_above_mean": sum(1 for v in values if v > stats["mean"]) / len(values),
    }


# ---------------------------------------------------------------------------
# Latency composition
# ---------------------------------------------------------------------------

def fanout_tail(single_p99: float, single_p50: float, fanout: int) -> float:
    """Tail latency when one request waits on `fanout` parallel sub-requests.

    A request that touches N replicas is as slow as the slowest of them. If
    each has a 1% chance of being slow, the chance that NONE is slow is
    0.99^N — so at N=100 your median user hits a p99 backend.

    This is why a quorum read with R=3 has a worse tail than R=1, and why
    "our p99 is fine" per service says little about the p99 users experience.
    """
    probability_all_fast = 0.99 ** fanout
    return single_p50 + (single_p99 - single_p50) * (1 - probability_all_fast)


def queueing_delay(utilization: float, service_time_ms: float) -> float:
    """M/M/1 waiting time: service_time * u / (1 - u).

    The number every capacity plan should include. At 50% utilisation you wait
    1x the service time; at 90%, 9x; at 99%, 99x. Latency does not degrade
    gracefully as a fleet fills — it goes vertical.
    """
    if utilization >= 1.0:
        return float("inf")
    return service_time_ms * utilization / (1 - utilization)


# ---------------------------------------------------------------------------
# SLOs and error budgets
# ---------------------------------------------------------------------------

class SLO:
    """A latency/availability objective and the budget it implies."""

    def __init__(self, name: str, threshold_ms: float, target: float = 0.99,
                 window_days: int = 30):
        if not 0 < target < 1:
            raise ValueError("target must be a fraction like 0.99")
        self.name = name
        self.threshold_ms = threshold_ms
        self.target = target
        self.window_days = window_days

    @property
    def allowed_failure_fraction(self) -> float:
        return 1 - self.target

    @property
    def budget_minutes(self) -> float:
        """How much total badness the window allows."""
        return self.window_days * 24 * 60 * self.allowed_failure_fraction

    def evaluate(self, latencies_ms: Sequence[float],
                 errors: int = 0) -> Dict[str, float]:
        """Compliance, and how much budget an incident of this size burns."""
        total = len(latencies_ms) + errors
        if total == 0:
            return {"compliance": 1.0, "budget_used": 0.0, "met": True}
        bad = sum(1 for v in latencies_ms if v > self.threshold_ms) + errors
        compliance = 1 - bad / total
        budget_used = (bad / total) / self.allowed_failure_fraction
        return {
            "compliance": compliance,
            "bad_events": bad,
            "budget_used": budget_used,
            "met": compliance >= self.target,
        }

    def __repr__(self) -> str:
        return (f"<SLO {self.name}: {self.target:.1%} under "
                f"{self.threshold_ms:.0f}ms over {self.window_days}d>")


def burn_rate(budget_used_fraction: float, window_hours: float,
              slo_window_days: int = 30) -> float:
    """How fast the budget is being spent, relative to sustainable.

    Burn rate 1.0 exactly exhausts the budget at the end of the window. 14.4x
    burns a 30-day budget in about 2 days — the usual threshold for paging
    someone. Alerting on burn rate rather than raw error rate is what stops
    a 3am page for a blip that costs 0.01% of the budget.
    """
    window_fraction = window_hours / (slo_window_days * 24)
    return budget_used_fraction / window_fraction if window_fraction > 0 else 0.0


# ---------------------------------------------------------------------------
# The metrics that matter per system
# ---------------------------------------------------------------------------

SERVING_GOLDEN_SIGNALS = {
    "ttft_p99_ms": "time to first token — what users feel as responsiveness",
    "itl_p99_ms": "inter-token latency — what they feel as generation speed",
    "output_tokens_per_s": "throughput — what you are billed for",
    "prefix_cache_hit_rate": "0 means caching is off or routing is wrong",
    "kv_util_pct": "sustained >90% means preemption is imminent",
    "preempt_per_s": "non-zero means the fleet is under-provisioned, full stop",
    "error_rate": "timeouts and 429s",
    "queue_depth": "leading indicator; rises before latency does",
}

STORE_GOLDEN_SIGNALS = {
    "read_error_rate": "quorum not met on reads",
    "write_error_rate": "quorum not met on writes",
    "p99_read_ms": "tail, not mean — see fanout_tail",
    "nodes_up": "against nodes_total",
    "hint_queue_total": "hinted handoff backlog; growing means a peer is down",
    "sibling_rate": "conflicting versions; a spike means a partition",
    "gossip_disagreement": "nodes disagree about membership",
    "pending_compactions": "rising means the node is losing to its own write rate",
}


def _demo() -> None:
    import random as _random

    rng = _random.Random(4)
    # A realistic latency distribution: mostly fast, with a heavy tail.
    latencies = [rng.gauss(120, 25) for _ in range(9500)] + \
                [rng.gauss(900, 400) for _ in range(500)]
    latencies = [max(5.0, v) for v in latencies]

    print("=== Why the mean is not enough ===")
    stats = summarize(latencies)
    for key in ("mean", "p50", "p90", "p99", "p999", "max"):
        print(f"  {key:<7}{stats[key]:>10.0f} ms")
    hidden = why_not_the_mean(latencies)
    print(f"\np99 is {hidden['p99_over_mean']:.1f}x the mean.")
    print(f"Only {hidden['fraction_above_mean']:.1%} of requests are above the mean —")
    print("a dashboard showing 160ms average looks healthy while 1 user in 100")
    print("waits over a second.")

    print("\n=== Queueing: latency does not degrade gracefully ===")
    print(f"{'utilisation':>13}{'wait (100ms service)':>24}")
    for util in (0.5, 0.7, 0.8, 0.9, 0.95, 0.99):
        print(f"{util:>13.0%}{queueing_delay(util, 100):>21.0f} ms")
    print("This is why capacity plans leave headroom, and why a fleet at 95%")
    print("is already failing its SLO even though it 'has capacity'.")

    print("\n=== Fan-out amplifies the tail ===")
    print(f"{'replicas queried':>18}{'effective p99':>15}")
    for fanout in (1, 3, 10, 100):
        print(f"{fanout:>18}{fanout_tail(900, 120, fanout):>12.0f} ms")
    print("A quorum read with R=3 waits for the slowest of 3. Per-service p99")
    print("says little about what a fanned-out request actually experiences.")

    print("\n=== SLOs and error budgets ===")
    slo = SLO("chat TTFT", threshold_ms=500, target=0.99, window_days=30)
    print(f"{slo}")
    print(f"budget: {slo.budget_minutes:.0f} minutes of badness per 30 days")
    result = slo.evaluate(latencies, errors=20)
    print(f"\ncompliance:  {result['compliance']:.3%}  "
          f"({'MET' if result['met'] else 'MISSED'})")
    print(f"bad events:  {result['bad_events']:.0f}")
    print(f"budget used: {result['budget_used']:.1%} of the 30-day allowance")

    print("\n=== Burn rate decides whether to page ===")
    print(f"{'budget used':>13}{'over':>8}{'burn rate':>12}   action")
    for used, hours in [(0.01, 1), (0.05, 1), (0.02, 6), (0.50, 24), (0.10, 1)]:
        rate = burn_rate(used, hours)
        action = ("page now" if rate > 14.4 else
                  "ticket" if rate > 3 else "ignore")
        print(f"{used:>13.0%}{hours:>7}h{rate:>12.1f}   {action}")
    print("Burn rate 14.4x exhausts a 30-day budget in ~2 days. Alerting on it")
    print("instead of raw error rate is what stops the 3am page for a blip.")

    print("\n=== What to actually watch ===")
    for name, signals in (("LLM serving", SERVING_GOLDEN_SIGNALS),
                          ("Key-value store", STORE_GOLDEN_SIGNALS)):
        print(f"\n{name}:")
        for metric, why in signals.items():
            print(f"  {metric:<24} {why}")


if __name__ == "__main__":
    _demo()
