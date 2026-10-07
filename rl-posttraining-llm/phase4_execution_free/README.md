# Phase 4 — Execution-free reward via graph matching (Graph-Reward-SQL)

**Goal:** compute a correctness reward **without ever running the generated
query against real data**. This is the phase that matters most for your
regulated setting: in production you often *cannot* execute model-generated SQL
against live/sensitive data to grade it during training.

## Why not just execute?

- **Safety/compliance:** running arbitrary generated SQL against production data
  is a non-starter under most data-governance regimes.
- **Cost/latency:** execution against large warehouses is slow and expensive as
  an inner-loop reward.
- **False positives:** you already saw in Phase 1 that result-set equality gives
  a semantically-wrong query full reward when it coincidentally matches. A
  *structural* comparison doesn't have that failure mode.

## The idea

Parse both the predicted and gold SQL into a canonical **graph** (query plan /
AST): nodes = relations, projections, predicates, aggregations, joins; edges =
their relationships. Reward = graph similarity (node/edge overlap, or a learned
matcher), optionally combined with a **stepwise** reward as in Graph-Reward-SQL.
No data is touched — only query structure.

## Exercises

1. **Canonicalize.** Normalize both queries: lowercase keywords, alias-resolve,
   sort commutative operands (`a AND b` == `b AND a`), so that trivially-equal
   queries produce identical graphs.
2. **Build the graph.** Extract a set of typed components:
   `{tables}`, `{join edges}`, `{filter predicates}`, `{projections}`,
   `{aggregations}`. On CPU, a regex/token extractor is enough; the real-model
   track uses `sqlglot` to get a proper AST and query-plan graph.
3. **Score.** Reward = weighted Jaccard over the component sets (or a graph edit
   distance turned into a similarity). Calibrate weights so join/aggregation
   mistakes are penalized more than projection-order differences.
4. **Beat the q5 false positive without executing.** The three `q5` candidates
   that all return `furniture` have *different aggregation structure*
   (`SUM(price*quantity)` vs `COUNT(*)` vs `price DESC`). Show your graph reward
   ranks the correct one first — using only the query text, never the data.
5. **Compare to execution reward** on the full task set: agreement rate, and the
   cases where they disagree (those are exactly the interesting ones).

## `template_graph_reward.py`

Skeleton with canonicalization, component extraction, and the Jaccard scorer.
Validate it against the `q5` candidates in `common/candidates.py`.

## Real-model track

Use `sqlglot` to parse to an AST, walk it into a typed component graph, and
score with weighted graph similarity. Optionally train a small GNN/matcher on
(pred, gold, is_equivalent) pairs mined from Spider. Then run GRPO with this as
the *only* reward — no executor in the loop — and compare final execution
accuracy (measured only at eval time) against Phase 2.

---

## Files in this phase

| File | Use it for |
|------|-----------|
| `guidelines.md` | the full spec: concepts, implementation steps, and the 14 numbered requirements the tests enforce |
| `template_graph_reward.py` | the file you implement |
| `test_phase4.py` | `python test_phase4.py` — checks your work (14 requirements; unimplemented shows as TODO, not failure) |
| `HINTS.md` | progressive hints (Level 1 nudge → Level 3 code) and a debugging table |

Read `guidelines.md` before you start writing code.

## Done when

Your reward ranks the correct `q5` query first without executing anything, and
you can quantify where graph reward and execution reward agree/disagree.
