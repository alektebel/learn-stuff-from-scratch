"""
Phase 0 template — implement REINFORCE, then add the GRPO group baseline.

Read `guidelines.md` first. Fill in the TODOs. Check your work with:

    python test_phase0.py

Stuck on one? `HINTS.md` has three escalating levels per function.
Pure stdlib — no imports beyond math/random needed.
"""
from __future__ import annotations

import math
import random

# Task setup: 3 prompts, 4 actions each, exactly one correct action per prompt.
CORRECT = [1, 3, 0]
N_PROMPTS = 3
N_ACTIONS = 4
GROUP_SIZE = 8


class SoftmaxPolicy:
    """A tabular softmax policy: one row of logits per prompt."""

    def __init__(self, n_prompts: int, n_actions: int, lr: float = 0.5):
        self.n_prompts, self.n_actions, self.lr = n_prompts, n_actions, lr
        self.logits = [[0.0] * n_actions for _ in range(n_prompts)]

    def probs(self, p: int) -> list[float]:
        """Return the action distribution for prompt `p`.

        Requirements: length n_actions, all entries >= 0, sums to 1.0, and
        numerically stable for large logits (subtract the max first!).
        """
        # TODO: numerically-stable softmax over self.logits[p]
        raise NotImplementedError

    def sample(self, p: int, rng: random.Random) -> int:
        """Sample an action index from probs(p) using `rng`."""
        # TODO: inverse-CDF sampling. Draw rng.random(), accumulate probs until
        #       the running total >= u, return that index. Return the last index
        #       as a fallback so float error can't fall off the end.
        raise NotImplementedError


def group_relative_advantages(rewards: list[float]) -> list[float]:
    """Standardize rewards within a group: (r - mean) / (std + eps).

    Use the POPULATION std (divide by n). The epsilon prevents a divide-by-zero
    when every reward in the group is identical.
    """
    # TODO: implement
    raise NotImplementedError


def reward_of(prompt: int, action: int) -> float:
    return 1.0 if action == CORRECT[prompt] else 0.0


def train(use_baseline: bool, steps: int = 150, seed: int = 0):
    """Train the policy. Returns (policy, mean_signal_sq).

    `mean_signal_sq` is the mean of advantage^2 over every sample seen during
    training — a stand-in for gradient variance. GRPO's should come out clearly
    lower than raw REINFORCE's; that reduction is the whole point of the phase.
    """
    rng = random.Random(seed)
    pol = SoftmaxPolicy(N_PROMPTS, N_ACTIONS, lr=0.5)
    signal_sq: list[float] = []

    for _ in range(steps):
        grad = [[0.0] * pol.n_actions for _ in range(pol.n_prompts)]
        n_samples = 0

        for p in range(pol.n_prompts):
            acts = [pol.sample(p, rng) for _ in range(GROUP_SIZE)]
            rews = [reward_of(p, a) for a in acts]

            # TODO: if use_baseline, advantages = group_relative_advantages(rews)
            #       else advantages = rews  (plain REINFORCE: raw reward)
            # TODO: signal_sq.extend(a * a for a in advantages)
            # TODO: probs = pol.probs(p)   <- compute ONCE, before the loop below
            # TODO: for each (action a, advantage adv), for each action index j:
            #           grad[p][j] += adv * ((1.0 if j == a else 0.0) - probs[j])
            # TODO: n_samples += GROUP_SIZE
            raise NotImplementedError

        # TODO: gradient ASCENT (we maximize reward): for every p, j:
        #           pol.logits[p][j] += (pol.lr / n_samples) * grad[p][j]

    mean_signal_sq = sum(signal_sq) / len(signal_sq) if signal_sq else 0.0
    return pol, mean_signal_sq


if __name__ == "__main__":
    for label, flag in [("REINFORCE (raw reward)", False),
                        ("GRPO (group baseline)", True)]:
        pol, var = train(use_baseline=flag)
        acc = sum(pol.probs(p)[CORRECT[p]] for p in range(N_PROMPTS)) / N_PROMPTS
        print(f"{label:26s}  final P(correct)={acc:.3f}  mean signal^2={var:.3f}")
