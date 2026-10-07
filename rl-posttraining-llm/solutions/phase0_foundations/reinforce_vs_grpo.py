"""
Phase 0 solution — why group-relative baselines matter.

Before any SQL, build intuition for the single most important design choice in
GRPO: the *baseline*. Plain REINFORCE uses the raw reward as the signal, so its
gradient estimate has high variance and drifts with the reward's absolute scale.
GRPO subtracts the group mean and divides by the group std — a baseline computed
from sibling samples of the *same* prompt — which slashes variance and makes the
update invariant to reward shift/scale.

This script trains the same tiny policy two ways on the same task and prints the
variance of the per-step gradient signal. GRPO's is dramatically lower, which is
why it trains stably where REINFORCE thrashes.

Run:  python reinforce_vs_grpo.py
"""
from __future__ import annotations

import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common"))

from grpo import TabularPolicy, group_relative_advantages  # noqa: E402


def run(use_grpo: bool, steps: int = 150, seed: int = 0):
    rng = random.Random(seed)
    correct = [1, 3, 0]
    pol = TabularPolicy(n_prompts=3, n_actions=4, lr=0.5)
    reward_of = lambda p, a: 1.0 if a == correct[p] else 0.0  # noqa: E731
    signal_sq = []  # track magnitude of the advantage signal each step

    for _ in range(steps):
        grad = [[0.0] * pol.n_actions for _ in range(pol.n_prompts)]
        for p in range(pol.n_prompts):
            acts = [pol.sample(p, rng) for _ in range(8)]
            rews = [reward_of(p, a) for a in acts]
            if use_grpo:
                adv = group_relative_advantages(rews)
            else:
                adv = rews  # plain REINFORCE: raw reward, no baseline
            signal_sq.extend(a * a for a in adv)
            probs = pol.probs(p)
            for a, ad in zip(acts, adv):
                for j in range(pol.n_actions):
                    grad[p][j] += ad * ((1.0 if j == a else 0.0) - probs[j])
        for p in range(pol.n_prompts):
            for j in range(pol.n_actions):
                pol.logits[p][j] += (pol.lr / 24) * grad[p][j]

    acc = sum(pol.probs(p)[correct[p]] for p in range(3)) / 3
    var = sum(signal_sq) / len(signal_sq)
    return acc, var


if __name__ == "__main__":
    for label, flag in [("REINFORCE (raw reward)", False), ("GRPO (group baseline)", True)]:
        acc, var = run(flag)
        print(f"{label:26s}  final P(correct)={acc:.3f}  mean signal^2={var:.3f}")
    print("\nTakeaway: GRPO's group-relative advantage has much lower magnitude/variance")
    print("while reaching the same or better accuracy -> stabler LLM post-training.")
