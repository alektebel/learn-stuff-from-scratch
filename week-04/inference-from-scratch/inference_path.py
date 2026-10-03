"""
Step 1 — The inference path
===========================
Know what happens on the GPU for every token, before you write a server.

Prefill (the prompt): one forward over all prompt tokens. Attention is
quadratic. No cache yet, or the cache is being *filled*.

Decode (each new token): one forward over a single token. With a KV cache
you do not recompute K,V for the prefix; you read them. That read is why
decode is memory-bandwidth bound — step 4 measures it.

TODO: trace(kind, prompt_len, cached_len, use_kv) launches the named
kernels on a ToyGPU and returns the gpu. The checker looks at event names
and at whether decode-with-cache skipped the quadratic attention.
"""

from typing import List

from toy_gpu import ToyGPU, decode_cost, prefill_cost


PREFILL_KERNELS: List[str] = [
    "embed", "qkv", "attn", "mlp", "lm_head",
]
DECODE_KERNELS: List[str] = [
    "embed", "qkv", "attn_cached", "mlp", "lm_head",
]


def trace(kind: str, prompt_len: int, cached_len: int = 0,
          use_kv: bool = False) -> ToyGPU:
    """Launch the kernels for one prefill or one decode step.

    kind is "prefill" or "decode".
    For prefill: launch PREFILL_KERNELS, costing prefill_cost(prompt_len)
      split however you like across the five names; total flops and bytes
      must match prefill_cost.
    For decode: launch DECODE_KERNELS if use_kv else PREFILL_KERNELS
      (without a cache, decode IS a prefill of cached_len+1).
      Totals must match decode_cost(cached_len, use_kv).

    Do not call synchronize() here. A path that syncs after every kernel
    is the thing step 7 is going to stop doing.
    """
    raise NotImplementedError


def kernel_names(gpu: ToyGPU) -> List[str]:
    """TODO: [e.name for e in gpu.events]"""
    raise NotImplementedError
