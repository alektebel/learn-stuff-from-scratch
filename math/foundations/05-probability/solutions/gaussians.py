"""Multivariate Gaussians from scratch: density, sampling, conditioning, change of variables.

Restates *Mathematics for Machine Learning* (Deisenroth, Faisal & Ong), chapter 6
("Probability and Distributions"): the closure properties of the Gaussian — a linear map
of a Gaussian is Gaussian, a product of Gaussians is Gaussian, its marginals and
conditionals are Gaussian — and how a probability density transforms under a change of
variables. Pure Python (standard library only); every matrix operation is written here.

The theme: **the Gaussian is the distribution whose algebra is linear, and the Cholesky
factor is the numerically honest way to compute with it.** A log density is evaluated
with a triangular solve, never by forming ``Σ⁻¹`` or ``det Σ``; a sample is ``μ + L z``
with ``L`` the Cholesky factor of ``Σ``; a conditional is a Schur complement. Drop the
Jacobian from a change of variables and the result is not a density any more.

DESIGN DECISION — inverse and determinant, or Cholesky?
Writing ``-½( log det Σ + (x−μ)ᵀΣ⁻¹(x−μ) )`` is the textbook formula and hides nothing.
But ``det Σ`` is a product of ``n`` eigenvalues: on a nearly singular covariance it loses
``≈ n·κ·ε`` relative digits, and the quadratic form through ``Σ⁻¹`` loses them too.
**Chosen: one Cholesky factor Σ = L Lᵀ, one forward solve L z = x−μ, and
``log det Σ = 2 Σ log Lᵢᵢ``.** The cost is that evaluating the density requires a
factorisation (``O(n³)``) instead of a stored inverse; the benefit is that the answer
stays accurate on the nearly singular covariances that actually occur (see the demo and
check step 4).

DESIGN DECISION — sample with ``random.gauss``, or with an explicitly written normal?
The standard library already provides ``random.gauss``, and re-deriving Box-Muller adds
a way to be wrong without teaching the Gaussian. **Chosen: the caller passes a
``random.Random`` and the sampler calls ``rng.gauss(0, 1)``.** The lesson is the
transform ``x = μ + L z``, not the generation of the scalar normal; taking the uniform
stream from the caller keeps the Monte-Carlo checks reproducible.

DESIGN DECISION — a fixed 2-block API, or general index lists?
The conditional of a 2-block Gaussian is the formula the chapter prints, and fixing the
blocks to ``(first half, second half)`` is shorter. **Chosen: index lists ``idx_a``,
``idx_b``**, because marginalisation, conditioning and the Schur complement are the same
operation on any subset of coordinates; the 2-block case is just ``idx_a=[0,1]``,
``idx_b=[2,3]``, and one function covers both without duplicating the solves.

DESIGN DECISION — the product of Gaussians in covariance or precision form?
Covariance form needs two inversions plus a third to return ``Σ``; the precision form
adds the precisions, which is the operation that is actually linear. **Chosen: the
precision form** ``P = Σ₁⁻¹ + Σ₂⁻¹``, ``μ = P⁻¹(Σ₁⁻¹μ₁ + Σ₂⁻¹μ₂)``. For two
Gaussians the product covariance shrinks below either factor — the probabilistic
reading of "combining two measurements makes you more certain" — and the precision
addition states that directly.

    python3 gaussians.py      # prints the measurements this file promises
"""

import math

_EPS = 1e-12
_TWO_PI = 2.0 * math.pi


class NotPositiveDefinite(Exception):
    """A covariance matrix must be symmetric positive definite (or it is not a covariance)."""


# ---------------------------------------------------------------------------
# Small matrix helpers — provided, not part of the exercise.
# ---------------------------------------------------------------------------

def _dot(u, v):
    return sum(a * b for a, b in zip(u, v))


def _matvec(A, v):
    return [sum(A[i][j] * v[j] for j in range(len(v))) for i in range(len(A))]


def _matmul(A, B):
    return [[sum(A[i][t] * B[t][j] for t in range(len(B)))
             for j in range(len(B[0]))] for i in range(len(A))]


def _transpose(A):
    return [list(row) for row in zip(*A)]


def _identity(n):
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _submatrix(A, rows, cols):
    return [[A[i][j] for j in cols] for i in rows]


def _forward_sub(L, b):
    """Solve L y = b for lower-triangular L with a non-zero diagonal."""
    n = len(L)
    y = [0.0] * n
    for i in range(n):
        s = b[i] - sum(L[i][j] * y[j] for j in range(i))
        y[i] = s / L[i][i]
    return y


def _back_sub(U, b):
    """Solve U y = b for upper-triangular U with a non-zero diagonal."""
    n = len(U)
    y = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = b[i] - sum(U[i][j] * y[j] for j in range(i + 1, n))
        y[i] = s / U[i][i]
    return y


def solve_spd(A, B):
    """Solve A X = B for a symmetric positive definite A, via its Cholesky factor.

    One factorisation serves every right-hand side: forward-substitute L Y = B, then
    back-substitute Lᵀ X = Y. This replaces "multiply by the inverse": never forming
    A⁻¹ is the point, and it is provided here as arithmetic support.
    """
    L = cholesky(A)
    n = len(A)
    cols = len(B[0])
    X = [[0.0] * cols for _ in range(n)]
    for c in range(cols):
        y = _forward_sub(L, [B[i][c] for i in range(n)])
        x = _back_sub(_transpose(L), y)
        for i in range(n):
            X[i][c] = x[i]
    return X


# ---------------------------------------------------------------------------
# 1. Cholesky: a covariance matrix is defined by its factor
# ---------------------------------------------------------------------------

def cholesky(A):
    """The Cholesky factor L of a symmetric positive definite matrix A = L Lᵀ.

    L is lower triangular with a strictly positive diagonal. The pivot on the diagonal
    is the squared length of the new direction, so ``pivot <= 0`` means some direction
    has non-positive variance and A is not a covariance. One pass both decides SPD and
    factors, so "has a Cholesky factor" and "is a covariance" are the same predicate.

    Raises NotPositiveDefinite when A is not square, not symmetric, or has a
    non-positive pivot — never returns a NaN factor.
    """
    n = len(A)
    if any(len(row) != n for row in A):
        raise NotPositiveDefinite("Cholesky needs a square matrix")
    scale = max(1.0, max(abs(v) for row in A for v in row))
    for i in range(n):
        for j in range(n):
            if abs(A[i][j] - A[j][i]) > _EPS * scale:
                raise NotPositiveDefinite("Cholesky needs a symmetric matrix")
    L = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = A[i][j] - sum(L[i][k] * L[j][k] for k in range(j))
            if i == j:
                if s <= 0.0:
                    raise NotPositiveDefinite(
                        f"pivot {s:.3e} at ({i},{i}) is not positive: A is not positive definite")
                L[i][i] = math.sqrt(s)
            else:
                L[i][j] = s / L[j][j]
    return L


# ---------------------------------------------------------------------------
# 2. The density, as a log to avoid underflow
# ---------------------------------------------------------------------------

def log_gaussian_density(x, mu, Sigma):
    """The log density of N(mu, Sigma) at x, through the Cholesky factor of Sigma.

    log p(x) = -½ ( n log 2π + log det Σ + (x−μ)ᵀ Σ⁻¹ (x−μ) ).

    With Σ = L Lᵀ, the quadratic form is ``‖L⁻¹(x−μ)‖²`` (one forward solve) and
    ``log det Σ = 2 Σ log Lᵢᵢ``. Neither Σ⁻¹ nor det Σ is formed; the log is returned
    rather than the density because the density itself underflows for even moderate n.
    """
    n = len(mu)
    if len(x) != n or len(Sigma) != n:
        raise ValueError("x, mu and Sigma must agree on the dimension")
    L = cholesky(Sigma)
    z = _forward_sub(L, [x[i] - mu[i] for i in range(n)])
    quadratic = _dot(z, z)
    log_det = 2.0 * sum(math.log(L[i][i]) for i in range(n))
    return -0.5 * (n * math.log(_TWO_PI) + log_det + quadratic)


def gaussian_density(x, mu, Sigma):
    """The density of N(mu, Sigma) at x, the exponential of the log density."""
    return math.exp(log_gaussian_density(x, mu, Sigma))


# ---------------------------------------------------------------------------
# 3. Sampling: x = mu + L z
# ---------------------------------------------------------------------------

def sample_gaussian(mu, Sigma, rng):
    """One draw from N(mu, Sigma), using the caller's ``random.Random``.

    If z ~ N(0, I) then x = μ + L z has mean μ and covariance L Lᵀ = Σ. Drawing z with
    ``rng.gauss`` keeps the Monte-Carlo checks reproducible; the lesson is the linear
    map, not the scalar normal.
    """
    n = len(mu)
    L = cholesky(Sigma)
    z = [rng.gauss(0.0, 1.0) for _ in range(n)]
    return [mu[i] + sum(L[i][j] * z[j] for j in range(i + 1)) for i in range(n)]


# ---------------------------------------------------------------------------
# 4. Linear maps and products stay Gaussian
# ---------------------------------------------------------------------------

def linear_transform(mu, Sigma, A, b=None):
    """The law of Y = A X + b when X ~ N(mu, Sigma): returns (mean, covariance).

    mean = A μ + b, covariance = A Σ Aᵀ. The Gaussian family is closed under affine
    maps, which is why every layer of a linear-Gaussian model stays tractable.
    """
    n = len(mu)
    m = len(A)
    if b is None:
        b = [0.0] * m
    mu_y = [b[i] + sum(A[i][j] * mu[j] for j in range(n)) for i in range(m)]
    Sigma_y = _matmul(_matmul(A, Sigma), _transpose(A))
    return mu_y, Sigma_y


def product_of_gaussians(mu1, Sigma1, mu2, Sigma2):
    """The Gaussian proportional to N(mu1, Sigma1)·N(mu2, Sigma2): returns (mean, cov).

    In precision form P = Σ₁⁻¹ + Σ₂⁻¹ and μ = P⁻¹(Σ₁⁻¹μ₁ + Σ₂⁻¹μ₂). The result is the
    Bayesian update: multiplying two beliefs about the same quantity sharpens it, so
    the product covariance is below either factor in the Loewner order.
    """
    n = len(mu1)
    I = _identity(n)
    P1 = solve_spd(Sigma1, I)
    P2 = solve_spd(Sigma2, I)
    P = [[P1[i][j] + P2[i][j] for j in range(n)] for i in range(n)]
    rhs = [sum(P1[i][j] * mu1[j] for j in range(n))
           + sum(P2[i][j] * mu2[j] for j in range(n)) for i in range(n)]
    Sigma = solve_spd(P, I)
    mu = _matvec(Sigma, rhs)
    return mu, Sigma


# ---------------------------------------------------------------------------
# 5. Marginals and conditionals: the Schur complement
# ---------------------------------------------------------------------------

def marginal(mu, Sigma, idx):
    """The marginal law of the coordinates in ``idx``: just the matching block.

    Marginals of a Gaussian need no integration: the block of the mean and the
    corresponding principal submatrix of the covariance are the answer.
    """
    return [mu[i] for i in idx], _submatrix(Sigma, idx, idx)


def conditional(mu, Sigma, idx_a, idx_b, x_b):
    """The law of coordinates ``idx_a`` given coordinates ``idx_b`` fixed at ``x_b``.

    With the blocks Σ_aa, Σ_ab, Σ_bb of Σ,
        Σ_{a|b} = Σ_aa − Σ_ab Σ_bb⁻¹ Σ_ba        (Schur complement)
        μ_{a|b} = μ_a + Σ_ab Σ_bb⁻¹ (x_b − μ_b).
    The subtraction is the whole content: conditioning removes the variance already
    explained by x_b, so Σ_{a|b} is below Σ_aa. One solve against Σ_bb gives
    Y = Σ_bb⁻¹ Σ_ba; then the mean adds ``Yᵀ(x_b − μ_b)`` and the covariance drops
    ``Σ_ab Y``.
    """
    S_aa = _submatrix(Sigma, idx_a, idx_a)
    S_ab = _submatrix(Sigma, idx_a, idx_b)
    S_bb = _submatrix(Sigma, idx_b, idx_b)
    Y = solve_spd(S_bb, _transpose(S_ab))              # Σ_bb⁻¹ Σ_ba
    d = [x_b[c] - mu[idx_b[c]] for c in range(len(idx_b))]
    na = len(idx_a)
    mu_a = [mu[idx_a[r]] + sum(Y[c][r] * d[c] for c in range(len(idx_b))) for r in range(na)]
    S_ab_Y = _matmul(S_ab, Y)
    Sigma_a = [[S_aa[r][c] - S_ab_Y[r][c] for c in range(na)] for r in range(na)]
    return mu_a, Sigma_a


# ---------------------------------------------------------------------------
# 6. Change of variables: the Jacobian is not optional
# ---------------------------------------------------------------------------

def change_of_variables_1d(pdf_x, g_inv, g_inv_prime):
    """The density of Y = g(X) from the density of X, for a monotone g.

    p_Y(y) = p_X(g⁻¹(y)) · |(g⁻¹)'(y)|. The absolute derivative is the Jacobian of the
    transformation: it accounts for how much a unit interval at y stretches when mapped
    back to x. Dropping it leaves a function that does not integrate to 1 and is
    therefore not a density at all (see check step 10).
    """

    def p_Y(y):
        return pdf_x(g_inv(y)) * abs(g_inv_prime(y))

    return p_Y


if __name__ == "__main__":
    import random
    import math as _m

    def _maxabs(M):
        return max(abs(v) for row in M for v in row)

    mu = [0.0, 1.0]
    Sigma = [[1.0, 0.5], [0.5, 1.0]]
    A = [[1.0, -1.0], [0.0, 2.0]]
    b = [0.5, -1.0]

    # (a) Monte-Carlo moments against the parameters.
    rng = random.Random(1)
    N = 20000
    xs = [sample_gaussian(mu, Sigma, rng) for _ in range(N)]
    mean_hat = [sum(p[i] for p in xs) / N for i in range(2)]
    cov_hat = [[sum((p[i] - mean_hat[i]) * (p[j] - mean_hat[j]) for p in xs) / N
                for j in range(2)] for i in range(2)]
    mean_err = max(abs(mean_hat[i] - mu[i]) for i in range(2))
    cov_err = _maxabs([[cov_hat[i][j] - Sigma[i][j] for j in range(2)] for i in range(2)])

    # (b) A linear map and a product.
    mu_y, Sigma_y = linear_transform(mu, Sigma, A, b)
    mu_p, Sigma_p = product_of_gaussians([0.0], [[1.0]], [1.0], [[2.0]])

    # (c) Conditioning a 2-block Gaussian.
    mu4 = [0.0, 0.0, 0.0, 0.0]
    S4 = [[1.0, 0.3, 0.5, 0.0],
          [0.3, 1.0, 0.2, 0.4],
          [0.5, 0.2, 1.0, 0.1],
          [0.0, 0.4, 0.1, 1.0]]
    mu_c, S_c = conditional(mu4, S4, [0, 1], [2, 3], [0.3, -0.2])

    # (d) Change of variables towards a log-normal, and its integral.
    def phi(x):
        return _m.exp(-0.5 * x * x) / _m.sqrt(_TWO_PI)

    p_log = change_of_variables_1d(phi, _m.log, lambda y: 1.0 / y)
    # A uniform grid in y is too coarse around the peak at y = 1; integrate with the
    # substitution y = eᶻ (which is the inverse map itself), so dy = eᶻ dz.
    lo, hi, steps = -8.0, 8.0, 4000
    h = (hi - lo) / steps
    integral = 0.0
    for k in range(steps + 1):
        z = lo + k * h
        w = 1.0 if k in (0, steps) else (4.0 if k % 2 else 2.0)
        integral += w * p_log(_m.exp(z)) * _m.exp(z)
    integral *= h / 3.0

    # (e) Log density when det Σ underflows: the Cholesky pivots survive.
    om = 1.0 - 1e-8
    tiny = 1e-160
    S_near = [[1.0, om, 0.0, 0.0],
              [om, 1.0, 0.0, 0.0],
              [0.0, 0.0, tiny, 0.0],
              [0.0, 0.0, 0.0, tiny]]
    naive_det = (1.0 - om * om) * tiny * tiny
    log_near = log_gaussian_density([0.3, -0.2, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], S_near)

    print("Multivariate Gaussians from scratch — measurements")
    print(f"  sampling   N = {N}  max|mean−μ| = {mean_err:.4f}  max|cov−Σ| = {cov_err:.4f}")
    print(f"  linear map μ_y = [{mu_y[0]:.2f}, {mu_y[1]:.2f}]  max|Σ_y−AΣAᵀ| = "
          f"{_maxabs([[Sigma_y[i][j] - _matmul(_matmul(A, Sigma), _transpose(A))[i][j] for j in range(2)] for i in range(2)]):.1e}")
    print(f"  product    μ = {mu_p[0]:.4f}  σ² = {Sigma_p[0][0]:.4f}  (below both 1 and 2)")
    print(f"  conditional μ_{{a|b}} = [{mu_c[0]:.3f}, {mu_c[1]:.3f}]  "
          f"var = [{S_c[0][0]:.3f}, {S_c[1][1]:.3f}]  (below the marginal 1.000)")
    print(f"  change-var ∫ p_Y dy = {integral:.6f}  (Jacobian included)")
    print(f"  near-singular det Σ = {naive_det:g} (underflows)  log p = {log_near:.3f} (Cholesky path)")
