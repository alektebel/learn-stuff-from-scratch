# Graphical models: d-separation, sum-product and max-sum

Conditional independence in Bayesian networks, belief propagation on a factor graph,
Viterbi-style decoding, and the failure of loopy belief propagation on a graph with a
cycle, from scratch. Implements chapter 8 of Bishop, *Pattern Recognition and Machine
Learning* (`bishop:8`; the argument is restated here, never copied). Pure standard
library; no numpy.

**Status: not built.** `graphical.py` holds the stubs; `check.py` grades them. This file
describes the work; `solutions/` is the reference.

## What you build

`graphical.py`, six graded functions. The internal helpers (`_num_values`, `_domains`,
`_cpt_dist`, `_topo_order`, `_make_factors`, `_var_to_factors`, `_joint_probability`,
`_normalise`) and the demo are given.

| Function | What it does |
|---|---|
| `d_separated(parents, a, b, given)` | `True` iff `a` and `b` are d-separated given the set `given` |
| `enumerate_marginals(parents, cpts)` | brute-force node marginals by summing the full joint |
| `sum_product(parents, cpts)` | belief propagation on a tree: exact node marginals |
| `max_sum(parents, cpts)` | Viterbi-style most probable assignment |
| `sample_independence(parents, cpts, n, rng, a, b, given)` | Monte-Carlo test of `a _||_ b \| given` |
| `loopy_bp(parents, cpts, iters)` | loopy BP on a general factor graph, with a convergence flag |

A model is `parents = {var: [parent, ...]}` with `cpts[var]` nested one axis per parent
and one axis per value of `var`:

```text
root:                 [p0, p1]
one parent:           [[p0|par=0, p1|par=0], [p0|par=1, p1|par=1]]
two parents (A, B):   cpt[a][b] -> distribution of var
```

## Running it

```bash
python3 check.py        # every step, stopping at the first one not written
python3 check.py 3      # just step 3
python3 check.py --all  # do not stop at the first gap
```

A step that raises `NotImplementedError` is reported as **TODO**, not a failure. A step
that asserts and fails is a **FAIL**; an exception is an **ERROR**. The checks import your
`graphical.py`, never `solutions/`.

## The checks

| Step | What it pins down |
|---|---|
| 1 | d-separation on hand cases: a chain blocked by the middle, a common cause blocked by the cause, a collider that *blocks* when nothing is observed and *opens* when the collider or one of its descendants is observed |
| 2 | the accept criterion: on a hand V-structure and eight random binary trees, `sum_product` equals `enumerate_marginals` to `1e-9` |
| 3 | max-sum matches the brute-force argmax on a deterministic chain and eight random trees (compared by joint probability, so ties are allowed) |
| 4 | the accept criterion: for three nets (chain, common cause, collider), the `d_separated` verdict agrees with `sample_independence` on 40000 of the checker's own samples, within `0.03` for an independent pair and above `0.10` for a dependent one |
| 5 | the limit: loopy BP on a tree converges to the exact marginals, while the strong-coupling triangle oscillates, reports `converged=False` and differs from the brute-force marginals by more than `1e-3` |

## Design decisions

- **d-separation via the ancestral moral graph, not ad-hoc path signs.** Restrict to the
  ancestors of `{a, b} \| given`, marry every pair of parents that share a child, drop the
  directions and delete the observed nodes; `a` and `b` are d-separated exactly when they
  are disconnected. Moralisation is the whole collider rule, and the descendant case falls
  out for free because a descendant of a collider is an ancestor of an observed node.
- **The belief is `Z * P(v)`; the marginal is the belief divided by its own total.** A
  variable's belief is the product of its incoming factor-to-variable messages. On a tree
  that product is the partition function times the marginal, so dividing by the belief's
  sum recovers the marginal. Dividing by a state count instead is the planted bug.
- **Max-sum runs max-product in log space.** Products underflow and the argmax is what
  matters, so the messages add log factors and take the max. The factor-to-variable
  message stores the argmax assignment, and the decode walks the back-pointers down from a
  chosen root.
- **`sample_independence` returns a gap, not a verdict.** It reports the largest
  `\|P(a,b\|given) - P(a\|given)P(b\|given)\|` over configurations with at least 20 samples.
  The threshold is the checker's business; the estimator stays a measurement.
- **Loopy messages are left un-normalised between sweeps.** `converged` then means the raw
  message vector has stopped moving. This is what makes the triangle's period-2 oscillation
  visible instead of being hidden by a per-sweep rescaling.

## Limit cases

- **A collider is not a chain.** With `A -> C <- B`, `A` and `B` are dependent when `C`
  is observed and independent when it is not — the opposite of a chain. Observing a
  descendant of `C` opens the path just as observing `C` does.
- **A tree is exact.** On any acyclic factor graph belief propagation reaches the true
  marginals to round-off; the checker verifies this both for `sum_product` and for
  `loopy_bp`, which is what catches a variable counting a factor's own message twice.
- **A triangle is neither exact nor stable.** For `A -> B`, `A -> C`, `B -> C` with all
  couplings `0.9`, the factor graph has a `A - B - C - A` cycle. The messages alternate
  between two states forever (`converged=False` after 200 sweeps) and the reported
  marginals are off by about `0.32`.
- **No convergence guarantee.** Loopy BP is not an algorithm with a correctness theorem;
  the triangle is the smallest example where it is both wrong and non-convergent. On a
  weaker coupling it may settle, but even then there is no guarantee it settles on the
  right values.

## Mutation coverage

`_build/mutations.py` plants one classic bug per mechanism; each is an exact edit to a
copy of the solutions and must be caught by the named step
(`python3 .claude/skills/graded-module/scripts/mutate.py math/prml/08-graphical-models math/prml/08-graphical-models/_build/mutations.py`).

| Bug | Step |
|---|---|
| d-separation skips moralisation (treats a collider like a chain) | 1 |
| sum-product normalises by the number of states, not the partition function | 2 |
| max-sum sums the candidate scores instead of taking the max | 3 |
| the loopy variable-to-factor update includes the factor's own message | 5 |
| the loopy limit case reports `converged=True` on the oscillating triangle | 5 |

## Questions

Answers are not given. Work them out from the code and the definitions.

1. Why does moralising the parents of a node capture exactly the collider rule? What would
   go wrong if you married parents across the whole graph instead of only within the
   ancestral set?
2. Why is the belief `prod_{f~v} m_{f->v}(v)` equal to `Z * P(v)` on a tree, and which
   identity fails the moment the factor graph has a cycle?
3. Max-sum and max-product decode the same assignment. Where exactly does the log space
   change the algorithm, and where is it only a numerical convenience?
4. In `sample_independence`, why condition on observed configurations separately rather
   than pooling? What goes wrong when a configuration is rare?
5. The triangle uses strong symmetric coupling. Try to make the messages converge by
   weakening it, then check whether the converged marginals are the true ones.

## Limits

- Domains are small and discrete; the enumeration and reconstruction are exponential in
  the number of variables. The checker only uses five binary variables.
- `sum_product` assumes a tree. On a cyclic model its recursion falls back to an
  all-ones message rather than looping; the intended tool for cycles is `loopy_bp`.
- `loopy_bp` is an undamped parallel (Jacobi) schedule. Damping, a different schedule or a
  better initialisation can change whether and where it converges.
- `sample_independence` is a Monte-Carlo estimate with a fixed seed and a fixed sample
  size; the accept step shows agreement within a tolerance, not an exact test.
- Continuous or hybrid Bayesian networks, junction trees and the sum-product algorithm
  over an arbitrary factor graph are out of scope.
