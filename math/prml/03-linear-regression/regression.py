"""Basis-function regression, from least squares to Bayesian evidence, from scratch.

Implements chapter 3 of Bishop, *Pattern Recognition and Machine Learning* (linear
models for regression), and the matching material in Murphy, *Probabilistic Machine
Learning: An Introduction* (`bishop:3`, `mml:9`). The argument is restated here, never
copied:

* basis-function regression: a design matrix ``Phi`` whose rows are the basis
  functions evaluated at the inputs;
* maximum likelihood (least squares) and regularised least squares (ridge) weights;
* Bayesian linear regression: the Gaussian posterior over the weights and the
  predictive distribution at new inputs;
* the evidence approximation, which selects the weight precision ``alpha`` and the
  noise precision ``beta`` by maximising the marginal likelihood.

Everything is the standard library (``math``), in double precision.

DESIGN DECISION -- what does ``mle_weights`` do when the normal equations are
singular? With fewer data points than basis functions (or a rank-deficient ``Phi``)
the maximum-likelihood solution is not unique, so returning one of infinitely many
solutions would be a silent lie. **Chosen: return ``None``.** The alternative is to
raise; the cost of ``None`` is that callers must test for it, but the limit case is
then explicit at the call site rather than an exception that is easy to swallow.

DESIGN DECISION -- the basis is a list of callables rather than a fixed polynomial?
The chapter's point is that the linear-in-the-weights model is general: polynomial,
Gaussian radial, Fourier. Taking ``basis`` as a list of one-argument callables keeps
``design_matrix`` and every downstream routine agnostic to which one is used. The
cost is that the caller must build the closures; the benefit is that the same code
demonstrates the polynomial and the RBF case without branching.

DESIGN DECISION -- the evidence is computed by a direct log-determinant, not by a
Cholesky factorisation and not by an eigenvalue decomposition? ``S_N^{-1}`` is
symmetric positive definite, so any of the three works. A log-determinant from
Gaussian elimination with partial pivoting is the least code and reuses the same
elimination as ``solve_linear``. **Chosen: log-determinant by elimination.** The cost
is a small loss of accuracy on badly conditioned matrices, which is exactly what the
``alpha I`` term prevents.

DESIGN DECISION -- hyperparameters by grid search, not by the fixed-point/Newton
updates of the textbook? The update equations are elegant but they hide the shape of
the evidence surface, which is the lesson. A deterministic grid shows the maximum is
interior, and it makes the accept criterion (the chosen ``beta`` recovers the true
noise precision) something the checker can reproduce. **Chosen: exhaustive grid over
the supplied ``alphas`` and ``betas``.** The cost is linear cost in the grid size.

    python3 regression.py     # prints the measurements this file promises
"""

import math
import random

# A tiny pivot below this magnitude means the matrix is numerically singular.
_SINGULAR = 1e-12


# ---------------------------------------------------------------------------
# Small dense linear algebra (all matrices are lists of row lists)
# ---------------------------------------------------------------------------

def solve_linear(A, b):
    """Solve ``A x = b`` by Gaussian elimination with partial pivoting.

    Raises ``ValueError`` when a pivot is numerically zero, i.e. ``A`` is singular.
    """
    n = len(A)
    m = [list(A[i]) + [b[i]] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < _SINGULAR:
            raise ValueError("singular matrix")
        m[col], m[pivot] = m[pivot], m[col]
        for r in range(col + 1, n):
            factor = m[r][col] / m[col][col]
            if factor != 0.0:
                for k in range(col, n + 1):
                    m[r][k] -= factor * m[col][k]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        tail = sum(m[i][j] * x[j] for j in range(i + 1, n))
        x[i] = (m[i][n] - tail) / m[i][i]
    return x


def inverse(A):
    """Invert ``A`` by Gauss-Jordan elimination; raise ``ValueError`` if singular."""
    n = len(A)
    m = [list(A[i]) + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < _SINGULAR:
            raise ValueError("singular matrix")
        m[col], m[pivot] = m[pivot], m[col]
        scale = m[col][col]
        for k in range(2 * n):
            m[col][k] /= scale
        for r in range(n):
            if r != col and m[r][col] != 0.0:
                factor = m[r][col]
                for k in range(2 * n):
                    m[r][k] -= factor * m[col][k]
    return [row[n:] for row in m]


def log_det(A):
    """``ln |det A|`` by Gaussian elimination with partial pivoting.

    Returns ``-inf`` for a singular matrix. ``A`` is assumed symmetric when used
    here, so the sign of the determinant is positive and is dropped.
    """
    n = len(A)
    m = [list(row) for row in A]
    total = 0.0
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < _SINGULAR:
            return -math.inf
        if pivot != col:
            m[col], m[pivot] = m[pivot], m[col]
        value = m[col][col]
        total += math.log(abs(value))
        for r in range(col + 1, n):
            factor = m[r][col] / value
            if factor != 0.0:
                for k in range(col, n):
                    m[r][k] -= factor * m[col][k]
    return total


def _gram(Phi, alpha=0.0):
    """``Phi^T Phi + alpha I`` as a dense ``M x M`` matrix."""
    cols = len(Phi[0])
    A = [[0.0] * cols for _ in range(cols)]
    for row in Phi:
        for i in range(cols):
            value = row[i]
            if value != 0.0:
                for j in range(cols):
                    A[i][j] += value * row[j]
    for i in range(cols):
        A[i][i] += alpha
    return A


def _rhs(Phi, ts):
    """``Phi^T t`` as a length-``M`` list."""
    cols = len(Phi[0])
    b = [0.0] * cols
    for row, t in zip(Phi, ts):
        for i in range(cols):
            b[i] += row[i] * t
    return b


# ---------------------------------------------------------------------------
# Basis-function regression: MLE and ridge
# ---------------------------------------------------------------------------

def design_matrix(xs, basis):
    """The ``N x M`` design matrix ``Phi[i][j] = basis[j](xs[i])``.

    ``basis`` is a list of callables, one per basis function. A polynomial basis is
    ``[lambda x, k=k: x ** k for k in range(degree + 1)]``; a Gaussian RBF basis is
    ``[lambda x, c=c: math.exp(-((x - c) ** 2) / (2 * s * s)) for c in centres]``.
    """
    # TODO: One row per input x, one column per basis callable: Phi[i][j] = basis[j](xs[i]). Return a list of lists of floats.
    raise NotImplementedError("design_matrix")


def mle_weights(Phi, ts):
    """Maximum-likelihood (least-squares) weights: solve ``Phi^T Phi w = Phi^T t``.

    Returns the weight list, or ``None`` when the normal equations are singular
    (``Phi`` rank-deficient, e.g. fewer data points than basis functions). The
    maximum-likelihood answer is then not unique, so there is no honest single
    vector to return.
    """
    # TODO: Normal equations: solve (Phi^T Phi) w = Phi^T t. Return None when the system is singular (rank(Phi) < M, e.g. fewer points than basis functions): the MLE is then not unique, so do not invent a vector. Catch the ValueError from solve_linear.
    raise NotImplementedError("mle_weights")


def ridge_weights(Phi, ts, alpha):
    """Regularised least-squares weights: solve ``(alpha I + Phi^T Phi) w = Phi^T t``.

    ``alpha > 0`` is the L2 penalty. Every basis weight is penalised (there is no
    special intercept column), so ``alpha I`` makes the system non-singular even
    when ``Phi^T Phi`` is not.
    """
    # TODO: Solve (alpha I + Phi^T Phi) w = Phi^T t: add alpha to EVERY diagonal entry (there is no unpenalised intercept column). alpha > 0 makes it non-singular even when Phi^T Phi is not. Do not subtract alpha.
    raise NotImplementedError("ridge_weights")


# ---------------------------------------------------------------------------
# Bayesian linear regression
# ---------------------------------------------------------------------------

def bayesian_posterior(Phi, ts, alpha, beta):
    """The Gaussian posterior ``p(w | t) = N(w | m_N, S_N)`` as ``(mean, covariance)``.

    With the prior ``w ~ N(0, alpha^{-1} I)`` and the likelihood precision ``beta``,

        ``S_N^{-1} = alpha I + beta Phi^T Phi``,   ``m_N = beta S_N Phi^T t``.

    ``alpha > 0`` and ``beta > 0`` make ``S_N`` well defined even when ``Phi^T Phi``
    is singular, which is the point of the limit case.
    """
    # TODO: S_N^{-1} = alpha I + beta Phi^T Phi and m_N = beta S_N Phi^T t. Multiply EVERY entry of Phi^T Phi and of Phi^T t by beta (a common bug drops beta from the Phi^T Phi side). Return (mean, covariance) with covariance = inverse(S_N^{-1}).
    raise NotImplementedError("bayesian_posterior")


def predictive_distribution(Phi_grid, post_mean, post_cov, beta):
    """Predictive mean and variance at new inputs, as ``(means, variances)``.

    ``p(t* | x*, t) = N(t* | phi(x*)^T m_N, 1/beta + phi(x*)^T S_N phi(x*))``.
    The ``1/beta`` term is the observation noise, which every prediction carries; it
    is the floor of the variance, and away from the data the ``phi^T S_N phi`` term
    grows on top of it.
    """
    # TODO: For each row phi: mean = phi . m_N, variance = 1/beta + phi^T S_N phi. The 1/beta observation-noise term is the floor and must not be dropped.
    raise NotImplementedError("predictive_distribution")


# ---------------------------------------------------------------------------
# The evidence approximation
# ---------------------------------------------------------------------------

def log_evidence(Phi, ts, alpha, beta):
    """Log marginal likelihood ``ln p(t | alpha, beta)`` (the evidence).

    Restating Bishop (3.77): with ``E(m_N) = beta/2 ||t - Phi m_N||^2 +
    alpha/2 m_N^T m_N`` and ``S_N^{-1} = alpha I + beta Phi^T Phi``,

        ``ln p(t | alpha, beta) = M/2 ln alpha + N/2 ln beta - E(m_N)
        - N/2 ln(2 pi) + 1/2 ln |S_N|``.

    The ``1/2 ln |S_N|`` term is the Occam factor: it shrinks the evidence of small
    ``alpha`` (very flexible models) and is what stops the grid from running to the
    smallest penalty.
    """
    # TODO: ln p(t|alpha,beta) = M/2 ln alpha + N/2 ln beta - E(m_N) - N/2 ln(2 pi) + 1/2 ln|S_N|, with E(m_N) = beta/2 ||t - Phi m_N||^2 + alpha/2 m_N^T m_N and S_N^{-1} = alpha I + beta Phi^T Phi. Note ln|S_N| = -ln|S_N^{-1}|; omitting the Occam term lets the grid run to the smallest alpha.
    raise NotImplementedError("log_evidence")


def maximise_evidence(Phi, ts, alphas, betas):
    """Grid-search ``alphas x betas`` for the pair of largest ``log_evidence``.

    Returns ``(alpha, beta)``. Non-positive hyperparameters are skipped. Ties go to
    the first pair in grid order, so the result is deterministic.
    """
    # TODO: Grid-search alphas x betas and return the (alpha, beta) with the largest log_evidence. Skip non-positive values; ties go to the first pair so the result is deterministic. Return the pair, not just its value.
    raise NotImplementedError("maximise_evidence")


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo():
    """Print one measurement per construction this module promises."""
    print("Basis-function regression — measurements")

    quadratic = [lambda x, k=k: x ** k for k in range(3)]
    xs = [-1.0 + 2.0 * i / 19.0 for i in range(20)]
    ts = [1.0 - 2.0 * x + 0.5 * x * x for x in xs]
    Phi = design_matrix(xs, quadratic)

    w_mle = mle_weights(Phi, ts)
    print(f"  MLE on an exact quadratic: {[round(w, 6) for w in w_mle]}  (expected [1, -2, 0.5])")

    w_ridge = ridge_weights(Phi, ts, 1.0)
    print(f"  ridge alpha=1:            {[round(w, 6) for w in w_ridge]}"
          f"  ||w||: MLE {math.dist(w_mle, [0.0] * 3):.4f} -> ridge {math.dist(w_ridge, [0.0] * 3):.4f}")

    alpha, beta = 0.5, 25.0
    mean, covariance = bayesian_posterior(Phi, ts, alpha, beta)
    print(f"  posterior mean (alpha={alpha}, beta={beta}): {[round(w, 6) for w in mean]}")
    print(f"  posterior std: {[round(math.sqrt(covariance[i][i]), 6) for i in range(3)]}")

    grid = design_matrix([0.0, 0.5, 1.0, 1.5, 2.0, 3.0], quadratic)
    _, variances = predictive_distribution(grid, mean, covariance, beta)
    print(f"  predictive variance at x = [0, .5, 1, 1.5, 2, 3]:"
          f" {[round(v, 5) for v in variances]}  (noise floor {1.0 / beta:.5f})")

    basis5 = [lambda x, k=k: x ** k for k in range(6)]
    xs6 = [-1.0 + 2.0 * i / 29.0 for i in range(30)]
    rng = random.Random(5)
    ts6 = [1.0 - 2.0 * x + 0.5 * x * x + rng.gauss(0.0, 0.2) for x in xs6]
    Phi6 = design_matrix(xs6, basis5)
    selected = maximise_evidence(Phi6, ts6, [10.0 ** e for e in (-3, -2, -1, 0, 1, 2)],
                                 [10.0 ** e for e in (0, 0.5, 1, 1.5, 2, 2.5, 3)])
    print(f"  evidence over a degree-5 basis on noisy quadratic data:"
          f" alpha={selected[0]:g}, beta={selected[1]:g} (true beta = 25)")

    xs_few = [-1.0 + 2.0 * i / 4.0 for i in range(5)]
    ts_few = [1.0 - 2.0 * x + 0.5 * x * x for x in xs_few]
    Phi_few = design_matrix(xs_few, [lambda x, k=k: x ** k for k in range(8)])
    print(f"  limit case (5 points, 8 basis functions): MLE = {mle_weights(Phi_few, ts_few)}")
    mean_few, cov_few = bayesian_posterior(Phi_few, ts_few, 1.0, 25.0)
    print(f"  the same under a Bayesian posterior: finite mean {[round(w, 3) for w in mean_few]}"
          f", trace(S_N) = {sum(cov_few[i][i] for i in range(8)):.4f}")


if __name__ == "__main__":
    demo()
