# Phase 4 Guidelines — Execution-free reward via graph matching

## Overview

Build a reward that scores a generated query **without running it**. This is the
phase that matters most for a regulated setting, and it's the one that finally
solves `q5` — the failure you've been carrying since Phase 1.

**File to implement:** `template_graph_reward.py`
**Validate with:** `python test_phase4.py`
**Hints:** `HINTS.md`

## Why you'd want this

- **Compliance.** Executing arbitrary model-generated SQL against production
  data during training is a non-starter under most data-governance regimes. An
  execution-free reward removes the data from the training loop entirely.
- **Cost and latency.** Execution against a real warehouse is far too slow to
  sit in an inner RL loop that needs `G` rollouts per prompt per step.
- **Correctness.** Result-set equality has false positives — that's `q5`.
  Structural comparison doesn't share that failure mode, because it compares
  what the query *means to do*, not what it happened to return.

## Key Concepts

### 1. Canonicalize, then compare structure

Parse both queries into a **typed component graph** and score the overlap:

| Component | Captures | Example |
|-----------|----------|---------|
| `tables` | which relations are scanned | `{orders, products}` |
| `aggs` | aggregate expressions | `{sum(price*quantity)}` |
| `filters` | value predicates | `{country='es'}` |
| `joins` | which columns are joined | `{id\|product_id}` |
| `modifiers` | meaning-changing keywords | `{not in, group by, limit}` |

Reward = weighted Jaccard across the components. No data touched.

### 2. Normalization is most of the work

Two queries that mean the same thing must produce the same graph, or you're
rewarding formatting:

- **Whitespace:** `SUM(p.price * o.quantity)` vs `SUM(p.price*o.quantity)`.
  Strip it inside aggregate expressions.
- **Aliases:** `p.price` and `products.price` and `price` are the same column.
  Strip the prefix.
- **Aliases as tables:** `FROM orders o` makes `o` look like a table. Intersect
  your table set with `SCHEMA_TABLES` to drop the noise.
- **Join conditions vs filters:** `o.product_id = p.id` is a *join*;
  `country = 'ES'` is a *filter*. Distinguish them by whether the right-hand
  side is a literal.

### 3. The lesson: your reward only sees what your graph encodes

Build the graph with only `tables`/`aggs`/`filters`/`joins` and run `q3`:

| Candidate | Query | Score |
|-----------|-------|-------|
| 0 (correct) | `WHERE id NOT IN (SELECT product_id ...)` | 1.0 |
| 2 (inverted) | `WHERE id IN (SELECT product_id ...)` | 1.0 |

**Exactly the same score for logically opposite queries.** Same tables, same
columns, no aggregates, no value filters — the graph simply has no slot for
negation, so the reward is blind to it.

That's why `modifiers` is a required component. And it generalizes: an
execution-free reward is only as good as its structural vocabulary. Execution
reward is blind where *data* collides; graph reward is blind where your
*encoding* collides. Neither is universally safe — which is the real argument
for combining them (and for the ablation table in Phase 7).

## Implementation Steps

### Step 1: `canonicalize`
Strip, drop a trailing `;`, collapse whitespace runs with `re.sub(r"\s+", " ", s)`.

### Step 2: `to_graph`
Use the provided regexes. Order of operations that works:
1. `tables` — `TABLE_RE`, lowercase, then `&` with `SCHEMA_TABLES`.
2. `aggs` — `AGG_RE` gives `(fn, arg)`. Remove whitespace from `arg`, strip alias
   prefixes with `re.sub(r"\b[a-z_][a-z0-9_]*\.", "", arg)`, rebuild `fn(arg)`.
3. `filters` — `FILTER_RE` gives `(col, op, val)`. Keep it only if `val` is a
   literal (starts with a quote) or the column isn't a key column.
4. `joins` — same matches, but keep the ones where both sides are qualified
   columns. Sort the pair before joining so `a=b` and `b=a` collide.
5. `modifiers` — substring search for each marker, with the `not in` guard.

### Step 3: `jaccard`
`len(a & b) / len(a | b)`, and **return 1.0 when both sets are empty**. Two
queries that both have no `WHERE` clause agree perfectly about filters; scoring
that `0.0` would punish every simple query.

### Step 4: `weighted_jaccard` and `graph_reward`
Sum `weights[name] * jaccard(...)`, divide by `sum(weights.values())` so the
result stays in `[0,1]` regardless of the weights you pass.

## Requirements (what the tests check)

| # | Requirement |
|---|-------------|
| 1 | `canonicalize` collapses whitespace and drops the trailing `;` |
| 2 | `to_graph` returns a set for every name in `COMPONENTS` |
| 3 | Table extraction ignores aliases (`FROM orders o` → `{orders}`, not `{orders, o}`) |
| 4 | Aggregates normalize across whitespace and aliases |
| 5 | Join conditions are not counted as value filters |
| 6 | `modifiers` distinguishes `IN` from `NOT IN` |
| 7 | `jaccard` is correct on ordinary sets, and `1.0` on two empty sets |
| 8 | `weighted_jaccard` stays in `[0,1]` and gives `1.0` for identical graphs |
| 9 | `graph_reward(gold, gold) == 1.0` for every task |
| 10 | **`graph_reward` never executes anything** — the test injects a poisoned executor that raises if called |
| 11 | **`q5` is solved without execution**: the correct candidate scores strictly highest |
| 12 | **`q3` negation is caught**: `NOT IN` outscores the inverted `IN` variant |
| 13 | The correct candidate ranks strictly first on *all five* tasks |
| 14 | Reward is graded, not binary — wrong candidates get a spread of scores |

## Done When

`python test_phase4.py` is all PASS. You now have a reward that ranks the correct
query first on every task while reading **zero rows of data** — the core result
of Graph-Reward-SQL, and the training configuration you'd actually be allowed to
run in a regulated environment.

## Real-Model Track

Swap the regexes for a real parser: `sqlglot.parse_one(sql)` gives you an AST,
and `.find_all(exp.Table)`, `exp.Column`, `exp.Join`, `exp.Where` walk it
properly (handling subqueries, CTEs, and nested expressions the regexes will
mangle). Then either keep weighted Jaccard, or train a small matcher on
`(pred, gold, is_equivalent)` pairs mined from Spider. Finally, run Phase 2's
GRPO loop with `graph_reward` as the *only* signal and measure execution
accuracy at eval time only — that's the number that proves you can train without
touching data.
