"""
Step 3 — Batching
=================
Static batching: wait until B requests arrive, run them together, no one
leaves until the longest finishes. Short requests pay the long request's
decode time. That is the failure continuous batching exists to fix.

Continuous batching: at every decode step, finished sequences drop out
and waiting sequences (after their own prefill) join. The batch size is
not a constant.

Metrics, measured in ToyGPU ticks after a synchronize():
  TTFT  — time to first token (prefill done)
  TPOT  — time per output token after that (mean inter-token)
  throughput — total output tokens / wall time

TODO:
  static_batch(requests) -> {results, wasted_decode_steps}
  continuous_batch(requests) -> {results, join_events}
  metrics(timeline) -> {ttft, tpot, throughput}
"""

from typing import Dict, List, Sequence


def static_batch(requests: Sequence[Dict]) -> Dict:
    """Pad every request to max(max_new). 

    wasted_decode_steps = sum(max_len - r['max_new'] for r in requests)
    That number is the tax. Continuous batching's job is to drive it to 0.

    results: one entry per request, {"id", "tokens"} with tokens=max_new.
    """
    raise NotImplementedError


def continuous_batch(requests: Sequence[Dict]) -> Dict:
    """Decode step by step. A request with max_new=T leaves at step T,
    and a request that has finished prefill may join on that same step.

    Assume each request's prefill takes 1 step and is done before decode
    of that request starts. Process in id order for determinism.

    join_events: list of {step, joined_id} every time a request starts
    decoding after step 0. If everyone starts together this is empty —
    that is static batching in disguise.
    """
    raise NotImplementedError


def metrics(ttft_ticks: Sequence[float],
            itl_ticks: Sequence[float],
            output_tokens: int,
            wall_ticks: float) -> Dict[str, float]:
    """TODO:
      ttft       = mean(ttft_ticks)
      tpot       = mean(itl_ticks)          # ITL == inter-token latency == TPOT
      throughput = output_tokens / wall_ticks
    Empty itl_ticks -> tpot 0.0. wall_ticks==0 -> throughput 0.0.
    """
    raise NotImplementedError
