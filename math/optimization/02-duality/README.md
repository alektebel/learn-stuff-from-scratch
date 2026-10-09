# Lagrange duality

The dual of a convex QP and of an LP, the KKT residuals, and the weak and strong
duality tests, from scratch. Implements chapter 5 of Boyd & Vandenberghe, *Convex
Optimization* (the argument is restated here, never copied).

**Status: not built.** `duality.py` holds the stubs; `check.py` grades them. This file
describes the work; `solutions/` is the reference.

## What you build

`duality.py`, six graded functions:

| Function | What it does |
|---|---|
| `solve_qp_dual(Q, c, A, b)` | the optimal value of the QP dual, `max_{lam>=0} g(lam)` |
| `solve_lp_dual(c, A, b)` | the optimal value of the LP dual, `max -b^T y` s.t. `A^T y = -c`, `y >= 0` |
| `kkt_residuals(Q, c, A, b, x, lam)` | the four KKT residuals at a candidate point |
| `weak_duality_gap(primal, dual)` | the gap `primal - dual`, which weak duality makes `>= 0` |
| `dual_value(Q, c, A, b)` | the QP dual optimum, via `solve_qp_dual` |
| `strong_duality_holds(primal, dual, tol)` | whether the gap is zero within `tol` |

The dense linear-algebra helpers (`_invert`, `_matmul`, ...), the teaching constants and
the demo are given; they are scaffolding, not your deliverable.

## Running it

```bash
python3 check.py        # every step, stopping at the first one not written
python3 check.py 3      # just step 3
python3 check.py --all  # do not stop at the first gap
```

A step that raises `NotImplementedError` is reported as **TODO**, not a failure. A step
that asserts and fails is a **FAIL**; an exception is an **ERROR**. The checks import your
`duality.py`, never `solutions/`.

## The checks

| Step | What it pins down |
|---|---|
| 1 | the QP `min (1/2)(2x1^2+2x2^2)` s.t. `x1+x2>=1` has dual `1/2`, matching its known primal optimum, and a second QP `1/2`-norm with `x1>=2` gives `2`; `dual_value` agrees with `solve_qp_dual` |
| 2 | the LP `min -x1-x2` s.t. `x1<=1, x2<=1, x1+x2<=1.5` and its dual both give `-1.5`, and a second LP gives `-4` |
| 3 | `kkt_residuals` is `< 1e-8` in all four parts at the QP optimum, and a perturbed `x`, a perturbed `lam`, and an infeasible point each raise a positive residual |
| 4 | weak duality: `weak_duality_gap(primal, dual) >= 0` on the QP and LP, and equals `3` on the known pair `(10, 7)` |
| 5 | the no-Slater problem `min e^{-x}` s.t. `x^2/y <= 0`, `y > 0` has dual `~0` against primal `1` (the checker evaluates the dual itself), so `strong_duality_holds` must return `False`, while a zero gap still returns `True` |

## Design decisions

- **The dual function, not the primal, is what you optimise.** For a convex QP the
  inner infimum is available in closed form: `g(lam) = -(1/2)(c+A^T lam)^T Q^{-1}(c+A^T lam) - b^T lam`.
  Maximising it over `lam >= 0` is an unconstrained-in-spirit concave problem.
- **Coordinate ascent with the exact per-coordinate maximiser.** No step size to tune,
  and the box `lam >= 0` is a clip. A gradient method needs a step below `1/||H||`.
- **Basis enumeration for the LP dual.** An optimum is basic; enumerate the bases and
  take the best feasible one. No pivoting rules, exact for the small teaching cases.
- **The gap is `primal - dual`, and it is a number.** Weak duality gives its sign; the
  limit case makes it strictly positive, so a sign error cannot hide.
- **`strong_duality_holds` is a comparison, not a constant.** It must say `False` where
  Slater's condition fails.

## Limit case

The problem `min e^{-x}` s.t. `x^2 / y <= 0`, `y > 0` is convex: the objective is
convex and the constraint set is convex. Its only feasible point is `x = 0` (any
`x != 0` needs `y <= 0`), so the primal optimum is `1` and there is no point that
strictly satisfies the nonlinear constraint — Slater's condition fails. The dual
function is `g(lam) = inf_{x, y>0} e^{-x} + lam x^2/y = inf_x e^{-x} = 0` for every
`lam >= 0` (take `y -> infinity`), so the dual optimum is `0` and the gap is exactly `1`.
Strong duality is not automatic; it is a theorem with a hypothesis, and this is where
the hypothesis bites.

## Mutation coverage

`_build/mutations.py` plants one classic bug per mechanism; each is an exact edit to a
copy of the solutions and must be caught by the named step
(`python3 .claude/skills/graded-module/scripts/mutate.py math/optimization/02-duality math/optimization/02-duality/_build/mutations.py`).

| Bug | Step |
|---|---|
| the QP dual value flips the sign of the lambda offset | 1 |
| the LP dual objective minimises instead of maximises | 2 |
| KKT stationarity drops the `A^T lam` term | 3 |
| weak duality gap returns `dual - primal` | 4 |
| `strong_duality_holds` assumes strong duality always holds | 5 |

## Questions

Answers are not given. Work them out from the code and the definitions.

1. The QP dual is `max_{lam >= 0} g(lam)`. What happens to `g` when you drop the
   constraint `lam >= 0`? Does the optimum move, and does the value change?
2. In the LP dual the equality `A^T y = -c` came from requiring the inner infimum over
   `x` to be finite. What is `g(y)` on the rest of the `y` space, and why can the dual
   optimum never sit there?
3. At the QP optimum all four KKT residuals are zero. Which one would move first if you
   scaled `Q` up by ten, and which primal/dual quantities scale with it?
4. The limit problem has a feasible set that is a single point. The gap is `1`. If you
   replaced the constraint by `x^2/y <= eps`, roughly how does the gap shrink, and does
   Slater's condition hold for any `eps > 0`?
5. `strong_duality_holds` uses `abs(primal - dual) <= tol`. Why is it enough to test the
   absolute difference here, when weak duality already fixes the sign?

## Limits

- The QP dual solver assumes `Q` positive definite and a positive diagonal
  `A Q^{-1} A^T`; a semidefinite `Q` or a redundant constraint can make the dual
  unbounded, which this node does not handle.
- The LP dual enumerates bases and skips singular ones; degenerate LPs (several bases at
  one vertex) are fine here, but the enumeration is exponential and only meant for the
  two-variable teaching cases.
- The residuals are unscaled; a large-magnitude problem would need a relative tolerance.
- The limit case's dual is evaluated on a grid in `check.py`, so its "zero" carries the
  grid's `~1e-5` resolution, far below the gap of `1`.
