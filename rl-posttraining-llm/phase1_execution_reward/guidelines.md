# Phase 1 Guidelines — The sparse execution-accuracy baseline

## Overview

Wire your Phase 0 GRPO onto a real text-to-SQL environment, with the reward
every paper starts from: **execution accuracy**. Then find out, empirically,
why nobody stops there.

**File to implement:** `template_grpo_sql.py`
**Validate with:** `python test_phase1.py`
**Hints:** `HINTS.md`

## Key Concepts

### 1. The reward

```
reward(query) = 1.0 if execute(query) == execute(gold_query) else 0.0
```

Result sets are normalized first (rows sorted, floats rounded — see
`common/tiny_sql_env.py::_normalize`) so that row order and float jitter don't
cause spurious mismatches. This is the standard "execution accuracy" metric from
Spider/BIRD, in miniature.

Its virtues are real: it needs no step labels, it's model-agnostic, and it
measures what you actually care about.

### 2. Why it's not enough — problem one: sparsity

Early in training almost every sampled query is wrong, so the reward is `0`
nearly everywhere. Recall from Phase 0 what happens to a group where all `G`
rewards are identical: `std == 0`, every advantage is `0`, **no gradient at
all**. The policy learns nothing from that batch.

In this phase the correct query is sitting in a 4-candidate pool, so a lucky
sample finds it and gets reinforced. With a real token-level policy the space is
effectively infinite and "get lucky" never happens for hard multi-join queries.
That's the starvation Phase 2 fixes.

### 3. Why it's not enough — problem two: false positives

This is the one you should really internalize, and you're going to reproduce it.

Execution accuracy compares **result sets**, not **meaning**. On small data,
semantically different queries collide. Task `q5` ("which category has the
highest total revenue?") has three candidates:

| # | Query intent | Returns |
|---|--------------|---------|
| 0 | `ORDER BY SUM(price*quantity)` — **correct** | `furniture` |
| 1 | `ORDER BY COUNT(*)` — wrong metric | `furniture` |
| 2 | `products ORDER BY price DESC` — ignores orders entirely | `furniture` |

All three score **1.0**. The policy has no reason to prefer the correct one, so
`P(correct)` for `q5` sits near chance (~0.25–0.3) while the mean reward happily
climbs to 1.0. **Your reward function is lying to you and your metric looks
great.** That is the motivation for Phases 3 and 4.

More data shrinks the collision probability but never eliminates it — any finite
table admits queries that agree on it and disagree in general.

## Implementation Steps

### Step 1: `reward_of_factory`

The RL loop speaks in integers (`prompt`, `action`); the environment speaks in
tasks and SQL strings. This factory is the adapter:

```
prompt index -> qids[prompt] -> task_by_qid(qid)  -> Task
action index -> CANDIDATES[qid][action]           -> completion string
```

Then `combine(completion, task, env, weights)`. Note it returns a
**tuple** `(total, breakdown)` — return only the total.

### Step 2: `train`

Nearly identical to Phase 0's loop, except `grpo_step` from `common/grpo.py`
does the gradient work for you. Per step:

```python
mean_r = grpo_step(policy, reward_of, None,      # None = no reference policy
                   list(range(len(qids))),        # every task in the batch
                   group_size=8, rng=rng)
```

Print every ~40 steps so you can watch the curve. The third argument is the
reference policy for KL regularization — `None` here, you'll want it once the
policy is a real LLM that can drift into gibberish.

### Step 3: `prob_correct`

`policy.probs(p)[CORRECT_INDEX[qids[p]]]` for each prompt. This is diagnostics
only — never feed it to training, or you've replaced RL with supervised
learning on the answer key.

## Requirements (what the tests check)

| # | Requirement |
|---|-------------|
| 1 | `reward_of_factory` returns a callable giving `1.0` for the correct candidate |
| 2 | …and `0.0` for a candidate that errors or returns the wrong rows |
| 3 | Rewards are `0.0`/`1.0` only — execution accuracy is binary |
| 4 | `train` returns `(policy, qids, env)` with a policy over all 5 tasks |
| 5 | `prob_correct` returns one probability per task, each in `[0,1]` |
| 6 | Training raises mean execution reward above `0.9` |
| 7 | The policy learns `q1`–`q4`: `P(correct) > 0.8` |
| 8 | **The `q5` false positive is reproduced**: `P(correct)` for `q5` stays below `0.5` even though mean reward is high |
| 9 | Sanity check on the environment: the three `q5` candidates really do all score `1.0` |
| 10 | Training is deterministic given a seed (same seed → same result) |

Requirement 8 is the unusual one: **the test asserts your agent fails on `q5`**.
If it passes `q5`, you've accidentally leaked information the execution reward
cannot contain — check you're not scoring with anything but `{"exec": 1.0}`.

## Done When

`python test_phase1.py` is all PASS, and you can write one sentence explaining
why adding more rows to the database would reduce but never eliminate the `q5`
problem.
