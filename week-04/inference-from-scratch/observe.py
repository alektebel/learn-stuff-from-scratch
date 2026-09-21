"""
Step 9 — Observability
======================
A request you cannot measure is a request you cannot tune.

Required fields on a finished RequestTrace:
  ttft          ticks until first output token
  itl           list of inter-token latencies (length = tokens - 1)
  tpot          mean(itl) or 0
  throughput    tokens / wall
  gpu_util      ToyGPU.util after the final sync
  kv_used       tokens stored in the paged cache for this request
  kv_capacity   tokens the pool can hold
  queue_time    ticks spent waiting before prefill started

`trace_request` builds one from a schedule: {queue_time, prefill_ticks,
decode_ticks: [t0, t1, ...], kv_used, kv_capacity, gpu}.
t0 is TTFT's decode half; ttft = queue_time + prefill_ticks + t0.
"""

from typing import Dict, List, Sequence


def summarise(trace: Dict) -> Dict[str, float]:
    """TODO: compute ttft, tpot, throughput, gpu_util, kv_used,
    kv_capacity, queue_time, itl_p50, itl_p95 from the raw trace.

    itl is trace["decode_ticks"][1:]  (the first decode tick is part of TTFT)
    p50 / p95: sort, index at 0.50 / 0.95 * (n-1), nearest.
    Empty itl -> p50=p95=tpot=0.
    """
    raise NotImplementedError


def trace_request(schedule: Dict) -> Dict:
    """TODO: attach the summarised metrics onto a copy of schedule
    under schedule["metrics"] = summarise(...). Return it.
    Also keep the raw fields so a dashboard can plot ITL.
    """
    raise NotImplementedError
