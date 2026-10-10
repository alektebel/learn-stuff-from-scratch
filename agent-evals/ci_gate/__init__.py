"""ci_gate — agent-evals #4: a regression gate that blocks on signal, not on noise.

Re-exports the public interface so that ``import ci_gate`` and ``python -m ci_gate`` work.
"""

from .ci_gate import (
    GateConfig,
    Verdict,
    evaluate,
    main,
    median,
    newcombe,
    read_jsonl,
    wilson,
)

__all__ = [
    "GateConfig",
    "Verdict",
    "evaluate",
    "main",
    "median",
    "newcombe",
    "read_jsonl",
    "wilson",
]
