# Continuous Optimization From Scratch

Gradient descent with a fixed step and with Armijo backtracking, heavy-ball momentum, and
Lagrange multipliers for an equality-constrained quadratic. Pure Python 3, standard library
only (no numpy).

Source: *Mathematics for Machine Learning* (Deisenroth, Faisal & Ong), chapter 7
("Continuous Optimization"). The chapter is restated here, not copied: its point is that
the gradient supplies the descent direction but the *step* decides convergence, that a line
search removes the need to know the largest curvature, that momentum damps the zig-zag along
an ill-conditioned valley, and that an equality-constrained quadratic is solved exactly by
its KKT system.

This is the node `foundations-06-optimization` in the skill tree; it follows
`foundations-04-vector-calculus` (the source of the central-difference gradient oracle) and
`foundations-03-matrix-decompositions`. It is the first node that *uses* gradients against a
convergence criterion instead of just checking them.

## Steps

Implement `optimization.py` (the template) step by step, re-running the checker:

| # | What | Theme |
|---|------|-------|
| 1 | `quadratic_gradient` | ∇(½xᵀAx − bᵀx) = Ax − b |
| 2 | `gradient_descent` | fixed step x ← x − t∇f, returning the trajectory |
| 3 | `backtracking_line_search` | Armijo sufficient decrease, and rejecting a non-descent direction |
| 4 | `gradient_descent_backtracking` | a start where the full step diverges still converges |
| 5 | `momentum` | the heavy ball v ← βv + ∇f, checked against a closed recurrence |
| 6 | `max_stable_step` | the fixed-step ceiling 2/L |
| 7 | the condition-number prediction (accept) | iterations grow as (κ−1)/(κ+1) predicts |
| 8 | the ill-conditioned valley (limit) | plain GD zig-zags, momentum does not |
| 9 | `lagrange_quadratic` | the optimum satisfies KKT to 1e-8 (accept) |
| 10 | `kkt_residuals` | stationarity *and* primal feasibility, not one of them |

## Running it

```bash
cd math/foundations/06-optimization
python3 check.py           # stop at the first step you have not written
python3 check.py --all     # run every step (unimplemented ones report TODO)
python3 solutions/optimization.py   # the reference measurements
```

To grade a finished `optimization.py` against the checker in a scratch directory:

```bash
tmp=$(mktemp -d)
cp solutions/*.py check.py "$tmp"/
(cd "$tmp" && python3 check.py --all)   # 10/10 passing
```

## Design decisions

- **Objective ½xᵀAx − bᵀx.** The half cancels in the gradient (∇f = Ax − b) and makes the
  Hessian exactly A, so A's largest eigenvalue *is* the L of the step-size bound. Cost: every
  demo writes an explicit ½.
- **Fixed step *and* backtracking, as separate routines.** The fixed step exposes the 2/L
  divergence boundary; backtracking recovers from a start where that step diverges. Cost: the
  line search needs f as well as ∇f, and several evaluations per iteration.
- **Armijo, not plain decrease.** f(x + αd) ≤ f(x) + c·α·∇fᵀd ties the accepted decrease to
  the directional derivative, so an overshooting step that happens to lower f is still
  rejected. Cost: one extra dot product per trial, and the step is not the exact 1-D minimiser.
- **Heavy-ball momentum.** Its per-mode recurrence e_{k+1} = (1 + β − tλ)e_k − βe_{k−1} is a
  second-order linear recurrence with a closed-form reference, so the checker can compare the
  whole trajectory. Cost: its stability limit is wider, 2(1+β)/λ_max, so the plain 2/L
  boundary does not apply to it.
- **KKT as a linear system, not by elimination.** The block matrix [[Q, Cᵀ], [C, 0]] needs no
  matrix inverse and no C Q⁻¹ Cᵀ. Cost: it is indefinite, so partial pivoting is required.
- **Every descent routine returns its history.** The condition-number, divergence and zig-zag
  claims are about a trajectory, not a final point. Cost: O(n · iterations) memory.

## Limit cases in the checks

- **Step above 2/L diverges; below converges** (step 6): with L = 100, 0.99·(2/L) reaches
  ‖∇f‖ ≤ 1e-8 in ~1140 iterations, while 1.01·(2/L) grows (‖∇f‖ ≈ 1e45). A ceiling of 1/L or
  4/L fails one half of this.
- **Ill-conditioned valley** (step 8): with κ = 1000 the optimal step makes the high-curvature
  mode's multiplier negative, so plain GD reverses direction on almost every one of its 10362
  steps (path length ≈ 1000 for a displacement of √2). Momentum's inertia cuts that to 531
  steps and a path of ≈ 25.
- **Armijo bites** (steps 3–4): at curvature 100 a full step from (1, 1) multiplies f by
  ~10⁴; the search must shrink it, and from a start whose full step diverges it must still
  converge.

## Mutation table

`_build/mutations.py`, run with
`python3 .claude/skills/graded-module/scripts/mutate.py <this dir> <this dir>/_build/mutations.py`.
Every planted bug is caught by the named step.

| Step | Mutation | Why it is caught |
|------|----------|------------------|
| 3 | backtracking accepts alpha0 unconditionally | the overshooting step increases f, so the Armijo/decrease assertions fail |
| 5 | momentum drops βv (v ← ∇f) | the trajectory no longer matches the heavy-ball recurrence from step 2 |
| 6 | ceiling is 1/L instead of 2/L | 1.01·(1/L) is still inside the true 2/L interval, so the "must diverge" case wrongly converges |
| 10 | KKT residuals omit stationarity | a primal-feasible, non-stationary point then reports a zero residual |

## Questions to answer yourself (no answers here)

1. Why is the best fixed step 2/(λ_min + λ_max), not 2/λ_max? What is the resulting contraction
   factor, and why does it depend only on the condition number?
2. Armijo backtracking uses c = 1e-4. What changes if c is close to 1? What if c is negative?
3. Momentum's per-mode recurrence is e_{k+1} = (1 + β − tλ)e_k − βe_{k−1}. For which (β, tλ)
   are its roots real, and when is the √β damping the fast one?
4. The KKT matrix [[Q, Cᵀ], [C, 0]] is symmetric but indefinite. Why can it still be solved by
   Gaussian elimination with partial pivoting, and when would that fail?
5. On the κ = 1000 valley, why is momentum's path length ≈ 25 while its iterate count is 531,
   and what limits each?

## Limits

- Matrices are small (2×2 to 3×3) and dense; `_solve` and `jacobi_eigenvalues` are textbook
  eliminations, not production linear algebra.
- The objectives are quadratic. The convergence-rate prediction is exact only because a
  quadratic's gradient is a fixed matrix times the error; for a general smooth f the constants
  change (and a line search is the only safe step choice).
- `jacobi_eigenvalues` assumes a real symmetric matrix. It is used only to read off λ_min,
  λ_max and the condition number.
- Positive definiteness is assumed, not checked: `lagrange_quadratic` and the descent routines
  require a unique minimum and a coercive quadratic.
