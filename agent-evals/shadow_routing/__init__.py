"""shadow_routing — agent-evals #2: mirror a slice of traffic to a second model.

Re-exports the public interface so that ``import shadow_routing`` and
``python -m shadow_routing`` both work.
"""

from .shadow_routing import (
    Comparison,
    ShadowConfig,
    compare,
    is_sampled,
    main,
    sampled_ids,
    shadow_run,
)

__all__ = [
    "Comparison",
    "ShadowConfig",
    "compare",
    "is_sampled",
    "main",
    "sampled_ids",
    "shadow_run",
]
