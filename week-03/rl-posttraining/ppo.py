"""TRPO's trust region, and the clip that replaced it.

Schulman et al., TRPO (2015) and PPO (2017); Spinning Up; YugeTen, "A Vision
Researcher's Guide to RL".

The clipped objective is ONE-SIDED per sample: it stops the ratio moving
further in the direction that already helped, and does nothing in the other.
Measure the clip fraction as the policy drifts -- that number is the whole
mechanism, and it is the one to log in a real run.

TODO(skeleton): write bodies and docstrings.
"""

from typing import List, Sequence, Tuple


def importance_ratio(new: Sequence[float], old: Sequence[float],
                     action: int) -> float:
    raise NotImplementedError


def clipped_objective(*args, **kwargs) -> float:
    raise NotImplementedError


def clip_fraction(*args, **kwargs) -> float:
    """Share of samples where the clip is active. Log this."""
    raise NotImplementedError


def trust_region_step(*args, **kwargs) -> List[float]:
    """TRPO's constrained step, for comparison against the clip."""
    raise NotImplementedError
