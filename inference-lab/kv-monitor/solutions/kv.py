"""
kv.py — KV cache arithmetic and the data model (provided; do not edit).

This is the calculator half of inference-lab project #3. It is the same
arithmetic as `deploy-and-debug/capacity.py` (`kv_bytes_per_token`,
`kv_cache_capacity`), restated here so the module stands alone; the new work of
#3 is the *monitor* built on top.

Sources
-------
- Kwon et al., "Efficient Memory Management for Large Language Model Serving
  with PagedAttention" (SOSP 2023): KV cache is allocated in fixed-size
  *blocks*, so memory is reserved a whole block at a time and a sequence's last
  partial block is wasted. `block_size` is the tokens per block.
- vLLM, engine arguments: `gpu_memory_utilization` is the fraction of the card
  the server may claim; `max_num_seqs` caps concurrent sequences; when the
  block pool is exhausted the scheduler *preempts* sequences rather than
  crashing. Those three knobs are what this module monitors.

DESIGN DECISION — KV is sized with the number of KV heads, not query heads.
  Llama-3-8B has 32 query heads and 8 KV heads (grouped-query attention); using
  the query count sizes the cache 4x too large. bytes_per_token = 2 (K and V) x
  layers x kv_heads x head_dim x dtype_bytes.

DESIGN DECISION — the simulation works in blocks, not bytes.
  A serving stack admits and evicts whole blocks, so utilisation is
  used_blocks / total_blocks. Working in bytes would hide the paging waste a
  block monitor exists to expose. `ServingConfig` therefore carries
  `total_blocks`, and `config_from_gpu` is the only place that converts a card's
  GiB into blocks.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

BYTES_PER_GIB = 1024 ** 3


@dataclass(frozen=True)
class ModelSpec:
    """The architecture facts a KV size depends on."""

    name: str
    num_layers: int
    num_kv_heads: int
    head_dim: int
    dtype_bytes: int = 2  # fp16


def bytes_per_token(spec: ModelSpec) -> int:
    """Bytes of KV cache one token occupies, across every layer.

    2 (K and V) x layers x kv_heads x head_dim x dtype_bytes. Uses
    `num_kv_heads`: with GQA the query-head count is often 4x larger.
    """
    return 2 * spec.num_layers * spec.num_kv_heads * spec.head_dim * spec.dtype_bytes


@dataclass(frozen=True)
class ServingConfig:
    """Everything the simulation needs: a block size and how many blocks exist."""

    bytes_per_token: int
    block_size: int
    total_blocks: int

    @property
    def block_bytes(self) -> int:
        return self.block_size * self.bytes_per_token


def config_from_gpu(spec: ModelSpec, total_gpu_gib: float, weights_gib: float,
                    gpu_memory_utilization: float = 0.90, activation_gib: float = 2.0,
                    block_size: int = 16) -> ServingConfig:
    """Turn a card's memory into a block budget (the `capacity.py` arithmetic).

    KV GiB = (total x gpu_memory_utilization) - weights - activations, floored
    at 0; blocks = floor(KV bytes / block bytes). `gpu_memory_utilization`
    below 1.0 leaves room for fragmentation and the CUDA context; push it to
    0.99 and you trade cache for OOM crashes on load spikes.
    """
    kv_gib = max(0.0, total_gpu_gib * gpu_memory_utilization - weights_gib - activation_gib)
    kv_bytes = int(math.floor(kv_gib * BYTES_PER_GIB))
    per_block = block_size * bytes_per_token(spec)
    return ServingConfig(bytes_per_token(spec), block_size, kv_bytes // per_block)


@dataclass(frozen=True)
class Request:
    """One arrival in the trace.

    `arrive` is the step the request shows up. `prompt_tokens` are prefilled at
    admission; `output_tokens` are then generated one per step. A request's
    lifetime peak is `prompt_tokens + output_tokens` tokens.
    """

    id: str
    arrive: int
    prompt_tokens: int
    output_tokens: int

    @property
    def final_len(self) -> int:
        return self.prompt_tokens + self.output_tokens


# A few models, so a reader can check a real number by hand.
MODELS = {
    "Llama-3-8B": ModelSpec("Llama-3-8B", 32, 8, 128),
    "Llama-3-70B": ModelSpec("Llama-3-70B", 80, 8, 128),
    "Mistral-7B": ModelSpec("Mistral-7B", 32, 8, 128),
    "Qwen2.5-32B": ModelSpec("Qwen2.5-32B", 64, 8, 128),
}


if __name__ == "__main__":
    spec = MODELS["Llama-3-8B"]
    bpt = bytes_per_token(spec)
    print("KV cache arithmetic — Llama-3-8B")
    print(f"  bytes per token: {bpt:,} ({bpt / 1024:.0f} KiB)")
    print(f"  one 16-token block: {bpt * 16 / 1024**2:.1f} MiB")
    cfg = config_from_gpu(spec, 80.0, 16.0)  # A100-80GB, fp16 weights, util 0.90
    print(f"  A100-80GB at util 0.90: {cfg.total_blocks} blocks "
          f"= {cfg.total_blocks * cfg.block_bytes / BYTES_PER_GIB:.1f} GiB of KV")
    print(f"  a 32k-token sequence needs {math.ceil(32768 / cfg.block_size)} blocks")
