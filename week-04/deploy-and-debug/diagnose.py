"""
Step 3 — Diagnosis: from metrics to root cause
===============================================
Effort: medium, and the centre of this directory. Everything else exists to
make this step possible.

You are handed a MetricSnapshot from a broken deployment — no fault label,
just numbers — and must name the cause.

What you build:
  diagnose_serving -> identify 6 serving faults
  diagnose_store   -> identify 5 store faults

The method, which is the part that transfers to systems this directory never
mentions:

  1. Start from the SYMPTOM a user would report (slow, failing, expensive).
  2. Find the metric that is ANOMALOUS, not merely high. "TTFT is 60 seconds"
     is a symptom; "only 1 sequence fits in KV" is a cause. Keep asking why
     until you reach something you can act on.
  3. Separate FLEET-WIDE from PER-REPLICA. One bad host and a systemically
     undersized fleet look identical in an average and completely different in
     a spread. Use snapshot.spread(key).
  4. Read the CONFIGURATION alongside the symptoms. Two store faults below have
     identical topology and differ only in R and W.
  5. Know your CONFUSABLE PAIR. Every real runbook reduces to a handful of
     "these two look alike, here is the separator".

Order your checks from most specific to most general. A broad "latency is
high" rule placed first swallows every other case.
"""

from typing import Dict, List, Optional

from deployment import (BAD_ROUTING, HEALTHY, HOT_PARTITION, NETWORK_PARTITION,
                        NODE_DOWN, OVERLOADED, PREFIX_CACHE_OFF,
                        QUORUM_TOO_STRICT, SLOW_REPLICA, UNDERSIZED_KV,
                        MetricSnapshot)


class Diagnosis:
    """A cause, the evidence for it, and what to do next.

    Carry the evidence. A diagnosis without it cannot be checked by the next
    person, and half of incident response is convincing someone else.
    """

    def __init__(self, cause: str, evidence: List[str], action: str,
                 confidence: str = "high"):
        self.cause = cause
        self.evidence = evidence
        self.action = action
        self.confidence = confidence

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.cause == other
        return isinstance(other, Diagnosis) and self.cause == other.cause

    def __repr__(self) -> str:
        lines = [f"cause:  {self.cause}  ({self.confidence} confidence)"]
        for item in self.evidence:
            lines.append(f"  - {item}")
        lines.append(f"action: {self.action}")
        return "\n".join(lines)


def diagnose_serving(snapshot: MetricSnapshot) -> Diagnosis:
    """Identify what is wrong with an LLM serving fleet.

    Useful fields: ttft_p99_ms, itl_p99_ms, prefix_cache_hit_rate,
    preempt_per_s, max_concurrent_seqs, requests_per_s, error_rate, and
    snapshot.spread("itl_p99_ms") across replicas.

    TODO, in this order:

    1. SLOW_REPLICA — spread("itl_p99_ms") > ~1.8. Check this FIRST: one bad
       host drags every fleet average, so every later rule would misfire.
       Name the offending replica index in the evidence.

    2. preempt_per_s > 1 means the KV budget cannot hold the working set.
       Two very different causes, and this is the confusable pair:
         - max_concurrent_seqs is tiny (<= 4)  -> UNDERSIZED_KV
           (the budget is wrong; traffic is normal)
         - max_concurrent_seqs is normal       -> OVERLOADED
           (the budget is fine; there is simply too much traffic)
       Fixing the wrong one costs a pointless scale-up or a no-op config change.

    3. prefix_cache_hit_rate < ~0.05 -> PREFIX_CACHE_OFF. Caching is disabled,
       or something per-request (a timestamp, a request id) is defeating the
       hash. Note there is no preemption here — this is config, not capacity.

    4. hit rate < ~0.70 -> BAD_ROUTING. Caching is on but a shared prefix is
       landing on every replica, so each one thrashes.

    5. ttft > ~2000ms with nothing else anomalous -> OVERLOADED, medium
       confidence.

    6. Otherwise HEALTHY.
    """
    raise NotImplementedError


def diagnose_store(snapshot: MetricSnapshot) -> Diagnosis:
    """Identify what is wrong with a Dynamo-style key-value store.

    Useful fields: read_error_rate, write_error_rate, nodes_up, nodes_total,
    n, r, w, hint_queue_total, sibling_rate, gossip_disagreement, and
    snapshot.spread("rps").

    TODO, in this order:

    1. gossip_disagreement > 0, or sibling_rate > ~0.15 -> NETWORK_PARTITION.
       Both halves keep serving and neither knows about the other; concurrent
       writes on both sides produce siblings.

    2. read or write error rate > ~0.05 — the quorum cannot be met. The second
       confusable pair:
         - R + W > N + 1 while few nodes are actually down -> QUORUM_TOO_STRICT
           (the config left no failure tolerance)
         - otherwise                                       -> NODE_DOWN
       Same symptom, opposite fix: change a config value, or replace hardware.

    3. spread("rps") > ~2.0 -> HOT_PARTITION. All nodes up, but one takes most
       of the traffic. Adding nodes will NOT help — say so in the action.

    4. hint_queue_total > ~100 with nodes_up < nodes_total -> NODE_DOWN, still
       serving. Quorum is met, but restore the node before the hint window
       expires.

    5. Otherwise HEALTHY.
    """
    raise NotImplementedError


def diagnose(snapshot: MetricSnapshot) -> Diagnosis:
    """TODO: dispatch on snapshot.kind ("serving" / "store"); raise otherwise."""
    raise NotImplementedError


def _demo() -> None:
    """Once implemented, you should identify 6/6 serving faults and 5/5 store
    faults from metrics alone.

    Then write out, in your own words, the two separators:

      undersized_kv vs overloaded    -> max_concurrent_seqs
      node_down vs quorum_too_strict -> R + W against N

    If you can state those two from memory, you have the transferable part.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
