# Phase 0 — Foundations: policy gradients, baselines, and GRPO from scratch

**Goal:** understand *why* GRPO looks the way it does before you apply it to
anything. If you can derive the update in this phase, every later phase is just
"what reward do I plug in?".

## Concepts

- **Policy gradient (REINFORCE).** Maximize expected reward
  `J(θ) = E[R]`. The score-function estimator gives
  `∇J = E[R · ∇ log π(a)]`. For a softmax policy,
  `∂ log π(a)/∂ logit_j = 1[j=a] − π(j)`.
- **The variance problem.** Raw `R` is a terrible multiplier — high variance,
  scale-sensitive. Subtract a **baseline** `b`: `∇J = E[(R − b) · ∇ log π(a)]`.
  Any `b` independent of the action is unbiased; a good `b` slashes variance.
- **GRPO's baseline.** Sample a **group** of `G` completions for the *same*
  prompt, and standardize: `A_i = (r_i − mean) / (std + ε)`. The baseline is the
  group mean; the scale is the group std. No value network to train.
- **KL-to-reference.** Add `−β·KL(π ‖ π_ref)` so the policy doesn't wander away
  from the SFT model (prevents reward hacking and gibberish).

## Exercises

1. **Derive and implement REINFORCE** on a bandit with one correct action per
   prompt. `template_reinforce.py` has the skeleton.
2. **Add the group baseline** and confirm the gradient signal's variance drops
   while accuracy holds or improves.
3. **Implement `group_relative_advantages`** and check it is zero-mean and
   correctly signed (already in `common/grpo.py` — re-derive it yourself, then
   diff).
4. **Add a KL term** toward a fixed reference policy and watch it slow down
   drift when the reward is noisy.

## Runnable solution

```bash
cd ../solutions/phase0_foundations && python reinforce_vs_grpo.py
```

Expected: both reach high `P(correct)`, but GRPO's `mean signal^2` (a proxy for
gradient variance) is markedly lower. That variance reduction is the entire
reason GRPO trains stably on real LLMs.

---

## Files in this phase

| File | Use it for |
|------|-----------|
| `guidelines.md` | the full spec: concepts, implementation steps, and the 12 numbered requirements the tests enforce |
| `template_reinforce.py` | the file you implement |
| `test_phase0.py` | `python test_phase0.py` — checks your work (12 requirements; unimplemented shows as TODO, not failure) |
| `HINTS.md` | progressive hints (Level 1 nudge → Level 3 code) and a debugging table |

Read `guidelines.md` before you start writing code.

## Done when

You can explain, without notes: why subtracting the group mean is unbiased, why
dividing by the group std helps, and what the KL term protects against.
