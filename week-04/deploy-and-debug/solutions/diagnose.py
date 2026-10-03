"""
Step 3 — Diagnosis: from metrics to root cause. Complete Solution.

The debugging skill, made concrete. You are handed a MetricSnapshot from a
broken deployment — no fault label, just numbers — and must name the cause.

The method, which is the transferable part:

  1. Start from the SYMPTOM the user reports (slow, failing, expensive).
  2. Find the metric that is anomalous, not merely high. "TTFT is 60 seconds"
     is a symptom; "max_concurrent_seqs is 1" is a cause.
  3. Separate FLEET-WIDE from PER-REPLICA. One bad replica and a systemically
     undersized fleet look identical in an average and completely different in
     a spread.
  4. Read the configuration alongside the symptoms. Two of the store faults
     below have identical topology and differ only in R and W.
  5. Distinguish the confusable pair. Every real runbook comes down to a
     handful of "these two look alike, here is what separates them".
"""

from typing import Dict, List, Optional

from deployment import (BAD_ROUTING, HEALTHY, HOT_PARTITION, NETWORK_PARTITION,
                        NODE_DOWN, OVERLOADED, PREFIX_CACHE_OFF,
                        QUORUM_TOO_STRICT, SLOW_REPLICA, UNDERSIZED_KV,
                        MetricSnapshot)


class Diagnosis:
    """A cause, the evidence for it, and what to do next."""

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


# ---------------------------------------------------------------------------
# Serving
# ---------------------------------------------------------------------------

def diagnose_serving(snapshot: MetricSnapshot) -> Diagnosis:
    """Diagnose an LLM serving fleet.

    Order matters. Check the most specific, most actionable signatures first;
    a broad "latency is high" rule placed early swallows every other case.
    """
    ttft = snapshot["ttft_p99_ms"]
    itl_spread = snapshot.spread("itl_p99_ms")
    hit_rate = snapshot["prefix_cache_hit_rate"]
    preempt = snapshot["preempt_per_s"]
    concurrent = snapshot["max_concurrent_seqs"]
    rps = snapshot["requests_per_s"]

    # One replica far slower than its peers. Check this BEFORE anything
    # fleet-wide: a single bad host drags every fleet average with it, and
    # every other rule would then misfire.
    if itl_spread > 1.8:
        worst = max(range(len(snapshot.per_replica)),
                    key=lambda i: snapshot.per_replica[i]["itl_p99_ms"])
        return Diagnosis(
            SLOW_REPLICA,
            [f"itl_p99 spread across replicas is {itl_spread:.1f}x",
             f"replica {worst} at {snapshot.per_replica[worst]['itl_p99_ms']:.0f}ms "
             f"vs fleet median",
             "load is even, so this is the host, not the traffic"],
            f"drain replica {worst}; check GPU clocks, ECC errors and thermals "
            "(nvidia-smi -q), then replace the host")

    # Preemption means the KV budget cannot hold the working set. The question
    # is whether the budget is too small or the traffic is too big.
    if preempt > 1.0:
        if concurrent <= 4:
            return Diagnosis(
                UNDERSIZED_KV,
                [f"only {concurrent:.0f} concurrent sequences fit",
                 f"preemption at {preempt:.1f}/s",
                 f"traffic is {rps:.0f} req/s — normal, so this is not load"],
                "raise --gpu-memory-utilization, or lower --max-model-len; "
                "check nothing else is resident on the GPU")
        return Diagnosis(
            OVERLOADED,
            [f"preemption at {preempt:.1f}/s",
             f"but {concurrent:.0f} sequences fit per replica — the budget is fine",
             f"arrival rate is {rps:.0f} req/s"],
            "add replicas, or shed load at the gateway; scaling the KV cache "
            "will not help")

    # Caching problems: latency is elevated but nothing is starved.
    if hit_rate < 0.05:
        return Diagnosis(
            PREFIX_CACHE_OFF,
            ["prefix cache hit rate is 0",
             "no preemption and KV utilisation is normal",
             "so this is configuration, not capacity"],
            "enable prefix caching (--enable-prefix-caching); confirm no "
            "per-request field is defeating the hash (timestamps, request ids)")

    if hit_rate < 0.70:
        return Diagnosis(
            BAD_ROUTING,
            [f"hit rate is {hit_rate:.0%} — caching is on but underperforming",
             "load is evenly spread across replicas",
             "traffic shares a long prefix that is landing on every replica"],
            "switch the load balancer to cache-aware / session-affinity "
            "routing so a tenant's prefix stays on one replica")

    if ttft > 2000:
        return Diagnosis(
            OVERLOADED,
            [f"ttft_p99 {ttft:.0f}ms with no preemption and healthy cache",
             "queueing delay dominates"],
            "add replicas or shed load", confidence="medium")

    return Diagnosis(
        HEALTHY,
        [f"ttft_p99 {ttft:.0f}ms, hit rate {hit_rate:.0%}, no preemption",
         f"{concurrent:.0f} concurrent sequences per replica"],
        "none")


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

def diagnose_store(snapshot: MetricSnapshot) -> Diagnosis:
    """Diagnose a Dynamo-style key-value store."""
    read_errors = snapshot["read_error_rate"]
    write_errors = snapshot["write_error_rate"]
    up, total = snapshot["nodes_up"], snapshot["nodes_total"]
    n, r, w = snapshot["n"], snapshot["r"], snapshot["w"]
    hints = snapshot["hint_queue_total"]

    # A split ring: both halves keep serving and neither knows about the other.
    if snapshot["gossip_disagreement"] > 0 or snapshot["sibling_rate"] > 0.15:
        return Diagnosis(
            NETWORK_PARTITION,
            [f"nodes disagree about membership",
             f"sibling rate {snapshot['sibling_rate']:.0%} — concurrent writes "
             "on both sides of the split",
             f"{up:.0f}/{total:.0f} nodes nominally up, so this is the network"],
            "check network reachability and security groups between racks; "
            "expect siblings to need application-level reconciliation afterwards")

    # Quorum unsatisfiable. Distinguish 'too many nodes down' from 'R/W set too
    # high for the fleet you have' — same symptom, opposite fix.
    if read_errors > 0.05 or write_errors > 0.05:
        down = total - up
        if r + w > n + 1 and down <= n - 1:
            return Diagnosis(
                QUORUM_TOO_STRICT,
                [f"R={r:.0f} W={w:.0f} N={n:.0f} leaves no failure tolerance",
                 f"only {down:.0f} node(s) down, which a sane quorum survives",
                 "errors are a configuration choice, not a capacity problem"],
                f"lower R or W (R=2 W=2 for N=3 survives one loss), or raise N "
                "to 5 if you need to survive two")
        return Diagnosis(
            NODE_DOWN,
            [f"{down:.0f} of {total:.0f} nodes down",
             f"quorum R={r:.0f}/W={w:.0f} cannot be met"],
            "restart or replace the failed nodes; check disk and heap first")

    # Load skew: one node taking a disproportionate share.
    rps_spread = snapshot.spread("rps")
    if rps_spread > 2.0:
        worst = max(range(len(snapshot.per_replica)),
                    key=lambda i: snapshot.per_replica[i]["rps"])
        return Diagnosis(
            HOT_PARTITION,
            [f"request rate spread across nodes is {rps_spread:.1f}x",
             f"node {worst} taking {snapshot.per_replica[worst]['rps']:.0f} rps",
             "all nodes are up, so this is key distribution not failure"],
            "find the hot key; add a salt or split the partition. More nodes "
            "will NOT help — the hot key still lands on one of them")

    # Everything serving, but a peer is missing and hints are piling up.
    if hints > 100 and up < total:
        return Diagnosis(
            NODE_DOWN,
            [f"{total - up:.0f} node(s) down",
             f"hinted handoff queue at {hints:.0f} and growing",
             "quorum is still being met, so reads and writes still succeed"],
            "restore the node before the hint window expires, or those writes "
            "fall to anti-entropy — and to a full repair if hints are dropped")

    return Diagnosis(
        HEALTHY,
        [f"{up:.0f}/{total:.0f} nodes up, no quorum errors",
         f"p99 read {snapshot['p99_read_ms']:.1f}ms"],
        "none")


def diagnose(snapshot: MetricSnapshot) -> Diagnosis:
    """Dispatch on the deployment kind."""
    if snapshot.kind == "serving":
        return diagnose_serving(snapshot)
    if snapshot.kind == "store":
        return diagnose_store(snapshot)
    raise ValueError(f"unknown deployment kind {snapshot.kind!r}")


def _demo() -> None:
    from deployment import (SERVING_FAULTS, STORE_FAULTS, ServingDeployment,
                            StoreDeployment)

    print("=" * 70)
    print("Diagnosing serving deployments from metrics alone")
    print("=" * 70)
    correct = 0
    for fault in SERVING_FAULTS:
        snapshot = ServingDeployment.with_fault(fault).observe()
        result = diagnose(snapshot)
        ok = result.cause == fault
        correct += ok
        print(f"\ninjected: {fault}   ->   {'CORRECT' if ok else 'WRONG'}")
        print(result)
    print(f"\n{correct}/{len(SERVING_FAULTS)} serving faults identified")

    print("\n" + "=" * 70)
    print("Diagnosing store deployments")
    print("=" * 70)
    store_correct = 0
    for fault in STORE_FAULTS:
        snapshot = StoreDeployment.with_fault(fault).observe()
        result = diagnose(snapshot)
        ok = result.cause == fault
        store_correct += ok
        print(f"\ninjected: {fault}   ->   {'CORRECT' if ok else 'WRONG'}")
        print(result)
    print(f"\n{store_correct}/{len(STORE_FAULTS)} store faults identified")

    print("\n" + "=" * 70)
    print("The two pairs that actually matter")
    print("=" * 70)
    print("""
undersized_kv vs overloaded
  Both show preemption, high TTFT and timeouts. Identical symptoms.
  Separator: max_concurrent_seqs. If only 1-2 sequences fit, the KV budget
  is wrong. If the normal number fits and traffic is 4x baseline, it is load.
  Fixing the wrong one costs you either a pointless scale-up or a config
  change that does nothing.

node_down vs quorum_too_strict
  Both show read/write errors with a node missing. Identical topology.
  Separator: R + W against N. One node down with R=2 W=2 N=3 is survivable
  by design; the same outage with R=3 W=3 fails every request. The fix is
  the opposite in each case — replace hardware, or fix a config value.
""")


if __name__ == "__main__":
    _demo()
