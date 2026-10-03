"""PROVIDED — a tiny environment so every file here runs on a CPU in seconds.

Nothing in this directory needs a model, a GPU, or a download. The mechanisms
being measured are properties of the ESTIMATORS, not of any policy worth
deploying, and a real model would only add noise to the measurement.

A "policy" here is a categorical distribution over tokens per state. A
"trajectory" is a short sequence of them. That is enough to reproduce every
result in the reading list this directory is built from.

TODO(skeleton): fill in. Deterministic, seedable, no dependencies.
"""

import random
from typing import Dict, List, Optional, Sequence, Tuple

Policy = List[List[float]]


def make_policy(states: int, actions: int, seed: int = 0) -> Policy:
    """A random categorical policy, one row per state."""
    raise NotImplementedError


def rollout(policy: Policy, length: int, rng: random.Random) -> List[Tuple[int, int]]:
    """Sample (state, action) pairs."""
    raise NotImplementedError


def episode_return(trajectory: Sequence[Tuple[int, int]],
                   reward: Sequence[Sequence[float]]) -> float:
    """Total reward for one trajectory. Terminal and sparse by default."""
    raise NotImplementedError
