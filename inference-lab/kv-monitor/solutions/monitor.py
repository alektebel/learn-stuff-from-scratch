"""
monitor.py — read a Timeline and say what the cache is doing (solution).

The calculator tells you how many blocks you *have*; this tells you how close
the running server gets to spending them. Three questions matter operationally:

  - how full did the pool get (`peak_utilisation`);
  - how long did it sit above a safe headroom (`steps_above`);
  - what `max_num_seqs` would have avoided preemption on this workload
    (`recommend_max_num_seqs`).

Sources
-------
- vLLM, `gpu_memory_utilization` and the scheduler's preemption path.
- Little's law and queueing: utilisation `u` makes wait grow as `u/(1-u)`, so
  "has capacity" is not the question — headroom is (see `deploy-and-debug`).

DESIGN DECISION — the safe headroom default is 0.9, and it is a parameter.
  At 90% the queueing factor is 9x the service time; at 99% it is 99x. The
  threshold is where an alert should fire *before* the pool is full, so it is
  deliberately below 1.0 and callers may move it.

DESIGN DECISION — the recommendation is the largest cap with zero preemption.
  Preemption is the symptom: it means the block pool, not the concurrency cap,
  became the binding constraint. The largest cap that never preempts on the
  workload spends the pool without thrashing; a smaller cap is just wasted
  concurrency. If even one sequence cannot fit, the answer is 1 (and the fix is
  more blocks, not a smaller cap).
"""

from __future__ import annotations

from typing import Optional, Sequence

from kv import Request, ServingConfig
from simulator import Timeline, simulate


def peak_utilisation(timeline: Timeline) -> float:
    """Highest fraction of the block pool in use at any step (0.0 if empty)."""
    if timeline.total_blocks == 0:
        return 0.0
    return timeline.peak_blocks / timeline.total_blocks


def steps_above(timeline: Timeline, threshold: float = 0.9) -> int:
    """How many steps ran strictly above `threshold` of the pool."""
    if timeline.total_blocks == 0:
        return 0
    return sum(1 for used in timeline.used_blocks
               if used / timeline.total_blocks > threshold)


def recommend_max_num_seqs(requests: Sequence[Request], config: ServingConfig,
                           max_model_len: Optional[int] = None) -> int:
    """Largest concurrency cap that replays `requests` with no preemption.

    Searches from `len(requests)` down. Any cap that completes everything with
    zero preemptions and no OOM qualifies; the largest is returned. Returns 1
    when nothing better can avoid preemption.
    """
    for cap in range(max(len(requests), 1), 0, -1):
        timeline = simulate(requests, config, max_num_seqs=cap, max_model_len=max_model_len)
        if timeline.preemptions == 0 and not timeline.oom and not timeline.rejected:
            return cap
    return 1


if __name__ == "__main__":
    config = ServingConfig(bytes_per_token=4, block_size=4, total_blocks=8)
    reqs = [Request(x, 0, 8, 8) for x in "abc"]
    timeline = simulate(reqs, config)
    print("monitor — three 8->16 token requests against 8 blocks of 4 tokens")
    print(f"  peak utilisation: {peak_utilisation(timeline):.0%}")
    print(f"  steps above 90%:  {steps_above(timeline, 0.9)} of {timeline.steps}")
    print(f"  preemptions:      {timeline.preemptions}")
    cap = recommend_max_num_seqs(reqs, config)
    ok = simulate(reqs, config, max_num_seqs=cap)
    print(f"  recommended max_num_seqs: {cap} "
          f"(preemptions there: {ok.preemptions})")
