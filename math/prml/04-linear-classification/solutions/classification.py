"""Linear models for classification, from least squares to the Bayesian Laplace fit.

Implements chapter 4 of Bishop, *Pattern Recognition and Machine Learning* (linear
models for classification). The argument is restated here, never copied:

* the least-squares classifier: encode the two classes as 0/1 targets and fit a linear
  discriminant by ordinary least squares. It is the simplest thing that works and the
  first thing an outlier ruins;
* Fisher's linear discriminant: choose the direction that maximises the between-class
  mean separation relative to the within-class scatter, ``w ∝ S_W^{-1} (m_1 - m_0)``;
* the perceptron: the online mistake-driven update ``w <- w + t_n phi_n`` for every
  point on the wrong side, which converges in finite steps when the data are linearly
  separable;
* logistic regression by maximum likelihood, fitted with iteratively reweighted least
  squares (IRLS), which is Newton-Raphson on the log-likelihood. Each Newton step solves
  ``(Phi^T R Phi) w = Phi^T R z`` with ``R = diag(p(1-p))``;
* the Laplace approximation for Bayesian logistic regression: a Gaussian centred on the
  MAP weights with covariance the inverse Hessian of the negative log posterior.

Everything is the standard library (``math``), in double precision.

DESIGN DECISION -- 0/1 targets or +1/-1 targets? Bishop uses ``t ∈ {0, 1}`` throughout
chapter 4; the logistic likelihood ``prod p^t (1-p)^{1-t}`` and the least-squares target
coding are both simplest in that convention. **Chosen: 0/1 in the public API.** The
perceptron is the one exception: its update needs the sign, so it maps 0/1 to +1/-1
internally rather than asking the caller for a different coding.

DESIGN DECISION -- does every linear model carry an explicit bias column? A decision
boundary that may not pass through the origin needs one. **Chosen: yes, every routine
prepends a column of ones to the inputs.** The cost is that the returned weight vector
is one longer than the feature dimension and its first entry is the bias; the benefit is
that the boundary is not forced through the origin.

DESIGN DECISION -- how is the within-class scatter ``S_W`` inverted in Fisher's rule?
``S_W`` is symmetric positive semi-definite and can be singular when a class lies on a
subspace. **Chosen: solve ``S_W w = (m_1 - m_0)`` directly by Gaussian elimination with
partial pivoting**, the same ``_solve`` used everywhere else. The alternative,
eigen-decomposition or a pseudo-inverse, is more code; the cost is that exactly singular
scatter raises ``ValueError`` rather than returning a minimum-norm direction, which
matches the other modules here.

DESIGN DECISION -- an L2 prior on the weights, added as ``ridge``? With separable data
the maximum-likelihood weight vector is unbounded: the likelihood keeps rising as the
weights grow along the separating direction. A zero-mean Gaussian prior of precision
``ridge`` turns the fit into penalised logistic regression and keeps the solution finite
and unique. **Chosen: expose ``ridge = 1 / prior_var`` as the last argument of
``logistic_irls``**, so the limit case (no prior, divergence) and the fix (a prior) are
one number apart.

DESIGN DECISION -- convergence criterion, the gradient norm or the step norm? The
iteration comparison against gradient descent must count the same quantity in both
algorithms, or it is not a comparison. **Chosen: stop when the norm of the gradient of
the negative log posterior falls below ``tol``.** IRLS reports the number of Newton
steps, gradient descent the number of gradient steps; on the same problem and tolerance
the contrast is the point of the exercise.

    python3 classification.py     # prints the measurements this file promises
"""

import math

# A pivot below this magnitude means the matrix is numerically singular.
_SINGULAR = 1e-12


# ---------------------------------------------------------------------------
# Small dense linear algebra (all matrices are lists of row lists)
# ---------------------------------------------------------------------------

def _design(Xs):
    """Prepend a bias column of ones: row ``i`` is ``[1.0, x_i...]``."""
    return [[1.0] + [float(v) for v in row] for row in Xs]


def _dot(a, b):
    return sum(ai * bi for ai, bi in zip(a, b))


def _solve(A, b):
    """Solve ``A x = b`` by Gaussian elimination with partial pivoting."""
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
        x[i] = (m[i][n] - sum(m[i][j] * x[j] for j in range(i + 1, n))) / m[i][i]
    return x


def _inverse(A):
    """Invert ``A`` by Gauss-Jordan elimination with partial pivoting."""
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


def _gram(B, weights=None):
    """``Phi^T R Phi`` for ``R = diag(weights)`` (all ones when omitted)."""
    d = len(B[0])
    A = [[0.0] * d for _ in range(d)]
    for r, row in enumerate(B):
        w = 1.0 if weights is None else weights[r]
        for i in range(d):
            wi = w * row[i]
            for j in range(d):
                A[i][j] += wi * row[j]
    return A


# ---------------------------------------------------------------------------
# The likelihood link and the first-order gradient
# ---------------------------------------------------------------------------

def sigmoid(z):
    """The logistic sigmoid ``1 / (1 + exp(-z))``, stable in both tails."""
    if z >= 0.0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def _gradient(B, ts, w, ridge):
    """Gradient of the negative log posterior: ``-Phi^T (t - p) + ridge * w``."""
    d = len(w)
    g = [0.0] * d
    for row, t in zip(B, ts):
        error = t - sigmoid(_dot(w, row))
        for i in range(d):
            g[i] -= error * row[i]
    if ridge:
        for i in range(d):
            g[i] += ridge * w[i]
    return g


# ---------------------------------------------------------------------------
# 4.1.1 / 4.1.2 -- least squares and Fisher's linear discriminant
# ---------------------------------------------------------------------------

def least_squares_classifier(Xs, ts):
    """Fit a linear discriminant by least squares on 0/1 targets.

    Solve ``(Phi^T Phi) w = Phi^T t``. Returns the weight vector
    ``[bias, w_1, ...]``; classify by ``sigmoid_or_sign(w . [1, x])``.
    """
    B = _design(Xs)
    A = _gram(B)
    rhs = [0.0] * len(B[0])
    for row, t in zip(B, ts):
        for i in range(len(rhs)):
            rhs[i] += row[i] * t
    return _solve(A, rhs)


def fisher_lda(Xs, ts):
    """Fisher's linear discriminant: direction and threshold.

    Returns ``(direction, threshold)``. The direction is the closed-form
    ``S_W^{-1} (m_1 - m_0)``, where ``S_W`` is the within-class scatter and
    ``m_c`` the class means. The threshold is the midpoint of the two projected
    class means, so the decision rule is ``direction . x > threshold`` for class 1.
    """
    d = len(Xs[0])
    n1 = sum(1 for t in ts if t >= 0.5)
    n0 = len(ts) - n1
    if n0 == 0 or n1 == 0:
        raise ValueError("Fisher's discriminant needs both classes represented")

    m1 = [0.0] * d
    m0 = [0.0] * d
    for x, t in zip(Xs, ts):
        target = m1 if t >= 0.5 else m0
        for j in range(d):
            target[j] += x[j]
    for j in range(d):
        m1[j] /= n1
        m0[j] /= n0

    scatter = [[0.0] * d for _ in range(d)]
    for x, t in zip(Xs, ts):
        mean = m1 if t >= 0.5 else m0
        diff = [x[j] - mean[j] for j in range(d)]
        for i in range(d):
            for j in range(d):
                scatter[i][j] += diff[i] * diff[j]

    direction = _solve(scatter, [m1[j] - m0[j] for j in range(d)])
    threshold = 0.5 * (_dot(direction, m1) + _dot(direction, m0))
    return direction, threshold


# ---------------------------------------------------------------------------
# 4.1.3 -- the perceptron
# ---------------------------------------------------------------------------

def perceptron(Xs, ts, maxit=100):
    """The perceptron algorithm for 0/1 targets.

    Maps the targets to ``+1/-1``, then sweeps the training set: whenever a point is
    on the wrong side (``y_n w . phi_n <= 0``) update ``w <- w + y_n phi_n``. Returns
    ``(w, iterations)`` where ``iterations`` counts the passes actually used. On
    linearly separable data it stops early (a pass with no mistakes); otherwise it
    returns after ``maxit`` passes.
    """
    B = _design(Xs)
    y = [1.0 if t >= 0.5 else -1.0 for t in ts]
    w = [0.0] * len(B[0])
    iters = 0
    for _ in range(maxit):
        iters += 1
        mistakes = 0
        for row, label in zip(B, y):
            if label * _dot(w, row) <= 0.0:
                for j in range(len(w)):
                    w[j] += label * row[j]
                mistakes += 1
        if mistakes == 0:
            break
    return w, iters


# ---------------------------------------------------------------------------
# 4.3 -- logistic regression by IRLS (Newton-Raphson)
# ---------------------------------------------------------------------------

def logistic_irls(Xs, ts, maxit=100, tol=1e-8, ridge=0.0):
    """Logistic regression by iteratively reweighted least squares.

    Newton-Raphson on the negative log posterior ``-sum[t ln p + (1-t) ln(1-p)]
    + ridge/2 ||w||^2``. Each step solves ``(Phi^T R Phi + ridge I) w_new =
    Phi^T R z``, equivalently ``w <- w + H^{-1} (Phi^T (t - p) - ridge w)`` with
    ``H = Phi^T R Phi + ridge I`` and ``R = diag(p(1-p))``. Returns ``(w, iterations)``
    with the iteration count at the gradient-norm tolerance ``tol``.
    """
    B = _design(Xs)
    d = len(B[0])
    w = [0.0] * d
    iters = 0
    for _ in range(maxit):
        p = [sigmoid(_dot(w, row)) for row in B]
        grad = _gradient(B, ts, w, ridge)
        if math.sqrt(sum(v * v for v in grad)) < tol:
            break
        weights = [pi * (1.0 - pi) for pi in p]
        hessian = _gram(B, weights)
        for i in range(d):
            hessian[i][i] += ridge
        rhs = [0.0] * d
        for row, t, pi in zip(B, ts, p):
            error = t - pi
            for i in range(d):
                rhs[i] += error * row[i]
        if ridge:
            for i in range(d):
                rhs[i] -= ridge * w[i]
        step = _solve(hessian, rhs)
        w = [w[i] + step[i] for i in range(d)]
        iters += 1
    return w, iters


def logistic_gradient_descent(Xs, ts, lr, maxit, tol, ridge=0.0):
    """Plain gradient descent on the same negative log posterior.

    The baseline for the iteration comparison: ``w <- w - lr * grad``. No line search,
    no curvature; returns ``(w, iterations)`` at the same gradient tolerance.
    """
    B = _design(Xs)
    d = len(B[0])
    w = [0.0] * d
    iters = 0
    for _ in range(maxit):
        grad = _gradient(B, ts, w, ridge)
        if math.sqrt(sum(v * v for v in grad)) < tol:
            break
        for i in range(d):
            w[i] -= lr * grad[i]
        iters += 1
    return w, iters


# ---------------------------------------------------------------------------
# 4.4 / 4.5 -- the Laplace approximation for Bayesian logistic regression
# ---------------------------------------------------------------------------

def laplace_logistic(Xs, ts, prior_var):
    """Laplace approximation to the posterior over logistic weights.

    The prior is ``w ~ N(0, prior_var I)``, i.e. precision ``ridge = 1 / prior_var``.
    The mean is the MAP estimate found by IRLS; the covariance is the inverse Hessian
    of the negative log posterior at that point: ``S_N = (Phi^T R Phi + ridge I)^{-1}``
    with ``R = diag(p(1-p))`` at the MAP. Returns ``(mean, covariance)``.
    """
    ridge = 1.0 / prior_var
    mean, _ = logistic_irls(Xs, ts, maxit=200, tol=1e-13, ridge=ridge)
    B = _design(Xs)
    d = len(B[0])
    p = [sigmoid(_dot(mean, row)) for row in B]
    hessian = _gram(B, [pi * (1.0 - pi) for pi in p])
    for i in range(d):
        hessian[i][i] += ridge
    return mean, _inverse(hessian)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def _separable_data():
    """Two well-separated 2-D clusters: class 0 around (-1,-1), class 1 around (1,1)."""
    xs = [[-1.2, -1.0], [-0.9, -1.3], [-1.4, -0.7], [-0.8, -0.9], [-1.1, -1.4],
          [1.1, 1.0], [0.9, 1.3], [1.4, 0.7], [0.8, 0.9], [1.1, 1.4]]
    ts = [0, 0, 0, 0, 0, 1, 1, 1, 1, 1]
    return xs, ts


def _overlapping_data():
    """A small 2-D set that is not linearly separable, so logistic has a finite MLE."""
    xs = [[-1.0, 0.0], [-0.3, 0.2], [0.4, -0.1], [0.8, 0.3],
          [-0.6, 0.1], [0.0, 0.3], [0.5, 0.4], [1.0, 0.0]]
    ts = [0, 0, 0, 0, 1, 1, 1, 1]
    return xs, ts


def demo():
    print("Linear classification — measurements")

    xs, ts = _separable_data()
    w_ls = least_squares_classifier(xs, ts)
    direction, threshold = fisher_lda(xs, ts)
    w_perc, iters = perceptron(xs, ts, maxit=100)
    print(f"  least squares weights : [{', '.join(f'{v:+.4f}' for v in w_ls)}]")
    print(f"  Fisher direction      : [{', '.join(f'{v:+.4f}' for v in direction)}]"
          f"  threshold {threshold:+.4f}")
    print(f"  perceptron            : [{', '.join(f'{v:+.4f}' for v in w_perc)}]"
          f"  ({iters} passes)")

    xs2, ts2 = _overlapping_data()
    w_irls, irls_iters = logistic_irls(xs2, ts2, maxit=100, tol=1e-10)
    w_gd, gd_iters = logistic_gradient_descent(xs2, ts2, lr=1.0, maxit=200000, tol=1e-10)
    print(f"  logistic IRLS         : [{', '.join(f'{v:+.4f}' for v in w_irls)}]"
          f"  ({irls_iters} Newton steps)")
    print(f"  logistic gradient desc: [{', '.join(f'{v:+.4f}' for v in w_gd)}]"
          f"  ({gd_iters} steps at the same tol)")

    mean, cov = laplace_logistic(xs2, ts2, prior_var=4.0)
    print(f"  Laplace MAP mean      : [{', '.join(f'{v:+.4f}' for v in mean)}]")
    print(f"  Laplace posterior std : [{', '.join(f'{math.sqrt(cov[i][i]):.4f}' for i in range(len(mean)))}]")

    # Limit case (a): separable data, no prior -> the weights keep growing.
    div_xs = [[-1.0], [-0.7], [-0.4], [0.4], [0.7], [1.0]]
    div_ts = [0, 0, 0, 1, 1, 1]
    norms = []
    for cap in (4, 8, 12):
        w, _ = logistic_irls(div_xs, div_ts, maxit=cap, tol=0.0)
        norms.append(math.sqrt(sum(v * v for v in w)))
    w_reg, _ = logistic_irls(div_xs, div_ts, maxit=12, tol=0.0, ridge=1.0)
    reg_norm = math.sqrt(sum(v * v for v in w_reg))
    print("  separable, no prior ||w|| at 4/8/12 Newton steps: "
          + ", ".join(f"{v:.3f}" for v in norms))
    print(f"  separable, L2 prior  ||w|| = {reg_norm:.3f}  (finite)")

    # Limit case (b): one outlier, least squares versus logistic.
    xs_clean = [[-1.0], [-0.8], [-0.4], [0.1], [-0.2], [0.6], [0.8], [1.0]]
    ts_clean = [0, 0, 0, 0, 1, 1, 1, 1]
    xs_out = xs_clean + [[8.0]]
    ts_out = ts_clean + [0]

    def boundary(weights):
        return -weights[0] / weights[1]

    ls_clean = boundary(least_squares_classifier(xs_clean, ts_clean))
    ls_out = boundary(least_squares_classifier(xs_out, ts_out))
    log_clean = boundary(logistic_irls(xs_clean, ts_clean, maxit=200, tol=1e-12)[0])
    log_out = boundary(logistic_irls(xs_out, ts_out, maxit=200, tol=1e-12)[0])
    print(f"  LS boundary   clean {ls_clean:+.4f} -> outlier {ls_out:+.4f}"
          f"  (shift {abs(ls_out - ls_clean):.4f})")
    print(f"  logit boundary clean {log_clean:+.4f} -> outlier {log_out:+.4f}"
          f"  (shift {abs(log_out - log_clean):.4f})")


if __name__ == "__main__":
    demo()
