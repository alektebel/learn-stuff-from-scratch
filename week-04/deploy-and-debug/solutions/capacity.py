"""
Step 1 — Capacity planning. Complete Solution.

The arithmetic you do BEFORE deploying, and the arithmetic that tells you what
went wrong afterwards. Every number here is one you would put in a config file
or a capacity review.
"""

import math
from typing import Dict, List, Optional

BYTES_PER_GIB = 1024 ** 3


# ---------------------------------------------------------------------------
# LLM serving
# ---------------------------------------------------------------------------

def kv_bytes_per_token(num_layers: int, num_kv_heads: int, head_dim: int,
                       dtype_bytes: int = 2) -> int:
    """KV cache cost of one token, one sequence.

        2 (K and V) x layers x kv_heads x head_dim x dtype_bytes

    `num_kv_heads`, not `num_heads`. Grouped-query attention shares K/V across
    query heads: Llama-3-8B has 32 query heads but only 8 KV heads, so using
    the wrong one overestimates the cache by 4x — and you will size the fleet
    four times too large.
    """
    return 2 * num_layers * num_kv_heads * head_dim * dtype_bytes


def kv_cache_capacity(total_gpu_gib: float, weights_gib: float,
                      gpu_memory_utilization: float = 0.90,
                      activation_gib: float = 2.0) -> float:
    """GiB left for KV cache after weights, activations and headroom.

    `gpu_memory_utilization` is vLLM's flag: the fraction of the card the
    server is allowed to claim. The rest is headroom for fragmentation,
    CUDA context and anything else on the device. Push it to 0.99 and you trade
    a bigger cache for OOM crashes under load spikes.
    """
    usable = total_gpu_gib * gpu_memory_utilization
    return max(0.0, usable - weights_gib - activation_gib)


def max_concurrent_sequences(kv_gib: float, bytes_per_token: int,
                             avg_context_tokens: int) -> int:
    """How many sequences fit at once. This IS your batch size ceiling.

    Note it depends on the AVERAGE context, not max_model_len. Sizing against
    max_model_len is the most common over-provisioning mistake; sizing against
    the average without headroom is the most common OOM.
    """
    if avg_context_tokens <= 0:
        raise ValueError("avg_context_tokens must be positive")
    per_seq = bytes_per_token * avg_context_tokens
    return int((kv_gib * BYTES_PER_GIB) // per_seq)


def throughput_estimate(concurrent: int, output_tokens: int,
                        prefill_tokens: int, prefill_ms_per_token: float = 0.09,
                        decode_ms_per_token: float = 7.5) -> Dict[str, float]:
    """Rough request/s and token/s from batch size and per-token costs.

    Deliberately crude: it ignores batching efficiency, chunked prefill and
    kernel details. Its job is to tell you whether you are within 2x of your
    target, which is the decision that matters at planning time.
    """
    service_ms = prefill_tokens * prefill_ms_per_token + \
        output_tokens * decode_ms_per_token
    requests_per_s = concurrent * 1000.0 / service_ms
    return {
        "service_ms": service_ms,
        "requests_per_s": requests_per_s,
        "output_tokens_per_s": requests_per_s * output_tokens,
    }


def replicas_needed(target_rps: float, per_replica_rps: float,
                    headroom: float = 0.7) -> int:
    """Replica count for a target load, leaving headroom.

    Never size to 100% utilisation. Queueing delay grows as 1/(1-u): at 90%
    utilisation your wait is 9x the service time, at 95% it is 19x. The tail
    latency you promised disappears long before the fleet is "full". 0.7 is a
    common starting point.
    """
    if not 0 < headroom <= 1:
        raise ValueError("headroom must be in (0, 1]")
    return max(1, math.ceil(target_rps / (per_replica_rps * headroom)))


# ---------------------------------------------------------------------------
# Distributed store
# ---------------------------------------------------------------------------

def quorum_is_strict(n: int, r: int, w: int) -> bool:
    """R + W > N — a read set and a write set must overlap."""
    return r + w > n


def tolerable_failures(n: int, r: int, w: int) -> Dict[str, int]:
    """How many replicas can be down before reads/writes start failing.

    This is the number to put in a capacity review, and the one people get
    wrong: with N=3, R=2, W=2 you survive ONE replica failure, not two. If your
    availability target assumes two, you need N=5.
    """
    return {
        "reads": max(0, n - r),
        "writes": max(0, n - w),
        "either": max(0, min(n - r, n - w)),
    }


def storage_per_node(total_keys: int, bytes_per_key: int, n: int,
                     num_nodes: int, compaction_overhead: float = 1.5) -> float:
    """GiB per node, including replication and compaction headroom.

    Replication multiplies raw data by N. Compaction needs room to write the
    merged output before deleting the inputs — size-tiered can transiently need
    as much as 50% more. A node that fills up stops accepting writes and does
    not recover on its own.
    """
    replicated = total_keys * bytes_per_key * n
    return (replicated * compaction_overhead) / num_nodes / BYTES_PER_GIB


def rebalance_cost(total_keys: int, num_nodes: int, adding: int = 1) -> Dict[str, float]:
    """What joining `adding` nodes moves. Consistent hashing moves ~1/N."""
    after = num_nodes + adding
    fraction = adding / after
    return {
        "fraction_moved": fraction,
        "keys_moved": total_keys * fraction,
        "keys_per_node_before": total_keys / num_nodes,
        "keys_per_node_after": total_keys / after,
    }


# ---------------------------------------------------------------------------
# Known model shapes, for worked examples
# ---------------------------------------------------------------------------

MODELS = {
    #                     layers  kv_heads  head_dim  weights_gib (fp16)
    "Llama-3-8B":         (32,    8,        128,      16.0),
    "Llama-3-70B":        (80,    8,        128,      140.0),
    "Mistral-7B":         (32,    8,        128,      14.5),
    "Qwen2.5-32B":        (64,    8,        128,      65.0),
}

GPUS = {"A100-40GB": 40.0, "A100-80GB": 80.0, "H100-80GB": 80.0, "L40S-48GB": 48.0}


def _demo() -> None:
    print("=== KV cache per token ===")
    print(f"{'model':<16}{'B/token':>10}{'KiB/token':>11}{'32k ctx':>12}")
    for name, (layers, kv_heads, head_dim, _w) in MODELS.items():
        per_token = kv_bytes_per_token(layers, kv_heads, head_dim)
        print(f"{name:<16}{per_token:>10,}{per_token / 1024:>11.0f}"
              f"{per_token * 32768 / BYTES_PER_GIB:>10.1f} GiB")
    print("Using num_heads instead of num_kv_heads would inflate Llama-3-8B by")
    print("4x (32 query heads, 8 KV heads) and size your fleet 4x too large.")

    print("\n=== Fitting Llama-3-8B on one A100-80GB ===")
    layers, kv_heads, head_dim, weights = MODELS["Llama-3-8B"]
    per_token = kv_bytes_per_token(layers, kv_heads, head_dim)
    print(f"{'gpu_mem_util':>13}{'KV GiB':>10}{'@2k ctx':>10}{'@8k':>7}{'@32k':>7}")
    for util in (0.80, 0.90, 0.95, 0.99):
        kv = kv_cache_capacity(80.0, weights, util)
        seqs = [max_concurrent_sequences(kv, per_token, ctx)
                for ctx in (2048, 8192, 32768)]
        print(f"{util:>13.2f}{kv:>10.1f}{seqs[0]:>10}{seqs[1]:>7}{seqs[2]:>7}")
    print("Context length, not the flag, dominates. Going from 2k to 32k costs")
    print("you 16x the batch size — which is why max_model_len is a capacity")
    print("decision, not a feature toggle.")

    print("\n=== Sizing a fleet for 400 req/s ===")
    kv = kv_cache_capacity(80.0, weights, 0.90)
    concurrent = max_concurrent_sequences(kv, per_token, 2048)
    estimate = throughput_estimate(concurrent, output_tokens=200,
                                   prefill_tokens=1800)
    print(f"concurrent sequences per replica: {concurrent}")
    print(f"service time per request:         {estimate['service_ms']:.0f} ms")
    print(f"per-replica throughput:           {estimate['requests_per_s']:.1f} req/s")
    print(f"{'headroom':>10}{'replicas':>10}{'utilisation':>13}{'queue factor':>14}")
    for headroom in (0.5, 0.7, 0.9, 1.0):
        count = replicas_needed(400.0, estimate["requests_per_s"], headroom)
        util = 400.0 / (count * estimate["requests_per_s"])
        factor = util / (1 - util) if util < 1 else float("inf")
        print(f"{headroom:>10.1f}{count:>10}{util:>12.0%}{factor:>13.1f}x")
    print("The queue factor is the multiplier on your waiting time. Sizing to")
    print("100% utilisation is how a fleet that 'has capacity' misses its SLO.")

    print("\n=== Store: what N/R/W actually survives ===")
    print(f"{'N/R/W':>10}{'strict?':>9}{'reads':>8}{'writes':>8}  meaning")
    for n, r, w in [(3, 2, 2), (3, 1, 1), (3, 3, 1), (3, 1, 3), (5, 3, 3), (5, 2, 2)]:
        tolerance = tolerable_failures(n, r, w)
        strict = "yes" if quorum_is_strict(n, r, w) else "NO"
        note = ("survives 1 failure" if tolerance["either"] == 1 else
                f"survives {tolerance['either']} failures")
        print(f"{f'{n}/{r}/{w}':>10}{strict:>9}{tolerance['reads']:>8}"
              f"{tolerance['writes']:>8}  {note}")
    print("N=3 R=2 W=2 survives ONE node loss, not two. If your availability")
    print("target assumes two concurrent failures, you need N=5.")

    print("\n=== Store: disk and rebalancing ===")
    keys, per_key = 500_000_000, 1024
    print(f"{'nodes':>7}{'GiB/node':>11}{'add 1 node moves':>19}")
    for nodes in (6, 12, 24):
        gib = storage_per_node(keys, per_key, n=3, num_nodes=nodes)
        cost = rebalance_cost(keys, nodes)
        print(f"{nodes:>7}{gib:>11.0f}{cost['fraction_moved']:>18.1%}")
    print("Compaction headroom (1.5x here) is not optional: a node that fills")
    print("up stops accepting writes and will not recover on its own.")


if __name__ == "__main__":
    _demo()
