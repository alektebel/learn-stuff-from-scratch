"""
Step 2 — Metrics, percentiles and error budgets
================================================
Effort: small. The measurement layer everything else reads.

What you build:
  percentile / summarize / why_not_the_mean
  fanout_tail / queueing_delay
  SLO / burn_rate

Background:
  One idea underlies this whole file: **averages hide exactly the failures your
  users notice.** A dashboard reading "160ms average" can conceal 1 request in
  100 taking over a second.

  Three specific effects to internalise:

    Queueing.  Waiting time is service_time * u / (1-u). At 50% utilisation
    you wait 1x the service time; at 90%, 9x; at 99%, 99x. Latency does not
    degrade gracefully as a fleet fills — it goes vertical.

    Fan-out.   A request touching N backends is as slow as the slowest. If each
    is slow 1% of the time, P(none slow) = 0.99^N. At N=100 your median user
    hits a p99 backend.

    Error budgets. A 99.9% target over 30 days allows ~43 minutes of badness.
    Alert on the BURN RATE, not the raw error rate: 14.4x burns a 30-day budget
    in ~2 days and deserves a page; 1.4x does not.
"""

import math
from typing import Dict, List, Optional, Sequence, Tuple


def percentile(values: Sequence[float], q: float) -> float:
    """TODO: nearest-rank q-th percentile (q in [0,1]); 0.0 for empty input.

    Sort, then index at round(q * (n-1)), clamped to the last element.
    """
    raise NotImplementedError


def summarize(values: Sequence[float]) -> Dict[str, float]:
    """TODO: count, mean, p50, p90, p99, p999, max. Handle the empty case."""
    raise NotImplementedError


def why_not_the_mean(values: Sequence[float]) -> Dict[str, float]:
    """TODO: mean, p99, their ratio, and the fraction of samples above the mean.

    On a realistic heavy-tailed latency distribution the last number is often
    ~11% — meaning the "average" is not typical of anything.
    """
    raise NotImplementedError


def fanout_tail(single_p99: float, single_p50: float, fanout: int) -> float:
    """Effective tail when one request waits on `fanout` parallel sub-requests.

    TODO: probability_all_fast = 0.99 ** fanout, then interpolate:
        p50 + (p99 - p50) * (1 - probability_all_fast)

    This is why a quorum read with R=3 has a worse tail than R=1, and why a
    healthy per-service p99 says little about what users experience.
    """
    raise NotImplementedError


def queueing_delay(utilization: float, service_time_ms: float) -> float:
    """TODO: service_time * u / (1 - u); infinity at u >= 1."""
    raise NotImplementedError


class SLO:
    """A latency/availability objective and the error budget it implies."""

    def __init__(self, name: str, threshold_ms: float, target: float = 0.99,
                 window_days: int = 30):
        """TODO: store the fields; raise ValueError unless 0 < target < 1."""
        raise NotImplementedError

    @property
    def allowed_failure_fraction(self) -> float:
        """TODO: 1 - target."""
        raise NotImplementedError

    @property
    def budget_minutes(self) -> float:
        """TODO: window_days * 24 * 60 * allowed_failure_fraction.

        99.9% over 30 days = 43.2 minutes. Say that number out loud when
        someone proposes 99.99%.
        """
        raise NotImplementedError

    def evaluate(self, latencies_ms: Sequence[float],
                 errors: int = 0) -> Dict[str, float]:
        """TODO: count bad events (over threshold, plus errors), then return
        compliance, bad_events, budget_used (bad fraction / allowed fraction),
        and met (compliance >= target)."""
        raise NotImplementedError


def burn_rate(budget_used_fraction: float, window_hours: float,
              slo_window_days: int = 30) -> float:
    """TODO: budget_used / (window_hours / (slo_window_days * 24)).

    Burn rate 1.0 exactly exhausts the budget at the end of the window. The
    conventional page threshold is 14.4x (a 30-day budget gone in ~2 days).
    Alerting on this instead of a raw error rate is what prevents the 3am page
    for a blip that cost 0.01% of the budget.
    """
    raise NotImplementedError


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
    """Once implemented, produce and explain:

    1. A heavy-tailed latency sample: mean ~158ms but p99 ~1217ms — 7.7x — with
       only ~11% of requests above the mean.
    2. The queueing table from 50% to 99% utilisation. Watch 100ms of service
       time become 9900ms of waiting.
    3. The fan-out table at 1, 3, 10, 100 backends.
    4. An SLO evaluation and the burn-rate table, with the page/ticket/ignore
       decision for each row.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
