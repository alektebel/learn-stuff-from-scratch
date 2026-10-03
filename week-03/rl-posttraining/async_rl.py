"""Off-policy staleness: how far generation can lag the update.

Xu, "Async GRPO in the Wild"; TRL and OpenInstruct's async paths.

Asynchronous rollout generation makes the samples off-policy by however many
updates the generator is behind. The importance ratio drifts, its variance
grows, and past some lag the estimator stops being usable. Sweeping lag against
ratio variance finds that point -- which is the actual constraint on async
throughput, not the hardware.

TODO(skeleton): write bodies and docstrings.
"""

from typing import List, Sequence


def staleness_ratios(*args, **kwargs) -> List[float]:
    raise NotImplementedError


def effective_sample_size(ratios: Sequence[float]) -> float:
    """(sum r)^2 / sum r^2. Falls as the ratios spread."""
    raise NotImplementedError


def usable_lag(*args, **kwargs) -> int:
    """Largest lag where ESS stays above a threshold."""
    raise NotImplementedError
