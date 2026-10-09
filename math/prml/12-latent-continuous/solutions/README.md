# Solutions — latent continuous variables

Worked implementation of the `latent.py` template. Pure standard library
(`math`, `random`), no NumPy.

## Files

- `latent.py` — the full implementation, plus `_jacobi`, `_solve`, `_inverse`,
  `_log_det` helpers and a `demo()` under `__main__`.

## Design notes

- **Data model.** `X` is `N x D` as nested lists. `covariance` uses the
  maximum-likelihood normalization `Xc^T Xc / N`, so the mean squared PCA
  reconstruction error equals the sum of the discarded eigenvalues exactly
  (the accept criterion in step 2).
- **Eigen-solver.** A cyclic Jacobi iteration handles every symmetric
  eigenproblem, returning eigenvalues sorted descending and matching unit
  eigenvectors. This keeps PCA, kernel PCA and the Gram route dependency-free.
- **Two PCA routes.** `pca_eig` uses the covariance; `pca_svd` uses `Xc^T Xc`
  and divides by `N`. They agree on eigenvalues, subspace and reconstruction;
  `pca_gram` uses the `N x N` Gram matrix for the `D > N` limit, where the
  eigenvalues are the raw ones (`N` times the covariance eigenvalues).
- **PPCA.** `ppca_closed_form` sets `sigma^2` to the average of the discarded
  eigenvalues, and `ppca_em` alternates posterior moments and parameter updates
  until convergence, returning the non-decreasing log-likelihood trajectory.
  EM reaches the closed-form subspace only up to a rotation, so comparisons use
  the projector `W (W^T W)^{-1} W^T`.
- **Kernel PCA.** `kernel_pca` centres `K` in feature space
  (`K - 1K/N - K1/N + 1K1/N^2`) before the eigen-decomposition, and returns the
  scores `sqrt(lambda_j) v_j`. The feature map is never formed.

## Expected output

```
$ python3 latent.py
PCA (eig): top variances = [17.53144, 1.70127]
           mean reconstruction error = 0.00933282  discarded eigenvalue sum = 0.00933282
PCA (svd): max |eig - svd| = 3.552713678800501e-15
PPCA: closed-form sigma^2 = 0.002333  EM sigma^2 = 0.002333  EM steps = 800
      EM log-likelihood -467.901 -> 74.425
Gram limit demo eigenvalue ratio (first) = skipped (D <= N)
Kernel PCA eigenvalues = [4.8461, 3.2796]
```

The demo data is `N = 40`, `D = 6`, so the Gram line prints `skipped (D <= N)`;
the `D > N` route is exercised by step 6 on `N = 5`, `D = 8` data instead.

## Run

```
python3 latent.py          # demo
```
