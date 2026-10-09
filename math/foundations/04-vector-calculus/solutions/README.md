# Vector Calculus From Scratch — Solutions

A complete version of the template in the parent directory. Pure Python 3, standard
library only (no numpy). Run it from the module directory:

```bash
python3 solutions/vector_calculus.py
```

Expected output:

```
Vector calculus from scratch — measurements
  quadratic  |g − (A+Aᵀ)x| = 0.00e+00  |g − 2Ax| = 8.00e+00
  least-sq   relative error vs central diff = 9.53e-11
  log-det    |g − X⁻ᵀ| = 0.00e+00  |g − X⁻¹| = 1.25e-01
  traces     |∇tr(AX) − Aᵀ| = 0.00e+00  |∇tr(XᵀAX) − (A+Aᵀ)X| = 0.00e+00
  hessian    |H − (A+Aᵀ)| = 0.00e+00
  taylor     err(0.05) = 4.200e-05  err(0.025) = 5.250e-06  ratio = 8.000 (→ h³)
  fd curve   h=1e-12: 7.7e-05   best h=1e-05: 1.5e-11   h=1e-1: 7.2e-04  (U-shape)
```

Three lines carry the chapter:

- The first: with a non-symmetric `A = [[2,5],[1,3]]`, `(A + Aᵀ)x` and `2Ax` differ by
  `8.00` — the symmetrisation is not cosmetic.
- The third: `|g − X⁻ᵀ| = 0` but `|g − X⁻¹| = 0.125` on a non-symmetric `X`; the gradient
  of log det is the transpose of the inverse.
- The last two: the Taylor remainder ratio is exactly `8.000`, i.e. it shrinks as `h³`,
  while the finite-difference error falls then rises (best `h ~ 1e-5`), the round-off
  floor of central differences.

To grade yourself, run the checker against these files in a scratch directory:

```bash
cd math/foundations/04-vector-calculus
tmp=$(mktemp -d)
cp solutions/*.py check.py "$tmp"/
(cd "$tmp" && python3 check.py --all)   # 9/9 passing
```
