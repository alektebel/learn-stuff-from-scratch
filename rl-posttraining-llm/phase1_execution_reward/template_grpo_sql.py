"""
Phase 1 template — GRPO on text-to-SQL with execution-only reward.

Read `guidelines.md` first. Fill in the TODOs. Check your work with:

    python test_phase1.py

Stuck? `HINTS.md` has three escalating levels per function.
"""
from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from tiny_sql_env import SQLEnv, TASKS  # noqa: E402
from rewards import combine  # noqa: E402
from grpo import TabularPolicy, grpo_step  # noqa: E402
from candidates import CANDIDATES, CORRECT_INDEX, task_by_qid  # noqa: E402

# Execution accuracy is the ONLY signal in this phase. That is the point.
WEIGHTS = {"exec": 1.0}


def reward_of_factory(env: SQLEnv, qids: list[str], weights: dict[str, float] = None):
    """Build reward_of(prompt_idx, action_idx) -> float.

    Maps the RL loop's integer indices onto the real environment: prompt index
    -> qid -> Task, action index -> candidate completion string. Then scores it
    with the shared reward library.
    """
    weights = weights or WEIGHTS

    def reward_of(prompt: int, action: int) -> float:
        qid = qids[prompt]
        completion = CANDIDATES[qid][action]
        # TODO: look up the Task with task_by_qid(qid), call
        #       combine(completion, task, env, weights), return the TOTAL
        #       (combine returns a (total, breakdown) tuple).
        raise NotImplementedError

    return reward_of


def train(steps: int = 200, seed: int = 0, weights: dict[str, float] = None,
          verbose: bool = True):
    """Run GRPO. Returns (policy, qids, env) so the tests can inspect it."""
    rng = random.Random(seed)
    env = SQLEnv()
    qids = [t.qid for t in TASKS]
    n_actions = max(len(CANDIDATES[q]) for q in qids)
    policy = TabularPolicy(len(qids), n_actions, lr=0.7)
    reward_of = reward_of_factory(env, qids, weights)

    for step in range(steps):
        # TODO: call grpo_step(policy, reward_of, None, list(range(len(qids))),
        #                     group_size=8, rng=rng) and keep its mean reward
        # TODO: every ~40 steps (if verbose), print the step, the mean reward,
        #       and policy.probs(p)[CORRECT_INDEX[qids[p]]] for each prompt p.
        #       Watch q5 STALL — that's the execution-accuracy false positive.
        raise NotImplementedError

    return policy, qids, env


def prob_correct(policy, qids) -> list[float]:
    """P(the intended-correct candidate) for each task. Reporting only."""
    # TODO: return [policy.probs(p)[CORRECT_INDEX[qids[p]]] for each prompt p]
    raise NotImplementedError


if __name__ == "__main__":
    policy, qids, env = train()
    print("Final P(correct):", [round(x, 3) for x in prob_correct(policy, qids)])
