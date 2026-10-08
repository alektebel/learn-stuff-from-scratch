# Support vector machines from scratch

Sparse kernel machines from the inside out: the maximum-margin classifier as a
constrained quadratic program, its dual, and how the support vectors fall out of the
KKT conditions. Implements the support-vector machine of chapter 7 of Bishop,
*Pattern Recognition and Machine Learning* (`bishop:7`). The argument is restated
here, never copied.

**Status: not built.** `svm.py` holds the stubs; `check.py` grades them. This file
describes the work; `solutions/` is the reference.

## What you build

`svm.py`, the SVM dual solver and the KKT read-out. The helpers `_clip`, the
`dual_objective` diagnostic, the projection `_project` and the demo are given: they
are scaffolding, not the SVM itself.

| Function | What it does |
|---|---|
| `linear_kernel(variance, offset)` | the kernel `k(x, y) = variance (x y + offset)` as a closure |
| `rbf_kernel(length_scale, variance)` | `variance exp(-(x - y)^2 / (2 length_scale^2))` |
| `gram(kernel, xs)` | the symmetric matrix `K_ij = k(x_i, x_j)` |
| `_violates_kkt(i, alphas, ts, E_i, C, tol)` | the soft-margin KKT violation test for point `i` |
| `_bias_from_support_vectors(alphas, ts, K, C, tol)` | the bias `b`, averaged over the free support vectors |
| `smo(Xs, ts, C, kernel, tol, maxit)` | solve the dual by sequential minimal optimisation; return `(alphas, b)` |
| `support_vectors(alphas, tol)` | the indices with `a_i > tol` |
| `decision_function(model, x)` | the decision value `sum_i a_i t_i k(x_i, x) + b` |
| `margin(model, Xs, ts)` | the geometric margin `2 / ||w||` from the support vectors |
| `reference_qp(Xs, ts, C, kernel)` | an independent projected-gradient solver for the same dual |

A kernel is a two-argument callable `k(x, y)`. A model is a dict with keys
`'alphas'`, `'b'`, `'Xs'`, `'ts'`, `'kernel'`.

## The dual and the KKT conditions

The primal soft-margin SVM minimises `1/2 ||w||^2 + C sum_i xi_i` subject to
`t_i (w . phi(x_i) + b) >= 1 - xi_i` and `xi_i >= 0`. Its dual is

```
maximise   W(a) = sum_i a_i - 1/2 sum_ij a_i a_j t_i t_j k(x_i, x_j)
subject to 0 <= a_i <= C  and  sum_i a_i t_i = 0,
```

with `w = sum_i a_i t_i phi(x_i)` and `f(x) = sum_i a_i t_i k(x_i, x) + b`. At the
optimum the KKT conditions split the points three ways: `a_i = 0` (correctly outside
the margin), `0 < a_i < C` (on the margin), and `a_i = C` (inside the margin or
misclassified). Only the points with `a_i > 0` are support vectors.

## Running it

```bash
python3 check.py        # every step, stopping at the first one not written
python3 check.py 3      # just step 3
python3 check.py --all  # do not stop at the first gap
```

A step that raises `NotImplementedError` is reported as **TODO**, not a failure. A
step that asserts and fails is a **FAIL**; an exception is an **ERROR**. The checks
import your `svm.py`, never `solutions/`.

## The checks

| Step | What it pins down |
|---|---|
| 1 | on a separable set SMO returns a feasible solution (`0 <= a_i <= C`, `sum_i a_i t_i = 0`) that classifies every training point |
| 2 | **ACCEPT**: `support_vectors` is exactly the set with `a_i > tol`; every support vector has margin `t_i f(x_i) = 1`; and `margin(...)` equals the primal `2 / ||w||` |
| 3 | **ACCEPT**: the SMO dual objective matches the checker's independent QP reference on a linear and an RBF problem |
| 4 | the soft margin absorbs a mislabelled outlier: the margin stays finite and the outlier's `a_i` saturates at `C` |
| 5 | **LIMIT CASES**: on non-separable data a hard margin (`C = infinity`) leaves the dual unbounded below and `smo` must raise `ValueError`, while the soft margin returns a feasible solution |

The checker carries its own kernel values, Gram matrix and dual solver
(accelerated projected gradient with a bisection projection), so the numeric
comparisons are against an independent implementation, not against a restatement of
yours.

## Design decisions

- **Solve the dual, not the primal.** The dual is an `n`-variable box-constrained
  QP with one linear equality; it is where the kernel appears and where sparsity is
  visible. SMO updates two variables at a time so the equality stays satisfied
  exactly.
- **The second working-set point is chosen at random.** Platt's simplified SMO
  trades a greedy selection for simplicity; a fixed seed makes it reproducible. A
  full pass with no pair changed means the KKT conditions hold, which for the convex
  dual is optimality.
- **The bias is the average of the free support vectors' candidates.** Each free
  support vector pins `b = t_i - sum_j a_j t_j k(x_i, x_j)`; averaging the candidates
  is the numerically stable choice. When no support vector is free (all at `0` or
  `C`, as in the degenerate outlier case) the fallback averages the on-margin
  points.
- **The margin is read off the support vectors, then cross-checked against the
  primal.** `||w||^2 = sum_ij a_i a_j t_i t_j k(x_i, x_j)` works for any kernel; for
  a linear kernel it equals `(sum_i a_i t_i x_i)^2`, so the two are independent
  routes to `2 / ||w||`.
- **Hard margin is `C = infinity`.** The upper box bound disappears; if the dual is
  unbounded below (non-separable data) the passes never settle and `smo` raises.
- **A reference solver with a different algorithm.** `reference_qp` runs accelerated
  projected gradient, so an SMO bug cannot hide behind a shared implementation.

## Limit cases

- **Non-separable data with a hard margin.** Labels `+1, -1, +1` in this order along
  a line cannot be separated by a threshold. The hard-margin dual is unbounded below
  (there is a direction with `Q d = 0` and `sum d_i > 0`), so `C = infinity` has no
  solution and `smo` raises `ValueError`.
- **The same data with a soft margin.** `C = 1` caps every `a_i`; the equality
  `sum_i a_i t_i = 0` is satisfied by putting weight on the conflicting points, and
  the solution is feasible even though the data are not separable.
- **A mislabelled outlier.** With `C = 1`, an isolated wrong-labelled point saturates
  its `a_i = C`; the other points stay inside the margin. A finite margin survives
  the outlier.

## Mutation coverage

`_build/mutations.py` plants one classic bug per mechanism; each is an exact edit to
a copy of the solutions and must be caught by the named step
(`python3 .claude/skills/graded-module/scripts/mutate.py math/prml/07-svm math/prml/07-svm/_build/mutations.py`).

| Bug | Step |
|---|---|
| the SMO KKT test drops `t_i` from the error | 1 |
| the bias update drops the averaging over the support vectors | 2 |
| `support_vectors` keeps the wrong side of the threshold (`a_i < 0`) | 2 |
| `margin` returns `||w||` instead of `2 / ||w||` | 2 |
| the hard-margin limit case claims success on non-separable data | 5 |

## Questions

Answers are not given. Work them out from the code and the definitions.

1. Why does SMO update two variables at once rather than one? What exactly would
   break if a single `a_i` were moved on its own?
2. The dual objective depends on the alphas but not on the bias. Where does `b`
   enter the solution, and why can it be non-unique when every alpha sits at `0` or
   `C`?
3. For a linear kernel the checker compares the support-vector margin with
   `2 / |sum_i a_i t_i x_i|`. Why are those two quantities the same?
4. On non-separable data with a hard margin, exhibit a direction `d` with
   `Q d = 0` and `sum_i d_i > 0`. What does it mean for the primal problem?
5. With `C -> infinity` on separable data, how many points are support vectors, and
   what is `||w||` in terms of the closest points to the boundary?

## Limits

- Everything here is one-dimensional and dense. Real SVMs use multivariate inputs
  (`x` becomes a vector and the linear kernel a dot product) and a sparse or
  decomposition solver for large `n`.
- SMO is implemented with a random second point for clarity: it is correct but not
  the fastest variant. Caching the errors and using a maximal-violating working set
  is the usual speed-up.
- The RBF kernel with distinct inputs shatters any finite sample, so the hard margin
  is always feasible there; non-separability is a property of the linear kernel's
  finite-dimensional feature space.
