"""Kernels and Gaussian process regression from scratch (Bishop chapter 6).

Pure standard library (`math`). A kernel is a symmetric function ``k(x, y)``; a
symmetric matrix is a valid kernel Gram matrix exactly when it is positive
semi-definite (PSD). Gaussian process regression is then linear algebra: build
the observation covariance ``C = K + noise I``, factor it, and condition.

A kernel is represented as a two-argument callable ``k(x, y)``. The three
constructors below return such callables rather than taking the two points
themselves, so hyperparameters (length scale, variance, degree) are bound once.
"""

import math


# ---------------------------------------------------------------------------
# Given: dense linear solve (reused from the earlier PRML modules)
# ---------------------------------------------------------------------------

def solve(A, b):
    """Solve ``A x = b`` by Gaussian elimination with partial pivoting."""
    n = len(A)
    m = [list(A[i]) + [b[i]] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-12:
            raise ValueError("singular matrix")
        m[col], m[pivot] = m[pivot], m[col]
        for r in range(col + 1, n):
            factor = m[r][col] / m[col][col]
            if factor != 0.0:
                for k in range(col, n + 1):
                    m[r][k] -= factor * m[col][k]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (m[i][n] - sum(m[i][j] * x[j] for j in range(i + 1, n))) / m[i][i]
    return x


# ---------------------------------------------------------------------------
# Kernels
# ---------------------------------------------------------------------------

def linear_kernel(variance=1.0, offset=0.0):
    """``k(x, y) = variance * (x y + offset)``. Returns a callable ``k(x, y)``."""
    def kernel(x, y):
        return variance * (x * y + offset)
    return kernel


def polynomial_kernel(degree, scale=1.0, offset=1.0, variance=1.0):
    """``k(x, y) = variance * (scale x y + offset) ** degree``.

    With ``offset >= 0`` and ``scale >= 0`` and integer ``degree`` the binomial
    expansion is a sum of products of the PSD kernel ``x y`` with itself, so the
    result is PSD (a constant kernel is PSD, and a pointwise product of PSD
    kernels is PSD by the Schur product theorem).
    """
    def kernel(x, y):
        return variance * (scale * x * y + offset) ** degree
    return kernel


def rbf_kernel(length_scale, variance):
    """``k(x, y) = variance * exp(-(x - y)^2 / (2 length_scale^2))``.

    The exponent is the *squared* distance. Dropping the square (using
    ``|x - y|``) gives a Laplace-style kernel: still symmetric and PSD, but a
    different function, so value checks pin it down.
    """
    def kernel(x, y):
        d = x - y
        return variance * math.exp(-0.5 * d * d / (length_scale * length_scale))
    return kernel


def gram_matrix(kernel, xs):
    """Symmetric Gram matrix ``K_ij = k(xs[i], xs[j])``.

    The lower and upper triangles are filled from the same value so symmetry is
    exact by construction, not up to floating-point rounding.
    """
    n = len(xs)
    K = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i, n):
            value = kernel(xs[i], xs[j])
            K[i][j] = value
            K[j][i] = value
    return K


# ---------------------------------------------------------------------------
# Validating a kernel
# ---------------------------------------------------------------------------

def _symmetric_eigenvalues(A, sweeps=100):
    """All eigenvalues of a symmetric matrix by the Jacobi rotation method.

    Infrastructure: ``is_psd`` stands on it, so it is given. Returns the
    eigenvalues in no particular order; the diagonal after the off-diagonal
    entries have been driven to zero.
    """
    n = len(A)
    a = [list(row) for row in A]
    for _ in range(sweeps):
        p = q = 0
        off = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                if abs(a[i][j]) > off:
                    off = abs(a[i][j])
                    p, q = i, j
        if off < 1e-14:
            break
        theta = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
        t = math.copysign(1.0, theta) / (abs(theta) + math.sqrt(theta * theta + 1.0))
        c = 1.0 / math.sqrt(t * t + 1.0)
        s = t * c
        for k in range(n):
            akp, akq = a[k][p], a[k][q]
            a[k][p] = c * akp - s * akq
            a[k][q] = s * akp + c * akq
        for k in range(n):
            apk, aqk = a[p][k], a[q][k]
            a[p][k] = c * apk - s * aqk
            a[q][k] = s * apk + c * aqk
    return [a[i][i] for i in range(n)]


def is_psd(K, tol=1e-10):
    """True iff the smallest eigenvalue of symmetric ``K`` is ``>= -tol``.

    Design choice: an eigen-decomposition, not a Cholesky-with-jitter test. A
    Cholesky test needs a jitter to be usable, and the jitter hides precisely
    the near-zero or negative eigenvalues this predicate exists to catch (the
    jitter turns a singular matrix into a positive-definite one). The Jacobi
    eigenvalues report the margin directly, so ``tol`` is the actual threshold.
    """
    values = _symmetric_eigenvalues(K)
    return min(values) >= -tol


# ---------------------------------------------------------------------------
# Cholesky
# ---------------------------------------------------------------------------

def cholesky(K, jitter=0.0):
    """Lower-triangular ``L`` with ``L L^T = K + jitter I``.

    Raise ``ValueError`` as soon as a pivot is non-positive: a PSD matrix that
    is singular (e.g. duplicated inputs) has no exact Cholesky factor, and that
    is information, not a bug. ``jitter > 0`` regularises the diagonal and makes
    the factor exist; callers choose how much.
    """
    n = len(K)
    L = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            total = K[i][j]
            if i == j:
                total += jitter
            for k in range(j):
                total -= L[i][k] * L[j][k]
            if i == j:
                if total <= 0.0:
                    raise ValueError(
                        "matrix is not positive definite; a jitter is required")
                L[i][i] = math.sqrt(total)
            else:
                L[i][j] = total / L[j][j]
    return L


def cholesky_with_fallback(K, jitter=1e-8):
    """Try an exact Cholesky, then retry with ``jitter`` on the diagonal.

    Infrastructure: the GP routines want a factor even when the training inputs
    contain duplicates, so they ask for the exact factor first and fall back.
    """
    try:
        return cholesky(K)
    except ValueError:
        return cholesky(K, jitter)


def _chol_solve(L, b):
    """Solve ``L L^T x = b`` from a lower-triangular ``L`` (forward/back)."""
    n = len(L)
    y = [0.0] * n
    for i in range(n):
        y[i] = (b[i] - sum(L[i][k] * y[k] for k in range(i))) / L[i][i]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (y[i] - sum(L[k][i] * x[k] for k in range(i + 1, n))) / L[i][i]
    return x


# ---------------------------------------------------------------------------
# Gaussian process regression
# ---------------------------------------------------------------------------

def _observation_covariance(kernel, xs, noise):
    """``C = K(X, X) + noise I``. Infrastructure, shared by the GP routines."""
    gram = gram_matrix(kernel, xs)
    n = len(xs)
    return [[gram[i][j] + (noise if i == j else 0.0) for j in range(n)]
            for i in range(n)]


def gp_posterior(xs_train, ys_train, xs_test, kernel, noise):
    """GP posterior mean and variance at ``xs_test``.

    The training covariance is ``C = K(X, X) + noise I`` (``noise`` is the
    observation-noise variance ``sigma^2``). With ``alpha = C^{-1} y``, the
    posterior mean at ``x`` is ``k* . alpha`` and the latent variance is
    ``k(x, x) - k* . C^{-1} k*``. Returns ``(means, variances)``.

    With ``noise = 0`` and distinct inputs the mean interpolates the training
    targets exactly: the GP is a prior over functions conditioned on them.
    """
    n = len(xs_train)
    gram = gram_matrix(kernel, xs_train)
    C = [[gram[i][j] + (noise if i == j else 0.0) for j in range(n)]
         for i in range(n)]
    L = cholesky_with_fallback(C)
    alpha = _chol_solve(L, ys_train)
    means = []
    variances = []
    for x in xs_test:
        k_star = [kernel(x, xt) for xt in xs_train]
        mean = sum(k_star[i] * alpha[i] for i in range(n))
        v = _chol_solve(L, k_star)
        variance = kernel(x, x) - sum(k_star[i] * v[i] for i in range(n))
        means.append(mean)
        variances.append(max(variance, 0.0))
    return means, variances


def gp_log_marginal_likelihood(xs, ys, kernel, noise):
    """The log evidence ``ln p(y | X)`` of a zero-mean GP.

    ``ln p(y) = -1/2 y^T C^{-1} y - 1/2 ln |C| - n/2 ln(2 pi)`` with
    ``C = K + noise I``. The two determinants come from the Cholesky factor:
    ``ln |C| = 2 sum_i ln L_ii``.
    """
    n = len(xs)
    C = _observation_covariance(kernel, xs, noise)
    L = cholesky_with_fallback(C)
    alpha = _chol_solve(L, ys)
    data_fit = sum(ys[i] * alpha[i] for i in range(n))
    log_det = 2.0 * sum(math.log(L[i][i]) for i in range(n))
    return -0.5 * data_fit - 0.5 * log_det - 0.5 * n * math.log(2.0 * math.pi)


def log_marginal_gradient_fd(xs, ys, kernel, params, noise, h=1e-5):
    """Central finite differences of the evidence w.r.t. the hyperparameters.

    ``kernel`` is a *factory*: ``kernel(params) -> k(x, y)``, so a perturbed
    parameter vector builds the perturbed kernel. ``params`` is a list of
    hyperparameter values in the factory's order. The result is a list with one
    partial derivative per parameter. Central differences are used because the
    error is ``O(h^2)`` rather than ``O(h)``.
    """
    gradient = []
    for i in range(len(params)):
        up = list(params)
        up[i] += h
        down = list(params)
        down[i] -= h
        f_up = gp_log_marginal_likelihood(xs, ys, kernel(up), noise)
        f_down = gp_log_marginal_likelihood(xs, ys, kernel(down), noise)
        gradient.append((f_up - f_down) / (2.0 * h))
    return gradient


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo():
    xs = [-2.0, -1.2, -0.4, 0.4, 1.2, 2.0]
    ys = [math.sin(x) + 0.4 * x for x in xs]
    kernel = rbf_kernel(0.8, 1.0)
    K = gram_matrix(kernel, xs)
    print("Kernels and Gaussian processes — demo")
    print(f"  RBF Gram matrix: {len(K)}x{len(K)}, "
          f"min eigenvalue={min(_symmetric_eigenvalues(K)):.3e}, is_psd={is_psd(K)}")

    mean, _ = gp_posterior(xs, ys, xs, kernel, 0.0)
    error = max(abs(mean[i] - ys[i]) for i in range(len(xs)))
    print(f"  noise-free GP interpolation: max |mean - y| = {error:.2e}")

    test = [1.6, 2.4, 3.2, 4.0]
    _, far = gp_posterior(xs, ys, test, kernel, 0.0)
    print("  posterior std away from the data at x="
          + str(test) + ": " + ", ".join(f"{math.sqrt(v):.4f}" for v in far))

    noise = 0.05
    kernel_n = rbf_kernel(0.8, 1.0)
    lml = gp_log_marginal_likelihood(xs, ys, kernel_n, noise)
    factory = lambda p: rbf_kernel(p[0], p[1])  # noqa: E731
    grad = log_marginal_gradient_fd(xs, ys, factory, [0.8, 1.0], noise)
    print(f"  log marginal likelihood (noise={noise}): {lml:.6f}")
    print("  finite-difference gradient w.r.t. [length_scale, variance]: "
          f"[{grad[0]:.6f}, {grad[1]:.6f}]")

    invalid = lambda x, y: -x * y  # noqa: E731
    K_bad = gram_matrix(invalid, [-1.0, 0.5, 2.0])
    print(f"  invalid kernel k(x,y) = -x y: min eigenvalue="
          f"{min(_symmetric_eigenvalues(K_bad)):.3e}, is_psd={is_psd(K_bad)}")

    duplicated = [0.0, 0.0, 1.0, 2.0]
    K_dup = gram_matrix(rbf_kernel(1.0, 1.0), duplicated)
    try:
        cholesky(K_dup)
        print("  singular Gram (duplicated input): cholesky unexpectedly succeeded")
    except ValueError:
        print("  singular Gram (duplicated input): cholesky fails without jitter")
    L = cholesky(K_dup, 1e-8)
    print(f"  cholesky(K_dup, jitter=1e-8) succeeds, "
          f"min diagonal={min(L[i][i] for i in range(len(L))):.3e}")


if __name__ == "__main__":
    demo()
