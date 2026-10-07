# Continuous Optimization From Scratch — Solutions

A complete version of the template in the parent directory. Pure Python 3, standard library
only (no numpy). Run it from the module directory:

```bash
python3 solutions/optimization.py
```

Expected output:

```
Optimization from scratch — measurements
  kappa   predicted   measured   (fixed step 2/(1+kappa), tol 1e-8)
     10         104        104
    100        1152       1152
   1000       12665      12665

  2/L = 0.02000:  0.99x -> |grad| = 9.95e-09 (1140 it)   1.01x -> |grad| = 1.00e+45 (5000 it)

  ill-conditioned valley (kappa=1000):
    plain GD   iterations  10362   path   1000.0   sign reversals  10361
    momentum   iterations    531   path     25.4   sign reversals    274

  constrained min: x = (1.7500, -0.7500), lambda = -2.1250
    KKT stationarity = 6.28e-16   primal feasibility = 0.00e+00

  rotated SPD matrix: eigenvalues [1.0, 3.0], condition number 3.000
```

Every line carries a claim:

- The first block: on x0 aligned with λ_max, the fixed-step error contracts by exactly
  (κ−1)/(κ+1), so the measured iteration count equals the closed-form prediction for κ = 10,
  100 and 1000. The count grows roughly linearly with κ (104 → 1152 → 12665), which is what
  "the number of iterations grows with the condition number as predicted" means.
- The second line: 0.99·(2/L) converges to 1e-8, 1.01·(2/L) does not — the 2/L boundary is
  genuinely a boundary, the `limit_cases` criterion for this node.
- The third block: on the κ = 1000 valley plain gradient descent reverses direction on
  essentially every one of its 10362 steps (the high-curvature multiplier is negative), while
  momentum takes 531 steps and a path of 25.4 instead of 1000.
- The fourth: the equality-constrained quadratic is solved to KKT stationarity 6.28e-16 and
  primal feasibility 0 — both below the 1e-8 `accept` bound.
- The last line exercises the spectral helpers on a non-diagonal SPD matrix (eigenvalues 1
  and 3, condition number 3).

To grade yourself, run the checker against these files in a scratch directory:

```bash
cd math/foundations/06-optimization
tmp=$(mktemp -d)
cp solutions/*.py check.py "$tmp"/
(cd "$tmp" && python3 check.py --all)   # 10/10 passing
```
