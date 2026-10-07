"""Smoke tests proving the zero-dependency core actually works on CPU.

Run:  python test_common.py     (from inside common/)
No pytest, no numpy, no torch required.
"""
from __future__ import annotations

import random

from tiny_sql_env import SQLEnv, TASKS
from rewards import combine, execution_accuracy, extract_sql
from grpo import TabularPolicy, grpo_step, group_relative_advantages


def test_env_executes_gold() -> None:
    env = SQLEnv()
    for t in TASKS:
        ok, res = env.execute(t.gold_sql)
        assert ok, f"gold failed for {t.qid}: {res}"
        assert res == env.gold_result(t)
    print("  [ok] all gold SQL executes and is self-consistent")


def test_execution_reward_discriminates() -> None:
    env = SQLEnv()
    t = TASKS[0]  # q1: count ES customers
    good = f"<sql>{t.gold_sql}</sql>"
    bad = "<sql>SELECT COUNT(*) FROM customers WHERE country='ZZ'</sql>"
    assert execution_accuracy(good, t, env) == 1.0
    assert execution_accuracy(bad, t, env) == 0.0
    print("  [ok] execution reward separates correct from incorrect")


def test_partial_rewards_are_denser_than_exec() -> None:
    """A *wrong-but-plausible* query should get 0 exec reward but >0 partial."""
    env = SQLEnv()
    t = TASKS[0]
    plausible = "<think>x</think><sql>SELECT COUNT(*) FROM customers</sql>"
    _, br = combine(
        plausible, t, env,
        {"format": 1, "syntax": 1, "schema": 1, "ngram": 1, "exec": 1},
    )
    assert br["exec"] == 0.0, "should be wrong on execution"
    assert br["format"] > 0 and br["syntax"] > 0 and br["schema"] > 0, br
    print(f"  [ok] partial rewards fire where exec is 0: {br}")


def test_advantages_zero_mean() -> None:
    adv = group_relative_advantages([0.0, 0.0, 1.0, 1.0])
    assert abs(sum(adv)) < 1e-6, adv
    assert adv[2] > 0 > adv[0]
    print("  [ok] group-relative advantages are zero-mean, correctly signed")


def test_grpo_learns() -> None:
    rng = random.Random(1)
    correct = [1, 3, 0, 2]
    pol = TabularPolicy(n_prompts=4, n_actions=4, lr=1.0)
    reward_of = lambda p, a: 1.0 if a == correct[p] else 0.0
    for _ in range(60):
        grpo_step(pol, reward_of, None, [0, 1, 2, 3], group_size=8, rng=rng)
    for p in range(4):
        assert pol.probs(p)[correct[p]] > 0.8, (p, pol.probs(p))
    print("  [ok] GRPO drives P(correct) > 0.8 on all prompts")


if __name__ == "__main__":
    print("Running common/ smoke tests (pure stdlib)...")
    test_env_executes_gold()
    test_execution_reward_discriminates()
    test_partial_rewards_are_denser_than_exec()
    test_advantages_zero_mean()
    test_grpo_learns()
    print("All tests passed.")
