"""k1, k2, k3 -- Schulman, "Approximating KL Divergence" (joschu.net).

With r = q(x)/p(x) sampled from q:

    k1 = -log r          unbiased, high variance, GOES NEGATIVE
    k2 = 0.5 (log r)^2   low variance, BIASED
    k3 = r - 1 - log r   unbiased AND non-negative

k3 is the one in every modern implementation and this is why. Three lines, and
it settles an argument people keep having.

TODO(skeleton): write bodies and docstrings.
"""

from typing import List, Sequence


def k1(*args, **kwargs) -> float:
    raise NotImplementedError


def k2(*args, **kwargs) -> float:
    raise NotImplementedError


def k3(*args, **kwargs) -> float:
    raise NotImplementedError


def estimator_report(*args, **kwargs) -> dict:
    """Bias, variance, and the fraction of samples below zero, for each."""
    raise NotImplementedError
