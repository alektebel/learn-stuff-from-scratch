"""
Phase 2 tests — run this to check your `template_partial_rewards.py`.

    python test_phase2.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from test_harness import Checker, assert_between, assert_close, load_student_module  # noqa: E402
from tiny_sql_env import SQLEnv, TASKS  # noqa: E402
from candidates import CANDIDATES, CORRECT_INDEX, task_by_qid  # noqa: E402
from rewards import combine  # noqa: E402
from grpo import TabularPolicy  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
m = load_student_module(HERE, "template_partial_rewards")

QIDS = [t.qid for t in TASKS]
SHAPING = ["format", "syntax", "schema", "ngram"]


def test_curriculum_has_all_components():
    for progress in (0.0, 0.5, 1.0):
        w = m.curriculum_weights(progress)
        for name in m.COMPONENTS:
            assert name in w, f"curriculum_weights({progress}) is missing '{name}'"


def test_curriculum_weights_non_negative():
    for progress in (0.0, 0.25, 0.5, 0.75, 1.0):
        for name, val in m.curriculum_weights(progress).items():
            assert val >= 0.0, f"weight '{name}' is negative ({val}) at progress={progress}"


def test_shaping_decreases():
    early = m.curriculum_weights(0.0)
    mid = m.curriculum_weights(0.5)
    late = m.curriculum_weights(1.0)
    for name in SHAPING:
        assert early[name] >= mid[name] >= late[name], (
            f"shaping weight '{name}' must decrease: "
            f"{early[name]} -> {mid[name]} -> {late[name]}"
        )


def test_exec_weight_increases():
    early = m.curriculum_weights(0.0)
    late = m.curriculum_weights(1.0)
    assert late["exec"] > early["exec"], (
        f"exec weight must grow with progress: {early['exec']} -> {late['exec']}"
    )


def test_endpoint_exec_dominates():
    late = m.curriculum_weights(1.0)
    shaping_sum = sum(late[n] for n in SHAPING)
    assert_close(shaping_sum, 0.0, 1e-6, "sum of shaping weights at progress=1.0")
    assert late["exec"] > shaping_sum, "at the end, exec must dominate the objective"


def test_start_has_real_shaping():
    early = m.curriculum_weights(0.0)
    shaping_sum = sum(early[n] for n in SHAPING)
    assert shaping_sum > 0.5, (
        f"shaping sum at progress=0 is only {shaping_sum:.3f}; early training "
        "needs a meaningful dense signal or you've reinvented Phase 1"
    )


def test_greedy_exec_acc_on_pinned_policy():
    env = SQLEnv()
    policy = TabularPolicy(len(QIDS), 4, lr=0.7)
    for p, qid in enumerate(QIDS):          # pin every prompt to its correct action
        policy.logits[p] = [0.0] * 4
        policy.logits[p][CORRECT_INDEX[qid]] = 20.0
    acc = m.greedy_exec_acc(env, QIDS, policy)
    assert_between(acc, 0.0, 1.0, "greedy_exec_acc")
    assert_close(acc, 1.0, 1e-9, "greedy_exec_acc for a policy pinned to gold")


def test_static_phased_reaches_full_accuracy():
    _, _, _, acc = m.train(steps=200, seed=0, use_curriculum=False, verbose=False)
    assert_close(acc, 1.0, 1e-9, "greedy exec accuracy with static phased rewards")


def test_curriculum_reaches_full_accuracy():
    _, _, _, acc = m.train(steps=200, seed=0, use_curriculum=True, verbose=False)
    assert_close(acc, 1.0, 1e-9, "greedy exec accuracy with the annealed curriculum")


def test_q5_is_fixed():
    """The payoff: dense signal breaks the tie execution reward could not."""
    policy, qids, _, _ = m.train(steps=200, seed=0, use_curriculum=True, verbose=False)
    q5 = qids.index("q5")
    pc = policy.probs(q5)[CORRECT_INDEX["q5"]]
    assert pc > 0.8, (
        f"q5 P(correct) = {pc:.3f}. Phase 1 got ~0.28 with execution reward alone; "
        "phased rewards should break the tie via schema-linking + n-gram."
    )


def test_reward_is_dense():
    """A wrong-but-plausible candidate must still earn nonzero reward."""
    env = SQLEnv()
    for qid in QIDS:
        plausible = CANDIDATES[qid][1]                    # wrong, but sensible SQL
        total, br = combine(plausible, task_by_qid(qid), env, m.PHASED_STATIC)
        assert total > 0.0, f"{qid}: plausible-but-wrong candidate scored 0 ({br})"


def test_reward_is_discriminative():
    """Correct candidate must strictly outscore every alternative."""
    env = SQLEnv()
    for qid in QIDS:
        scores = [combine(c, task_by_qid(qid), env, m.PHASED_STATIC)[0]
                  for c in CANDIDATES[qid]]
        ci = CORRECT_INDEX[qid]
        for i, s in enumerate(scores):
            if i == ci:
                continue
            assert scores[ci] > s, (
                f"{qid}: correct candidate scored {scores[ci]:.3f} but candidate "
                f"{i} scored {s:.3f} — the phased reward is not discriminative"
            )


def test_reward_hacking_is_reproducible():
    """With a surface-form proxy alone, the reward stops tracking correctness."""
    env = SQLEnv()
    broken = []
    for qid in QIDS:
        scores = [combine(c, task_by_qid(qid), env, {"ngram": 1.0})[0]
                  for c in CANDIDATES[qid]]
        ci = CORRECT_INDEX[qid]
        if any(s >= scores[ci] for i, s in enumerate(scores) if i != ci):
            broken.append(qid)
    assert broken, (
        "expected an n-gram-only reward to fail to rank the correct query first "
        "on at least one task (it should be q5)"
    )


if __name__ == "__main__":
    c = Checker("Phase 2 — phased rewards and reward curricula")
    c.check("curriculum returns all five components", test_curriculum_has_all_components)
    c.check("all weights are non-negative", test_curriculum_weights_non_negative)
    c.check("shaping weights decrease with progress", test_shaping_decreases)
    c.check("exec weight increases with progress", test_exec_weight_increases)
    c.check("at progress=1, exec dominates", test_endpoint_exec_dominates)
    c.check("at progress=0, shaping is meaningful", test_start_has_real_shaping)
    c.check("greedy_exec_acc works on a pinned policy", test_greedy_exec_acc_on_pinned_policy)
    c.check("static phased rewards reach acc 1.0", test_static_phased_reaches_full_accuracy)
    c.check("curriculum reaches acc 1.0", test_curriculum_reaches_full_accuracy)
    c.check("q5 is FIXED by dense rewards", test_q5_is_fixed)
    c.check("reward is dense (wrong-but-plausible > 0)", test_reward_is_dense)
    c.check("reward is discriminative", test_reward_is_discriminative)
    c.check("reward hacking is reproducible", test_reward_hacking_is_reproducible)
    sys.exit(c.summary())
