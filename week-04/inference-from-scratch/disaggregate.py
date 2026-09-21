"""Prefill and decode are different machines pretending to be one.

Fregly, AI Systems Performance Engineering, ch. 17 and 18; Zhong et al.,
"DistServe" (OSDI 2024); Patel et al., "Splitwise" (ISCA 2024).

    PREFILL   processes the whole prompt at once. Compute-bound, high
              arithmetic intensity, wants big batches and lots of FLOPs.
    DECODE    produces one token at a time against a growing KV cache.
              MEMORY-BANDWIDTH-bound, terrible arithmetic intensity, and
              batching helps it for a completely different reason.

Run them on the same replica and they interfere: a long prefill blocks decode
and every streaming user sees a stall, which is why TTFT and inter-token latency
move in opposite directions when you tune batch size. Disaggregation gives each
phase its own pool, sized independently, and pays for it by shipping the KV
cache across the network between them.

The question this file answers is not "is disaggregation good". It is: **at
what prompt length, batch size and interconnect bandwidth does the KV transfer
cost less than the interference it removes?** That is a crossover, and it moves.

Builds on `scheduler.py` and `paged_kv.py` in this directory.

TODO(skeleton): signatures only. Write the CHECK in check.py first.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple


def prefill_cost(*args, **kwargs) -> float:
    """Compute-bound: roughly quadratic in prompt length. TODO"""
    raise NotImplementedError


def decode_cost(*args, **kwargs) -> float:
    """Memory-bound: per token, and it grows with the KV cache. TODO"""
    raise NotImplementedError


def kv_transfer_cost(*args, **kwargs) -> float:
    """Bytes of KV cache / interconnect bandwidth. The price of disaggregating.

    Compute the bytes exactly: 2 (K and V) x layers x heads x head_dim x
    tokens x dtype_size. Guessing this number is how people conclude
    disaggregation is free.

    TODO
    """
    raise NotImplementedError


def interference_penalty(*args, **kwargs) -> float:
    """What a long prefill costs every decode sharing the replica.

    This is the term disaggregation removes, and the one people forget to
    measure -- so they compare a disaggregated system against a colocated one
    that was never under mixed load.

    TODO
    """
    raise NotImplementedError


def colocated_latency(*args, **kwargs) -> Dict[str, float]:
    """TTFT and inter-token latency with both phases on one replica. TODO"""
    raise NotImplementedError


def disaggregated_latency(*args, **kwargs) -> Dict[str, float]:
    """The same, with separate pools and a KV hop between them. TODO"""
    raise NotImplementedError


def crossover_prompt_length(*args, **kwargs) -> float:
    """Where disaggregation starts winning, given a bandwidth. TODO"""
    raise NotImplementedError


def pool_ratio(*args, **kwargs) -> float:
    """Prefill replicas per decode replica, for a given traffic mix.

    The reason to disaggregate at all: these two numbers should not be equal,
    and cannot be tuned separately while the phases share a machine.

    TODO
    """
    raise NotImplementedError
