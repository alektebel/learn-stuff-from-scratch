# Phase 2 Guidelines — Phased rewards and reward curricula

## Overview

Fix Phase 1's two problems — sparsity and the `q5` false positive — by layering
dense partial rewards underneath execution accuracy, then annealing them away.
This is Reasoning-SQL plus Progress-SQL.

**File to implement:** `template_partial_rewards.py`
**Validate with:** `python test_phase2.py`
**Hints:** `HINTS.md`

## Key Concepts

### 1. Partial rewards (Reasoning-SQL)

Instead of one sparse signal, score several things at once:

```
total = w_format·format + w_syntax·syntax + w_schema·schema_link
      + w_ngram·ngram_sim + w_exec·execution
```

All five already exist in `common/rewards.py`, each returning `[0, 1]`:

| Component | What it measures | Density |
|-----------|------------------|---------|
| `format` | did it emit `<think>` and `<sql>` tags? | very dense — fires immediately |
| `syntax` | does the query prepare without a SQL error? | dense |
| `schema` | F1 of referenced tables/columns vs the gold link set | dense |
| `ngram` | bigram overlap with the gold query | dense |
| `exec` | result set matches gold | **sparse** (the ground truth) |

The key property, and the one worth staring at: **a query that is wrong on
execution still gets nonzero total reward**, and a *less* wrong query gets
*more* of it. That's a gradient where Phase 1 had none.

This also fixes `q5`. Execution reward gave all three colliding candidates
`1.0`; schema-linking and n-gram do not — the correct query references
`quantity` and `price` and aggregates them, the `COUNT(*)` variant doesn't. The
tie breaks.

### 2. Why RL here beats SFT

Worth understanding, since it's Reasoning-SQL's headline claim. SFT imitates one
gold query per question — it never sees a *wrong* query, so it never learns what
makes one wrong. RL samples many candidates per question, good and bad, and the
group-relative advantage explicitly contrasts them. You're learning a decision
boundary, not a single point. That's why it generalizes better to unseen schemas.

### 3. The reward curriculum (Progress-SQL)

Static weights have a problem: the shaping terms stay in the objective forever,
so at convergence you're partly optimizing "looks like the gold query" instead of
"is correct". Anneal them:

```
progress:  0.0 ────────────────────► 1.0
shaping:   1.0 ────────────────────► 0.0     (format/syntax/schema/ngram)
exec:      0.5 ────────────────────► 2.0
```

Early training gets dense guidance; late training optimizes the true objective
almost alone. This is a curriculum baked into the *reward* rather than into the
data ordering.

### 4. Reward hacking — see it yourself

Exercise 4 asks you to set `w_ngram` high and `w_exec` to zero. The policy learns
to produce queries that *look* like the gold query without being correct — high
reward, zero accuracy. Every dense proxy you add is a new hacking surface. The
curriculum is a defence: whatever the proxy taught early on, the final objective
is dominated by execution accuracy.

This is the single most valuable habit from this phase: **always evaluate on the
true metric, separately from the training reward.** That's what `greedy_exec_acc`
is for.

## Implementation Steps

### Step 1: `curriculum_weights(progress)`

```python
shaping = max(0.0, 1.0 - progress)      # 1.0 -> 0.0
exec_w  = 0.5 + 1.5 * progress          # 0.5 -> 2.0
return {"format": 0.3 * shaping, "syntax": 0.4 * shaping,
        "schema": 0.6 * shaping, "ngram": 0.3 * shaping, "exec": exec_w}
```

The exact constants don't matter much; the *shape* does. Check the endpoint: at
`progress = 1.0` shaping weights are `0` and `exec` is `2.0`, so execution
accuracy is the entire objective. The tests check that property, not the numbers.

### Step 2: `greedy_exec_acc`

Argmax action per prompt, score with `execution_accuracy`, average. Two things
to be careful about:
- use `execution_accuracy` directly, **not** `combine` — this is the metric, and
  it must be independent of whatever weights you're training with;
- it's evaluation only. Never let it touch the policy update.

### Step 3: `train`

Same loop as Phase 1, with one addition: recompute `weights` each step from
`progress = step / (steps - 1)`, and rebuild `reward_of` with the new weights.
Since `grpo_step` takes `reward_of` as an argument, a fresh closure per step is
the natural way to do it.

## Requirements (what the tests check)

| # | Requirement |
|---|-------------|
| 1 | `curriculum_weights` returns all five components at any progress |
| 2 | All weights are non-negative |
| 3 | Shaping weights decrease monotonically with progress |
| 4 | The `exec` weight increases with progress |
| 5 | At `progress = 1.0` shaping is ~0 and `exec` dominates the sum |
| 6 | At `progress = 0.0` shaping is meaningful (sum of shaping > 0.5) |
| 7 | `greedy_exec_acc` returns a value in `[0,1]` and equals `1.0` for a policy pinned to the correct candidates |
| 8 | Static phased rewards reach `greedy_exec_acc == 1.0` |
| 9 | The curriculum also reaches `greedy_exec_acc == 1.0` |
| 10 | **Phased rewards fix `q5`**: `P(correct) > 0.8` (Phase 1 could not) |
| 11 | Reward is dense — a wrong-but-plausible candidate scores > 0 |
| 12 | Reward is discriminative — the correct candidate outscores the plausible-wrong one for every task |
| 13 | **Reward hacking is reproducible**: with `{"ngram": 1.0}` only, some task has a *wrong* candidate scoring at least as high as the correct one (it's `q5` — the `COUNT(*)` variant ties the correct query on bigram overlap) |

Requirement 13 asserts you can *break* it on purpose. Understanding the failure
mode is the deliverable, not avoiding it.

## Real-Model Track (optional)

`common/rewards.py` plugs straight into TRL:

```python
def make_reward_func(env, task_lookup, weights):
    def reward_func(prompts, completions, **kw):
        return [combine(c, task_lookup(p), env, weights)[0]
                for p, c in zip(prompts, completions)]
    return reward_func

trainer = GRPOTrainer(model=..., reward_funcs=[make_reward_func(env, lookup, W)], ...)
```

For the curriculum, register one reward function per component and update their
coefficients from a callback, or rebuild the reward function each epoch.

## Done When

`python test_phase2.py` is all PASS, `q5` is solved, and you have produced a
reward-hacked policy on purpose and can explain why the curriculum prevents it.
