"""
Step 7 — Optimising the GPU path
================================
Four knobs, one lesson each.

1. CUDA graphs  — record a decode step, replay it. launches stay the same
                  on record; replay does not add launches. The win is the
                  CPU launch overhead, which ToyGPU models as a sync.
2. Fusion       — one kernel for qkv+attn+mlp instead of three. launches
                  drop; bytes_moved must not grow (fusion that re-reads
                  is not fusion).
3. Quantization — bytes_moved scales with the type. int8 is 0.5x fp16
                  in this ledger (BYTES_PER_ELEMENT = 2).
4. Host sync    — synchronize() once per request, not once per kernel.
                  A decode step with 5 kernels and 5 syncs is the naive
                  path; 5 kernels and 1 sync is the graph-shaped path.

TODO: the four functions below. All operate on a ToyGPU you are given
or create.
"""

from typing import Dict, List

from toy_gpu import BYTES_PER_ELEMENT, ToyGPU


def record_and_replay(record_fn, n_replay: int) -> ToyGPU:
    """Call record_fn(gpu) once, then 'replay' n_replay times.

    TODO: replay means: do NOT call record_fn again. Copy the event
    list (without flipping synced) n_replay times onto the same gpu,
    or increment a replay counter the checker can read as
    gpu.launches == launches_after_record  (replay adds no launches)
    AND a attribute gpu.replays == n_replay.

    Set gpu.replays. The checker reads it.
    """
    raise NotImplementedError


def fused_decode(gpu: ToyGPU, cached_len: int) -> None:
    """TODO: a SINGLE launch named "fused_decode" whose flops and bytes
    equal decode_cost(cached_len, use_kv=True).
    """
    raise NotImplementedError


def quantize_bytes(fp16_bytes: int, dtype: str) -> int:
    """TODO: fp16 -> fp16_bytes; int8 -> fp16_bytes // 2; int4 -> // 4.
    Raise ValueError on an unknown dtype.
    """
    raise NotImplementedError


def decode_with_sync_policy(n_kernels: int, policy: str) -> ToyGPU:
    """Launch n_kernels dummy kernels (1 flop, 1 byte each).

    policy "per_kernel": synchronize after every launch
    policy "per_step":   synchronize once at the end
    The checker asserts syncs == n_kernels vs syncs == 1.
    """
    raise NotImplementedError
