"""Baselines cut variance without moving the mean -- and which ones do not.

Spinning Up "Extra Material"; Weng; Sutton & Barto ch. 13.4.

Subtracting b(s) from the return leaves the estimator UNBIASED because
E[grad log pi] = 0. Subtracting anything that depends on the ACTION does not,
and the bias is easy to introduce by accident.

TODO(skeleton): write bodies and docstrings.
"""

from typing import List, Sequence


def constant_baseline(*args, **kwargs) -> float:
    """Mean return over the batch."""
    raise NotImplementedError


def state_baseline(*args, **kwargs) -> List[float]:
    """Per-state mean return. Still unbiased."""
    raise NotImplementedError


def action_baseline(*args, **kwargs) -> List[float]:
    """Depends on the action taken. BIASED -- included so it can be measured."""
    raise NotImplementedError


def estimator_variance(samples: Sequence[Sequence[float]]) -> float:
    """Mean per-coordinate variance of a set of gradient samples."""
    raise NotImplementedError
