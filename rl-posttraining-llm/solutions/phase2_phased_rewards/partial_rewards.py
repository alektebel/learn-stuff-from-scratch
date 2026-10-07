"""
Phase 2 solution — phased / progressive rewards (Reasoning-SQL, Progress-SQL).

Same environment, same candidate pool, same GRPO as Phase 1. The ONLY change is
the reward: instead of sparse execution accuracy, we layer partial rewards
underneath it (format, syntax, schema-linking, n-gram) so that even a query that
is *wrong on execution* still receives gradient telling it which direction is
better. This is Reasoning-SQL's core claim.

We then demonstrate Progress-SQL's second idea: a **curriculum baked into the
reward**. Early in training the dense shaping rewards dominate; as training
proceeds we anneal their weights down and let execution accuracy take over, so
we don't end up optimizing surface form instead of correctness.

Compare the printed curves against Phase 1:
  * partial rewards give a smooth, immediately-nonzero signal from step 0;
  * the annealed schedule ends up optimizing the true objective (exec acc),
    not the proxy.

Run:  python partial_rewards.py
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


# Static "phased" weights: dense shaping + sparse ground truth, all on at once.
PHASED_STATIC = {"format": 0.2, "syntax": 0.3, "schema": 0.5, "ngram": 0.3, "exec": 1.0}


def curriculum_weights(progress: float) -> dict[str, float]:
    """Progress-SQL-style schedule. `progress` in [0,1] over training.

    Start shaping-heavy (dense, easy signal), anneal toward execution accuracy
    so the final objective is correctness, not surface similarity.
    """
    shaping = max(0.0, 1.0 - progress)          # 1 -> 0
    exec_w = 0.5 + 1.5 * progress               # 0.5 -> 2.0
    return {
        "format": 0.3 * shaping,
        "syntax": 0.4 * shaping,
        "schema": 0.6 * shaping,
        "ngram": 0.3 * shaping,
        "exec": exec_w,
    }


def build_reward_fn(env: SQLEnv, qids: list[str]):
    def reward_of(prompt: int, action: int, weights: dict[str, float]) -> float:
        qid = qids[prompt]
        completion = CANDIDATES[qid][action]
        total, _ = combine(completion, task_by_qid(qid), env, weights)
        return total
    return reward_of


def exec_only_score(env: SQLEnv, qids, policy: TabularPolicy) -> float:
    """Greedy true-objective eval: pick argmax action, measure exec accuracy."""
    from rewards import execution_accuracy
    hits = 0
    for p, qid in enumerate(qids):
        probs = policy.probs(p)
        best = max(range(len(probs)), key=lambda a: probs[a])
        hits += execution_accuracy(CANDIDATES[qid][best], task_by_qid(qid), env)
    return hits / len(qids)


def train(steps: int = 200, seed: int = 0, use_curriculum: bool = True) -> None:
    rng = random.Random(seed)
    env = SQLEnv()
    qids = [t.qid for t in TASKS]
    n_actions = max(len(CANDIDATES[q]) for q in qids)
    policy = TabularPolicy(n_prompts=len(qids), n_actions=n_actions, lr=0.7)
    base_reward = build_reward_fn(env, qids)

    label = "curriculum (annealed)" if use_curriculum else "static phased"
    print(f"\n=== Phase 2: {label} rewards ===")
    print("step  mean_reward  greedy_exec_acc")
    for step in range(steps):
        progress = step / max(steps - 1, 1)
        weights = curriculum_weights(progress) if use_curriculum else PHASED_STATIC
        reward_of = lambda p, a: base_reward(p, a, weights)  # noqa: E731
        r = grpo_step(policy, reward_of, None, list(range(len(qids))),
                      group_size=8, rng=rng)
        if step % 40 == 0 or step == steps - 1:
            acc = exec_only_score(env, qids, policy)
            print(f"{step:>4}  {r:>10.3f}  {acc:>13.2f}")
    print("Final greedy execution accuracy:", exec_only_score(env, qids, policy))


if __name__ == "__main__":
    train(use_curriculum=False)   # static phased rewards
    train(use_curriculum=True)    # Progress-SQL-style annealed curriculum
