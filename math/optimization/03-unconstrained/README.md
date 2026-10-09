# Unconstrained minimisation

Gradient descent with backtracking and Newton's method with the Newton-decrement
stopping rule, from scratch. Implements chapter 9 of Boyd & Vandenberghe, *Convex
Optimization* (the argument is restated here, never copied).

**Status: not built.** `minimise.py` holds the stubs; `check.py` grades them. This file
describes the work; `solutions/` is the reference.

## What you build

`minimise.py`, four graded functions (plus the given `solve`):

| Function | What it does |
|---|---|
| `backtracking_line_search(f, grad, x, d, alpha, beta)` | the Armijo step size along `d`: start at 1 and shrink by `beta` until `f(x+td) <= f(x) + alpha t g^T d` |
| `gradient_descent(f, grad, x0, tol, maxit)` | steepest descent with the backtracking step; `-> (x, f(x), history)` |
| `newton_decrement(grad_vec, hess_mat)` | the squared Newton decrement `g^T H^{-1} g`, solving `H y = g` and returning `g^T y` |
| `newton(f, grad, hess, x0, tol, maxit, line_search=True)` | Newton's method; `-> (x, decrement_history, iterations)` |

The Gaussian-elimination helper `solve(A, b)`, the vector helpers and the demo are given;
they are scaffolding, not your deliverable.

## Running it

```bash
python3 check.py        # every step, stopping at the first one not written
python3 check.py 3      # just step 3
python3 check.py --all  # do not stop at the first gap
```

A step that raises `NotImplementedError` is reported as **TODO**, not a failure. A step
that asserts and fails is a **FAIL**; an exception is an **ERROR**. The checks import your
`minimise.py`, never `solutions/`.

## The checks

| Step | What it pins down |
|---|---|
| 1 | the backtracking step satisfies Armijo sufficient decrease; gradient descent reaches the optimum of the convex quadratic `1/2 x^T A x - b^T x` and of `e^x1 - x1 + e^x2 - x2` to `1e-4` |
| 2 | **ACCEPT** — on `e^x - x` Newton's decrement sequence shows a log-log slope of ~2: the error squares each iteration (digits double) |
| 3 | Newton converges on a quadratic in a handful of iterations, far fewer than gradient descent on the same `tol` |
| 4 | **LIMIT** — undamped Newton on `sqrt(1 + x^2)` maps `x -> -x^3` and runs away from `x = 2`, while damped Newton converges |
| 5 | a singular-Hessian start is handled safely: the decrement stays finite and positive, and Newton still reaches the flat valley |

## Design decisions

- **Backtracking, not a fixed step.** The step `1/L` needs the Lipschitz constant of the
  gradient, which is not known; backtracking finds a sufficient-decrease step from the
  function values alone. A step above `2/L` diverges, so the fixed-step shortcut is a real
  bug, not a style choice.
- **The Newton decrement is the stopping criterion.** Solving `H y = g` gives both the
  direction `-y` and the scalar `decrement = g^T y`. Near the optimum the decrement is
  twice the duality gap of the local quadratic model, so `decrement / 2 <= tol` stops at a
  controlled suboptimality with no separate gradient-norm test.
- **A ridge for singular Hessians.** A singular `H` is not an error in a convex problem;
  adding `lam*I` with growing `lam` turns the solve into a well-posed one and keeps the
  step a descent direction on a flat valley.
- **Line search on Newton by a flag.** `line_search=False` exposes the raw step. It is the
  honest way to see the limit case: without damping the raw Newton step has no safeguard,
  and from a far start it overshoots and diverges.

## Limit case

The function `f(x) = sqrt(1 + x^2)` is smooth and convex with minimum at `0`. Its gradient
is `x / sqrt(1 + x^2)` and its Hessian is `(1 + x^2)^{-3/2}`, so the undamped Newton
iteration is

```
x_{k+1} = x_k - f'(x_k) / f''(x_k) = x_k - x_k (1 + x_k^2) = -x_k^3.
```

The map `x -> -x^3` has derivative magnitude `3x^2 > 1` for `|x| > 1`, so from `x = 2` the
iterates run away (`2, -8, 512, ...`). Newton's convergence is only *local*: the quadratic
rate in step 2 is a statement about the basin around the optimum. Damping with the
backtracking line search caps each step by the requirement that `f` decrease, and the same
start then converges.

## Mutation coverage

`_build/mutations.py` plants one classic bug per mechanism; each is an exact edit to a
copy of the solutions and must be caught by the named step
(`python3 .claude/skills/graded-module/scripts/mutate.py math/optimization/03-unconstrained math/optimization/03-unconstrained/_build/mutations.py`).

| Bug | Step |
|---|---|
| backtracking accepts any step (Armijo test dropped) | 1 |
| `gradient_descent` uses a fixed step (ignores line search) | 1 |
| `newton` uses the gradient step (drops the Hessian) | 3 |
| the stopping test is so loose the quadratic exponent is not observed | 2 |
| the limit case assumes undamped Newton converges from far away | 4 |

## Questions

Answers are not given. Work them out from the code and the definitions.

1. Why does backtracking need only `alpha` and `beta` and not the Lipschitz constant `L`,
   while a fixed step must stay below `2/L` to converge?
2. Newton's method is affine invariant: scaling the variable does not change the iterates.
   Gradient descent is not. Where in the two implementations can you see that difference?
3. The decrement `g^T H^{-1} g` is twice the value gap of the local quadratic model. Why
   is `decrement / 2 <= tol` a stopping rule for *suboptimality*, and what does it say when
   `H` is ill-conditioned?
4. On the flat valley `1/2 (x1+x2)^2` every point with `x1 + x2 = 0` is optimal, so the
   minimiser is not unique. Which part of the algorithm decides which one it returns?
5. Undamped Newton oscillates and grows on `sqrt(1+x^2)`. Describe the set of starts from
   which the raw iteration still converges, and how the line search changes it.

## Limits

- Everything assumes `f` is twice differentiable and convex; the Newton direction is a
  descent direction only for positive-definite `H`. A non-convex problem can make the raw
  step climb, and the ridge only fixes indefiniteness by accident.
- The convergence-rate check reads the decrement sequence, so it needs enough iterations
  in the quadratic regime; with a very loose tolerance there is nothing to measure.
- The ridge `lam*I` is a heuristic. It keeps the solve from failing, but on a numerically
  singular Hessian the returned direction is only approximate.
- All problems are small and dense; no exploitation of sparsity, no quasi-Newton
  approximation of `H`, no stopping rule based on a line search that fails.
