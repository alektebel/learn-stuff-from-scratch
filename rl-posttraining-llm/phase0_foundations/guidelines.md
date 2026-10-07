# Phase 0 Guidelines — Policy gradients, baselines, GRPO

## Overview

You'll implement the RL machinery that every later phase reuses. No SQL yet —
a bandit with one correct action per prompt, so that when something breaks you
know it's your gradient, not your reward.

**File to implement:** `template_reinforce.py`
**Validate with:** `python test_phase0.py`
**Stuck?** `HINTS.md` (three levels, open them in order)

## Key Concepts

### 1. The score-function estimator

You cannot differentiate through sampling an action. The trick:

```
∇_θ E[R] = E[ R · ∇_θ log π_θ(a) ]
```

Sample an action, compute its log-prob gradient, weight it by the reward. For a
softmax policy over logits `z`:

```
∂ log π(a) / ∂ z_j  =  1[j == a] − π(j)
```

That identity is the whole gradient. Everything else is bookkeeping.

### 2. Why a baseline (the core of the phase)

- **Problem:** `R` is always ≥ 0 here, so *every* sampled action gets pushed
  **up** — correct ones just get pushed a bit harder. Learning happens only
  through the relative difference, which is a slow, high-variance signal.
- **Solution:** subtract a baseline `b`: use `(R − b)` instead of `R`. Actions
  worse than the baseline now get pushed **down**.
- **Why it stays correct:** `E[b · ∇ log π(a)] = b · ∇ E[1] = 0` for any `b`
  that doesn't depend on the action. Subtracting it changes the variance, not
  the expected gradient. Unbiased.

### 3. GRPO's specific baseline

Sample a **group** of `G` completions *for the same prompt*, then standardize:

```
A_i = (r_i − mean(r_1..r_G)) / (std(r_1..r_G) + ε)
```

- Baseline = group mean → "was this better than my other attempts?"
- Scale = group std → makes the update invariant to reward shift **and** scale,
  so you can change reward weights (Phase 2!) without retuning the LR.
- No value network. That's the practical win over PPO for LLMs: no critic to
  train, no critic to go stale.

### 4. The gradient-ascent detail people get wrong

You are **maximizing** reward, so you **add** the gradient:
`logits += lr * grad`. Subtracting silently trains the policy to be wrong — and
it looks like a learning-rate bug. If your accuracy drops toward 0, check this
first.

## Implementation Steps

### Step 1: `SoftmaxPolicy.probs`

Numerically stable softmax — subtract the max before exponentiating:

```
z = logits[p]
m = max(z)
exps = [exp(v - m) for v in z]
return [e / sum(exps) for e in exps]
```

Without the `- m`, large logits overflow to `inf` and you get `nan`.

### Step 2: `SoftmaxPolicy.sample`

Inverse-CDF sampling: draw `u ~ U(0,1)`, walk the probabilities accumulating
until the running sum ≥ `u`, return that index. Return the last index as a
fallback so floating-point error can't fall off the end.

### Step 3: `group_relative_advantages`

Mean, then population std (divide by `n`, not `n−1`), then
`(r − mean) / (std + 1e-6)`. The epsilon matters: when all `G` rewards are
identical the std is 0, and without it you divide by zero. With it you get all
zeros — which is exactly right, since a group where everything scored the same
carries no information about which action was better.

### Step 4: The training loop

For each step:
1. Zero a gradient accumulator shaped like `logits`.
2. For each prompt: sample `G` actions, score them, compute advantages.
3. For each sampled action `a` with advantage `A`, for every action index `j`:
   `grad[p][j] += A * ((1 if j == a else 0) - probs[j])`.
4. After all prompts: `logits[p][j] += (lr / n_samples) * grad[p][j]`.

Normalizing by the number of samples keeps the step size independent of `G` —
otherwise doubling the group size doubles your effective learning rate.

**Important:** compute `probs` **once per prompt before** the inner loop, not
inside it. They're the probabilities *under which you sampled*; recomputing them
mid-update would mix old and new policies.

## Requirements (what the tests check)

| # | Requirement |
|---|-------------|
| 1 | `probs` returns a valid distribution (length `n_actions`, non-negative, sums to 1) |
| 2 | `probs` is numerically stable for huge logits (no `nan`/`inf`) |
| 3 | `probs` is order-preserving: a larger logit gets a larger probability |
| 4 | `sample` only returns valid indices and respects the distribution (a near-deterministic policy samples its favourite ≥ 90% of the time) |
| 5 | `group_relative_advantages` is zero-mean |
| 6 | It has unit population std when rewards differ |
| 7 | It is sign-correct: above-mean reward → positive advantage |
| 8 | It returns all zeros (no `nan`) when every reward is identical |
| 9 | It is shift- and scale-invariant: rewards `[0,1]` and `[10,20]` give the same advantages |
| 10 | `train(use_baseline=True)` reaches `P(correct) > 0.8` on every prompt |
| 11 | `train(use_baseline=False)` also learns (REINFORCE works, it's just noisier) |
| 12 | The GRPO run's advantage signal has strictly lower mean-square than raw REINFORCE |

## Done When

`python test_phase0.py` is all PASS, and you can explain without notes: why
subtracting the group mean is unbiased, why dividing by the std helps, and what
the `+1e-6` is protecting you from.
