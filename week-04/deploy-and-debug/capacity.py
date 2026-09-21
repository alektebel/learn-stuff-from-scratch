"""
Step 1 — Capacity planning
===========================
Effort: small. Pure arithmetic — and the arithmetic that decides whether your
deployment works before you ever start it.

What you build:
  kv_bytes_per_token / kv_cache_capacity / max_concurrent_sequences
  throughput_estimate / replicas_needed
  quorum_is_strict / tolerable_failures / storage_per_node / rebalance_cost

Background:
  Every number here goes into a config file or a capacity review. Getting one
  wrong by 4x is easy and expensive:

    KV per token = 2 x layers x KV_HEADS x head_dim x dtype_bytes

  Note KV_heads, not query heads. Llama-3-8B has 32 query heads and 8 KV heads
  (grouped-query attention). Use the wrong one and you size the fleet 4x too
  large.

  And the two facts that surprise people:
    - max_model_len is a capacity decision. 2k -> 32k context costs 16x batch.
    - N=3, R=2, W=2 survives ONE node loss, not two.
"""

import math
from typing import Dict, List, Optional

BYTES_PER_GIB = 1024 ** 3


def kv_bytes_per_token(num_layers: int, num_kv_heads: int, head_dim: int,
                       dtype_bytes: int = 2) -> int:
    """TODO: 2 (K and V) x layers x kv_heads x head_dim x dtype_bytes.

    Use num_kv_heads. With GQA the query-head count is often 4x larger.
    """
    raise NotImplementedError


def kv_cache_capacity(total_gpu_gib: float, weights_gib: float,
                      gpu_memory_utilization: float = 0.90,
                      activation_gib: float = 2.0) -> float:
    """GiB left for KV after weights, activations and headroom.

    TODO: (total x gpu_memory_utilization) - weights - activations, floored at 0.

    gpu_memory_utilization is vLLM's flag: the fraction of the card the server
    may claim. The remainder absorbs fragmentation and the CUDA context. Push
    it to 0.99 and you trade cache size for OOM crashes on load spikes.
    """
    raise NotImplementedError


def max_concurrent_sequences(kv_gib: float, bytes_per_token: int,
                             avg_context_tokens: int) -> int:
    """TODO: floor(kv_bytes / (bytes_per_token * avg_context_tokens)).

    Raise ValueError on a non-positive context length.

    Size against the AVERAGE context, not max_model_len — but leave headroom.
    Sizing against max_model_len over-provisions massively; sizing against the
    average with no headroom is the classic OOM.
    """
    raise NotImplementedError


def throughput_estimate(concurrent: int, output_tokens: int,
                        prefill_tokens: int, prefill_ms_per_token: float = 0.09,
                        decode_ms_per_token: float = 7.5) -> Dict[str, float]:
    """TODO: service_ms from prefill + decode, then
    requests_per_s = concurrent * 1000 / service_ms, and output tokens/s.

    Crude on purpose. Its job is to tell you whether you are within 2x of the
    target, which is the decision capacity planning actually makes.
    """
    raise NotImplementedError


def replicas_needed(target_rps: float, per_replica_rps: float,
                    headroom: float = 0.7) -> int:
    """TODO: ceil(target / (per_replica * headroom)), at least 1. Validate headroom.

    Never size to 100%. Queueing delay grows as u/(1-u): at 90% utilisation you
    wait 9x the service time, at 99% you wait 99x. Your tail latency is gone
    long before the fleet is "full".
    """
    raise NotImplementedError


def quorum_is_strict(n: int, r: int, w: int) -> bool:
    """TODO: R + W > N."""
    raise NotImplementedError


def tolerable_failures(n: int, r: int, w: int) -> Dict[str, int]:
    """TODO: return {"reads": n-r, "writes": n-w, "either": min of the two},
    each floored at 0.

    Put this number in the capacity review. N=3 R=2 W=2 survives ONE failure.
    If your availability target assumes two concurrent failures, you need N=5.
    """
    raise NotImplementedError


def storage_per_node(total_keys: int, bytes_per_key: int, n: int,
                     num_nodes: int, compaction_overhead: float = 1.5) -> float:
    """TODO: keys x bytes x N x compaction_overhead / num_nodes, in GiB.

    Compaction needs room to write merged output before deleting inputs. A node
    that fills up stops accepting writes and does not recover on its own.
    """
    raise NotImplementedError


def rebalance_cost(total_keys: int, num_nodes: int,
                   adding: int = 1) -> Dict[str, float]:
    """TODO: fraction moved = adding / (num_nodes + adding); also return
    keys_moved and keys per node before and after."""
    raise NotImplementedError


MODELS = {
    #                     layers  kv_heads  head_dim  weights_gib (fp16)
    "Llama-3-8B":         (32,    8,        128,      16.0),
    "Llama-3-70B":        (80,    8,        128,      140.0),
    "Mistral-7B":         (32,    8,        128,      14.5),
    "Qwen2.5-32B":        (64,    8,        128,      65.0),
}

GPUS = {"A100-40GB": 40.0, "A100-80GB": 80.0, "H100-80GB": 80.0, "L40S-48GB": 48.0}


def _demo() -> None:
    """Once implemented, produce and sanity-check:

    1. KV per token: Llama-3-8B = 131,072 bytes (128 KiB), so a 32k context is
       4.0 GiB for ONE sequence.
    2. Llama-3-8B on an A100-80GB at util 0.90 leaves ~54 GiB of KV: 216
       concurrent sequences at 2k context, but only 13 at 32k. Sixteen times
       fewer, from one config value.
    3. Sizing for 400 req/s: at 0.7 headroom you need 5 replicas (62%
       utilisation, 1.6x queue factor); at 1.0 headroom, 4 replicas at 77% and
       a 3.3x queue factor. The second is how a fleet that "has capacity"
       misses its SLO.
    4. The N/R/W table. Confirm 3/2/2 survives exactly one failure.
    """
    raise NotImplementedError


if __name__ == "__main__":
    _demo()
