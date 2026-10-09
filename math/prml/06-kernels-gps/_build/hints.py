"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every graded function for Bishop's chapter 6 (kernels and Gaussian processes) is
listed, so make_templates stubs it and replaces its body with `raise
NotImplementedError`. The given infrastructure (`solve`, `_chol_solve`,
`_symmetric_eigenvalues`, `_observation_covariance`, `cholesky_with_fallback`)
and the demo are left implemented: they are the linear algebra the exercise
stands on, not the GP itself.
"""

HINTS = {
 "kernels.py": {
  "linear_kernel":
      "k(x, y) = variance * (x y + offset). Return a closure `kernel(x, y)` that "
      "captures variance and offset. Symmetric by construction.",
  "polynomial_kernel":
      "k(x, y) = variance * (scale x y + offset) ** degree. Return a closure. With "
      "offset >= 0, scale >= 0 and integer degree the binomial expansion is a sum of "
      "Schur products of the PSD kernel x y, so the result is PSD.",
  "rbf_kernel":
      "k(x, y) = variance * exp(-(x - y)^2 / (2 length_scale^2)). The exponent is the "
      "SQUARED distance d*d; using |d| gives a different (Laplace-style) kernel. Return "
      "a closure `kernel(x, y)`.",
  "gram_matrix":
      "Return an n x n list of lists with K[i][j] = kernel(xs[i], xs[j]). Fill both "
      "K[i][j] and K[j][i] from the same value so symmetry is exact.",
  "is_psd":
      "A symmetric matrix is PSD iff its smallest eigenvalue is >= -tol. Use the given "
      "`_symmetric_eigenvalues` (Jacobi) and compare the minimum to -tol. Do NOT use a "
      "Cholesky-with-jitter test here: the jitter would hide the near-zero/negative "
      "eigenvalues this predicate is supposed to catch.",
  "cholesky":
      "Standard lower-triangular Cholesky: for i, for j <= i, "
      "total = K[i][j] + (jitter if i == j else 0) - sum_k L[i][k] L[j][k]. On the "
      "diagonal, if total <= 0 raise ValueError (the matrix is not positive definite "
      "without more jitter); otherwise L[i][i] = sqrt(total). Off-diagonal, "
      "L[i][j] = total / L[j][j]. Return L. Add the jitter to the DIAGONAL only.",
  "gp_posterior":
      "C = K(X, X) + noise I. Factor C (cholesky_with_fallback), solve C alpha = y, "
      "solve C v = k* for each test point. mean = k* . alpha; latent variance = "
      "k(x, x) - k* . v, clamped at 0. Return parallel lists (means, variances). The "
      "noise term MUST be on the training covariance diagonal even when the data are "
      "noise-free.",
  "gp_log_marginal_likelihood":
      "C = K(X, X) + noise I; L = cholesky_with_fallback(C); alpha = L L^T^-1 y. "
      "Return -1/2 y . alpha - sum_i ln L[i][i] - n/2 ln(2 pi). The log-determinant "
      "comes from ln|C| = 2 sum_i ln L[i][i].",
  "log_marginal_gradient_fd":
      "Central finite differences: for each parameter i, build params +/- h e_i, form "
      "the kernel with the factory `kernel(params)`, evaluate the log evidence at both "
      "points, and take (f_plus - f_minus) / (2h). Return the list of partials. `kernel` "
      "is a factory: kernel(params) -> k(x, y).",
 },
}
