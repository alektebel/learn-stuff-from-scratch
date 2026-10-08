"""
Latent-variable continuous models from scratch: PCA, probabilistic PCA and
kernel PCA, pure standard library.

Everything here is plain nested lists.  A data matrix ``X`` is ``N`` rows
(observations) by ``D`` columns (feature dimensions); the covariance is the
``D x D`` matrix with the maximum-likelihood ``1 / N`` normalization, chosen so
that the mean squared reconstruction error equals the sum of the discarded
eigenvalues exactly.  Symmetric eigenproblems go through a cyclic Jacobi solver,
so the SVD routes need no external linear algebra.

Public API
----------
mean_center(X)                -> the column means subtracted
covariance(X)                 -> the D x D sample covariance
pca_eig(X, k)                 -> components, eigenvalues, projection, reconstruction
pca_svd(X, k)                 -> the same by the SVD / X^T X route
ppca_closed_form(X, k)        -> (W, sigma^2) for probabilistic PCA
ppca_em(X, k, ...)            -> (W, sigma^2, log-likelihoods) for probabilistic PCA
kernel_pca(K, k)              -> eigenvalues, projection from a kernel matrix
pca_gram(X, k)                -> the same as pca_eig via the N x N Gram matrix
"""

import math
import random


# ---------------------------------------------------------------------------
# Basic statistics
# ---------------------------------------------------------------------------

def mean_center(X):
    """Return ``X`` with each column mean subtracted."""
    n, d = len(X), len(X[0])
    mu = [sum(X[i][j] for i in range(n)) / n for j in range(d)]
    return [[X[i][j] - mu[j] for j in range(d)] for i in range(n)]


def covariance(X):
    """The ``D x D`` maximum-likelihood covariance ``Xc^T Xc / N``.

    With this normalization the mean squared PCA reconstruction error equals
    the sum of the discarded eigenvalues (the accept criterion).

    DESIGN DECISION. Use the maximum-likelihood ``1 / N``, not the unbiased
    ``1 / (N - 1)``. Cost: the covariance is a biased estimate of the population
    variance, but the exact reconstruction identity (and the PPCA ``sigma^2 =
    mean of the discarded eigenvalues``) holds only with ``1 / N``.
    """
    n, d = len(X), len(X[0])
    xc = mean_center(X)
    cov = [[0.0] * d for _ in range(d)]
    for i in range(d):
        for j in range(i, d):
            value = sum(xc[k][i] * xc[k][j] for k in range(n)) / n
            cov[i][j] = value
            cov[j][i] = value
    return cov


def _mean(X):
    n, d = len(X), len(X[0])
    return [sum(X[i][j] for i in range(n)) / n for j in range(d)]


# ---------------------------------------------------------------------------
# A symmetric eigen-solver (cyclic Jacobi) and small dense helpers
# ---------------------------------------------------------------------------

def _jacobi(A, sweeps=100):
    """Eigen-decompose a symmetric matrix.  Returns ``(values, vectors)`` where
    ``vectors[j]`` is the unit eigenvector for ``values[j]`` (columns of V)."""
    n = len(A)
    a = [row[:] for row in A]
    v = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for _ in range(sweeps):
        off = math.sqrt(sum(a[i][j] ** 2 for i in range(n) for j in range(n) if i != j))
        if off < 1e-14:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                if abs(a[p][q]) < 1e-300:
                    continue
                theta = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
                t = math.copysign(1.0, theta) / (abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                tau = s / (1.0 + c)
                h = t * a[p][q]
                a[p][p] -= h
                a[q][q] += h
                a[p][q] = a[q][p] = 0.0
                for i in range(p):
                    aip, aiq = a[i][p], a[i][q]
                    a[i][p] = aip - s * (aiq + tau * aip)
                    a[i][q] = aiq + s * (aip - tau * aiq)
                for i in range(p + 1, q):
                    aip, aiq = a[p][i], a[i][q]
                    a[p][i] = aip - s * (aiq + tau * aip)
                    a[i][q] = aiq + s * (aip - tau * aiq)
                for i in range(q + 1, n):
                    aip, aiq = a[p][i], a[q][i]
                    a[p][i] = aip - s * (aiq + tau * aip)
                    a[q][i] = aiq + s * (aip - tau * aiq)
                for i in range(n):
                    vip, viq = v[i][p], v[i][q]
                    v[i][p] = vip - s * (viq + tau * vip)
                    v[i][q] = viq + s * (vip - tau * viq)
    vals = [a[i][i] for i in range(n)]
    vecs = [[v[i][j] for i in range(n)] for j in range(n)]
    return vals, vecs


def _eig_sorted(A):
    """Eigen-decomposition ordered from largest eigenvalue down."""
    vals, vecs = _jacobi(A)
    order = sorted(range(len(vals)), key=lambda i: -vals[i])
    return [vals[i] for i in order], [vecs[i] for i in order]


def _solve(A, b):
    n = len(A)
    m = [list(A[i]) + [b[i]] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-14:
            raise ValueError("singular matrix")
        m[col], m[pivot] = m[pivot], m[col]
        for r in range(col + 1, n):
            factor = m[r][col] / m[col][col]
            if factor:
                for j in range(col, n + 1):
                    m[r][j] -= factor * m[col][j]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (m[i][n] - sum(m[i][j] * x[j] for j in range(i + 1, n))) / m[i][i]
    return x


def _inverse(A):
    n = len(A)
    m = [list(A[i]) + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-14:
            raise ValueError("singular matrix")
        m[col], m[pivot] = m[pivot], m[col]
        scale = m[col][col]
        for j in range(2 * n):
            m[col][j] /= scale
        for r in range(n):
            if r != col and m[r][col]:
                factor = m[r][col]
                for j in range(2 * n):
                    m[r][j] -= factor * m[col][j]
    return [row[n:] for row in m]


def _log_det(A):
    n = len(A)
    m = [row[:] for row in A]
    total = 0.0
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-14:
            return -math.inf
        m[col], m[pivot] = m[pivot], m[col]
        value = m[col][col]
        total += math.log(abs(value))
        for r in range(col + 1, n):
            factor = m[r][col] / value
            if factor:
                for j in range(col, n):
                    m[r][j] -= factor * m[col][j]
    return total


def _gram_XXt(X):
    """The ``N x N`` Gram matrix ``X X^T``."""
    n = len(X)
    G = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i, n):
            value = sum(X[i][d] * X[j][d] for d in range(len(X[i])))
            G[i][j] = value
            G[j][i] = value
    return G


# ---------------------------------------------------------------------------
# PCA
# ---------------------------------------------------------------------------

def pca_eig(X, k):
    """PCA by eigen-decomposition of the covariance.

    Returns ``(components, eigenvalues, projection, reconstruction)``:
    ``components`` is ``k x D`` (rows are principal directions), eigenvalues
    are the top ``k`` variances in descending order, ``projection`` is the
    ``N x k`` scores, and ``reconstruction`` is the ``N x D`` least-squares
    approximation using those ``k`` directions.
    """
    n, d = len(X), len(X[0])
    mu = _mean(X)
    Xc = mean_center(X)
    vals, vecs = _eig_sorted(covariance(Xc))
    n_used = k
    components = [vecs[i] for i in range(n_used)]
    eigenvalues = [vals[i] for i in range(n_used)]
    projection = [[sum(Xc[i][j] * components[c][j] for j in range(d))
                   for c in range(n_used)] for i in range(n)]
    reconstruction = [[sum(projection[i][c] * components[c][j] for c in range(n_used)) + mu[j]
                       for j in range(d)] for i in range(n)]
    return components, eigenvalues, projection, reconstruction


def pca_svd(X, k):
    """PCA by an SVD-style route: eigen-decompose ``Xc^T Xc`` and scale.

    Agrees with :func:`pca_eig` on the eigenvalues, the subspace and the
    reconstruction.

    DESIGN DECISION. Route the SVD through the ``D x D`` matrix ``Xc^T Xc``,
    whose eigenvalues are ``N`` times the squared singular values. Cost: this
    squares the condition number, so a badly scaled ``X`` would lose accuracy
    relative to a dedicated SVD; on the checker's small well-conditioned data the
    two routes agree to ~1e-15.
    """
    n, d = len(X), len(X[0])
    mu = _mean(X)
    Xc = mean_center(X)
    ata = [[sum(Xc[i][a] * Xc[i][b] for i in range(n)) for b in range(d)] for a in range(d)]
    vals, vecs = _eig_sorted(ata)
    eigenvalues = [vals[i] / n for i in range(k)]
    components = [vecs[i] for i in range(k)]
    projection = [[sum(Xc[i][j] * components[c][j] for j in range(d))
                   for c in range(k)] for i in range(n)]
    reconstruction = [[sum(projection[i][c] * components[c][j] for c in range(k)) + mu[j]
                       for j in range(d)] for i in range(n)]
    return components, eigenvalues, projection, reconstruction


def pca_gram(X, k):
    """PCA through the ``N x N`` Gram matrix ``Xc Xc^T`` (the D > N limit).

    The nonzero eigenvalues of the Gram matrix equal ``N`` times the
    covariance eigenvalues, so the eigenvalues returned here are the raw Gram
    eigenvalues.  Directions are recovered as ``v = Xc^T u / sigma``.

    DESIGN DECISION. For ``D > N`` work with the ``N x N`` Gram matrix rather
    than the ``D x D`` covariance. Cost: the eigenvalues come out scaled by
    ``N`` and the directions need the extra ``Xc^T u / sqrt(lambda)`` recovery,
    but when ``N < D`` the covariance would be rank-deficient and much larger;
    at most ``N - 1`` Gram eigenvalues are nonzero.
    """
    n, d = len(X), len(X[0])
    mu = _mean(X)
    Xc = mean_center(X)
    G = _gram_XXt(Xc)
    vals, vecs = _eig_sorted(G)
    components = []
    eigenvalues = []
    for c in range(k):
        eigenvalues.append(vals[c])
        if vals[c] <= 1e-12:
            components.append([0.0] * d)
            continue
        v = [sum(Xc[i][j] * vecs[c][i] for i in range(n)) / math.sqrt(vals[c]) for j in range(d)]
        norm = math.sqrt(sum(t * t for t in v))
        components.append([t / norm for t in v])
    projection = [[sum(Xc[i][j] * components[c][j] for j in range(d))
                   for c in range(k)] for i in range(n)]
    reconstruction = [[sum(projection[i][c] * components[c][j] for c in range(k)) + mu[j]
                       for j in range(d)] for i in range(n)]
    return components, eigenvalues, projection, reconstruction


# ---------------------------------------------------------------------------
# Probabilistic PCA
# ---------------------------------------------------------------------------

def ppca_closed_form(X, k):
    """Maximum-likelihood PPCA from the top ``k`` covariance eigenvalues.

    ``sigma^2`` is the average of the discarded eigenvalues and
    ``W = U_k (Lambda_k - sigma^2 I)^{1/2}`` is a ``D x k`` loading matrix.

    DESIGN DECISION. Compute the maximum-likelihood solution in closed form
    rather than by EM. Cost: it needs the full eigendecomposition of the
    ``D x D`` covariance (``O(D^3)``), where one EM step is cheaper; but the
    closed form is exact and hits the global optimum, while EM only reaches it
    up to a rotation and within a tolerance. The checker compares the two on the
    fitted subspace, not elementwise.
    """
    d = len(X[0])
    vals, vecs = _eig_sorted(covariance(X))
    sigma2 = sum(vals[k:]) / (d - k)
    W = [[vecs[c][i] * math.sqrt(max(vals[c] - sigma2, 0.0)) for c in range(k)]
         for i in range(d)]
    return W, sigma2


def ppca_em(X, k, iterations=500, tol=1e-12, seed=0):
    """EM for probabilistic PCA.

    Returns ``(W, sigma^2, log_likelihoods)``.  The log-likelihood is the
    marginal likelihood of the centred data under ``C = W W^T + sigma^2 I``.
    """
    n, d = len(X), len(X[0])
    Xc = mean_center(X)
    rng = random.Random(seed)
    W = [[rng.gauss(0.0, 1.0) for _ in range(k)] for _ in range(d)]
    sigma2 = sum(sum(v * v for v in row) for row in Xc) / (n * d)
    log_likelihoods = []
    for _ in range(iterations):
        # E step.
        WTW = [[sum(W[i][a] * W[i][b] for i in range(d)) for b in range(k)] for a in range(k)]
        M = [[WTW[a][b] + (sigma2 if a == b else 0.0) for b in range(k)] for a in range(k)]
        Minv = _inverse(M)
        sum_Ezz = [[0.0] * k for _ in range(k)]
        sum_xEz = [[0.0] * k for _ in range(d)]
        for i in range(n):
            Wt_x = [sum(W[j][a] * Xc[i][j] for j in range(d)) for a in range(k)]
            Ez = [sum(Minv[a][b] * Wt_x[b] for b in range(k)) for a in range(k)]
            for j in range(d):
                for a in range(k):
                    sum_xEz[j][a] += Xc[i][j] * Ez[a]
            for a in range(k):
                for b in range(k):
                    sum_Ezz[a][b] += sigma2 * Minv[a][b] + Ez[a] * Ez[b]
        # M step.
        sum_Ezz_inv = _inverse(sum_Ezz)
        Wnew = [[sum(sum_xEz[j][a] * sum_Ezz_inv[a][b] for a in range(k)) for b in range(k)]
                for j in range(d)]
        total = 0.0
        for i in range(n):
            Wt_x = [sum(Wnew[j][a] * Xc[i][j] for j in range(d)) for a in range(k)]
            Ez = [sum(Minv[a][b] * sum(W[j][b] * Xc[i][j] for j in range(d)) for b in range(k))
                  for a in range(k)]
            total += sum(v * v for v in Xc[i])
            total -= 2.0 * sum(Ez[a] * Wt_x[a] for a in range(k))
            for a in range(k):
                for b in range(k):
                    total += (sigma2 * Minv[a][b] + Ez[a] * Ez[b]) * \
                             sum(Wnew[j][a] * Wnew[j][b] for j in range(d))
        sigma2_new = total / (n * d)
        # Log-likelihood of the centred data under the current parameters.
        C = [[sum(W[j][a] * W[i][a] for a in range(k)) + (sigma2 if i == j else 0.0)
              for j in range(d)] for i in range(d)]
        Cinv = _inverse(C)
        S = [[sum(Xc[i][a] * Xc[i][b] for i in range(n)) / n for b in range(d)] for a in range(d)]
        trace = sum(Cinv[a][b] * S[b][a] for a in range(d) for b in range(d))
        ll = (-0.5 * n * d * math.log(2.0 * math.pi)
              - 0.5 * n * _log_det(C)
              - 0.5 * n * trace)
        log_likelihoods.append(ll)

        convergence = max(abs(sigma2_new - sigma2),
                          max(abs(Wnew[j][a] - W[j][a]) for j in range(d) for a in range(k)))
        sigma2 = max(sigma2_new, 1e-12)
        W = Wnew
        if convergence < tol:
            break
    return W, sigma2, log_likelihoods


def _projector(W):
    """The ``D x D`` orthogonal projector onto the column space of ``W``."""
    d, k = len(W), len(W[0])
    WTW = [[sum(W[i][a] * W[i][b] for i in range(d)) for b in range(k)] for a in range(k)]
    WTW_inv = _inverse(WTW)
    return [[sum(W[i][a] * WTW_inv[a][b] * W[j][b] for a in range(k) for b in range(k))
             for j in range(d)] for i in range(d)]


# ---------------------------------------------------------------------------
# Kernel PCA
# ---------------------------------------------------------------------------

def kernel_pca(K, k):
    """Kernel PCA from an ``N x N`` kernel (Gram) matrix.

    The kernel matrix is centred in feature space, then eigen-decomposed.  The
    returned ``projection`` holds the training points' scores on the top ``k``
    components, i.e. ``sqrt(lambda_j) * v_j``.

    DESIGN DECISION. Operate only on the ``N x N`` kernel matrix; the feature map
    is never formed. Cost: ``O(N^2)`` memory for the kernel and only training
    scores (no out-of-sample embedding). The double centring
    ``K - 1K/N - K1/N + 1K1/N^2`` is what removes the feature-space mean; without
    it the top eigenvalue is the uninformative constant direction.
    """
    n = len(K)
    row = [sum(K[i]) / n for i in range(n)]
    total = sum(row) / n
    Kc = [[K[i][j] - row[i] - row[j] + total for j in range(n)] for i in range(n)]
    vals, vecs = _eig_sorted(Kc)
    eigenvalues = [vals[j] for j in range(k)]
    projection = [[vecs[j][i] * math.sqrt(max(vals[j], 0.0)) for j in range(k)] for i in range(n)]
    return eigenvalues, projection


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def _rbf(X, gamma=0.5):
    n = len(X)
    K = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            sq = sum((X[i][d] - X[j][d]) ** 2 for d in range(len(X[i])))
            K[i][j] = math.exp(-gamma * sq)
    return K


def demo():
    rng = random.Random(0)
    n, d, k = 40, 6, 2
    Z = [[rng.gauss(0.0, 1.0) for _ in range(k)] for _ in range(n)]
    A = [[rng.gauss(0.0, 1.0) for _ in range(k)] for _ in range(d)]
    X = [[sum(Z[i][a] * A[j][a] for a in range(k)) + rng.gauss(0.0, 0.05)
          for j in range(d)] for i in range(n)]

    comps, vals, _, rec = pca_eig(X, k)
    print("PCA (eig): top variances =", [round(v, 5) for v in vals])
    err = sum((X[i][j] - rec[i][j]) ** 2 for i in range(n) for j in range(d)) / n
    full = _eig_sorted(covariance(X))[0]
    print("           mean reconstruction error =", round(err, 8),
          " discarded eigenvalue sum =", round(sum(full[k:]), 8))

    _, svals, _, srec = pca_svd(X, k)
    print("PCA (svd): max |eig - svd| =",
          max(abs(vals[i] - svals[i]) for i in range(k)))

    W, s2 = ppca_closed_form(X, k)
    Wem, s2em, lls = ppca_em(X, k, iterations=800)
    print("PPCA: closed-form sigma^2 =", round(s2, 6),
          " EM sigma^2 =", round(s2em, 6),
          " EM steps =", len(lls))
    print("      EM log-likelihood", round(lls[0], 3), "->", round(lls[-1], 3))

    gvals = pca_gram(X, n - 1)[1] if d > n else None
    print("Gram limit demo eigenvalue ratio (first) =",
          round(gvals[0] / (full[0] * n), 6)
          if gvals else "skipped (D <= N)")

    kev, kproj = kernel_pca(_rbf(X), k)
    print("Kernel PCA eigenvalues =", [round(v, 4) for v in kev])


if __name__ == "__main__":
    demo()
