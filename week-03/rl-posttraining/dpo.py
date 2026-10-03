"""The identity that lets you skip the reward model.

Rafailov et al., DPO (2023); the RLHF Book's derivation.

    pi*(y|x)  =  pi_ref(y|x) exp(r(x,y)/beta) / Z(x)

is the optimum of `maximise E[r] - beta KL(pi || pi_ref)`. Invert it:

    r(x,y)  =  beta log( pi*(y|x) / pi_ref(y|x) )  +  beta log Z(x)

so any policy IS an implicit reward model, up to a per-prompt constant that
cancels in a pairwise comparison. Round-trip it and the derivation is verified.

Then the part the identity does not give you: DPO's preference data is
off-policy by construction, and `llm-from-scratch/distill.py` already measured
what off-policy costs. Measure it here too.

TODO(skeleton): write bodies and docstrings.
"""

from typing import List, Sequence


def kl_regularised_optimum(reference: Sequence[float], reward: Sequence[float],
                           beta: float) -> List[float]:
    raise NotImplementedError


def implicit_reward(policy: Sequence[float], reference: Sequence[float],
                    beta: float) -> List[float]:
    """Recovers the reward up to one additive constant per prompt."""
    raise NotImplementedError


def pairwise_margin(*args, **kwargs) -> float:
    """The constant cancels here. That is why DPO never fits Z."""
    raise NotImplementedError


def dpo_loss(*args, **kwargs) -> float:
    raise NotImplementedError
