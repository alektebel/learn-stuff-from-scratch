# Convex sets and convex functions

Numerical convexity tests and the operations that preserve convexity, from scratch.
Implements chapters 2 and 3 of Boyd & Vandenberghe, *Convex Optimization* (the argument
is restated here, never copied).

**Status: not built.** `convexity.py` holds the stubs; `check.py` grades them. This file
describes the work; `solutions/` is the reference.

## What you build

`convexity.py`, nine graded functions:

| Function | What it does |
|---|---|
| `hessian(f, x, h)` | the Hessian by central differences |
| `jacobi_eigenvalues(A)` | the eigenvalues of a symmetric matrix |
| `is_psd(A, tol)` | are all eigenvalues >= -tol (semidefinite counts) |
| `jensen_gap(f, box, n, rng)` | the largest violation of Jensen's inequality |
| `nonneg_sum(fs, weights)` | a nonnegative weighted sum, as a function |
| `pointwise_max(fs)` | the pointwise maximum, as a function |
| `affine_compose(f, A, b)` | the composition `f(A x + b)`, as a function |
| `sublevel_grid_test(f, lo, hi, levels)` | a naive sublevel-set test, kept as a foil |
| `classify(f, box, rng)` | convex iff both real tests agree |

The catalogue of functions the tests are graded on, and the expected table, are given in
the file (they are reference data, not your deliverable).

## Running it

```bash
python3 check.py        # every step, stopping at the first one not written
python3 check.py 3      # just step 3
python3 check.py --all  # do not stop at the first gap
```

A step that raises `NotImplementedError` is reported as **TODO**, not a failure. A step
that asserts and fails is a **FAIL**; an exception is an **ERROR**. The checks import your
`convexity.py`, never `solutions/`.

## The checks

| Step | What it pins down |
|---|---|
| 1 | the Hessian of `x^2` and `x*y`, and `is_psd` on six matrices including the semidefinite `[[0]]` and the trace-zero indefinite `[[0,1],[1,0]]`, plus Jacobi eigenvalues |
| 2 | the Jensen gap is ~0 for `x^2` and strictly positive for `-x^2` and `x*y` |
| 3 | nonnegative sums, pointwise maxima and affine compositions of convex functions are convex; a negative weight is not |
| 4 | the whole catalogue is classified correctly, including `log-sum-exp` (convex) and the geometric mean (concave), and `classify` returns exactly the expected boolean |
| 5 | the naive sublevel test is fooled by `sqrt(abs(x))` but rejects `-x^2`, and `classify` calls `sqrt(abs(x))` non-convex |

## Design decisions

- **Central differences, not forward.** The Hessian uses `f(x ± h)` pairs with `h = 1e-4`.
  Forward differences carry an `O(h)` bias that a semidefinite curvature can hide under.
- **Jacobi eigenvalues, not Cholesky.** A convex function may have a *semidefinite*
  Hessian (the zero matrix at `x = 0` for `x^4`), and Cholesky rejects semidefinite.
  Jacobi returns the spectrum, so the tolerance is a statement about the eigenvalues.
- **A negative PSD tolerance.** `is_psd` accepts any eigenvalue `>= -tol`. The
  tolerance is load-bearing for a zero Hessian (`[[0]]`) and for log-sum-exp's rank-1
  Hessian, whose eigenvalue is exactly `0` up to round-off; without it those would be
  called non-convex.
- **Sweep the whole convex combination, not just the midpoint.** This is robustness,
  not a necessity for one example: a general non-convexity's largest violation over a
  chord can sit at any weight. (For `-x^2` the maximum happens to be at the midpoint.)
  The gap is a maximum over weights, never a minimum, so a single witness is enough.
- **Maximum, never minimum.** The gap is a witness: the largest violation is the one to
  report.
- **Two tests, kept honest.** Jensen is the definition (it finds global violations, and a
  *positive* gap means non-convex *or* concave); the Hessian is the local certificate at
  the box centre. `classify` requires both, so neither test alone carries the answer.

## Limit case

`sqrt(abs(x))` is quasiconvex but not convex: every sublevel set is an interval, so the
naive grid test in step 5 says "convex", while the Jensen gap and `classify` say it is
not. The repeated-eigenvalue and semidefinite cases are the smooth analogue: the answer
must not assume a strictly positive curvature.

## Mutation coverage

`_build/mutations.py` plants one classic bug per mechanism; each is an exact edit to a
copy of the solutions and must be caught by the named step
(`python3 .claude/skills/graded-module/scripts/mutate.py math/optimization/01-convexity math/optimization/01-convexity/_build/mutations.py`).

| Bug | Step |
|---|---|
| `is_psd` tests the trace instead of every eigenvalue | 1 |
| the Hessian off-diagonal divides by `h^2` instead of `4h^2` | 1 |
| `jensen_gap` keeps the minimum over the sweep | 2 |
| `pointwise_max` takes the minimum | 3 |
| `classify` drops the Jensen test (Hessian at the centre only) | 4 |
| the sublevel grid test uses the superlevel sets | 5 |

## Questions

Answers are not given. Work them out from the code and the definitions.

1. Why does `is_psd` need a *negative* tolerance rather than a strictly positive one? Which
   catalogue entry fails if you flip it?
2. `-x^2` gives a positive Jensen gap. Does that prove `-x^2` is non-convex, or only that
   it is not convex? What does a positive gap actually witness?
3. The geometric mean is concave. Which test catches it — Jensen or the Hessian? What does
   that say about whether a single test suffices?
4. Is the pointwise minimum of two convex functions convex? Give a counterexample from the
   catalogue.
5. `sublevel_grid_test` returns `True` for a quasiconvex function. Why can no sublevel-set
   test, however fine the grid, ever prove convexity?

## Limits

- The tests are numerical: they sample. `classify` can, in principle, miss a violation
  confined to a region Jensen never creates a chord across. The two tests make that
  unlikely, not impossible.
- The Hessian is central-difference, so it is only meaningful for functions smooth on the
  sampled scale `h`; `abs(x)` at `x = 0` is evaluated by Jensen, not by a derivative.
- `sublevel_grid_test` is 1-D only (a convex subset of the line is an interval). It is a
  foil for the limit case, not a general convexity test.
