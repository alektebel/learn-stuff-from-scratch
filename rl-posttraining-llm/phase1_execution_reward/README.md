# Phase 1 — The sparse execution-accuracy baseline

**Goal:** train a text-to-SQL policy with GRPO using *only* execution accuracy
as the reward — the honest baseline that every paper on your list improves upon
— and feel exactly why it's not enough.

## The reward

```
reward(query) = 1 if execute(query) == execute(gold) else 0
```

Correct, model-agnostic, and requires no labels beyond the gold query. It is
also **sparse**: early in training almost every sampled query is wrong, so the
reward is 0 almost everywhere and there is no gradient telling the policy which
*direction* is better. With a large token-level action space this is fatal for
hard queries.

## Exercises

1. **Wire the loop.** Use `common/tiny_sql_env.py` (environment + executor),
   `common/rewards.py::execution_accuracy`, and `common/grpo.py`. `template_grpo_sql.py`
   has the skeleton; the group is sampled from `common/candidates.py`.
2. **Run it and read the curve.** The correct query *is* in the candidate pool,
   so a lucky sample gets reinforced and the policy eventually concentrates on
   it — but notice how jumpy and luck-dependent it is.
3. **Find the execution-accuracy false positive.** Task `q5` ("highest total
   revenue") has **three** candidates that all return `furniture` on the tiny
   DB, only one of which is semantically correct. Execution reward gives all
   three a 1.0 — so the policy has *no reason* to prefer the correct query.
   Confirm it: `P(correct)` for `q5` stalls even as mean reward hits 1.0.

   ```bash
   cd ../solutions/phase1_execution_reward && python grpo_sql.py
   ```

   This is the concrete motivation for Phases 2–4. Write down, in one sentence,
   why more data would only *reduce* — not eliminate — this problem.

## Real-model track

Swap the tabular policy for `Qwen2.5-0.5B-Instruct` + `trl.GRPOTrainer`, prompt
= schema + question, `reward_funcs=[execution_accuracy_adapter]`. Train on
Spider's train split; evaluate execution accuracy on dev. Expect it to learn
easy single-table queries and stall on multi-join ones — the same starvation,
at scale.

---

## Files in this phase

| File | Use it for |
|------|-----------|
| `guidelines.md` | the full spec: concepts, implementation steps, and the 10 numbered requirements the tests enforce |
| `template_grpo_sql.py` | the file you implement |
| `test_phase1.py` | `python test_phase1.py` — checks your work (10 requirements; unimplemented shows as TODO, not failure) |
| `HINTS.md` | progressive hints (Level 1 nudge → Level 3 code) and a debugging table |

Read `guidelines.md` before you start writing code.

## Done when

You can state precisely why sparse execution reward starves early training, and
you've reproduced the `q5` false positive.
