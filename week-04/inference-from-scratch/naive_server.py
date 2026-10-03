"""
Step 2 — A naive inference server
=================================
One GPU, one request at a time, generate the whole completion before
accepting the next. Make it work. Then watch two overlapping requests
fall apart.

DESIGN DECISION — why write the dumb one first?
  Continuous batching, paging, and a scheduler are solutions to failures
  this file is about to produce. If you start with vLLM you never feel
  the failure, and the machinery looks like taste.

A Request is {id, prompt_len, max_new, priority?}.
`generate(request)` runs prefill then decode on a fresh ToyGPU and
returns {id, tokens, gpu}.

`serve(requests, concurrent=False)`:
  concurrent=False — sequential, works.
  concurrent=True  — the naive server's lie: it still has one GPU and
  pretends it can run two generates at once. Return a result dict with
  ok=False and reason="single_flight" (or raise the same idea). The
  checker wants a *named* failure, not a silent interleaving of tokens.
"""

from typing import Dict, List, Sequence

from toy_gpu import ToyGPU


def generate(request: Dict) -> Dict:
    """TODO: prefill then max_new decode steps, no KV cache (use_kv=False).
    Return {"id": ..., "tokens": max_new, "gpu": ToyGPU}.
    Import trace from inference_path and accumulate onto ONE gpu
    (do not reset between tokens — the ledger is the request).
    """
    raise NotImplementedError


def serve(requests: Sequence[Dict], concurrent: bool = False) -> Dict:
    """TODO.
    sequential: {"ok": True, "results": [generate(r) for r in requests]}
    concurrent: {"ok": False, "reason": "single_flight"}
      if len(requests) > 1, else the sequential path.

    "single_flight" is the name of the constraint. A server that silently
    concatenates two prompts onto one GPU has not failed honestly.
    """
    raise NotImplementedError
