# Vector Calculus From Scratch

Gradients of the standard matrix expressions, the central-difference checker that
verifies them, and the second-order Taylor expansion with the Hessian. Pure Python 3,
standard library only (no numpy).

Source: *Mathematics for Machine Learning* (Deisenroth, Faisal & Ong), chapter 5
("Vector Calculus"). The chapter is restated here, not copied: its point is that the
derivative of a matrix expression is another matrix expression, and that a central
difference is an independent oracle for it.

This is the node `foundations-04-vector-calculus` in the skill tree; it follows
`foundations-01-linear-algebra`. The finite-difference checker (`central_difference` /
`relative_gradient_error`) is meant to be imported by every later node that computes a
gradient, so its step-size behaviour is defined once, here.

## Steps

Implement `vector_calculus.py` (the template) step by step, re-running the checker:

| # | What | Theme |
|---|------|-------|
| 1 | `quadratic_gradient` | ∇(xᵀAx) = (A + Aᵀ)x, correct for non-symmetric A |
| 2 | `least_squares_gradient` | ∇‖Ax − b‖² = 2Aᵀ(Ax − b), and its sign |
| 3 | `logdet_gradient` | ∇ log det X = X⁻ᵀ (transpose matters) |
| 4 | `trace_linear_gradient` | ∇ tr(A X) = Aᵀ |
| 5 | `trace_quadratic_gradient` | ∇ tr(XᵀA X) = (A + Aᵀ)X |
| 6 | `central_difference`, `relative_gradient_error` | the shared finite-difference checker |
| 7 | `quadratic_hessian` | ∇²(xᵀAx) = A + Aᵀ |
| 8 | `taylor_second_order` | remainder shrinks as h³ |
| 9 | `error_curve` | the U-shaped error over h |

## Running it

```bash
cd math/foundations/04-vector-calculus
python3 check.py           # stop at the first step you have not written
python3 check.py --all     # run every step (unimplemented ones report TODO)
python3 solutions/vector_calculus.py   # the reference measurements
```

To grade a finished `vector_calculus.py` against the checker in a scratch directory:

```bash
tmp=$(mktemp -d)
cp solutions/*.py check.py "$tmp"/
(cd "$tmp" && python3 check.py --all)   # 9/9 passing
```

## Design decisions

- **Quadratic gradient: (A + Aᵀ)x, not 2Ax.** They agree only when A is symmetric. The
  general form carries the transpose explicitly, so it stays correct on the non-symmetric
  A of the limit case. Cost: one extra matrix add.
- **Central, not forward, differences.** Forward error is O(h); central is O(h²). At
  ordinary h the central estimate reaches 1e-6, which is what later nodes want to trust.
  Cost: a second function evaluation per coordinate, and a new failure mode at tiny h
  (round-off O(ε/h)).
- **One shared checker, not one per expression.** `central_difference` +
  `relative_gradient_error` live here and are imported later, so the step size is chosen
  once. Cost: matrix expressions must be wrapped as scalar functions of a flat vector.
- **log det via the inverse.** Return X⁻ᵀ through a Gauss-Jordan `_inverse`; the transpose
  is the lesson (Jacobi: d det = det·tr(X⁻¹ dX)). Cost: O(n³) even for a symmetric X,
  where the transpose is invisible.
- **Hessian in closed form.** `quadratic_hessian` returns A + Aᵀ; the finite-difference
  Hessian is used only in the checker. For a quadratic the second-order Taylor expansion is
  exact, so the h³ test uses a cubic scalar function, whose third derivative is nonzero.

## Limit cases in the checks

- Non-symmetric A: (A + Aᵀ)x ≠ 2Ax, so a `2Ax` implementation fails step 1. Likewise
  γ tr(XᵀA X) = (A + Aᵀ)X ≠ A X (step 5).
- Non-symmetric X with det X > 0: X⁻ᵀ ≠ X⁻¹, so a missing transpose in `logdet_gradient`
  fails step 3.
- h too small: at h = 1e-12 the subtraction in a central difference loses its digits and
  the error is ~1e-4; the sweep in step 9 / the demo shows the U shape, with a best h
  around 1e-5 and truncation dominating for large h.

## Mutation table

`_build/mutations.py`, run with
`python3 .claude/skills/graded-module/scripts/mutate.py <this dir> <this dir>/_build/mutations.py`.
Every planted bug is caught by the named step.

| Step | Mutation | Why it is caught |
|------|----------|------------------|
| 1 | gradient of xᵀAx as 2A x | non-symmetric A: 2Ax ≠ (A+Aᵀ)x |
| 2 | sign of ∇‖Ax − b‖² flipped | x − t∇f becomes ascent, so f(x − t∇f) > f(x) |
| 3 | log det returns X⁻¹ not X⁻ᵀ | non-symmetric X: X⁻¹ ≠ X⁻ᵀ |
| 4 | tr(A X) gradient returns A not Aᵀ | non-symmetric A |
| 5 | tr(XᵀA X) gradient returns A X | missing symmetrisation |
| 6 | forward differences instead of central | O(h) error ≈1e-5 at h=1e-5, above the 1e-7 bound |
| 7 | Hessian returns A not A+Aᵀ | Hessian must be symmetric; differs from finite differences |
| 8 | second-order Taylor drops the quadratic term | remainder becomes O(h²), ratio ≈4 not ≈8 |

## Questions to answer yourself (no answers here)

1. For which matrices A does `quadratic_gradient` return 2Ax even without special-casing?
2. Why is the best central-difference step size roughly ε^(1/3), and why does it differ
   for a forward difference?
3. `logdet_gradient` is X⁻ᵀ. When is X⁻ᵀ = X⁻¹? What does that say about symmetry?
4. The second-order Taylor remainder of a quadratic form is zero for every h. What is the
   remainder's order for a general smooth f, and how does that bound the gradient check?
5. Why must a Hessian be symmetric, from its definition as the matrix of second partial
   derivatives?

## Limits

- Matrices are small (2×2 to 3×3) and dense; `_det`/`_inverse` are Gauss/LU eliminations,
  not production linear algebra.
- `logdet_gradient` requires det X > 0 (the real logarithm). No numpy, so there is no SVD
  or Cholesky here; the reference for it lives in the neighbouring foundations nodes.
