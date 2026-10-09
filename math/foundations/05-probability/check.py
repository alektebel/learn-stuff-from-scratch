"""
Progress checker for the probability templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

Every reference value is computed here, independently: exact rational (Fraction)
arithmetic for the density oracles, the checker's own Gaussian elimination for the
regression and Schur references, closed-form 2×2 inverses, and numerical quadrature for
the integrals. The checker never asks your code what the right answer is.
"""

import math
import pathlib
import random
import shutil
import sys
import traceback
from fractions import Fraction

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


# ---------------------------------------------------------------------------
# The checker's own arithmetic (independent of the learner's)
# ---------------------------------------------------------------------------

def _dot(u, v):
    return sum(a * b for a, b in zip(u, v))


def _matmul(A, B):
    return [[sum(A[i][t] * B[t][j] for t in range(len(B))) for j in range(len(B[0]))]
            for i in range(len(A))]


def _transpose(A):
    return [list(row) for row in zip(*A)]


def _matvec(A, v):
    return [sum(A[i][j] * v[j] for j in range(len(v))) for i in range(len(A))]


def _identity(n):
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _maxabs(A):
    return max(abs(v) for row in A for v in row)


def _submatrix(A, rows, cols):
    return [[A[i][j] for j in cols] for i in rows]


def _inverse(A):
    """A⁻¹ by Gauss-Jordan with partial pivoting; the checker's own reference."""
    n = len(A)
    M = [list(A[i]) + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for col in range(n):
        p = max(range(col, n), key=lambda i: abs(M[i][col]))
        if abs(M[p][col]) < 1e-300:
            raise ZeroDivisionError("singular matrix in reference")
        M[col], M[p] = M[p], M[col]
        pv = M[col][col]
        M[col] = [v / pv for v in M[col]]
        for i in range(n):
            if i != col and M[i][col]:
                f = M[i][col]
                M[i] = [a - f * b for a, b in zip(M[i], M[col])]
    return [row[n:] for row in M]


def _cholesky(A):
    n = len(A)
    L = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = A[i][j] - sum(L[i][k] * L[j][k] for k in range(j))
            if i == j:
                L[i][i] = math.sqrt(s)
            else:
                L[i][j] = s / L[j][j]
    return L


def _sample(mu, Sigma, rng):
    """The checker's own draw, so sampling tests never lean on the learner's sampler."""
    L = _cholesky(Sigma)
    n = len(mu)
    z = [rng.gauss(0.0, 1.0) for _ in range(n)]
    return [mu[i] + sum(L[i][j] * z[j] for j in range(i + 1)) for i in range(n)]


def _simpson(f, lo, hi, n):
    """Composite Simpson's rule with n (even) intervals."""
    h = (hi - lo) / n
    s = f(lo) + f(hi)
    for k in range(1, n):
        s += (4.0 if k % 2 else 2.0) * f(lo + k * h)
    return s * h / 3.0


def _frac_det_inv(A):
    """Exact determinant and inverse of an integer/Fraction matrix, over Fraction."""
    n = len(A)
    M = [[Fraction(A[i][j]) for j in range(n)]
         + [Fraction(1 if i == j else 0) for j in range(n)] for i in range(n)]
    det = Fraction(1)
    for col in range(n):
        p = next((i for i in range(col, n) if M[i][col] != 0), None)
        if p is None:
            return Fraction(0), None
        if p != col:
            M[col], M[p] = M[p], M[col]
            det = -det
        det *= M[col][col]
        pv = M[col][col]
        M[col] = [v / pv for v in M[col]]
        for i in range(n):
            if i != col and M[i][col] != 0:
                f = M[i][col]
                M[i] = [a - f * b for a, b in zip(M[i], M[col])]
    inv = [[M[i][n + j] for j in range(n)] for i in range(n)]
    return det, inv


def _frac_log_density(A_int, mu, x):
    """Exact-hyperarithmetic reference log density at integer inputs, then float."""
    mu_f = [Fraction(m) for m in mu]
    d = [Fraction(x[i]) - mu_f[i] for i in range(len(x))]
    det, inv = _frac_det_inv(A_int)
    qf = sum(d[i] * inv[i][j] * d[j] for i in range(len(d)) for j in range(len(d)))
    return -0.5 * (len(x) * math.log(2.0 * math.pi) + math.log(float(det)) + float(qf))


# ---------------------------------------------------------------------------
# Step 1: Cholesky factors a covariance and rejects a non-covariance
# ---------------------------------------------------------------------------

def check_cholesky_spd() -> None:
    from gaussians import NotPositiveDefinite, cholesky

    A = [[4.0, 2.0], [2.0, 3.0]]
    L = cholesky(A)
    assert len(L) == 2 and all(L[0][1] == 0.0 for _ in [0]), (
        "the Cholesky factor is lower triangular: L[0][1] must be 0")
    assert all(L[i][i] > 0.0 for i in range(2)), "a Cholesky diagonal must be strictly positive"
    assert _maxabs([[sum(L[i][k] * L[j][k] for k in range(2)) - A[i][j]
                     for j in range(2)] for i in range(2)]) < 1e-12, (
        "L Lᵀ ≠ A: the factor does not reconstruct the covariance")

    A3 = [[4.0, 2.0, 1.0], [2.0, 5.0, 3.0], [1.0, 3.0, 6.0]]
    L3 = cholesky(A3)
    assert _maxabs([[sum(L3[i][k] * L3[j][k] for k in range(3)) - A3[i][j]
                     for j in range(3)] for i in range(3)]) < 1e-12, "3×3 L Lᵀ ≠ A"
    for i in range(3):
        for j in range(i + 1, 3):
            assert L3[i][j] == 0.0, "the Cholesky factor must be lower triangular"

    bad = {
        "an indefinite matrix": [[1.0, 0.0], [0.0, -1.0]],
        "a singular matrix": [[1.0, 1.0], [1.0, 1.0]],
        "a non-symmetric matrix": [[1.0, 2.0], [3.0, 4.0]],
        "a non-square matrix": [[1.0, 0.0], [0.0, 1.0], [0.0, 1.0]],
    }
    for name, M in bad.items():
        try:
            cholesky(M)
            raise AssertionError(
                f"cholesky() accepted {name} {M}: a covariance must be symmetric positive "
                "definite, and a non-positive pivot means some direction has variance ≤ 0")
        except NotPositiveDefinite:
            pass


# ---------------------------------------------------------------------------
# Step 2: the log density matches an exact rational reference
# ---------------------------------------------------------------------------

def check_log_density_matches_formula() -> None:
    from gaussians import gaussian_density, log_gaussian_density

    # Integer SPD matrices, so the reference is exact over Fraction.
    cases = [
        ([[4, 1], [1, 3]], [0, 0], [1, -1]),
        ([[5, 2, 0], [2, 4, 1], [0, 1, 3]], [1, -2, 0], [2, 1, -1]),
        ([[2, -1], [-1, 2]], [0, 0], [3, 3]),
    ]
    for A, mu, x in cases:
        got = log_gaussian_density([float(v) for v in x], [float(v) for v in mu],
                                   [[float(v) for v in row] for row in A])
        ref = _frac_log_density(A, mu, x)
        assert abs(got - ref) < 1e-9, (
            f"log density {got:.12f} ≠ exact reference {ref:.12f}: check the quadratic form "
            "L z = x−μ and the log determinant 2 Σ log Lᵢᵢ")
        d = gaussian_density([float(v) for v in x], [float(v) for v in mu],
                             [[float(v) for v in row] for row in A])
        assert abs(d - math.exp(ref)) < 1e-9, "gaussian_density must be exp(log_gaussian_density)"


# ---------------------------------------------------------------------------
# Step 3: the density integrates to 1 (numerical quadrature)
# ---------------------------------------------------------------------------

def check_density_integrates_to_one() -> None:
    from gaussians import gaussian_density

    mu = [0.0, 0.0]
    Sigma = [[1.0, 0.5], [0.5, 1.0]]
    lo, hi, n = -8.0, 8.0, 400
    h = (hi - lo) / n
    weights = []
    for k in range(n + 1):
        weights.append(1.0 if k in (0, n) else (4.0 if k % 2 else 2.0))
    total = 0.0
    for i in range(n + 1):
        for j in range(n + 1):
            x = lo + i * h
            y = lo + j * h
            total += weights[i] * weights[j] * gaussian_density([x, y], mu, Sigma)
    total *= (h / 3.0) ** 2
    assert abs(total - 1.0) < 1e-6, (
        f"∫∫ N(x; μ, Σ) dx = {total:.9f}, expected 1: the normalising constant or the "
        "quadratic form is wrong")


# ---------------------------------------------------------------------------
# Step 4: a nearly singular covariance (limit case — Cholesky, not inverse+det)
# ---------------------------------------------------------------------------

def check_log_density_nearly_singular() -> None:
    from gaussians import log_gaussian_density

    # A covariance with a nearly dependent block AND a tiny-variance block. Its
    # determinant is ~2e-8 * (1e-160)^2 ≈ 2e-328: below the smallest double, so any
    # code that forms det Σ sees 0.0. The log determinant through the Cholesky pivots
    # (log det = 2 Σ log Lᵢᵢ) is ~ -756 and survives.
    one_minus = 1.0 - 1e-8
    tiny = 1e-160
    Sigma = [[1.0, one_minus, 0.0, 0.0],
             [one_minus, 1.0, 0.0, 0.0],
             [0.0, 0.0, tiny, 0.0],
             [0.0, 0.0, 0.0, tiny]]
    mu = [0.0, 0.0, 0.0, 0.0]
    x = [0.3, -0.2, 0.0, 0.0]                 # nothing in the tiny directions, to stay finite

    det_a = 1.0 - one_minus * one_minus        # the determinant the float input actually has
    qa = (x[0] * x[0] - 2.0 * one_minus * x[0] * x[1] + x[1] * x[1]) / det_a
    ref = -0.5 * (4 * math.log(2.0 * math.pi) + math.log(det_a)
                  + 2 * math.log(tiny) + qa)

    got = log_gaussian_density(x, mu, Sigma)
    assert math.isfinite(got), "the log density blew up on a nearly singular covariance"
    assert abs(got - ref) < 1e-3, (
        f"log density {got:.6f} ≠ {ref:.6f} on a covariance whose determinant underflows "
        "(det ≈ 2e-328): forming det Σ gives 0.0; use the Cholesky pivots, "
        "log det Σ = 2 Σ log Lᵢᵢ, and solve L z = x − μ")


# ---------------------------------------------------------------------------
# Step 5: sampled mean and covariance match the parameters (Monte Carlo + CLT)
# ---------------------------------------------------------------------------

def check_sampling_moments() -> None:
    from gaussians import sample_gaussian

    mu = [1.0, -2.0, 0.5]
    Sigma = [[1.0, 0.4, -0.2],
             [0.4, 2.0, 0.3],
             [-0.2, 0.3, 0.5]]
    N = 40000
    rng = random.Random(11)
    xs = [sample_gaussian(mu, Sigma, rng) for _ in range(N)]
    mean_hat = [sum(p[i] for p in xs) / N for i in range(3)]
    cov_hat = [[sum((p[i] - mean_hat[i]) * (p[j] - mean_hat[j]) for p in xs) / N
                for j in range(3)] for i in range(3)]

    # CLT: se(mean_i) = sqrt(Σᵢᵢ/N), se(cov_ij) ≈ sqrt((ΣᵢᵢΣⱼⱼ + Σᵢⱼ²)/N).
    tol_mean = 6.0 * max(math.sqrt(Sigma[i][i] / N) for i in range(3))
    tol_cov = 6.0 * max(math.sqrt((Sigma[i][i] * Sigma[j][j] + Sigma[i][j] ** 2) / N)
                        for i in range(3) for j in range(3))
    for i in range(3):
        assert abs(mean_hat[i] - mu[i]) < tol_mean, (
            f"sample mean {mean_hat[i]:.4f} ≠ {mu[i]} beyond the CLT tolerance {tol_mean:.4f}: "
            "the shift μ is missing from x = μ + L z")
        for j in range(3):
            assert abs(cov_hat[i][j] - Sigma[i][j]) < tol_cov, (
                f"sample covariance ({i},{j}) = {cov_hat[i][j]:.4f} ≠ {Sigma[i][j]} beyond "
                f"{tol_cov:.4f}: x = μ + L z must use the Cholesky factor of Σ, not z itself")


# ---------------------------------------------------------------------------
# Step 6: an affine map of a Gaussian is Gaussian
# ---------------------------------------------------------------------------

def check_linear_transform() -> None:
    from gaussians import linear_transform

    mu = [0.5, -1.0, 2.0]
    Sigma = [[1.0, 0.2, 0.0],
             [0.2, 1.5, -0.3],
             [0.0, -0.3, 0.8]]
    A = [[1.0, -2.0, 0.5], [0.0, 1.0, 1.0]]
    b = [1.0, -0.5]

    mu_y, Sigma_y = linear_transform(mu, Sigma, A, b)
    ref_mu = [b[i] + sum(A[i][j] * mu[j] for j in range(3)) for i in range(2)]
    ref_S = _matmul(_matmul(A, Sigma), _transpose(A))
    assert max(abs(mu_y[i] - ref_mu[i]) for i in range(2)) < 1e-12, (
        "the transformed mean must be A μ + b")
    assert _maxabs([[Sigma_y[i][j] - ref_S[i][j] for j in range(2)] for i in range(2)]) < 1e-12, (
        "the transformed covariance must be A Σ Aᵀ (both sides!), not A Σ")

    # Independent closure check: moments of A·X + b for samples of X.
    N = 40000
    rng = random.Random(23)
    ys = []
    for _ in range(N):
        x = _sample(mu, Sigma, rng)
        ys.append([b[i] + sum(A[i][j] * x[j] for j in range(3)) for i in range(2)])
    mean_hat = [sum(p[i] for p in ys) / N for i in range(2)]
    cov_hat = [[sum((p[i] - mean_hat[i]) * (p[j] - mean_hat[j]) for p in ys) / N
                for j in range(2)] for i in range(2)]
    tol_mean = 6.0 * max(math.sqrt(ref_S[i][i] / N) for i in range(2))
    tol_cov = 6.0 * max(math.sqrt((ref_S[i][i] * ref_S[j][j] + ref_S[i][j] ** 2) / N)
                        for i in range(2) for j in range(2))
    assert max(abs(mean_hat[i] - ref_mu[i]) for i in range(2)) < tol_mean, (
        f"sampled A·X + b mean {mean_hat} ≠ {ref_mu} beyond the CLT tolerance {tol_mean:.3f}")
    assert _maxabs([[cov_hat[i][j] - ref_S[i][j] for j in range(2)] for i in range(2)]) < tol_cov, (
        f"sampled A·X + b covariance {cov_hat} ≠ analytic A Σ Aᵀ beyond {tol_cov:.3f}")

    mu0, Sigma0 = linear_transform(mu, Sigma, [[1.0, 0.0, 0.0]])
    assert abs(mu0[0] - mu[0]) < 1e-12 and abs(Sigma0[0][0] - Sigma[0][0]) < 1e-12, (
        "b must default to 0")


# ---------------------------------------------------------------------------
# Step 7: the product of two Gaussians is Gaussian (precision form)
# ---------------------------------------------------------------------------

def check_product_of_gaussians() -> None:
    from gaussians import product_of_gaussians

    mu1, S1 = [0.0, 0.0], [[1.0, 0.2], [0.2, 1.0]]
    mu2, S2 = [1.0, -1.0], [[2.0, -0.5], [-0.5, 1.5]]

    mu, S = product_of_gaussians(mu1, S1, mu2, S2)
    P1, P2 = _inverse(S1), _inverse(S2)
    P = [[P1[i][j] + P2[i][j] for j in range(2)] for i in range(2)]
    ref_S = _inverse(P)
    rhs = _matvec(P1, mu1)
    rhs = [rhs[i] + _matvec(P2, mu2)[i] for i in range(2)]
    ref_mu = _matvec(ref_S, rhs)

    assert _maxabs([[S[i][j] - S[j][i] for j in range(2)] for i in range(2)]) < 1e-12, (
        "the product covariance must be symmetric")
    assert max(abs(mu[i] - ref_mu[i]) for i in range(2)) < 1e-9, (
        f"product mean {mu} ≠ {ref_mu}: combine precisions, μ = (Σ₁⁻¹+Σ₂⁻¹)⁻¹(Σ₁⁻¹μ₁+Σ₂⁻¹μ₂)")
    assert _maxabs([[S[i][j] - ref_S[i][j] for j in range(2)] for i in range(2)]) < 1e-9, (
        f"product covariance {S} ≠ {ref_S}: the precisions add, then invert")
    assert abs(S[0][0] - S1[0][0]) > 1e-6 and abs(S[0][0] - S2[0][0]) > 1e-6, (
        "the product must be sharper than either factor: combining two measurements "
        "reduces the variance")


# ---------------------------------------------------------------------------
# Step 8: marginalising a Gaussian
# ---------------------------------------------------------------------------

def check_marginal() -> None:
    from gaussians import marginal

    mu = [0.5, -1.0, 2.0, 0.0]
    Sigma = [[1.0, 0.3, 0.5, 0.0],
             [0.3, 1.0, 0.2, 0.4],
             [0.5, 0.2, 1.0, 0.1],
             [0.0, 0.4, 0.1, 1.0]]
    idx = [0, 2]
    m, S = marginal(mu, Sigma, idx)
    assert m == [mu[0], mu[2]], "the marginal mean is the matching block of μ"
    assert _maxabs([[S[r][c] - Sigma[idx[r]][idx[c]] for c in range(2)] for r in range(2)]) < 1e-15, (
        "the marginal covariance is the principal submatrix Σ[idx, idx]: marginals need no "
        "integration for a Gaussian")

    # And it matches the empirical marginal of samples of the joint.
    N = 40000
    rng = random.Random(31)
    xs = [_sample(mu, Sigma, rng) for _ in range(N)]
    mean_hat = [sum(p[i] for p in xs) / N for i in idx]
    cov_hat = [[sum((p[idx[r]] - mean_hat[r]) * (p[idx[c]] - mean_hat[c]) for p in xs) / N
                for c in range(2)] for r in range(2)]
    assert max(abs(mean_hat[r] - m[r]) for r in range(2)) < 0.05, "marginal mean ≠ sample mean"
    assert _maxabs([[cov_hat[r][c] - S[r][c] for c in range(2)] for r in range(2)]) < 0.06, (
        "marginal covariance does not match the empirical marginal")


# ---------------------------------------------------------------------------
# Step 9: the conditional is a Schur complement, and it regresses (accept)
# ---------------------------------------------------------------------------

def check_conditional_regression() -> None:
    from gaussians import conditional

    mu = [0.5, -0.5, 1.0, 2.0]
    Sigma = [[1.0, 0.3, 0.5, 0.0],
             [0.3, 1.0, 0.2, 0.4],
             [0.5, 0.2, 1.0, 0.1],
             [0.0, 0.4, 0.1, 1.0]]
    ia, ib = [0, 1], [2, 3]
    x_b = [1.3, 1.7]

    S_aa = _submatrix(Sigma, ia, ia)
    S_ab = _submatrix(Sigma, ia, ib)
    S_bb = _submatrix(Sigma, ib, ib)
    Y = _matmul(_inverse(S_bb), _transpose(S_ab))          # Σ_bb⁻¹ Σ_ba
    ref_mu = [mu[ia[r]] + sum(Y[c][r] * (x_b[c] - mu[ib[c]]) for c in range(2))
              for r in range(2)]
    ref_S = [[S_aa[r][c] - sum(S_ab[r][t] * Y[t][c] for t in range(2))
              for c in range(2)] for r in range(2)]

    got_mu, got_S = conditional(mu, Sigma, ia, ib, x_b)
    assert max(abs(got_mu[r] - ref_mu[r]) for r in range(2)) < 1e-9, (
        f"conditional mean {got_mu} ≠ {ref_mu}: it is μ_a + Σ_ab Σ_bb⁻¹ (x_b − μ_b)")
    assert _maxabs([[got_S[r][c] - ref_S[r][c] for c in range(2)] for r in range(2)]) < 1e-9, (
        f"conditional covariance {got_S} ≠ Schur complement {ref_S}: conditioning must "
        "SUBTRACT Σ_ab Σ_bb⁻¹ Σ_ba from Σ_aa, removing the variance explained by x_b")
    assert got_S[0][0] < S_aa[0][0] + 1e-9 and got_S[1][1] < S_aa[1][1] + 1e-9, (
        "observing x_b cannot increase the variance of x_a")

    # Accept criterion: the analytic conditional equals a regression fitted on samples.
    N = 60000
    rng = random.Random(41)
    xs = [_sample(mu, Sigma, rng) for _ in range(N)]
    b_hat = [sum(p[i] for p in xs) / N for i in ib]
    a_hat = [sum(p[i] for p in xs) / N for i in ia]
    Caa = [[sum((p[ia[r]] - a_hat[r]) * (p[ia[c]] - a_hat[c]) for p in xs) / N
            for c in range(2)] for r in range(2)]
    C = [[sum((p[ia[r]] - a_hat[r]) * (p[ib[c]] - b_hat[c]) for p in xs) / N
          for c in range(2)] for r in range(2)]
    Cbb = [[sum((p[ib[r]] - b_hat[r]) * (p[ib[c]] - b_hat[c]) for p in xs) / N
            for c in range(2)] for r in range(2)]
    B = _matmul(C, _inverse(Cbb))
    reg_mean = [a_hat[r] + sum(B[r][c] * (x_b[c] - b_hat[c]) for c in range(2)) for r in range(2)]
    Cbb_inv = _inverse(Cbb)
    reg_cov = [[Caa[r][c] - sum(C[r][t] * Cbb_inv[t][u] * C[c][u]
                                for t in range(2) for u in range(2)) for c in range(2)]
               for r in range(2)]
    assert max(abs(got_mu[r] - reg_mean[r]) for r in range(2)) < 0.05, (
        f"conditional mean {got_mu} ≠ regression mean {reg_mean} on {N} samples")
    assert _maxabs([[got_S[r][c] - reg_cov[r][c] for c in range(2)] for r in range(2)]) < 0.06, (
        f"conditional covariance {got_S} ≠ regression residual covariance {reg_cov}")


# ---------------------------------------------------------------------------
# Step 10: change of variables keeps the Jacobian (accept)
# ---------------------------------------------------------------------------

def check_change_of_variables() -> None:
    from gaussians import change_of_variables_1d

    def phi(x):
        return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

    # (a) Affine: Y = 3X − 2, so (g⁻¹)′ = 1/3. Uniform grid, Simpson.
    p_aff = change_of_variables_1d(phi, lambda y: (y + 2.0) / 3.0, lambda y: 1.0 / 3.0)
    total_aff = _simpson(p_aff, -30.0, 30.0, 4000)
    assert abs(total_aff - 1.0) < 1e-8, (
        f"∫ p_Y dy = {total_aff:.6f} for Y = 3X−2, expected 1: the Jacobian factor "
        "|(g⁻¹)′| = 1/3 is missing, which stretches the density by 3")

    # (b) Log-normal: Y = exp(X), (g⁻¹)′(y) = 1/y. The peak at y = 1 is too sharp for a
    # uniform grid, so integrate with the substitution y = eᶻ (the inverse map itself).
    p_log = change_of_variables_1d(phi, math.log, lambda y: 1.0 / y)
    def integrand(z):
        return p_log(math.exp(z)) * math.exp(z)
    total_log = _simpson(integrand, -8.0, 8.0, 4000)
    assert abs(total_log - 1.0) < 1e-8, (
        f"∫ p_Y dy = {total_log:.6f} for the log-normal, expected 1: dropping 1/y leaves "
        "∫ p_X(x) eˣ dx = e^{1/2} ≈ 1.649, which is not a density")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("gaussians.py", "Cholesky factors a covariance, rejects a non-covariance", check_cholesky_spd),
    ("gaussians.py", "log density matches an exact reference", check_log_density_matches_formula),
    ("gaussians.py", "the density integrates to 1", check_density_integrates_to_one),
    ("gaussians.py", "nearly singular covariance (limit: Cholesky path)", check_log_density_nearly_singular),
    ("gaussians.py", "sampled mean and covariance match the parameters", check_sampling_moments),
    ("gaussians.py", "affine map of a Gaussian (A μ + b, A Σ Aᵀ)", check_linear_transform),
    ("gaussians.py", "product of Gaussians (precision form)", check_product_of_gaussians),
    ("gaussians.py", "marginal of a Gaussian", check_marginal),
    ("gaussians.py", "conditional = Schur complement = regression", check_conditional_regression),
    ("gaussians.py", "change of variables keeps the Jacobian", check_change_of_variables),
]


def run_one(check: Callable[[], None]) -> Tuple[str, str]:
    try:
        check()
        return PASS, ""
    except NotImplementedError as exc:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, (str(exc) or where)
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:  # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = f"\n      at {frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))
    print(f"\n{BOLD}Probability and Distributions From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<13} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<13} {title}")
            print(f"      {GREY}not implemented yet{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<13} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")
    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()
    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built the Gaussian machinery from scratch.{RESET}")
        print(f"  {GREY}Run solutions/gaussians.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
