# Matrix Decompositions From Scratch — Solutions

A complete version of the template in the parent directory. Pure Python 3, no
dependencies. Run it from the module directory:

```bash
python3 solutions/decompositions.py
```

Expected output:

```
Matrix decompositions from scratch — measurements
  cholesky   max|A − LLᵀ| = 0.0e+00   diagonal = [2.0000, 1.0000, 3.0000]
  eigen      k = 3, eigenvalues = [+3.701796, +1.383622, -0.085418]
  eigen      max ‖Av − λv‖ = 6.77e-16
  svd        σ = [4.000000, 2.000000, 0.500000]   (known [4, 2, 0.5])
  eckart-you ‖M − M₂‖ = 5.000000e-01   (σ₃ = 0.5)
  condition  true σ₂ = 1e-07, Gram-SVD σ₂ = 9.985106e-08   (relative error 1.49e-03)
```

Two lines carry the chapter. The `eckart-you` line: dropping the smallest of three known
singular values `[4, 2, 0.5]` costs exactly `σ₃ = 0.5` in the spectral norm — not
approximately, exactly, which is Eckart-Young. The last line: the true second singular
value is `1e-7` and the value computed through the eigenvalues of `AᵀA` is `9.99e-8`, a
relative error of `1.5e-3`. The condition number is `1e7`, so `AᵀA` has condition number
`1e14` and roughly `κ²·ε ≈ 1e-2` of the small eigenvalue is noise — the loss appears even
though `A` itself is perfectly representable.

To grade yourself, run the checker against these files in a scratch directory:

```bash
cd math/foundations/03-matrix-decompositions
tmp=$(mktemp -d)
cp solutions/*.py check.py "$tmp"/
(cd "$tmp" && python3 check.py --all)   # 8/8 passing
```
