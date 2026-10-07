"""
Phase 1 solution — GRPO on text-to-SQL with ONLY execution accuracy reward.

This is the honest baseline every text-to-SQL RL paper starts from and then
argues against: reward = 1 if the generated query's result set matches the gold
result set, else 0. Correct, but sparse. Run it and watch two things:

  1. It *does* eventually learn on this tiny pool (the correct query is in the
     candidate set, so a lucky sample gets reward and is reinforced).
  2. The learning curve is jumpy and depends heavily on getting lucky early.
     With a real token-level policy and a large action space, "get lucky early"
     basically never happens for hard queries — that's the sparse-reward
     starvation Phase 2 fixes with partial rewards.

Run:  python grpo_sql.py
(from solutions/phase1_execution_reward/ — it adds ../../common to the path)
"""
from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common"))

from tiny_sql_env import SQLEnv, TASKS  # noqa: E402
from rewards import combine  # noqa: E402
from grpo import TabularPolicy, grpo_step  # noqa: E402
from candidates import CANDIDATES, CORRECT_INDEX, task_by_qid  # noqa: E402


# Execution-only reward weights.
WEIGHTS = {"exec": 1.0}


def build_reward_fn(env: SQLEnv, qids: list[str], weights: dict[str, float]):
    """Map (prompt_idx, action_idx) -> scalar reward using the real reward lib."""
    def reward_of(prompt: int, action: int) -> float:
        qid = qids[prompt]
        completion = CANDIDATES[qid][action]
        total, _ = combine(completion, task_by_qid(qid), env, weights)
        return total
    return reward_of


def train(weights: dict[str, float], steps: int = 200, seed: int = 0) -> TabularPolicy:
    rng = random.Random(seed)
    env = SQLEnv()
    qids = [t.qid for t in TASKS]
    n_actions = max(len(CANDIDATES[q]) for q in qids)
    policy = TabularPolicy(n_prompts=len(qids), n_actions=n_actions, lr=0.7)
    reward_of = build_reward_fn(env, qids, weights)

    print(f"weights={weights}")
    print("step  mean_reward  P(correct picks)")
    for step in range(steps):
        r = grpo_step(policy, reward_of, None, list(range(len(qids))),
                      group_size=8, rng=rng)
        if step % 40 == 0 or step == steps - 1:
            pc = [round(policy.probs(p)[CORRECT_INDEX[qids[p]]], 2)
                  for p in range(len(qids))]
            print(f"{step:>4}  {r:>10.3f}  {pc}")
    return policy


if __name__ == "__main__":
    train(WEIGHTS)
