# Phase 6 Guidelines — Agentic data analysis beyond single-shot SQL

## Overview

Generalize from "write one query" to "analyze the data": a chain of queries,
reasoning over what came back, and an answer. Two new problems follow, and this
phase is about both.

**File to implement:** `template_data_agent.py`
**Validate with:** `python test_phase6.py`
**Hints:** `HINTS.md`

## What changes

### There is no gold query any more

Phases 1–5 always had one. "Which category drives revenue?" has *many* valid
query chains, so you grade the **answer** (checkable) and the **process** (how
the answer was reached), not the SQL text.

### The training data doesn't exist

Real analytic questions with verified answers are scarce. The EvoDS/CurateEvo
answer: **generate your own**, and let the executor label them. That's the
second half of this phase.

## Key Concepts

### 1. Process-level reward for analysis

An analysis step is good if it (a) ran, (b) is **grounded** in what the previous
step returned, and (c) isn't a redundant repeat. Of those, grounding is the one
that matters most and the one that's easy to skip.

`cites_previous_result` checks that the step's reasoning actually mentions
values the previous query returned. Without a check like this, an agent happily
writes "the data shows furniture leads" before running any query — fluent,
confident, and unsupported. That is the dominant failure mode of analytic agents,
and no outcome reward catches it, because the final answer can still be right by
luck.

This is "Rewarding the Scientific Process" in miniature: reward *justified*
steps, not just correct conclusions.

### 2. Verification

For checkable questions, grade programmatically. Be careful about three things
that will otherwise produce silent zeros:
- results come back wrapped: `[('furniture',)]`, not `'furniture'` — unwrap
  single-cell results;
- floats need a tolerance, and `160` should match `160.0`;
- the verifier must **never raise** — a solver returning `None` or a stray type
  is a wrong answer, not a crash.

For open-ended questions you'd use an LLM judge. Keep the judge separate from the
policy, or you're training the model to persuade its own grader.

### 3. Unambiguous gold answers

Check your gold answers are actually unique before trusting them. The first
draft of these tasks asked for the top-revenue **country** — but `ES` and `CN`
both total `320.0`, so "the answer" depended on SQLite's tiebreak. The four
tasks shipped here all have unique answers; the tests assert it.

Whenever you auto-generate an evaluation set, tie-checking belongs in the
generator, not in your head.

### 4. The self-improvement loop (EvoDS)

```
generate candidate questions (schema-grounded, from templates or a model)
  -> answer each with the EXECUTOR          (this is the label)
  -> solve each with the current agent
  -> validate against the executor's answer
  -> keep the solved ones as training data
  -> keep the FAILED ones as the curriculum  <- the valuable half
  -> retrain, repeat
```

The failures matter more than the successes: they're the tasks at the edge of
the agent's ability, which is exactly what you want to train on next round.

## Implementation Steps

1. **`cites_previous_result`** — walk the cells of `previous_result`, stringify
   each, and substring-search the lowercased reasoning. Handle the float case:
   for `160.0`, also try `"160"`.
2. **`process_reward`** — average `(ok + grounded + novel) / 3` over the steps.
   The first step gets grounding credit for free (no predecessor). Track earlier
   queries in a set to detect repeats.
3. **`make_verifier`** — unwrap single-cell results recursively, branch on
   numeric vs string, wrap the whole thing in `try/except` returning `0.0`.
4. **`generate_candidate_questions`** — sample a template and a table; if the
   template needs a numeric column, skip tables that have none (`customers` has
   no numeric column — sampling `AVG(price) FROM customers` is a guaranteed
   failure). Execute, discard anything that errors or returns `NULL`, and loop
   until you have `n`. Keep a guard counter so a bad template can't hang you.
5. **`self_improve_round`** — generate, solve, verify, split into kept/failed.

## Requirements (what the tests check)

| # | Requirement |
|---|-------------|
| 1 | Every `ANALYTIC_TASKS` gold answer matches its `reference_sql` output |
| 2 | Gold answers are unambiguous (no ties in the underlying ranking) |
| 3 | `cites_previous_result` finds a value that is present |
| 4 | …returns `False` for `None`/empty previous results |
| 5 | …matches `"160"` against `160.0`, and is case-insensitive |
| 6 | `process_reward` is in `[0,1]` and `0.0` for an empty episode |
| 7 | A grounded, successful, non-redundant episode scores higher than a hallucinated one |
| 8 | A repeated query is penalized as redundant |
| 9 | `make_verifier` accepts the exact answer and rejects a wrong one |
| 10 | …unwraps single-cell results like `[('furniture',)]` |
| 11 | …tolerates float/int and case differences |
| 12 | …returns `0.0` rather than raising on garbage input |
| 13 | `generate_candidate_questions` returns exactly `n` schema-grounded tasks |
| 14 | Every generated task's `reference_sql` executes and matches its gold answer |
| 15 | `self_improve_round` returns all four keys with consistent counts |
| 16 | A perfect solver gets `accuracy == 1.0`; a broken solver gets `0.0` and a non-empty `failed` list |

## Done When

`python test_phase6.py` is all PASS. You have a process reward that punishes
ungrounded reasoning, a verifier that doesn't lie to you, and a loop that
manufactures its own executor-labeled training data.

## Real-Model Track

Give the model a tool loop (`run_sql`, plus a small table-reasoning helper),
have it emit reasoning and queries, and reward with
`w_proc * process_reward + w_ans * verify(answer)`. Then run the EvoDS loop for
several rounds and plot held-out accuracy against round number — that curve is
the actual claim of the self-evolving-agent papers, and it's the one worth
reproducing. For **Mixture-of-Minds**, split into planner / SQL-writer /
table-reasoner and train only the SQL-writer first, adding agents one at a time.
