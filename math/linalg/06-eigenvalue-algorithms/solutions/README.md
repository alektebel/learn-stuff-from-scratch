# Eigenvalue Algorithms From Scratch — Solutions

A complete version of the template in the parent directory. Pure Python 3, standard
library only (`math` for the arithmetic, `random` for the demo's test matrices). Run it
from the module directory:

```bash
python3 solutions/eigenalg.py
```

Expected output (last digits may vary across platforms):

```
Eigenvalue algorithms — measurements
  hessenberg: max|Q H Q^T - A| = 3.55e-15  max|Q^T Q - I| = 6.66e-16  max below-subdiagonal |H| = 6.22e-16
  tridiagonalize: max|Q T Q^T - A| = 9.77e-15  max off-tridiagonal |T| = 1.78e-15
  shifted QR vs Jacobi reference: worst eigenvalue error over 25 random symmetric matrices = 1.03e-13  (accept < 1e-10)
  Rayleigh quotient iteration: lambda = 4.745281240174139  (reference 4.745281240174140, residual 8.88e-16)
    error sequence: ['7.45e-01', '3.15e-01', '2.09e-02', '3.74e-06', '0.00e+00', '8.88e-16']
    observed convergence exponent = 3.23  (cubic is 3)
  equal-magnitude eigenvalues [-2.0, -1.0, 1.0, 2.0]:
    unshifted QR: 200 sweeps, eigenvalues [-0.0, -0.0, 0.0, 0.0]
    Wilkinson QR: 2 sweeps, eigenvalues [-2.0, -1.0, 1.0, 2.0]
```

The lines that carry the acceptance criteria:

- **Hessenberg and tridiagonal reduction.** `Q H Qᵀ = A` to `4e-15` with `QᵀQ = I` to
  `7e-16`. The reduction is a similarity (reflector applied on both sides); a one-sided
  application would leave `Q H Qᵀ ≠ A`.
- **Shifted QR against an independent reference.** The worst eigenvalue error over 25
  random symmetric matrices is `1.03e-13`, comfortably inside the `1e-10` accept line.
  The reference is the module's own high-accuracy Jacobi solver here; the checker carries
  a duplicate so it never trusts this number.
- **Cubic Rayleigh quotient iteration.** The error sequence
  `7.45e-01 → 3.15e-01 → 2.09e-02 → 3.74e-06 → 0` gives a tail exponent of `3.23`: the
  ratio `log e_{k+1} / log e_k` approaches 3, the signature of cubic convergence. A fixed
  shift would give an exponent near 1.
- **The equal-magnitude limit case.** The unshifted iteration runs its full 200-sweep
  budget and returns `{0, 0, 0, 0}` — it is a fixed point on each 2×2 block and never
  separates `±1` or `±2`. The Wilkinson shift converges in **2 sweeps** to `{−2, −1, 1, 2}`.

## Environment adaptation

The node's acceptance line names `numpy.linalg.eigvalsh`; numpy is not available in this
repository. The oracle is a self-contained cyclic Jacobi solver (in both this file's demo
and the checker) plus known exact spectra, and the `1e-10` requirement is unchanged. See
the parent `README.md` for the full statement.

## Grade yourself

Run the checker against these files in a scratch directory:

```bash
cd math/linalg/06-eigenvalue-algorithms
tmp=$(mktemp -d)
cp solutions/*.py check.py "$tmp"/
(cd "$tmp" && python3 check.py --all)   # 5/5 passing
```

`check.py` never imports `solutions/`; it computes every reference value with its own
Jacobi solver and its own known exact spectra, and states its numerical tolerances at the
assertions. Its resistance to planted bugs is documented in the parent README
(`_build/mutations.py`).
