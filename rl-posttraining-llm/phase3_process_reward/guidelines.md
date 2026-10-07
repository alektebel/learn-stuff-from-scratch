# Phase 3 Guidelines — Process reward models

## Overview

Move the reward from the *final answer* to the *reasoning trace*, and get the
labels for free from the executor you already have.

Then discover this phase's real lesson: **a PRM auto-labeled by execution
outcomes inherits the executor's blind spots.** It will not save you from `q5`.
That's what Phase 4 is for.

**File to implement:** `template_prm.py`
**Validate with:** `python test_phase3.py`
**Hints:** `HINTS.md`

## Key Concepts

### 1. ORM vs PRM

- **Outcome reward model:** one score for the finished query. What Phases 1–2 used.
- **Process reward model:** a score for *each step*, conditioned on the steps
  before it. "Given what's been built so far, is this a good next move?"

A PRM gives you `n_steps` signals per rollout instead of one, which is why it's
the standard densification move for long reasoning chains.

### 2. What counts as a "step"

With a real LLM the steps are the model's `<think>` lines. On CPU we need
something deterministic, so we decompose the **query into clauses**:

```
"SELECT name FROM products WHERE id = 1"
  -> ["SELECT name", "FROM products", "WHERE id = 1"]
```

Building a query clause by clause is a genuine process, and each prefix is a
partial state we can evaluate. Same mechanism, no GPU.

### 3. Where labels come from: Monte-Carlo roll-outs

This is the important idea, and it's the Math-Shepherd recipe:

> A prefix is **good** if completing it tends to reach a correct answer.

So: take a prefix, sample `k` completions of it, execute each, and label the
prefix with the fraction that came out correct. **No human annotation.** The
executor is the oracle, and you already built it in Phase 1.

Notice what this gives you that outcome reward doesn't. In `q1`, the prefix
`SELECT COUNT(*) FROM customers` belongs to a *wrong* candidate — but it labels
`1.0`, because it *can* be completed correctly (just add the `WHERE`). Outcome
reward calls that candidate a total failure; the PRM correctly says "good start,
bad finish." That's the densification working.

### 4. The blind spot (the lesson)

MC labels are grounded in execution. So wherever execution accuracy is blind,
the labels are blind too.

For `q5`, candidates 0 and 1 both execute correctly, so both get MC label
**exactly 1.0**. Identical labels ⇒ no gradient ⇒ the PRM cannot learn to prefer
the semantically correct one. The blind spot propagates.

You will assert this in the tests. It's not a bug in your implementation — it's
a property of outcome-grounded supervision, and it motivates Phase 4's
*structural*, execution-free reward.

## Implementation Steps

### Step 1: `decompose` — mind the string literals

The trap: it's natural to write `sql.lower()` and slice that. But then
`WHERE country='ES'` becomes `WHERE country='es'`, which matches **zero rows**,
and every downstream execution silently returns the wrong answer. Your PRM then
trains on garbage labels and you'll spend an hour wondering why.

Lowercase a **copy** to find keyword positions; slice the **original**.

### Step 2: `step_features`

Four features (see the template docstring). The one worth care is #1: count
spurious **tables**, not identifiers. If you count all identifiers, `id` — a
column on every table — pollutes the count and the feature stops separating good
steps from bad ones.

### Step 3: `mc_label`

The CPU roll-out recipe: pick a random candidate from the same task's pool, take
its clauses *after* the prefix's length, append them to the prefix, and execute.
Repeat `k` times, return the hit fraction. (With a real model you'd sample `k`
continuations from the policy instead — same idea, better roll-outs.)

### Step 4: `PRM.score` and `fit_step`

Standard logistic regression. The sigmoid needs the two-branch form to avoid
`math.exp` overflowing on large negative `z`. The gradient for sigmoid +
log-loss is just `error = score - label`:

```
w_i -= lr * error * f_i
b   -= lr * error
```

### Step 5: `train_prm`, `prm_trace_score`, `shaped_reward`

Sample a task, sample a candidate, decompose, walk the prefixes, label, fit.
Then `shaped_reward = w_exec * exec + w_prm * mean_step_score`.

## Requirements (what the tests check)

| # | Requirement |
|---|-------------|
| 1 | `decompose` splits a simple query into its clauses in order |
| 2 | **`decompose` preserves case** — `'ES'` does not become `'es'` |
| 3 | `decompose` handles a query with no keywords (single chunk) and empty input |
| 4 | `step_features` returns exactly `FEATURE_DIM` floats, all in `[0,1]` |
| 5 | Coverage is higher for a step naming gold tables than for an irrelevant one |
| 6 | The spurious-table feature is higher for an off-schema step than a gold one |
| 7 | `mc_label` returns a value in `[0,1]` |
| 8 | `mc_label` separates a completable prefix from a hopeless one |
| 9 | `PRM.score` stays in `[0,1]`, including for extreme features (no overflow) |
| 10 | `fit_step` moves the score toward the label |
| 11 | `train_prm` returns a PRM that actually learned (weights not all zero) |
| 12 | `prm_trace_score` returns `[0,1]` and `0.0` for an empty trace |
| 13 | `shaped_reward` reduces exactly to execution accuracy when `w_prm = 0` |
| 14 | `shaped_reward` is dense: it separates candidates that tie on execution alone within a task where execution is informative |
| 15 | **The blind spot is reproduced**: `q5` candidates 0 and 1 get identical MC labels |

## Done When

`python test_phase3.py` is all PASS, and you can explain in one sentence why a
PRM trained on Monte-Carlo execution labels cannot fix `q5` — and what kind of
signal could.

## Real-Model Track

Generate traces with the base model (`<think>` steps, then `<sql>`), auto-label
step prefixes by MC roll-out + executor, and fine-tune a small regression head
(on the base model's hidden states, or a separate small model) as the PRM. Add
its score to the TRL reward. Compare PRM-shaped GRPO against outcome-only GRPO
on multi-join queries, where the reasoning chain is longest and the outcome
signal is sparsest.
