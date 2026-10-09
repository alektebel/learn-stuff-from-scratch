# Solutions — kernels and Gaussian processes

`kernels.py` is the reference implementation of the nine graded functions, plus
the given dense linear algebra and the demo. Run the checker against it by copying
`kernels.py` and `check.py` into one directory:

```bash
python3 check.py --all   # 5/5 passing
```

## Expected demo output

`python3 kernels.py` from this directory prints:

```
Kernels and Gaussian processes — demo
  RBF Gram matrix: 6x6, min eigenvalue=7.951e-02, is_psd=True
  noise-free GP interpolation: max |mean - y| = 2.22e-16
  posterior std away from the data at x=[1.6, 2.4, 3.2, 4.0]: 0.1171, 0.3526, 0.9149, 0.9983
  log marginal likelihood (noise=0.05): -7.503388
  finite-difference gradient w.r.t. [length_scale, variance]: [5.492828, 0.349987]
  invalid kernel k(x,y) = -x y: min eigenvalue=-5.250e+00, is_psd=False
  singular Gram (duplicated input): cholesky fails without jitter
  cholesky(K_dup, jitter=1e-8) succeeds, min diagonal=1.414e-04
```

What the lines show:

- The RBF Gram matrix of six distinct inputs is positive definite (smallest
  eigenvalue `7.95e-2`), so the kernel is valid.
- Conditioning on noise-free targets reproduces them to machine precision
  (`2.2e-16`): the posterior mean interpolates the data.
- Moving away from the data the posterior standard deviation rises from `0.12`
  at `x = 1.6` to `1.0` at `x = 4.0`, approaching the prior standard deviation
  `sqrt(variance) = 1`.
- The log evidence at noise `0.05` is `-7.503`, and its finite-difference
  gradient w.r.t. `[length_scale, variance]` is `[5.493, 0.350]`.
- The invalid kernel `k(x, y) = -x y` has a negative eigenvalue (`-5.25`) and
  `is_psd` rejects it.
- A duplicated input gives a singular Gram matrix: `cholesky` raises without
  jitter and succeeds with `jitter = 1e-8` (`min diagonal = 1.41e-4`).

The exact floating-point digits depend on the platform; the qualitative behaviour
and the pass/fail verdicts do not.
