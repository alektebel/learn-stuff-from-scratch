# Interior-point methods from scratch

Equality-constrained Newton and the log-barrier method, the two ways to turn a
constrained problem into a sequence of easier ones. Built from Boyd & Vandenberghe,
*Convex Optimization*, ch. 10 (equality-constrained minimisation and the KKT system)
and ch. 11 (the barrier method), with the LP duality of ch. 5 explaining the gap.

The solver is `interior.py`; `solutions/` is a worked reference. Pure stdlib
(`math` only), Python 3.

```
cd math/optimization/04-interior-point
python3 check.py        # run the steps, stop at the first one not written yet
python3 check.py --all  # run every step even after a gap
```

## Steps

| # | what it checks | file |
|---|----------------|------|
| 1 | equality-constrained Newton reaches the KKT point (`Ax = b`, reduced gradient zero) | `interior.py` |
| 2 | the log-barrier LP converges to the enumeration optimum as `t` grows | `interior.py` |
| 3 | ACCEPT: the barrier duality gap tracks `m/t` over the outer rounds | `interior.py` |
| 4 | ACCEPT: the barrier matches an independent BFS enumeration on random 2-D LPs | `interior.py` |
| 5 | limit: a phase-I LP detects an infeasible system | `interior.py` |

A step that raises `NotImplementedError` is reported as TODO, not a failure. The
checker never imports `solutions/`: it solves KKT systems itself with its own
Gaussian elimination (`_gauss`) and enumerates LP vertices itself (`_enum_lp`).

## What you build

`solve` (Gaussian elimination), the matrix helpers and `_find_interior` are given.
You write:

* `equality_constrained_newton(Q, c, A, b, x0, tol, maxit)` -- Newton on the KKT
  system `[[Q, A^T], [A, 0]]`, returning `(x, residuals)`.
* `log_barrier_lp(c, A_ub, b_ub, t, x0)` -- damped Newton on
  `c^T x - (1/t) sum_i log(b_i - a_i x)`.
* `barrier_method(c, A_ub, b_ub, t0, mu, tol, maxit, x0=None)` -- the outer loop that
  multiplies `t` by `mu`, returning `(x, history)` with `history[k] = {"t",
  "objective", "gap" = m/t, "x"}`.
* `simplex_lp(c, A_ub, b_ub)` -- the 2-D enumeration reference.
* `phase_one(A_ub, b_ub)` -- feasibility by a phase-I LP.

## Design decisions

* **Interior start.** The barrier is only defined where every slack is positive.
  `barrier_method` takes a strictly feasible `x0`; absent one it only vouches for
  `x = 0`. An infeasible-start method would need its own phase I, which is what
  `phase_one` already is.
* **Ridge fallback.** The barrier Hessian is a sum of rank-one terms, so it is PSD
  but can be singular when constraint normals are parallel (the phase-I LP for a
  strip is the standard example). We add a ridge scaled to the Hessian and take the
  minimum-norm step in the flat direction instead of failing.
* **Enumeration instead of the simplex tableau.** In two variables the LP optimum is
  a vertex, i.e. the intersection of two constraint boundaries. Enumerating pairs is
  slower than a tableau but obviously correct, which is what a reference needs.
* **Phase-I formulation.** Minimise `sum_i s_i` subject to `a_i x - s_i <= b_i` and
  `s_i >= 0`. The minimum is 0 exactly when the original system is feasible, and the
  augmented LP always has the interior start `x = 0, s_i = 1 + max(0, -b_i)`.

## Limit cases

* An **infeasible** system (`x1 + x2 <= 1` with `x1 + x2 >= 3`) has a positive
  phase-I optimum; step 5 requires `phase_one` to say `False`. The two constraint
  normals are parallel, which is what forces the ridge fallback.
* A LP where two constraints cross at a point that violates a third
  (`x1 <= 1, x2 <= 1, x1 + x2 >= 1.5`) has an *infeasible* vertex cheaper than the
  true optimum. Step 4 uses it to catch a reference that forgets to test feasibility.

## Mutation table

Every planted bug is caught by the step named in `_build/mutations.py`:

| step | planted bug |
|------|-------------|
| 1 | `equality_constrained_newton` solves the unconstrained system (drops the `A^T lambda` / `A` blocks) |
| 2 | `log_barrier_lp` flips the sign of the linear cost term |
| 3 | `barrier_method` never grows `t` (the gap stays at `m/t0`) |
| 4 | the enumeration reference accepts infeasible vertices |
| 5 | `phase_one` declares every LP feasible |

Run them with:

```
python3 .claude/skills/graded-module/scripts/mutate.py \
    math/optimization/04-interior-point \
    math/optimization/04-interior-point/_build/mutations.py
```

## Questions to answer yourself

1. The bound says the suboptimality `c^T x(t) - p*` is at most `m/t`. The demo's
   pentagon settles at ratio `0.4`, not `1`. Why? (Hint: how many constraints are
   active at the optimum, and what does the proof of the bound actually sum over?)
2. Why does the cone `min x1 + x2 s.t. x1, x2 >= 0` show ratio exactly `1`?
3. Phase-I uses `s_i = 1 + max(0, -b_i)` as a start. Check that it is strictly
   feasible for the augmented LP, and explain the `max`.
4. Equality-constrained Newton solves a quadratic in one step. What does it do on
   `min x1^2 + x2^2 s.t. x1 = x2`? Try `x0 = (10, -10)` and look at the residuals.

## Limits

* `simplex_lp` is a 2-D reference only; it raises for any other dimension.
* The barrier Hessian ridge is a numerical safeguard, not a proof of feasibility;
  `phase_one` is the feasibility oracle.
* No line search guarantees an exact central point at large `t`, so the measured gap
  is `m/t` only to the Newton tolerance.
