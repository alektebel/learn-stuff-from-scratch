"""simulated_service — agent-evals: the shared synthetic production double for #2, #9, #10.

Re-exports the public interface so that ``import simulated_service`` and
``python -m simulated_service`` both work.
"""

from .simulated_service import (
    CATEGORIES,
    MODELS,
    TENANTS,
    Drift,
    ModelConfig,
    Request,
    Response,
    SimulatedService,
    main,
    read_jsonl,
    success_rate,
    totals,
    write_jsonl,
)

__all__ = [
    "CATEGORIES",
    "MODELS",
    "TENANTS",
    "Drift",
    "ModelConfig",
    "Request",
    "Response",
    "SimulatedService",
    "main",
    "read_jsonl",
    "success_rate",
    "totals",
    "write_jsonl",
]
