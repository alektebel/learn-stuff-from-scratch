# Phase 3 — Process reward models (step-wise reasoning supervision)

**Goal:** move the reward from the *final answer* to the *reasoning trace*.
Reward-SQL trains a **Process Reward Model (PRM)** that scores each intermediate
step of the chain-of-thought that builds a query, giving a much denser signal
than any outcome reward — and one that is robust to the execution-accuracy false
positive you found in Phase 1 (the *reasoning* to a coincidentally-right answer
is still visibly wrong).

## Concepts

- **Outcome reward model (ORM)** scores the final query. **Process reward model
  (PRM)** scores each step: "given the steps so far, is this next step a correct
  move toward the goal?"
- **Where the labels come from.** Two standard recipes:
  1. *Monte-Carlo roll-outs* (Math-Shepherd style): a step is "good" if
     completing from it reaches the correct answer often. Fully automatic —
     you already have an executor to check the endpoint.
  2. *Human/LLM step annotations*: cheaper to bootstrap, noisier.
- **Using the PRM in RL.** Two options: (a) per-step reward shaping — add the
  PRM score of each step to the GRPO reward; (b) best-of-N / step-level beam
  search at inference. Start with (a).

## Exercises

1. **Define the step schema.** Decompose SQL construction into steps, e.g.
   `link_schema → choose_tables → build_joins → add_filters → add_aggregation →
   finalize`. Represent a trace as an ordered list of steps.
2. **Auto-label with MC roll-outs.** For each prefix of a trace, sample K
   completions with the tabular policy and use `execution_accuracy` at the end
   as the label. This reuses the Phase 1 executor — no new supervision needed.
3. **Train a PRM.** On CPU, a logistic-regression-style scorer over
   hand-features of `(prefix, step)` is enough to feel the mechanism. Features:
   does the step introduce a gold table? a spurious table? a needed filter?
4. **Shape the GRPO reward.** `reward = w_exec·exec + w_prm·mean(prm_step_scores)`.
   Verify it is genuinely denser: on `q1`, the three candidates that execution
   reward flattens to `0.0` now get distinct, nonzero scores.
5. **Find the limit.** Check whether the shaped reward fixes `q5`. It does
   **not** — and understanding why is the point of the phase. MC labels come
   from the executor, so wherever execution accuracy is blind, the labels are
   blind too: `q5` candidates 0 and 1 both execute correctly and receive
   *identical* labels of `1.0`. No label difference, no gradient. Outcome-grounded
   supervision cannot escape an outcome-level blind spot — which is exactly the
   argument for Phase 4's structural, execution-free reward.

## `template_prm.py`

Skeleton with the step schema, MC-labeling loop, a tiny feature-based scorer,
and the reward-shaping hook. Reuses `common/` throughout.

## Real-model track

Generate traces with the base model (`<think>` steps then `<sql>`), auto-label
step prefixes by MC roll-out + executor, fine-tune a small regression head on
the base model's hidden states (or a separate small model) as the PRM, then add
its score to the TRL reward. Compare PRM-shaped GRPO vs outcome-only GRPO on
multi-join queries.

---

## Files in this phase

| File | Use it for |
|------|-----------|
| `guidelines.md` | the full spec: concepts, implementation steps, and the 15 numbered requirements the tests enforce |
| `template_prm.py` | the file you implement |
| `test_phase3.py` | `python test_phase3.py` — checks your work (15 requirements; unimplemented shows as TODO, not failure) |
| `HINTS.md` | progressive hints (Level 1 nudge → Level 3 code) and a debugging table |

Read `guidelines.md` before you start writing code.

## Done when

You have an auto-labeled PRM (no manual step labels), PRM-shaped GRPO gives
denser signal than outcome-only GRPO on execution-failing candidates, and you
can explain in one sentence why it still cannot fix `q5`.

Full requirements and acceptance criteria: `guidelines.md`. Run
`python test_phase3.py` to check yourself.
