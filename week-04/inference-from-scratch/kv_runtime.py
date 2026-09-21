"""
Step 4 — KV caching, then the bandwidth bound
=============================================
context-caching/ already built the data structure. This file measures
why decode *becomes* memory-bandwidth bound once you have it.

Without a cache, each decode step recomputes the prefix: FLOPs grow with
length, intensity stays high, you look compute-bound and you are wasting
work.

With a cache, each decode step reads K,V of the prefix: bytes grow with
length, FLOPs stay about constant, intensity falls under the ridge
(200 FLOP/byte on ToyGPU), and you are bandwidth-bound.

That is not a slogan. `bound_of` must return "bandwidth" for a cached
decode of a long prefix and "compute" for a prefill of the same length.
"""

from typing import Dict

from toy_gpu import RIDGE, ToyGPU


def run_decode(cached_len: int, use_kv: bool) -> ToyGPU:
    """TODO: trace("decode", prompt_len=0, cached_len=cached_len, use_kv=use_kv)
    and return the gpu.
    """
    raise NotImplementedError


def bound_of(gpu: ToyGPU) -> str:
    """TODO: gpu.bound  (or recompute flops/bytes vs RIDGE).
    Return "bandwidth" or "compute".
    """
    raise NotImplementedError


def why_decode_is_bandwidth_bound(cached_len: int) -> Dict[str, float]:
    """Compare cached vs uncached decode at this length.

    TODO return:
      intensity_cached
      intensity_uncached
      ridge                 (the ToyGPU RIDGE constant)
      cached_bound          1.0 if bandwidth else 0.0
    The checker asserts intensity_cached < ridge < intensity_uncached
    at a long prefix (256).
    """
    raise NotImplementedError
