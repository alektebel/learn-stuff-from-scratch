# PRML 12 — Latent Continuous Variables

PCA, probabilistic PCA (PPCA) and kernel PCA from scratch, pure standard library.
Implements chapter 12 of Bishop, *Pattern Recognition and Machine Learning*
(`bishop:12`), and the matching material in Deisenroth, Faisal & Ong, *Mathematics
for Machine Learning*, ch. 10 (`mml:10`; the argument is restated here, never
copied).

**Status: not built.** `latent.py` holds the stubs; `check.py` grades them. This
file describes the work; `solutions/` is the reference.

## What you build

`latent.py`, eight graded functions. A cyclic Jacobi symmetric eigen-solver, a
small dense solver, an inverse and a log-determinant are yours to write as well;
the demo is given.

| Function | What it does |
|---|---|
| `mean_center(X)` | subtract the column means |
| `covariance(X)` | the `D x D` maximum-likelihood covariance `Xc^T Xc / N` |
| `pca_eig(X, k)` | PCA by the covariance eigen-decomposition |
| `pca_svd(X, k)` | the same result along the SVD / `Xc^T Xc` route |
| `ppca_closed_form(X, k)` | maximum-likelihood PPCA `(W, sigma^2)` |
| `ppca_em(X, k, ...)` | PPCA by EM; returns the log-likelihood trajectory |
| `kernel_pca(K, k)` | kernel PCA from a kernel matrix; returns eigenvalues and scores |
| `pca_gram(X, k)` | PCA through the `N x N` Gram matrix for `D > N` |

## Running it

```bash
python3 check.py        # every step, stopping at the first one not written
python3 check.py 3      # just step 3
python3 check.py --all  # do not stop at the first gap
```

A step that raises `NotImplementedError` is reported as **TODO**, not a failure. A
step that asserts and fails is a **FAIL**; an exception is an **ERROR**. The
checks import your `latent.py`, never `solutions/`.

## The checks

| Step | What it pins down |
|---|---|
| 1 | `pca_eig` and `pca_svd` agree on eigenvalues, subspace and reconstruction, and the principal directions are orthonormal |
| 2 | the accept criterion: the mean squared reconstruction error equals the sum of the discarded eigenvalues to `1e-9` (this needs the `1/N` covariance) |
| 3 | each principal direction is an eigenvector of the covariance (Rayleigh quotient), and the explained variances are non-increasing |
| 4 | the accept criterion: `ppca_em`'s `sigma^2` reaches the closed form and its subspace matches up to rotation (compared through the projector `W (W^T W)^{-1} W^T`), with a non-decreasing log-likelihood |
| 5 | `kernel_pca` eigendecomposes the feature-space-centred kernel, not the raw `K`, and its score columns are the centred kernel's own eigenvectors (`Kc p = lambda p`) with squared norms equal to the eigenvalues (so a transposed eigenvector index is caught) |
| 6 | the limit case `D > N`: `pca_gram` recovers the same nonzero eigenvalues (as raw Gram eigenvalues, `N` times the covariance ones) and the same reconstruction as the covariance route |

## Design decisions

- **The covariance is `1/N`, not `1/(N-1)`.** This is the maximum-likelihood
  estimate and the one for which the mean squared reconstruction error is exactly
  the discarded-eigenvalue sum. The unbiased estimator is a defensible alternative
  but breaks the identity.
- **Two PCA routes.** `pca_eig` works with the `D x D` covariance; `pca_svd`
  works with `Xc^T Xc` and divides by `N`. Squaring the matrix squares the
  condition number, so the SVD route is only as accurate as the data allows; on
  the checker's small well-conditioned input the two agree to `~1e-15`.
- **PPCA closed form and by EM.** The closed form is exact and global; EM is
  cheaper per step but reaches the same subspace only up to a rotation and to a
  tolerance. Keeping both makes the rotation issue explicit.
- **`kernel_pca` never forms the feature map.** It centres the `N x N` kernel in
  feature space (`K - 1K/N - K1/N + 1K1/N^2`) and eigen-decomposes it. Cost:
  `O(N^2)` memory and only training scores, no out-of-sample embedding.
- **`pca_gram` for `D > N`.** The `D x D` covariance is rank-deficient and larger
  than the data, so the `N x N` Gram matrix `Xc Xc^T` is used instead; its
  eigenvalues are the raw ones and directions come back as `Xc^T u / sqrt(lambda)`.

## Limit cases

- **`D > N`.** The centred data has rank at most `N - 1`, so the covariance is
  singular. The checker uses `N = 5`, `D = 8` and checks that the `N x N` Gram
  route returns the nonzero eigenvalues and reconstructs exactly like the
  covariance route.
- **Kernel PCA needs the centring.** Forgetting the feature-space centring leaves
  the top eigenvalue as the uninformative constant direction and shifts the whole
  spectrum; step 5 catches it against the checker's own centred eigen-decomposition.

## Mutation coverage

`_build/mutations.py` plants one classic bug per mechanism; each is an exact edit
to a copy of the solutions and must be caught by the named step
(`python3 .claude/skills/graded-module/scripts/mutate.py math/prml/12-latent-continuous math/prml/12-latent-continuous/_build/mutations.py`).

| Bug | Step |
|---|---|
| `pca_eig` does not mean-centre the data | 2 |
| `pca_eig` reconstruction uses `k + 1` components | 2 |
| `ppca_closed_form` drops the noise-term average | 4 |
| `ppca_em` never updates `sigma^2` | 4 |
| `kernel_pca` skips the feature-space centring of `K` | 5 |
| `kernel_pca` transposes the eigenvector indexing | 5 |
| Gram limit uses the `D x D` covariance matrix | 6 |

## Questions

Answers are not given. Work them out from the code and the definitions.

1. Why is it the `1/N` and not the `1/(N-1)` covariance for which the mean squared
   reconstruction error equals the discarded-eigenvalue sum? Carry the factor
   through the projection once.
2. `pca_svd` squares the condition number by using `Xc^T Xc`. For which data
   configurations does that matter numerically, and how would a power iteration or
   a true bidiagonal SVD avoid it?
3. EM for PPCA reaches the closed-form subspace only up to a rotation. Why can the
   loading matrix `W` not be identified on its own, and what quantity is
   rotation-invariant?
4. Centring the kernel matrix in feature space is a projection. Write it as
   `(I - 11^T/N) K (I - 11^T/N)` and say why the resulting eigenvalues are exactly
   the eigenvalues of the centred feature covariance times `N`.
5. For `D > N`, the Gram matrix and the covariance share nonzero eigenvalues up to
   the factor `N`. Recover one direction `v` from a Gram eigenvector `u` and check
   the relation `Xc^T Xc v = lambda v` from `Xc Xc^T u = N lambda u`.

## Limits

- The methods are dense and batch; streaming/online PCA and randomized SVD are out
  of scope.
- Kernel PCA uses the full `N x N` kernel and returns training scores only; it does
  not embed new points (that needs the Nyström extension).
- PPCA is limited to the isotropic-noise model `W W^T + sigma^2 I`; EM is
  initialised from a fixed seed and compared by subspace, not elementwise.
- The `D > N` case stops at `N - 1` nonzero eigenvalues; the smallest Gram
  eigenvalue is numerically zero and is not returned.
