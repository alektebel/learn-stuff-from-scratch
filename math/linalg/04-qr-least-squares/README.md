# QR and least squares from scratch

Householder QR and the three standard least-squares routes, built with the
standard library only (`math`, `fractions`). Restated from Trefethen & Bau,
*Numerical Linear Algebra*, lectures 6-11 (`trefethen-bau:6` .. `trefethen-bau:11`)
and the corresponding Gilbert Strang lectures on orthogonalisation and least
squares (`strang:6` .. `strang:11`). Nothing is copied from those sources; the
code and the measurements are original.

## Run it

```
cd math/linalg/04-qr-least-squares
python3 check.py           # run every check, stop at the first unimplemented step
python3 check.py 3         # only step 3
python3 check.py --all     # keep going through the TODOs
```

Edit `leastsquares.py` (a generated template: keep the signatures and
docstrings). When every step passes, compare with `solutions/leastsquares.py`
and run its `__main__` demo.

## Steps

| # | what | what the check verifies |
| --- | --- | --- |
| 1 | `householder_qr` | `Q^T Q = I` to 1e-14 on a well- **and** an ill-conditioned `A`, and `A = Q R` |
| 2 | `normal_equations`, `qr_least_squares`, `svd_least_squares` | the three routes agree to 1e-8 on a well-conditioned problem |
| 3 | `exact_least_squares` | the exact `Fraction` minimiser matches QR on integer data |
| 4 | `condition_number` + the limit case | on a Hilbert `7 x 6`, the normal-equations error is `>10x` QR's and loses about twice the digits, against the exact reference |
| 5 | `residual_norm` | the residual is (near-)minimal: `A^T (A x - b) = 0` for all three routes |

## Design decisions

- **Householder, not classical Gram-Schmidt.** Gram-Schmidt loses orthogonality
  as the condition number grows; a product of Householder reflectors stays
  orthogonal to working precision, which is the accept criterion here (step 1
  tests an ill-conditioned `A` on purpose).
- **Keep all three routes.** The normal equations are the fastest and square the
  condition number; QR keeps it; the SVD degrades gracefully on a rank-deficient
  `A`. Step 4 is the measurement that shows *why* the normal equations are the
  naive route.
- **An exact `Fraction` reference.** Floating point cannot decide which of two
  float answers is right; on rational data the normal equations solved in exact
  arithmetic give the true minimiser. This is what makes step 4 a measurement
  rather than an opinion.
- **`condition_number` from singular values.** The ratio of diagonal entries is
  basis-dependent and can be small while `A` is nearly singular; the 2-norm
  condition number is `sigma_max / sigma_min`.
- **The SVD engine is provided plumbing.** It is the cyclic-Jacobi pattern from
  `math/linalg/03-spectral-theorem`, copied so this module is standalone. It also
  squares the condition number while forming `A^T A`, so it is *not* the
  reference for step 4 — the exact solver is.

## Questions to answer yourself (no answers here)

1. Why does `A^T A` square the condition number, and what does that predict for
   the number of correct digits in `x`?
2. QR never forms `A^T A`; where, exactly, is that saving spent in work?
3. On a rank-deficient `A`, which of the three routes still gives a least-squares
   solution, and which singular values must be set to zero?
4. Step 4 compares digit *losses* (`log10(error / eps)`) rather than raw errors.
   Why is that the ratio that should come out near two?
5. The Householder `Q` is stored as a full `m x m` product here. What does LAPACK
   store instead, and what does it cost to ask for `Q` explicitly?

## Limits

- `householder_qr` and `_svd` assume `m >= n` (tall or square); a wide system is
  out of scope for this node.
- The SVD route is built from `A^T A`, so on the extreme Hilbert case it is less
  accurate than QR. A bidiagonal SVD would fix that but is a different node.
- The limit case stops at the **7x6** Hilbert matrix on purpose. The `A^T A` route
  squares the condition number, and for 7x7 the smallest eigenvalue of `H^T H`
  (~4.5e-18) falls below relative `eps` against `||H^T H||` (~1.66), so
  `condition_number` returns `inf` and the comparison is no longer a fair one. At 7x6
  the condition number is ~7.2e6 and the normal-equations error is ~3.1e5x the QR
  error (about 2x the digits). A bidiagonal SVD would lift the cap.
- The exact reference only exists for integer or rational `A` and `b`; the
  checker constructs the limit case with a Hilbert matrix to stay rational.
- `_solve` uses plain Gaussian elimination with partial pivoting; on the
  ill-conditioned normal equations it is the *method* that limits accuracy, not
  the solver.

## Mutation table

`python3 .claude/skills/graded-module/scripts/mutate.py math/linalg/04-qr-least-squares math/linalg/04-qr-least-squares/_build/mutations.py`

| mutation | caught by |
| --- | --- |
| Householder `Q` accumulated with the wrong reflector weight (`Q^T Q != I`) | step 1 |
| normal equations form `A A^T` and use `b` instead of `A^T A` and `A^T b` | step 2 |
| QR least squares back-substitutes the wrong `R` rows (bottom `n` instead of top `n`) | step 2 |
| `condition_number` uses the ratio of diagonal entries instead of singular values | step 4 |
| limit-case check accepts the normal-equations error as equal to QR (`normal_equations` aliased to the QR answer) | step 4 |
