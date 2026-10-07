# Phase 5 Guidelines — Multi-turn RL over an unknown schema

## Overview

Stop handing the model the schema. Make **schema discovery an action**, grade the
agent on whether what it discovered was enough to answer the question, and train
the whole episode with GRPO. This is TRUST-SQL / MARSQL territory, and it's the
step most relevant to a real "analyze the data in a database" agent.

**File to implement:** `template_agent_loop.py`
**Validate with:** `python test_phase5.py`
**Hints:** `HINTS.md`

## What changes from Phases 1–4

Everything so far was single-shot: prompt in, query out, reward. Now an episode
is a **trajectory** of tool calls:

```
question (schema NOT in the prompt)
  -> describe(orders)     -> "orders(id, customer_id, product_id, quantity, order_date)"
  -> describe(products)   -> "products(id, name, category, price)"
  -> final                -> write the query from what was discovered
```

Two new problems come with that:

1. **Credit assignment across turns.** The reward arrives at the end, but the
   decisions were spread over several turns. The GRPO answer is simple and
   effective: compute one advantage for the whole trajectory, then apply it to
   **every turn** in that trajectory. Good episodes make all their actions more
   likely; bad episodes make all of theirs less likely.
2. **Exploration has a cost.** Without one, the agent describes every table
   every time. `turn_shaping` charges `STEP_COST` per call.

## Key Concepts

### 1. The action space is tools, not queries

`ACTIONS = [describe_customers, describe_products, describe_orders, final]`.
The agent never picks a query. The query is written at the end by `write_sql`,
a **fixed** writer that can only produce the correct query if every table the
task needs was discovered:

```python
if needed_tables <= discovered_tables:  return correct_query
else:                                   return a query that fails
```

That coupling is the entire design. It converts "did you explore well?" into
"did you answer correctly?", so a plain outcome reward trains exploration.

> One subtlety worth noting: the failing fallback must *really* fail. An earlier
> version of this exercise used `q5`'s candidate 2 as the fallback — which
> executes correctly by coincidence (the Phase 1 false positive again). The agent
> then got full reward for discovering *nothing* on `q5`. The fallback is now
> candidate 3, which errors on every task. When you build reward couplings, check
> that your "failure" branch actually fails.

### 2. Conditioning the policy on the turn

`policy_index(task_idx, turn) = task_idx * MAX_TURNS + turn` gives each
(task, turn) its own row of logits. This is what lets the agent learn a
*sequence* — "describe orders, then products, then stop" — instead of one fixed
action repeated. It's a crude stand-in for an LLM conditioning on its context.

### 3. Trajectory-level GRPO

Identical to Phase 0, one level up:

```
for each task:
    run G rollouts
    rewards    = [trajectory_reward(t) for t in rollouts]
    advantages = group_relative_advantages(rewards)     # same function!
    for each rollout, for each (row, action) it took:
        grad[row][j] += advantage * (1[j==action] - probs[row][j])
apply ascent, normalized by the number of (trajectory, turn) updates
```

Note you must record the `(row, action)` pairs *as the rollout happens* — after
the fact you can't tell which turn produced which action.

### 4. What turn shaping buys you

Train twice, `w_shaping=0.0` and `w_shaping=0.3`:

| | tasks solved | total greedy turns |
|---|---|---|
| no shaping | 5/5 | 20 |
| shaping | 5/5 | **16** |

Same accuracy, less probing: `q1` and `q2` learn to describe their one table and
call `final` immediately instead of burning the whole turn budget. On a real
system where each tool call is a database round-trip, that's the difference
between a usable agent and an expensive one.

## Implementation Steps

1. **`policy_index`** — one line: `task_idx * max_turns + turn`.
2. **`rollout`** — loop up to `max_turns`; sample an action; on `final`, set
   `finished = True` and break; otherwise call `env.describe(table)`, append
   `(action_name, observation)` to `steps`, add the table to `discovered`. After
   the loop (either exit path), set `final_sql = write_sql(discovered, task)`.
3. **`turn_shaping`** — `len(gold_tables & discovered) * 1.0 - STEP_COST * len(steps)`.
   Using a set for `discovered` gives you the no-double-counting requirement for
   free.
4. **`trajectory_reward`** — `execution_accuracy(final_sql, task, env.db) +
   w_shaping * turn_shaping(...)`.
5. **`train`** — the loop in concept 3. Use a **fresh `ToolEnv` per rollout** so
   call counts don't leak between episodes.

## Requirements (what the tests check)

| # | Requirement |
|---|-------------|
| 1 | `policy_index` is unique for every (task, turn) pair and fits the policy |
| 2 | `rollout` returns a `Trajectory` and never exceeds `max_turns` steps |
| 3 | `rollout` records one step per tool call and populates `discovered` |
| 4 | A policy pinned to `final` produces an episode with 0 steps and `finished=True` |
| 5 | `rollout` always sets `final_sql` |
| 6 | Discovering all needed tables yields a query that executes correctly |
| 7 | Discovering nothing yields a query that fails (the coupling holds) |
| 8 | `turn_shaping` gives +1 per distinct gold table found |
| 9 | `turn_shaping` charges `STEP_COST` per call and doesn't double-count repeats |
| 10 | `trajectory_reward` equals execution accuracy exactly when `w_shaping=0` |
| 11 | `train` returns a policy with a row for every (task, turn) |
| 12 | The trained agent solves **all 5 tasks** greedily |
| 13 | The trained agent discovers every table each task needs |
| 14 | Turn shaping reduces total greedy turns without losing accuracy |

## Done When

`python test_phase5.py` is all PASS: the agent discovers the schema it needs —
not the whole schema — and turn shaping makes it efficient about it.

## Real-Model Track

Replace the tabular policy with an LLM tool-use loop: system prompt lists the
tools, the model emits a tool call, you execute it and append the observation,
repeat to a turn budget, then grade the final query. Train with TRL's GRPO over
whole trajectories (reward on the last step). Two extensions worth doing:
- add `sample(table)` so the agent can inspect *values*, which matters for
  guessing enum-like columns;
- evaluate on a schema the agent never saw in training — that generalization
  test is the real point of learning discovery rather than memorizing tables.
