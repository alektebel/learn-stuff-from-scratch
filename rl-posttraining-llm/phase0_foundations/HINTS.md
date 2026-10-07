# Phase 0 — Progressive Hints

Open one level at a time. Level 1 is a nudge, Level 2 is the shape of the
solution, Level 3 is essentially the code. Try to stop at the earliest level
that unblocks you.

---

## `SoftmaxPolicy.probs`

<details><summary>Level 1 — nudge</summary>

Softmax is `exp(z_j) / Σ exp(z_k)`. The naive version overflows: `exp(1000)` is
`inf`, and `inf/inf` is `nan`. There's a standard one-line fix that doesn't
change the result mathematically — what can you subtract from every logit
without changing the ratio?
</details>

<details><summary>Level 2 — structure</summary>

Subtracting a constant `c` from every logit leaves the softmax unchanged, since
`exp(z-c)/Σexp(z_k-c) = (exp(z)/exp(c))/(Σexp(z_k)/exp(c))`. Pick `c = max(z)`.
Then the largest exponent is `exp(0) = 1` and nothing can overflow.

1. `z = self.logits[p]`
2. `m = max(z)`
3. exponentiate each `v - m`
4. divide each by the sum
</details>

<details><summary>Level 3 — code</summary>

```python
def probs(self, p):
    z = self.logits[p]
    m = max(z)
    exps = [math.exp(v - m) for v in z]
    s = sum(exps)
    return [e / s for e in exps]
```
</details>

---

## `SoftmaxPolicy.sample`

<details><summary>Level 1 — nudge</summary>

You have a list of probabilities summing to 1 and `rng.random()` giving a
uniform number in `[0, 1)`. Picture the probabilities as adjacent segments on a
number line from 0 to 1 — which segment does your random number land in?
</details>

<details><summary>Level 2 — structure</summary>

Inverse-CDF sampling:
1. `u = rng.random()`
2. walk the probabilities keeping a running total `cum`
3. the first index where `cum >= u` is your sample
4. return the last index as a fallback (floating-point error means `cum` may end
   at `0.9999999` and never reach `u`)
</details>

<details><summary>Level 3 — code</summary>

```python
def sample(self, p, rng):
    probs = self.probs(p)
    u, cum = rng.random(), 0.0
    for a, pa in enumerate(probs):
        cum += pa
        if u <= cum:
            return a
    return self.n_actions - 1
```
</details>

---

## `group_relative_advantages`

<details><summary>Level 1 — nudge</summary>

Two operations: centre, then scale. Centre by the group mean; scale by the group
standard deviation. Use the **population** std (divide by `n`), and add a small
epsilon to the denominator — think about what happens when all `G` rewards in the
group are `0.0`.
</details>

<details><summary>Level 2 — structure</summary>

```
mean = sum(rewards) / n
var  = sum((r - mean)**2 for r in rewards) / n      # population, so /n
std  = sqrt(var)
return [(r - mean) / (std + 1e-6) for r in rewards]
```

The epsilon is doing real work: a group where every completion scored the same
has `std == 0`. With the epsilon you get all zeros — no gradient — which is
correct, because such a group tells you nothing about which action was better.
</details>

<details><summary>Level 3 — code</summary>

```python
def group_relative_advantages(rewards, eps=1e-6):
    n = len(rewards)
    mean = sum(rewards) / n
    var = sum((r - mean) ** 2 for r in rewards) / n
    std = math.sqrt(var)
    return [(r - mean) / (std + eps) for r in rewards]
```
</details>

---

## The `train` loop

<details><summary>Level 1 — nudge</summary>

Three things sink most attempts here:
1. **Sign.** You're maximizing reward, so it's gradient *ascent*: `+=`.
2. **When you compute `probs`.** Once per prompt, *before* you loop over the
   sampled actions — they're the probabilities you sampled under.
3. **Normalization.** Divide the update by the number of samples, or the group
   size silently becomes part of your learning rate.
</details>

<details><summary>Level 2 — structure</summary>

Per prompt:
```
acts       = [sample() for _ in range(GROUP_SIZE)]
rews       = [reward_of(p, a) for a in acts]
advantages = group_relative_advantages(rews) if use_baseline else rews
signal_sq.extend(a*a for a in advantages)
probs      = pol.probs(p)                      # ONCE, here
for a, adv in zip(acts, advantages):
    for j in range(n_actions):
        grad[p][j] += adv * ((1.0 if j == a else 0.0) - probs[j])
n_samples += GROUP_SIZE
```
Then after all prompts, one ascent step over the whole `grad`.
</details>

<details><summary>Level 3 — code</summary>

```python
for p in range(pol.n_prompts):
    acts = [pol.sample(p, rng) for _ in range(GROUP_SIZE)]
    rews = [reward_of(p, a) for a in acts]
    advantages = group_relative_advantages(rews) if use_baseline else rews
    signal_sq.extend(a * a for a in advantages)
    probs = pol.probs(p)
    for a, adv in zip(acts, advantages):
        for j in range(pol.n_actions):
            indicator = 1.0 if j == a else 0.0
            grad[p][j] += adv * (indicator - probs[j])
    n_samples += GROUP_SIZE

# after the prompt loop, still inside the step loop:
for p in range(pol.n_prompts):
    for j in range(pol.n_actions):
        pol.logits[p][j] += (pol.lr / n_samples) * grad[p][j]
```
</details>

---

## Debugging table

| Symptom | Likely cause |
|---------|--------------|
| `P(correct)` collapses toward 0 | gradient **descent** — you used `-=` instead of `+=` |
| `nan` everywhere | missing `- max(z)` in softmax, or `std == 0` with no epsilon |
| Nothing moves at all | you re-computed `probs` inside the action loop, or forgot to apply `grad` to `logits` |
| GRPO variance ≥ REINFORCE variance | you passed raw rewards when `use_baseline=True` |
| Learning is wildly unstable | forgot to divide the update by `n_samples` |
