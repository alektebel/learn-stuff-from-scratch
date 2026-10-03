"""
Step 11 — Now read the engines
==============================
Only after steps 1–10. Compare their design decisions with yours.

Return a dict keyed by "yours", "vllm", "sglang", "tensorrt_llm".
Each value MUST contain exactly these keys, with values from the
allowed sets:

  kv              "none" | "contiguous" | "paged" | "radix"
  batching        "static" | "continuous" | "continuous+radix"
  scheduler       "fcfs" | "priority" | "priority+preempt"
  graphs          "no" | "decode" | "decode+prefill"
  speculate       "no" | "draft-target" | "mtp" | "eagle"
  disaggregation  "no" | "optional" | "first-class"

The allowed answers for the three engines are the ones in their
published designs as of 2026, not a guess:

  vllm          paged, continuous, priority+preempt, decode, draft-target, optional
  sglang        radix, continuous+radix, priority, decode, eagle, optional
  tensorrt_llm  paged, continuous, priority, decode+prefill, draft-target, first-class

"yours" must describe what YOU built in this directory (paged,
continuous, priority, decode, draft-target, no) if you followed the
steps. If you skipped paging, say contiguous — do not claim paged.
"""

from typing import Dict


def engine_choices() -> Dict[str, Dict[str, str]]:
    raise NotImplementedError
