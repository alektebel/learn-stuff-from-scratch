"""Proxy reward rising while true reward falls, and what the KL budget buys.

The RLHF Book (rlhfbook.com), ch. on over-optimisation; Gao et al. scaling laws
for reward-model over-optimisation.

Give the optimiser a deliberately gameable proxy and measure both curves. The
KL coefficient is the knob that trades them, and it is the same axis as
forward-versus-reverse KL in `llm-from-scratch/distill.py`, reached from the
other side.

TODO(skeleton): write bodies and docstrings.
"""

from typing import List, Sequence, Tuple


def gameable_reward(*args, **kwargs) -> List[float]:
    """A proxy that agrees with the true reward except on one exploitable axis."""
    raise NotImplementedError


def optimise_against_proxy(*args, **kwargs) -> List[Tuple[float, float, float]]:
    """(kl_from_reference, proxy_reward, true_reward) along the optimisation."""
    raise NotImplementedError


def overoptimisation_point(*args, **kwargs) -> float:
    """KL at which the true reward turns over."""
    raise NotImplementedError
