"""
Simulated deployments you can break. PROVIDED, NOT AN EXERCISE.

You cannot learn to debug a system by reading about it. You need one that is
actually broken, that you did not break yourself, that reports only what a real
deployment would report: metrics.

This file models two deployments — an LLM serving cluster and a Dynamo-style
key-value store — well enough that faults produce *realistic, distinguishable
signatures* in the metrics. The numbers are computed from a model of the
system, not hardcoded per fault, so the signatures are consequences rather than
answers written in advance.

What you get back is a MetricSnapshot: exactly the shape of thing a Prometheus
scrape or a `nodetool tpstats` would give you. No fault labels. Your job, in
diagnose.py, is to work out what is wrong from the numbers alone.
"""

import math
import random
from typing import Dict, List, Optional, Sequence

# ---------------------------------------------------------------------------
# Faults
# ---------------------------------------------------------------------------

# Serving faults
HEALTHY = "healthy"
UNDERSIZED_KV = "undersized_kv"            # gpu_memory_utilization set too low
PREFIX_CACHE_OFF = "prefix_cache_off"      # someone disabled APC
BAD_ROUTING = "bad_routing"                # round-robin over cache-affine traffic
SLOW_REPLICA = "slow_replica"              # one GPU throttling / on a bad host
OVERLOADED = "overloaded"                  # more traffic than the fleet can take

# Store faults
NODE_DOWN = "node_down"                    # one replica process is gone
QUORUM_TOO_STRICT = "quorum_too_strict"    # R or W set too high for the fleet
HOT_PARTITION = "hot_partition"            # one key range taking most traffic
NETWORK_PARTITION = "network_partition"    # the ring split in two

SERVING_FAULTS = [HEALTHY, UNDERSIZED_KV, PREFIX_CACHE_OFF, BAD_ROUTING,
                  SLOW_REPLICA, OVERLOADED]
STORE_FAULTS = [HEALTHY, NODE_DOWN, QUORUM_TOO_STRICT, HOT_PARTITION,
                NETWORK_PARTITION]


class MetricSnapshot:
    """What a monitoring system would show you. No fault label. That is the point."""

    def __init__(self, kind: str, fleet: Dict[str, float],
                 per_replica: List[Dict[str, float]]):
        self.kind = kind                   # "serving" or "store"
        self.fleet = fleet
        self.per_replica = per_replica

    def __getitem__(self, key: str) -> float:
        return self.fleet[key]

    def get(self, key: str, default: float = 0.0) -> float:
        return self.fleet.get(key, default)

    def replica_values(self, key: str) -> List[float]:
        return [r[key] for r in self.per_replica]

    def spread(self, key: str) -> float:
        """max / mean across replicas. 1.0 is perfectly even."""
        values = self.replica_values(key)
        mean = sum(values) / len(values) if values else 0.0
        return max(values) / mean if mean > 1e-9 else 0.0

    def render(self) -> str:
        lines = [f"=== {self.kind} fleet ==="]
        for key, value in sorted(self.fleet.items()):
            lines.append(f"  {key:<26}{value:>12.2f}")
        lines.append(f"  --- per replica ({len(self.per_replica)}) ---")
        keys = sorted(self.per_replica[0]) if self.per_replica else []
        header = "  " + "".join(f"{k[:11]:>13}" for k in keys)
        lines.append(header)
        for i, replica in enumerate(self.per_replica):
            lines.append(f"{i:>2}" + "".join(f"{replica[k]:>13.2f}" for k in keys))
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"<MetricSnapshot {self.kind} {len(self.per_replica)} replicas>"


def _percentile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(int(q * (len(ordered) - 1) + 0.5), len(ordered) - 1)
    return ordered[index]


# ---------------------------------------------------------------------------
# LLM serving cluster
# ---------------------------------------------------------------------------

class ServingDeployment:
    """A vLLM-style fleet: N replicas, each with a KV budget and a prefix cache.

    The physics that matters, and that the metrics reflect:

      - A replica can hold `kv_tokens` of KV cache. Concurrent sequences share
        it. Run out and the scheduler PREEMPTS: a running sequence is evicted
        and its prefill recomputed later. Preemption is the single most useful
        signal that a serving fleet is under-provisioned.
      - Prefill is O(uncached prompt tokens) and dominates TTFT.
      - Decode is memory-bound and roughly constant per token: that is ITL.
      - Queueing time adds to TTFT and grows without bound once arrival rate
        exceeds service rate.
    """

    def __init__(self, num_replicas: int = 4, kv_tokens_per_replica: int = 8192,
                 prefix_cache: bool = True, cache_aware_routing: bool = True,
                 arrival_rate: float = 12.0, seed: int = 7):
        self.num_replicas = num_replicas
        self.kv_tokens = kv_tokens_per_replica
        self.prefix_cache = prefix_cache
        self.cache_aware_routing = cache_aware_routing
        self.arrival_rate = arrival_rate      # requests per second
        self.seed = seed
        self.slow_replica: Optional[int] = None
        self.slow_factor = 1.0

    # -- fault injection ----------------------------------------------------

    @classmethod
    def with_fault(cls, fault: str, seed: int = 7) -> "ServingDeployment":
        base = dict(num_replicas=4, kv_tokens_per_replica=8192,
                    prefix_cache=True, cache_aware_routing=True,
                    arrival_rate=12.0, seed=seed)
        deployment = cls(**base)
        if fault == UNDERSIZED_KV:
            deployment.kv_tokens = 1200        # gpu_memory_utilization far too low
        elif fault == PREFIX_CACHE_OFF:
            deployment.prefix_cache = False
        elif fault == BAD_ROUTING:
            deployment.cache_aware_routing = False
        elif fault == SLOW_REPLICA:
            deployment.slow_replica = 2
            deployment.slow_factor = 6.0
        elif fault == OVERLOADED:
            deployment.arrival_rate = 55.0
        return deployment

    # -- the model ----------------------------------------------------------

    def observe(self, duration_s: float = 60.0) -> MetricSnapshot:
        rng = random.Random(self.seed)
        num_requests = int(self.arrival_rate * duration_s)

        # Traffic: a shared 600-token system prompt, then a short user turn.
        system_tokens, user_tokens, gen_tokens = 600, 60, 120
        prompt_tokens = system_tokens + user_tokens

        # Cache hit rate. Cache-aware routing concentrates each tenant on a
        # replica, so the shared prefix stays resident; round-robin spreads it
        # and every replica thrashes.
        if not self.prefix_cache:
            hit_rate = 0.0
        elif self.cache_aware_routing:
            hit_rate = min(0.92, self.kv_tokens / (self.kv_tokens + 900))
        else:
            hit_rate = min(0.55, self.kv_tokens / (self.kv_tokens + 4200))

        cached_tokens = prompt_tokens * hit_rate
        prefill_tokens = prompt_tokens - cached_tokens

        # KV footprint per running sequence, and how many fit at once.
        kv_per_seq = prompt_tokens + gen_tokens
        capacity = max(1, int(self.kv_tokens / kv_per_seq))

        # Service rate per replica: prefill plus decode, in tokens of work.
        prefill_ms = prefill_tokens * 0.09
        decode_ms_per_token = 7.5
        service_ms = prefill_ms + gen_tokens * decode_ms_per_token
        per_replica_rps = (capacity * 1000.0) / max(service_ms, 1e-6)

        offered = self.arrival_rate / self.num_replicas
        replicas: List[Dict[str, float]] = []
        all_ttft: List[float] = []
        all_itl: List[float] = []
        preemptions_total = 0.0
        errors = 0.0

        for index in range(self.num_replicas):
            slow = self.slow_factor if index == self.slow_replica else 1.0
            effective_rps = per_replica_rps / slow

            # Cache-aware routing concentrates load slightly; round-robin is
            # perfectly even but wastes cache.
            share = offered
            if self.cache_aware_routing and index == 0:
                share = offered * 1.15
            elif self.cache_aware_routing:
                share = offered * 0.95

            utilisation = share / max(effective_rps, 1e-9)
            # M/M/1-ish queueing: waiting time blows up as utilisation -> 1.
            if utilisation < 0.98:
                queue_ms = (utilisation / (1 - utilisation)) * service_ms * 0.35
            else:
                queue_ms = service_ms * 40
                errors += share * 0.18       # timeouts / 429s

            # Preemption: when the KV budget cannot hold the working set.
            desired = share * service_ms / 1000.0        # Little's law
            preemptions = max(0.0, desired - capacity) * 6.0
            preemptions_total += preemptions
            preempt_penalty = preemptions * prefill_ms * 0.5

            ttft = (prefill_ms * slow) + queue_ms + preempt_penalty
            itl = decode_ms_per_token * slow * (1 + 0.35 * min(utilisation, 1.5))

            samples = [ttft * rng.uniform(0.75, 1.6) for _ in range(60)]
            itl_samples = [itl * rng.uniform(0.85, 1.4) for _ in range(60)]
            all_ttft += samples
            all_itl += itl_samples

            replicas.append({
                "ttft_p99_ms": _percentile(samples, 0.99),
                "itl_p99_ms": _percentile(itl_samples, 0.99),
                "running_seqs": min(desired, capacity),
                "kv_util_pct": 100.0 * min(desired, capacity) / capacity,
                "preempt_per_s": preemptions,
                "rps": share,
            })

        throughput = sum(r["rps"] for r in replicas) * gen_tokens
        return MetricSnapshot("serving", {
            "ttft_p50_ms": _percentile(all_ttft, 0.50),
            "ttft_p99_ms": _percentile(all_ttft, 0.99),
            "itl_p99_ms": _percentile(all_itl, 0.99),
            "output_tokens_per_s": throughput,
            "prefix_cache_hit_rate": hit_rate,
            "kv_util_pct": sum(r["kv_util_pct"] for r in replicas) / len(replicas),
            "preempt_per_s": preemptions_total,
            "max_concurrent_seqs": float(capacity),
            "error_rate": errors / max(self.arrival_rate, 1e-9),
            "requests_per_s": self.arrival_rate,
        }, replicas)


# ---------------------------------------------------------------------------
# Dynamo-style key-value store
# ---------------------------------------------------------------------------

class StoreDeployment:
    """A Dynamo-style ring: S nodes, N replicas per key, R and W quorums."""

    def __init__(self, num_nodes: int = 6, n: int = 3, r: int = 2, w: int = 2,
                 dead_nodes: Optional[List[int]] = None,
                 partitioned: bool = False, hot_key_share: float = 0.0,
                 request_rate: float = 900.0, seed: int = 11):
        self.num_nodes = num_nodes
        self.n, self.r, self.w = n, r, w
        self.dead_nodes = dead_nodes or []
        self.partitioned = partitioned
        self.hot_key_share = hot_key_share
        self.request_rate = request_rate
        self.seed = seed

    @classmethod
    def with_fault(cls, fault: str, seed: int = 11) -> "StoreDeployment":
        deployment = cls(seed=seed)
        if fault == NODE_DOWN:
            deployment.dead_nodes = [3]
        elif fault == QUORUM_TOO_STRICT:
            deployment.r = 3
            deployment.w = 3
            deployment.dead_nodes = [3]
        elif fault == HOT_PARTITION:
            deployment.hot_key_share = 0.75
        elif fault == NETWORK_PARTITION:
            deployment.partitioned = True
        return deployment

    def observe(self, duration_s: float = 60.0) -> MetricSnapshot:
        rng = random.Random(self.seed)
        live = [i for i in range(self.num_nodes) if i not in self.dead_nodes]

        # With a partition, each side sees only its half of the ring.
        visible = self.num_nodes // 2 if self.partitioned else len(live)
        reachable_replicas = min(self.n, max(1, int(self.n * visible / self.num_nodes)))

        read_fail = 1.0 if reachable_replicas < self.r else 0.0
        write_fail = 1.0 if reachable_replicas < self.w else 0.0
        # Even when the quorum is satisfiable, a dead replica costs retries.
        degraded = len(self.dead_nodes) / max(self.num_nodes, 1)

        replicas: List[Dict[str, float]] = []
        base_rps = self.request_rate / self.num_nodes
        for index in range(self.num_nodes):
            dead = index in self.dead_nodes
            share = 0.0 if dead else base_rps
            if self.hot_key_share > 0 and index == 1 and not dead:
                share = self.request_rate * self.hot_key_share
            elif self.hot_key_share > 0 and not dead:
                share = self.request_rate * (1 - self.hot_key_share) / (self.num_nodes - 1)

            load = share / 260.0                       # 260 rps saturates a node
            latency = 4.0 + (load / max(1 - min(load, 0.97), 0.03)) * 3.0
            replicas.append({
                "rps": share,
                "p99_ms": 0.0 if dead else latency * rng.uniform(0.95, 1.15),
                "up": 0.0 if dead else 1.0,
                "hint_queue": 0.0 if dead else
                              (len(self.dead_nodes) * 420.0 / max(len(live), 1)),
                "cpu_pct": min(99.0, load * 92.0),
            })

        alive_latencies = [r["p99_ms"] for r in replicas if r["up"]]
        sibling_rate = 0.22 if self.partitioned else (0.01 + 0.03 * degraded)

        return MetricSnapshot("store", {
            "read_error_rate": read_fail,
            "write_error_rate": write_fail,
            "p99_read_ms": max(alive_latencies) if alive_latencies else 0.0,
            "nodes_up": float(len(live)),
            "nodes_total": float(self.num_nodes),
            "n": float(self.n), "r": float(self.r), "w": float(self.w),
            "hint_queue_total": sum(r["hint_queue"] for r in replicas),
            "sibling_rate": sibling_rate,
            "gossip_disagreement": 1.0 if self.partitioned else 0.0,
            "requests_per_s": self.request_rate,
        }, replicas)


def _demo() -> None:
    print("Two deployments, each breakable in several ways.")
    print("The metrics below are all diagnose.py ever sees — no fault labels.\n")

    for fault in (HEALTHY, UNDERSIZED_KV, SLOW_REPLICA):
        snapshot = ServingDeployment.with_fault(fault).observe()
        print(f"--- serving, fault = {fault} ---")
        print(f"  ttft_p99      {snapshot['ttft_p99_ms']:>9.1f} ms")
        print(f"  itl_p99       {snapshot['itl_p99_ms']:>9.1f} ms")
        print(f"  cache hit     {snapshot['prefix_cache_hit_rate']:>9.1%}")
        print(f"  preempt/s     {snapshot['preempt_per_s']:>9.2f}")
        print(f"  max concurrent{snapshot['max_concurrent_seqs']:>9.0f}")
        print(f"  itl spread    {snapshot.spread('itl_p99_ms'):>9.2f}x")
        print()

    for fault in (HEALTHY, NODE_DOWN, QUORUM_TOO_STRICT):
        snapshot = StoreDeployment.with_fault(fault).observe()
        print(f"--- store, fault = {fault} ---")
        print(f"  read errors   {snapshot['read_error_rate']:>9.1%}")
        print(f"  write errors  {snapshot['write_error_rate']:>9.1%}")
        print(f"  nodes up      {snapshot['nodes_up']:>9.0f} / "
              f"{snapshot['nodes_total']:.0f}")
        print(f"  N/R/W         {snapshot['n']:.0f}/{snapshot['r']:.0f}/"
              f"{snapshot['w']:.0f}")
        print(f"  hint queue    {snapshot['hint_queue_total']:>9.0f}")
        print()

    print("Note the last two: identical node count, identical hint queue — the")
    print("ONLY difference is R and W. That is why diagnosis has to read the")
    print("configuration alongside the symptoms.")


if __name__ == "__main__":
    _demo()
