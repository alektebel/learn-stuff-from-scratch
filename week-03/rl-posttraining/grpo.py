"""GRPO, and the two normalisations Dr. GRPO removes.

DeepSeekMath / DeepSeek-R1 (GRPO); Lan, "From REINFORCE to Dr. GRPO".

GRPO replaces the value network with a GROUP-RELATIVE baseline: sample a group
of responses to the same prompt, use the group mean as the baseline. No critic,
no GAE, no second model to train.

Dr. GRPO's correction: dividing by the group's standard deviation and by
response length each introduce a bias. Measure the length bias, remove the
terms, measure it gone.

TODO(skeleton): write bodies and docstrings.
"""

from typing import List, Sequence


def group_advantage(returns: Sequence[float], normalise_std: bool = True
                    ) -> List[float]:
    raise NotImplementedError


def grpo_objective(*args, **kwargs) -> float:
    raise NotImplementedError


def length_bias(*args, **kwargs) -> float:
    """Correlation between response length and advantage. Should be ~0."""
    raise NotImplementedError
