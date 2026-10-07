# Phase 6 — Agentic data-analysis post-training (beyond single-shot SQL)

**Goal:** generalize from "write one query" to "analyze the data" — a multi-step
agent that queries, reads the returned tables, reasons over them, and produces an
answer or a chart. This is the "Scaling Generalist Data-Analytic Agents" and
"Rewarding the Scientific Process" territory, plus the multi-agent
(Mixture-of-Minds) and self-improving (EvoDS / CurateEvo) directions.

## What changes vs Phase 5

Phase 5's reward was still ultimately "is the final SQL correct?". Real data
analysis has **no single gold query** — a question like *"which customer segment
is driving the revenue drop?"* is answered by a *chain* of queries and
reasoning over their results. So:

- The unit of reward is the **analysis trace**, not one query.
- You need **process-level reward modeling**: was each analytical step
  justified by the data returned so far? (maps directly onto your
  decision-tree / trace idea).
- Ground truth is scarce → you **generate your own training data** (EvoDS /
  CurateEvo): the agent proposes questions, solves them, an LLM-judge or an
  executable check validates, and the validated traces become new training data.

## Sub-topics and exercises

1. **Multi-step analytic tasks.** Extend `common/` with questions that need
   several queries (e.g. compute a per-country revenue table, then find the
   outlier). Represent an episode as `[query, read_result, reason, query, ...,
   answer]`.
2. **Process-level reward (Rewarding the Scientific Process).** Score each step:
   is the next query motivated by the last result? does the reasoning cite the
   returned numbers? Reuse your Phase 3 PRM machinery on analysis steps.
3. **Answer verification.** For questions with a checkable answer, grade the
   final answer programmatically; for open ones, use an LLM-judge rubric. Keep
   the judge *separate* from the policy to avoid reward hacking.
4. **Mixture-of-Minds (multi-agent).** Split roles — a *planner*, a *SQL writer*,
   a *table-reasoner* — and train them with multi-agent RL (shared or per-agent
   rewards). Start with a fixed planner and only RL the SQL writer; add agents
   incrementally.
5. **Self-evolving data (EvoDS / CurateEvo).** Loop: agent generates candidate
   questions over the schema → solves them → validates (executor / judge) →
   keeps the ones that are hard-but-solvable → adds them to the training set →
   retrain. Measure whether self-generated curriculum improves held-out accuracy.

## `template_data_agent.py`

Skeleton for the multi-step analysis episode, a process-reward hook, an
answer-verifier interface, and the self-data-generation loop.

## Real-model track

This is where you want a real model and `trl`. Build the analysis tool loop
(query + a small pandas-like table reasoner), reward with a process-reward model
plus final-answer verification, and run the EvoDS self-improvement loop for a
few rounds. Track: held-out task accuracy vs number of self-generated rounds.

---

## Files in this phase

| File | Use it for |
|------|-----------|
| `guidelines.md` | the full spec: concepts, implementation steps, and the 16 numbered requirements the tests enforce |
| `template_data_agent.py` | the file you implement |
| `test_phase6.py` | `python test_phase6.py` — checks your work (16 requirements; unimplemented shows as TODO, not failure) |
| `HINTS.md` | progressive hints (Level 1 nudge → Level 3 code) and a debugging table |

Read `guidelines.md` before you start writing code.

## Done when

You have an agent that answers a multi-step analytic question correctly, a
process reward that rewards *justified* steps (not just the final answer), and
one working round of self-generated-data improvement.
