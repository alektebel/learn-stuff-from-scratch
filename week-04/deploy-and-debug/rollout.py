"""
Step 4 — Deploying safely: health checks, canaries and rollback
===============================================================
Effort: medium. The "deploy" half of the directory.

Deployment is not "the new version is running". It is "the new version is
running, AND you found out quickly if it is worse, AND you can get back".

What you build:
  HealthCheck / probe_plan
  compare_versions / enough_samples / canary_verdict
  Rollout / rollback_triggers

Background:
  LIVENESS vs READINESS is the distinction that causes the most self-inflicted
  outages:

    liveness  — "is this process wedged?"  Failing it RESTARTS the container.
    readiness — "should this replica get traffic?"  Failing it removes it from
                the load balancer. No restart.

  A model server loading 16GB of weights is ALIVE but NOT READY for two
  minutes. If that fails a liveness probe, the orchestrator kills it mid-load,
  forever, and you have an infinite crash loop that looks exactly like a bad
  image. A startup probe is what covers the load window.

  A replica whose KV cache is full should fail READINESS (shed traffic, drain)
  and pass LIVENESS (it is working fine, just busy).

  The other idea: a canary that has not seen enough traffic proves nothing.
  Shipping on an underpowered canary is worse than not canarying at all — it
  manufactures confidence.
"""

import math
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from metrics import SLO, burn_rate, percentile


class HealthCheck:
    """One probe, with consecutive-failure tracking."""

    def __init__(self, name: str, kind: str, timeout_s: float,
                 failure_threshold: int = 3):
        """TODO: store fields; raise ValueError unless kind is one of
        'liveness', 'readiness', 'startup'. Start consecutive_failures at 0."""
        raise NotImplementedError

    def record(self, healthy: bool) -> str:
        """TODO: returns 'none', 'remove_from_lb' or 'restart'.

        A healthy result RESETS the counter — probes must fail consecutively,
        or a single blip on a flaky network restarts your fleet. Below the
        threshold, return 'none'. At or above it, 'restart' for liveness and
        'remove_from_lb' for anything else.
        """
        raise NotImplementedError


def probe_plan(model_load_seconds: float) -> Dict[str, Dict[str, float]]:
    """TODO: return startup / readiness / liveness settings that survive a slow
    model load.

    The startup probe needs period * failure_threshold to comfortably exceed
    model_load_seconds. Readiness should drain fast (short period, low
    threshold). Liveness can be slow and forgiving, because once startup has
    passed, a hang really is a bug.
    """
    raise NotImplementedError


def compare_versions(baseline_latencies: Sequence[float],
                     canary_latencies: Sequence[float],
                     baseline_errors: int = 0,
                     canary_errors: int = 0) -> Dict[str, float]:
    """TODO: p99 of each, their ratio, error rates, their delta, and the total
    canary sample count (latencies + errors)."""
    raise NotImplementedError


def enough_samples(canary_samples: int, baseline_rate: float,
                   detectable_increase: float = 2.0) -> bool:
    """Is the canary carrying enough traffic to conclude anything?

    TODO: roughly, you need 10 / baseline_rate / detectable_increase samples.
    Guard a zero baseline_rate (use ~0.001).

    At a 0.1% baseline error rate that is thousands of requests. A canary at 1%
    of traffic for 90 seconds has seen nothing, and its clean metrics prove
    nothing.
    """
    raise NotImplementedError


def canary_verdict(comparison: Dict[str, float],
                   p99_tolerance: float = 1.20,
                   error_tolerance: float = 0.005) -> Tuple[str, str]:
    """TODO: return (verdict, reason) — 'promote', 'rollback' or 'hold'.

    Check in this order:
      1. Not enough samples          -> 'hold'   (do this FIRST)
      2. error_rate_delta > tolerance -> 'rollback'
      3. p99_ratio > tolerance        -> 'rollback'
      4. otherwise                    -> 'promote'

    'hold' is a real answer and the one most often missing from homegrown
    canary tooling. If the canary has not seen enough traffic, neither
    promoting nor rolling back is justified.
    """
    raise NotImplementedError


class Rollout:
    """A staged rollout that can stop itself."""

    def __init__(self, stages: Optional[List[float]] = None,
                 p99_tolerance: float = 1.20,
                 error_tolerance: float = 0.005):
        self.stages = stages or [0.01, 0.05, 0.25, 1.00]
        self.p99_tolerance = p99_tolerance
        self.error_tolerance = error_tolerance
        self.history: List[Dict[str, object]] = []

    def run(self, observe: Callable[[float], Dict[str, float]]) -> Dict[str, object]:
        """TODO: walk the stages, calling observe(fraction) at each and taking
        a verdict. Record every stage in self.history. Stop and return on
        'rollback' or 'hold'; return 'promoted' if every stage passes.

        Stages exist so the blast radius only grows after evidence. A single 1%
        canary would miss a regression that only appears under real load —
        which the demo demonstrates.
        """
        raise NotImplementedError


def rollback_triggers(slo: SLO, budget_used: float,
                      window_hours: float) -> Tuple[bool, str]:
    """Should an automated system revert right now?

    TODO: compute the burn rate, then
      > 14.4 -> (True, ...)   the 30-day budget is gone in ~2 days
      > 6    -> (False, ...)  page a human, but do not auto-revert
      else   -> (False, ...)  within budget

    Tie this to the error BUDGET, never the raw error rate. A 2% error rate for
    30 seconds is noise; 0.5% sustained for six hours eats a month's budget.
    """
    raise NotImplementedError


def _demo() -> None:
    """Once implemented, produce:

    1. A probe plan for a 100s model load, showing the startup probe tolerating
       ~360s while liveness stays tight.
    2. The KV-cache-full case: readiness fails (remove_from_lb), liveness
       passes (none).
    3. Four canary scenarios. The instructive one is a canary that is 3x SLOWER
       and still returns 'hold', because 90 requests establish nothing.
    4. A staged rollout against a build that is fine at 1% and 5% and falls
       over at 25%. It should roll back AT 25%, never reaching 100% — which a
       single 1% canary would have missed.
    5. The auto-revert table, spanning burn rates from 1.4x to 36x.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
