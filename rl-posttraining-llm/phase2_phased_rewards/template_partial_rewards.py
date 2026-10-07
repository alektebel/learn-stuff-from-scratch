"""
Phase 2 template — phased rewards + a reward curriculum.

Read `guidelines.md` first. Fill in the TODOs. Check your work with:

    python test_phase2.py

Stuck? `HINTS.md` has three escalating levels per function.
"""
from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from tiny_sql_env import SQLEnv, TASKS  # noqa: E402
from rewards import combine, execution_accuracy  # noqa: E402
from grpo import TabularPolicy, grpo_step  # noqa: E402
from candidates import CANDIDATES, CORRECT_INDEX, task_by_qid  # noqa: E402

# All five components on at once, with fixed weights (Reasoning-SQL style).
PHASED_STATIC = {"format": 0.2, "syntax": 0.3, "schema": 0.5, "ngram": 0.3, "exec": 1.0}

# The five component names your curriculum must emit.
COMPONENTS = ["format", "syntax", "schema", "ngram", "exec"]


def curriculum_weights(progress: float) -> dict[str, float]:
    """Progress-SQL-style schedule. `progress` goes 0.0 -> 1.0 across training.

    Requirements:
      * return a weight for every name in COMPONENTS
      * all weights >= 0
      * the four SHAPING weights (format/syntax/schema/ngram) decrease with
        progress and reach ~0 at progress = 1.0
      * the `exec` weight INCREASES with progress
      * at progress = 1.0, exec must dominate: exec > sum(shaping weights)
    """
    # TODO: shaping = max(0.0, 1.0 - progress)   -> 1.0 down to 0.0
    # TODO: exec_w  = 0.5 + 1.5 * progress       -> 0.5 up to 2.0
    # TODO: scale each shaping component by `shaping` and return the dict
    raise NotImplementedError


def greedy_exec_acc(env: SQLEnv, qids: list[str], policy) -> float:
    """Evaluate the TRUE objective: take each task's argmax action and measure
    execution accuracy. Never used as a training signal — this is your metric.
    """
    # TODO: for each prompt p: find the argmax of policy.probs(p), score
    #       execution_accuracy(CANDIDATES[qids[p]][best], task, env), average.
    raise NotImplementedError


def train(steps: int = 200, seed: int = 0, use_curriculum: bool = True,
          weights_override: dict[str, float] = None, verbose: bool = True):
    """Run GRPO with phased rewards. Returns (policy, qids, env, final_acc)."""
    rng = random.Random(seed)
    env = SQLEnv()
    qids = [t.qid for t in TASKS]
    n_actions = max(len(CANDIDATES[q]) for q in qids)
    policy = TabularPolicy(len(qids), n_actions, lr=0.7)

    for step in range(steps):
        progress = step / max(steps - 1, 1)
        # TODO: choose this step's weights:
        #         weights_override if given,
        #         else curriculum_weights(progress) if use_curriculum,
        #         else PHASED_STATIC
        # TODO: build reward_of(p, a) that scores CANDIDATES[qids[p]][a] with
        #       combine(..., weights) and returns the total
        # TODO: call grpo_step(...) as in Phase 1
        # TODO: if verbose, print step / mean reward / greedy_exec_acc every ~40
        raise NotImplementedError

    return policy, qids, env, greedy_exec_acc(env, qids, policy)


if __name__ == "__main__":
    print("=== static phased rewards ===")
    train(use_curriculum=False)
    print("\n=== annealed curriculum ===")
    train(use_curriculum=True)
