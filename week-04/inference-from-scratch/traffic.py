"""
Step 10 — Real concurrent traffic
=================================
Throw N overlapping requests at the continuous batcher and find the
concurrency where throughput stops scaling.

On this GPU the knee is not mysterious: once running == max_batch and
waiting is growing, extra concurrency adds queue time, not tokens/tick.
`throughput_curve(conc_list)` returns one point per concurrency, and
`knee(curve)` is the first concurrency where the next point's throughput
grows by less than 5%.

The *reason* must be one of:
  "batch_full"     — max_batch is the cap
  "kv_full"        — the paged pool cannot admit the next request
  "still_scaling"  — no knee in the measured range

TODO:
  run_load(n, max_batch, kv_blocks, prompt_len, max_new) -> metrics dict
  throughput_curve(ns, ...) -> [{n, throughput, ttft, reason_local}]
  knee(curve) -> {n, reason}
"""

from typing import Dict, List, Sequence


def run_load(n: int, max_batch: int, kv_blocks: int,
             prompt_len: int = 16, max_new: int = 8) -> Dict:
    """Admit n identical requests. Use Scheduler + PagedKV.

    A request needs ceil((prompt_len+max_new) / block_size) blocks
    (block_size=16). If admit() fails or can_allocate is False, that
    request is rejected.

    Return {
      admitted, rejected, throughput, ttft, reason
    }
    reason is "kv_full" if any rejection was from the pager,
    "batch_full" if waiting grew because running hit max_batch,
    "ok" otherwise.
    throughput = admitted * max_new / max(1, n)   # a stand-in the
    checker only uses relatively — keep it monotone in admitted.
    """
    raise NotImplementedError


def throughput_curve(ns: Sequence[int], max_batch: int,
                     kv_blocks: int) -> List[Dict]:
    """TODO: [run_load(n, max_batch, kv_blocks) | {n: n} merged] for n in ns"""
    raise NotImplementedError


def knee(curve: Sequence[Dict]) -> Dict:
    """First n where the next point's throughput / this throughput < 1.05.

    reason comes from the NEXT point (what stopped the scale).
    If every step grows by >= 5%, reason is "still_scaling" and n is
    the last measured concurrency.
    """
    raise NotImplementedError
