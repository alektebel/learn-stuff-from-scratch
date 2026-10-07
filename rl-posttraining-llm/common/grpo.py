"""
grpo.py — a from-scratch, dependency-free implementation of the core math
behind GRPO (Group Relative Policy Optimization), the algorithm underneath
DeepSeek-R1-style and most current text-to-SQL RL work.

Why GRPO and not PPO here? GRPO throws away the value network. For a *group* of
G completions sampled for the same prompt, it estimates the advantage of each
completion by standardizing its reward against the group:

        A_i = (r_i - mean(r_1..r_G)) / (std(r_1..r_G) + eps)

That is the entire trick: "how much better than my other tries was this one?"
No critic to train, no reward-model drift on the value side. This file gives you
that computation plus a minimal policy-gradient update on a *tabular softmax*
policy, so you can watch reward go up on a CPU with no torch installed.

The tabular policy is a stand-in for a real LLM: instead of generating tokens,
it picks one of K candidate completions per prompt. Everything about credit
assignment (group-relative advantage, KL-to-reference regularization, the sign
of the gradient) is identical to the real thing — only the function
approximator is swapped for something you can read end to end.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass


# --------------------------------------------------------------------------- #
# The group-relative advantage — this function is exactly what a real GRPO
# trainer computes, regardless of model. Study it; it is the whole idea.
# --------------------------------------------------------------------------- #
def group_relative_advantages(rewards: list[float], eps: float = 1e-6) -> list[float]:
    n = len(rewards)
    mean = sum(rewards) / n
    var = sum((r - mean) ** 2 for r in rewards) / n
    std = math.sqrt(var)
    return [(r - mean) / (std + eps) for r in rewards]


# --------------------------------------------------------------------------- #
# A tiny softmax policy over K discrete actions, per prompt. logits[p] is a
# list of K preference scores for prompt p. This is our stand-in "LLM".
# --------------------------------------------------------------------------- #
@dataclass
class TabularPolicy:
    n_prompts: int
    n_actions: int
    lr: float = 0.5
    logits: list[list[float]] = None  # type: ignore

    def __post_init__(self) -> None:
        if self.logits is None:
            self.logits = [[0.0] * self.n_actions for _ in range(self.n_prompts)]

    def probs(self, prompt: int) -> list[float]:
        z = self.logits[prompt]
        m = max(z)
        exps = [math.exp(v - m) for v in z]
        s = sum(exps)
        return [e / s for e in exps]

    def sample(self, prompt: int, rng: random.Random) -> int:
        p = self.probs(prompt)
        r, cum = rng.random(), 0.0
        for a, pa in enumerate(p):
            cum += pa
            if r <= cum:
                return a
        return self.n_actions - 1

    def logprob(self, prompt: int, action: int) -> float:
        return math.log(self.probs(prompt)[action] + 1e-12)


# --------------------------------------------------------------------------- #
# One GRPO update step over a batch of prompts. For each prompt we sample a
# group of G actions, score them, standardize rewards -> advantages, and nudge
# the log-probs of good actions up / bad ones down. The KL term keeps us from
# collapsing away from a reference policy (the SFT model, in the real setting).
# --------------------------------------------------------------------------- #
def grpo_step(
    policy: TabularPolicy,
    reward_of,                 # callable(prompt:int, action:int) -> float
    ref_policy: TabularPolicy | None,
    prompts: list[int],
    group_size: int,
    rng: random.Random,
    kl_coeff: float = 0.0,
) -> float:
    """Apply one policy-gradient update in place. Returns mean batch reward."""
    total_reward = 0.0
    n = 0
    # accumulate gradient on logits
    grad = [[0.0] * policy.n_actions for _ in range(policy.n_prompts)]

    for prompt in prompts:
        actions = [policy.sample(prompt, rng) for _ in range(group_size)]
        rewards = [reward_of(prompt, a) for a in actions]
        advantages = group_relative_advantages(rewards)
        total_reward += sum(rewards)
        n += len(rewards)

        probs = policy.probs(prompt)
        for a, adv in zip(actions, advantages):
            # d logπ(a)/d logit_j = [j==a] - π(j)   (softmax score function)
            for j in range(policy.n_actions):
                indicator = 1.0 if j == a else 0.0
                grad[prompt][j] += adv * (indicator - probs[j])

        # KL(π || π_ref) regularization pulls toward the reference policy.
        if ref_policy is not None and kl_coeff > 0.0:
            ref = ref_policy.probs(prompt)
            for j in range(policy.n_actions):
                # gradient of KL wrt logit_j, approximated locally
                grad[prompt][j] -= kl_coeff * (probs[j] - ref[j])

    # gradient ascent (we are maximizing reward)
    scale = policy.lr / max(len(prompts) * group_size, 1)
    for p in range(policy.n_prompts):
        for j in range(policy.n_actions):
            policy.logits[p][j] += scale * grad[p][j]

    return total_reward / max(n, 1)


if __name__ == "__main__":
    # Sanity demo: 3 prompts, 4 actions, exactly one correct action per prompt.
    rng = random.Random(0)
    correct = [2, 0, 3]
    pol = TabularPolicy(n_prompts=3, n_actions=4, lr=1.0)

    def reward_of(prompt: int, action: int) -> float:
        return 1.0 if action == correct[prompt] else 0.0

    print("step  mean_reward")
    for step in range(30):
        r = grpo_step(pol, reward_of, None, [0, 1, 2], group_size=8, rng=rng)
        if step % 5 == 0:
            print(f"{step:>4}  {r:.3f}")
    final = [pol.probs(p)[correct[p]] for p in range(3)]
    print("P(correct) per prompt after training:", [round(x, 3) for x in final])
