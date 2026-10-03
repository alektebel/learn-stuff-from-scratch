"""The identity everything else is a variance argument about.

    grad E_pi[R]  =  E_pi[ R * grad log pi ]

Sutton & Barto ch. 13; Spinning Up "Intro to Policy Optimization"; Weng,
"Policy Gradient Algorithms".

The whole of the rest of this directory is people trying to estimate the right
hand side with fewer samples. Verify it against a finite-difference gradient
first, because every later claim assumes it.

TODO(skeleton): write bodies and docstrings.
"""

from typing import Callable, List, Sequence


def log_prob_gradient(probabilities: Sequence[float], action: int) -> List[float]:
    """d log pi(a) / d logits. Equals onehot(a) - pi."""
    raise NotImplementedError


def reinforce_estimator(*args, **kwargs) -> List[float]:
    """One Monte Carlo sample of R * grad log pi over a trajectory."""
    raise NotImplementedError


def exact_gradient(*args, **kwargs) -> List[float]:
    """The true gradient, by enumerating a small state space."""
    raise NotImplementedError


def finite_difference(f: Callable[[List[float]], float],
                      values: Sequence[float], epsilon: float = 1e-5) -> List[float]:
    """Central differences, for checking the identity holds."""
    raise NotImplementedError
