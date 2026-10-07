"""
Phase 1 tests — run this to check your `template_grpo_sql.py`.

    python test_phase1.py

Note requirement 8: this phase asserts your agent *fails* on q5. That failure is
the lesson — execution reward cannot distinguish those candidates.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from test_harness import Checker, assert_between, load_student_module  # noqa: E402
from tiny_sql_env import SQLEnv, TASKS  # noqa: E402
from candidates import CANDIDATES, CORRECT_INDEX  # noqa: E402
from rewards import execution_accuracy  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
m = load_student_module(HERE, "template_grpo_sql")

QIDS = [t.qid for t in TASKS]


def _trained(seed: int = 0):
    return m.train(steps=200, seed=seed, verbose=False)


def test_reward_rewards_correct():
    env = SQLEnv()
    r = m.reward_of_factory(env, QIDS)
    for p, qid in enumerate(QIDS):
        got = r(p, CORRECT_INDEX[qid])
        assert got == 1.0, f"correct candidate for {qid} scored {got}, expected 1.0"


def test_reward_punishes_broken():
    env = SQLEnv()
    r = m.reward_of_factory(env, QIDS)
    # q1 candidate 3 is a malformed query (typo'd table) -> must score 0
    got = r(0, 3)
    assert got == 0.0, f"malformed q1 candidate scored {got}, expected 0.0"
    # q2 candidate 1 returns the wrong rows -> must score 0
    got = r(1, 1)
    assert got == 0.0, f"wrong-rows q2 candidate scored {got}, expected 0.0"


def test_reward_is_binary():
    env = SQLEnv()
    r = m.reward_of_factory(env, QIDS)
    for p, qid in enumerate(QIDS):
        for a in range(len(CANDIDATES[qid])):
            got = r(p, a)
            assert got in (0.0, 1.0), (
                f"{qid} candidate {a} scored {got}; execution accuracy is binary. "
                "Are you passing weights other than {'exec': 1.0}?"
            )


def test_train_returns_policy():
    policy, qids, env = _trained()
    assert len(qids) == len(TASKS), f"expected {len(TASKS)} tasks, got {len(qids)}"
    assert policy.n_prompts == len(TASKS), "policy must cover every task"
    for p in range(policy.n_prompts):
        probs = policy.probs(p)
        assert abs(sum(probs) - 1.0) < 1e-6, f"probs for prompt {p} don't sum to 1"


def test_prob_correct_shape():
    policy, qids, env = _trained()
    pc = m.prob_correct(policy, qids)
    assert len(pc) == len(TASKS), f"prob_correct returned {len(pc)} values"
    for i, x in enumerate(pc):
        assert_between(x, 0.0, 1.0, f"prob_correct[{i}]")


def test_mean_reward_climbs():
    policy, qids, env = _trained()
    r = m.reward_of_factory(env, qids)
    # greedy mean reward across tasks
    total = 0.0
    for p in range(len(qids)):
        probs = policy.probs(p)
        best = max(range(len(probs)), key=lambda a: probs[a])
        total += r(p, best)
    mean = total / len(qids)
    assert mean > 0.9, f"greedy mean execution reward is only {mean:.2f} after training"


def test_learns_the_unambiguous_tasks():
    policy, qids, env = _trained()
    pc = m.prob_correct(policy, qids)
    for p, qid in enumerate(qids):
        if qid == "q5":
            continue
        assert pc[p] > 0.8, f"{qid}: P(correct) only {pc[p]:.3f} after 200 steps"


def test_q5_false_positive_is_reproduced():
    """The whole point of the phase: exec reward CANNOT solve q5."""
    policy, qids, env = _trained()
    pc = m.prob_correct(policy, qids)
    q5 = qids.index("q5")
    assert pc[q5] < 0.5, (
        f"q5 P(correct) = {pc[q5]:.3f}, but execution reward cannot distinguish "
        "q5's candidates (three of them return identical rows). If this passes, "
        "your reward is using more than execution accuracy."
    )


def test_q5_candidates_really_collide():
    """Sanity-check the environment claim the lesson rests on."""
    env = SQLEnv()
    task = next(t for t in TASKS if t.qid == "q5")
    scores = [execution_accuracy(c, task, env) for c in CANDIDATES["q5"]]
    colliding = sum(1 for s in scores if s == 1.0)
    assert colliding >= 3, (
        f"expected >=3 q5 candidates to score 1.0, got {colliding} (scores={scores})"
    )


def test_training_is_deterministic():
    p1, _, _ = m.train(steps=50, seed=7, verbose=False)
    p2, _, _ = m.train(steps=50, seed=7, verbose=False)
    for p in range(p1.n_prompts):
        a, b = p1.probs(p), p2.probs(p)
        for x, y in zip(a, b):
            assert abs(x - y) < 1e-9, "same seed must give the same result"


if __name__ == "__main__":
    c = Checker("Phase 1 — sparse execution-accuracy reward")
    c.check("reward = 1.0 for correct candidates", test_reward_rewards_correct)
    c.check("reward = 0.0 for broken/wrong candidates", test_reward_punishes_broken)
    c.check("reward is binary", test_reward_is_binary)
    c.check("train() returns a usable policy", test_train_returns_policy)
    c.check("prob_correct() has the right shape", test_prob_correct_shape)
    c.check("greedy mean reward > 0.9", test_mean_reward_climbs)
    c.check("learns q1-q4 (P(correct) > 0.8)", test_learns_the_unambiguous_tasks)
    c.check("q5 false positive IS reproduced (expected failure)",
            test_q5_false_positive_is_reproduced)
    c.check("env sanity: q5 candidates collide", test_q5_candidates_really_collide)
    c.check("training is deterministic given a seed", test_training_is_deterministic)
    sys.exit(c.summary())
