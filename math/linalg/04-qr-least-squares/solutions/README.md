# Solutions — QR and least squares from scratch

`leastsquares.py` is the complete implementation. Nothing here is imported by
`check.py`; it is the reference you compare against after the checker passes.

## What each function does

| function | route |
| --- | --- |
| `householder_qr(A)` | `A = Q R` by accumulating Householder reflectors; `Q` orthogonal, `R` upper triangular |
| `normal_equations(A, b)` | solve `A^T A x = A^T b` (fast; squares the condition number) |
| `qr_least_squares(A, b)` | `x = R^{-1} Q^T b` from the QR factor (keeps the condition number) |
| `svd_least_squares(A, b)` | `x = V Sigma^+ U^T b` from the module's own SVD (handles rank deficiency) |
| `residual_norm(A, b, x)` | `||A x - b||_2` |
| `condition_number(A)` | largest over smallest singular value (not the diagonal ratio) |
| `exact_least_squares(A, b)` | exact rational minimiser via `fractions.Fraction` |

`_jacobi_eigh` and `_svd` are provided plumbing (the same cyclic-Jacobi pattern
as `math/linalg/03-spectral-theorem`, copied so this module is standalone). The
SVD route therefore also squares the condition number while forming `A^T A`; on
the extreme limit case it is less accurate than QR, and the `Fraction` solver —
not the SVD — is the reference.

## Expected output of `python3 solutions/leastsquares.py`

```
Householder QR and the three least-squares routes — measurements
  well-conditioned Q^T Q - I max = 2.220e-16   max|A - Q R| = 8.882e-16
  Hilbert 7        Q^T Q - I max = 6.661e-16   max|A - Q R| = 4.441e-16
  well-conditioned: max|normal - qr| = 2.665e-15   max|svd - qr| = 1.110e-15
  exact Fraction reference vs QR: max error = 1.332e-15
  Hilbert 7x6: condition number = 7.178e+06
    normal-equations error = 8.024e-05   QR error = 2.575e-10   ratio = 3.116e+05
  residual optimality: max|A^T (A x - b)| = 3.553e-15   residual norm = 9.930e-16
```

The last two lines are the point of the node: on the ill-conditioned Hilbert
`7 x 6`, the normal equations lose about twice as many digits as QR (measured
against the exact rational reference), while both residuals satisfy
`A^T (A x - b) = 0`.
