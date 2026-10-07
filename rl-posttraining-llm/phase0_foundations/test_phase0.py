"""
Phase 0 tests — run this to check your `template_reinforce.py`.

    python test_phase0.py

Unimplemented functions show up as TODO, not as failures, so you can run this
from the very start and use it as your checklist.
"""
from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

from test_harness import (  # noqa: E402
    Checker, assert_between, assert_close, assert_is_probs, load_student_module,
)

HERE = os.path.dirname(os.path.abspath(__file__))
m = load_student_module(HERE, "template_reinforce")


def test_probs_is_distribution():
    pol = m.SoftmaxPolicy(3, 4)
    for p in range(3):
        assert_is_probs(pol.probs(p), 4, f"probs({p})")
    # uniform logits -> uniform distribution
    assert_close(pol.probs(0)[0], 0.25, 1e-9, "uniform probs entry")


def test_probs_numerically_stable():
    pol = m.SoftmaxPolicy(1, 3)
    pol.logits[0] = [1000.0, 999.0, -1000.0]
    p = pol.probs(0)
    assert all(x == x for x in p), f"got nan in probs: {p}"          # nan != nan
    assert all(x not in (float("inf"), float("-inf")) for x in p), p
    assert_is_probs(p, 3, "probs with huge logits")
    assert p[0] > p[1] > p[2], f"ordering broken under large logits: {p}"


def test_probs_order_preserving():
    pol = m.SoftmaxPolicy(1, 3)
    pol.logits[0] = [0.0, 2.0, 1.0]
    p = pol.probs(0)
    assert p[1] > p[2] > p[0], f"larger logit must get larger prob, got {p}"


def test_sample_in_range_and_follows_distribution():
    rng = random.Random(0)
    pol = m.SoftmaxPolicy(1, 4)
    for _ in range(200):
        a = pol.sample(0, rng)
        assert isinstance(a, int), f"sample returned {type(a).__name__}, want int"
        assert 0 <= a < 4, f"sample returned out-of-range action {a}"
    # near-deterministic policy should overwhelmingly pick action 2
    pol.logits[0] = [0.0, 0.0, 10.0, 0.0]
    hits = sum(pol.sample(0, rng) == 2 for _ in range(300))
    assert hits >= 270, f"peaked policy picked its favourite only {hits}/300 times"


def test_advantages_zero_mean():
    adv = m.group_relative_advantages([0.0, 0.0, 1.0, 1.0])
    assert_close(sum(adv), 0.0, 1e-6, "sum of advantages")


def test_advantages_unit_std():
    adv = m.group_relative_advantages([0.0, 1.0, 2.0, 3.0])
    mean = sum(adv) / len(adv)
    var = sum((a - mean) ** 2 for a in adv) / len(adv)
    assert_close(var ** 0.5, 1.0, 1e-3, "population std of advantages")


def test_advantages_sign_correct():
    adv = m.group_relative_advantages([0.0, 0.0, 1.0, 1.0])
    assert adv[2] > 0 > adv[0], f"above-mean must be positive, below-mean negative: {adv}"


def test_advantages_constant_group_is_safe():
    adv = m.group_relative_advantages([1.0, 1.0, 1.0])
    assert all(a == a for a in adv), f"nan from a constant group: {adv}"
    for a in adv:
        assert_close(a, 0.0, 1e-3, "advantage in a constant-reward group")


def test_advantages_shift_scale_invariant():
    a1 = m.group_relative_advantages([0.0, 1.0, 0.0, 1.0])
    a2 = m.group_relative_advantages([10.0, 20.0, 10.0, 20.0])
    for x, y in zip(a1, a2):
        assert_close(x, y, 1e-4, "advantage under reward shift+scale")


def test_grpo_learns():
    pol, _ = m.train(use_baseline=True, steps=150, seed=0)
    for p in range(m.N_PROMPTS):
        pc = pol.probs(p)[m.CORRECT[p]]
        assert pc > 0.8, f"GRPO: P(correct) on prompt {p} is only {pc:.3f}"


def test_reinforce_also_learns():
    pol, _ = m.train(use_baseline=False, steps=150, seed=0)
    for p in range(m.N_PROMPTS):
        pc = pol.probs(p)[m.CORRECT[p]]
        assert pc > 0.5, (
            f"REINFORCE: P(correct) on prompt {p} is {pc:.3f}. "
            "If it's near 0 you are doing gradient DESCENT — flip the sign."
        )


def test_grpo_has_lower_signal_variance():
    _, var_grpo = m.train(use_baseline=True, steps=150, seed=0)
    _, var_reinforce = m.train(use_baseline=False, steps=150, seed=0)
    assert var_grpo < var_reinforce, (
        f"expected GRPO signal^2 ({var_grpo:.3f}) < REINFORCE ({var_reinforce:.3f}); "
        "the group baseline should shrink the update magnitude"
    )


if __name__ == "__main__":
    c = Checker("Phase 0 — policy gradients, baselines, GRPO")
    c.check("probs() returns a valid distribution", test_probs_is_distribution)
    c.check("probs() is numerically stable", test_probs_numerically_stable)
    c.check("probs() is order-preserving", test_probs_order_preserving)
    c.check("sample() is in-range and follows probs", test_sample_in_range_and_follows_distribution)
    c.check("advantages are zero-mean", test_advantages_zero_mean)
    c.check("advantages have unit std", test_advantages_unit_std)
    c.check("advantages are sign-correct", test_advantages_sign_correct)
    c.check("constant group -> zeros, not nan", test_advantages_constant_group_is_safe)
    c.check("advantages are shift/scale invariant", test_advantages_shift_scale_invariant)
    c.check("GRPO reaches P(correct) > 0.8", test_grpo_learns)
    c.check("REINFORCE also learns", test_reinforce_also_learns)
    c.check("GRPO has lower signal variance", test_grpo_has_lower_signal_variance)
    sys.exit(c.summary())
