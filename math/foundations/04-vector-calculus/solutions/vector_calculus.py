"""Vector calculus from scratch: gradients, finite differences, Taylor expansions.

Implements *Mathematics for Machine Learning* (Deisenroth, Faisal & Ong), chapter 5
("Vector Calculus"): the gradient of a scalar function of a vector or a matrix, the
Hessian, and the finite-difference approximation used to check both.

The chapter's lesson is that the derivative of a matrix expression is another matrix
expression, and that you do not have to trust either: a central difference is an
independent oracle, cheap enough to run on every gradient. This module builds the
standard gradients (xᵀAx, ‖Ax − b‖², log det, trace forms), one shared central-difference
checker, and the second-order Taylor expansion with its Hessian.

Everything is standard-library Python: no numpy. Matrices are lists of lists of floats;
small helpers for the arithmetic (`_det`, `_inverse`) are provided, not part of the
lesson.

DESIGN DECISION — gradient of a quadratic form: 2Ax or (A + Aᵀ)x?
When A is symmetric the two agree, so the simpler 2Ax covers most uses. **Chosen:
always (A + Aᵀ)x.** For a general A only (A + Aᵀ)x is right, because xᵀAx = xᵀ((A + Aᵀ)/2)x.
A symmetric fast path would hide the (A + Aᵀ) that carries the transpose, and the bug is
invisible until a non-symmetric A appears — exactly the limit case this node tests.

DESIGN DECISION — central differences or forward differences?
Forward, (f(x + h e) − f(x))/h, costs one extra evaluation per coordinate and has error
O(h); central, (f(x + h e) − f(x − h e))/(2h), costs two and has error O(h²). **Chosen:
central**, because the later nodes want to trust the checker at 1e-6 and O(h²) reaches it
at an ordinary h. The price is a new failure mode: for h too small the two nearby function
values cancel and round-off O(ε/h) takes over, so there is a best h (the U-shaped curve of
the demo).

DESIGN DECISION — one finite-difference checker, or one per expression?
Per-expression differences duplicate the step-size choice and let them drift. **Chosen:
one `central_difference` and one `relative_gradient_error` that every later node imports**,
so the truncation/round-off trade-off is stated once. The cost is that a matrix expression
must be wrapped as a scalar function of a flat vector before it can be checked.

DESIGN DECISION — log det via the inverse or via Jacobi's formula?
The derivative of det is det(X)·X⁻ᵀ (Jacobi), which is fiddly to build directly. **Chosen:
compute X⁻ᵀ from a Gauss-Jordan `_inverse` and transpose it.** The transpose is the whole
lesson: the gradient is X⁻ᵀ, not X⁻¹, and a symmetric X hides that, so the check uses a
non-symmetric invertible X.

DESIGN DECISION — Hessian analytically or by finite differences?
A finite-difference Hessian is noisy (second differences lose two digits). **Chosen: the
closed form A + Aᵀ for the quadratic form**, with the finite-difference Hessian living only
in the checker. For a quadratic the second-order Taylor expansion is exact, so the h³
shrinking test uses a cubic scalar function, whose third derivative is nonzero.

    python3 vector_calculus.py     # prints the measurements this file promises
"""

import math

_EPS = 1e-12


# ---------------------------------------------------------------------------
# Small matrix helpers (the arithmetic, not the lesson)
# ---------------------------------------------------------------------------

def _dot(u, v):
    return sum(a * b for a, b in zip(u, v))


def _norm(u):
    return math.sqrt(_dot(u, u))


def _matvec(A, v):
    return [sum(A[i][j] * v[j] for j in range(len(v))) for i in range(len(A))]


def _matmul(A, B):
    return [[sum(A[i][t] * B[t][j] for t in range(len(B)))
             for j in range(len(B[0]))] for i in range(len(A))]


def _transpose(A):
    return [list(row) for row in zip(*A)]


def _identity(n):
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _det(A):
    """Determinant by LU elimination with partial pivoting."""
    n = len(A)
    M = [list(row) for row in A]
    det = 1.0
    for col in range(n):
        p = max(range(col, n), key=lambda i: abs(M[i][col]))
        if abs(M[p][col]) <= _EPS:
            return 0.0
        if p != col:
            M[col], M[p] = M[p], M[col]
            det = -det
        det *= M[col][col]
        for i in range(col + 1, n):
            f = M[i][col] / M[col][col]
            M[i] = [M[i][j] - f * M[col][j] for j in range(n)]
    return det


def _inverse(A):
    """Inverse by Gauss-Jordan elimination; raises ValueError if A is singular."""
    n = len(A)
    M = [list(A[i]) + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for col in range(n):
        p = max(range(col, n), key=lambda i: abs(M[i][col]))
        if abs(M[p][col]) <= _EPS:
            raise ValueError("matrix is singular")
        M[col], M[p] = M[p], M[col]
        pv = M[col][col]
        M[col] = [v / pv for v in M[col]]
        for i in range(n):
            if i != col:
                f = M[i][col]
                if f:
                    M[i] = [a - f * b for a, b in zip(M[i], M[col])]
    return [row[n:] for row in M]


# ---------------------------------------------------------------------------
# Analytic gradients of the standard matrix expressions
# ---------------------------------------------------------------------------

def quadratic_gradient(A, x):
    """Gradient of f(x) = xᵀ A x with respect to x.

    For any square A, ∇f(x) = (A + Aᵀ) x. Only when A is symmetric does this reduce to
    2 A x; the general form is not optional (see the non-symmetric limit case).
    """
    n = len(x)
    S = [[A[i][j] + A[j][i] for j in range(n)] for i in range(n)]
    return [sum(S[i][j] * x[j] for j in range(n)) for i in range(n)]


def least_squares_gradient(A, b, x):
    """Gradient of f(x) = ‖A x − b‖² with respect to x: 2 Aᵀ (A x − b)."""
    m = len(A)
    n = len(x)
    r = [sum(A[i][j] * x[j] for j in range(n)) - b[i] for i in range(m)]
    return [2.0 * sum(A[i][j] * r[i] for i in range(m)) for j in range(n)]


def logdet_gradient(X):
    """Gradient of f(X) = log det X with respect to X: X⁻ᵀ.

    Valid for an invertible X with det X > 0. Jacobi's formula gives d det = det·tr(X⁻¹ dX),
    so the gradient of log det is X⁻ᵀ — the transpose of the inverse, not the inverse.
    """
    return _transpose(_inverse(X))


def trace_linear_gradient(A):
    """Gradient of f(X) = tr(A X) with respect to X: Aᵀ."""
    return _transpose(A)


def trace_quadratic_gradient(A, X):
    """Gradient of f(X) = tr(Xᵀ A X) with respect to X: (A + Aᵀ) X."""
    n = len(X)
    S = [[A[i][j] + A[j][i] for j in range(n)] for i in range(n)]
    return [[sum(S[i][k] * X[k][j] for k in range(n))
             for j in range(n)] for i in range(n)]


def quadratic_hessian(A):
    """Hessian of f(x) = xᵀ A x: the constant matrix A + Aᵀ."""
    n = len(A)
    return [[A[i][j] + A[j][i] for j in range(n)] for i in range(n)]


# ---------------------------------------------------------------------------
# The shared finite-difference checker
# ---------------------------------------------------------------------------

def central_difference(f, x, h=1e-6):
    """Gradient of a scalar function f at x by central differences.

    Component j is (f(x + h eⱼ) − f(x − h eⱼ)) / (2h), accurate to O(h²). The default
    h = 1e-6 sits near the bottom of the round-off/truncation trade-off for double
    precision (see error_curve).
    """
    n = len(x)
    grad = []
    for j in range(n):
        xp = list(x)
        xp[j] += h
        xm = list(x)
        xm[j] -= h
        grad.append((f(xp) - f(xm)) / (2.0 * h))
    return grad


def relative_gradient_error(f, grad_f, x, h=1e-6):
    """Relative error between an analytic gradient and its central-difference estimate."""
    g = grad_f(x)
    fd = central_difference(f, x, h)
    scale = max(_norm(g), _norm(fd), 1e-12)
    return max(abs(a - b) for a, b in zip(g, fd)) / scale


def error_curve(f, grad_f, x, hs):
    """Relative gradient error for each step size in hs: [(h, error), ...].

    Sweeping h exposes the U-shaped trade-off: truncation O(h²) on the right, round-off
    O(ε/h) on the left, and a best h in between.
    """
    return [(h, relative_gradient_error(f, grad_f, x, h)) for h in hs]


# ---------------------------------------------------------------------------
# Second-order Taylor expansion
# ---------------------------------------------------------------------------

def taylor_second_order(f, grad_f, hess_f, x, p):
    """Second-order Taylor approximation of f at x in direction p.

    f(x + p) ≈ f(x) + ∇f(x)ᵀ p + ½ pᵀ ∇²f(x) p. For a quadratic f it is exact, so the
    remainder first appears at third order and shrinks as ‖p‖³.
    """
    n = len(x)
    g = grad_f(x)
    H = hess_f(x)
    linear = sum(g[i] * p[i] for i in range(n))
    quad = 0.5 * sum(p[i] * H[i][j] * p[j] for i in range(n) for j in range(n))
    return f(x) + linear + quad


if __name__ == "__main__":
    def _maxabs(M):
        return max(abs(v) for row in M for v in row)

    def _diff(A, B):
        return _maxabs([[A[i][j] - B[i][j] for j in range(len(A[0]))]
                        for i in range(len(A))])

    # A deliberately non-symmetric A: the general gradient is (A + Aᵀ)x, not 2Ax.
    A = [[2.0, 5.0], [1.0, 3.0]]
    x = [1.5, -2.0]
    gq = quadratic_gradient(A, x)
    twice = [2.0 * v for v in _matvec(A, x)]
    fq = lambda v: _dot(v, _matvec(A, v))

    Als = [[1.0, 2.0], [0.0, 1.0], [2.0, -1.0]]
    bls = [1.0, -1.0, 2.0]
    xls = [0.5, 1.5]
    fls = lambda v: sum((sum(Als[i][j] * v[j] for j in range(2)) - bls[i]) ** 2
                        for i in range(3))

    X = [[2.0, 1.0, 0.0], [0.5, 3.0, 1.0], [0.0, 1.5, 2.0]]     # non-symmetric, det = 8
    Xt = [[0.7, -0.3], [0.4, 1.2]]
    At = [[2.0, 5.0], [1.0, 3.0]]

    def cubic(v):
        return sum(a ** 3 for a in v) / 3.0

    def cubic_grad(v):
        return [a * a for a in v]

    xc = [1.5, -2.0, 0.5]
    d = [0.7, -0.4, 0.9]
    cubic_hess = lambda v: [[2.0 * a if i == j else 0.0 for j, a in enumerate(v)]
                            for i in range(len(v))]

    def taylor_err(h):
        p = [h * c for c in d]
        f_here = cubic([xc[i] + p[i] for i in range(3)])
        return abs(f_here - taylor_second_order(cubic, cubic_grad, cubic_hess, xc, p))

    hs = [1e-12, 1e-10, 1e-8, 1e-6, 1e-5, 1e-4, 1e-2, 1e-1]
    curve = error_curve(cubic, cubic_grad, xc, hs)
    best_h = min(curve, key=lambda pair: pair[1])

    print("Vector calculus from scratch — measurements")
    print(f"  quadratic  |g − (A+Aᵀ)x| = {max(abs(gq[i] - sum((A[i][j] + A[j][i]) * x[j] for j in range(2))) for i in range(2)):.2e}"
          f"  |g − 2Ax| = {max(abs(gq[i] - twice[i]) for i in range(2)):.2e}")
    print(f"  least-sq   relative error vs central diff = {relative_gradient_error(fls, lambda v: least_squares_gradient(Als, bls, v), xls):.2e}")
    print(f"  log-det    |g − X⁻ᵀ| = {_diff(logdet_gradient(X), _transpose(_inverse(X))):.2e}"
          f"  |g − X⁻¹| = {_diff(logdet_gradient(X), _inverse(X)):.2e}")
    print(f"  traces     |∇tr(AX) − Aᵀ| = {_diff(trace_linear_gradient(At), _transpose(At)):.2e}"
          f"  |∇tr(XᵀAX) − (A+Aᵀ)X| = {_diff(trace_quadratic_gradient(At, Xt), _matmul([[At[i][j] + At[j][i] for j in range(2)] for i in range(2)], Xt)):.2e}")
    print(f"  hessian    |H − (A+Aᵀ)| = {_diff(quadratic_hessian(A), [[A[i][j] + A[j][i] for j in range(2)] for i in range(2)]):.2e}")
    print(f"  taylor     err(0.05) = {taylor_err(0.05):.3e}  err(0.025) = {taylor_err(0.025):.3e}"
          f"  ratio = {taylor_err(0.05) / taylor_err(0.025):.3f} (→ h³)")
    print(f"  fd curve   h=1e-12: {dict(curve)[1e-12]:.1e}   best h={best_h[0]:.0e}: {best_h[1]:.1e}"
          f"   h=1e-1: {dict(curve)[1e-1]:.1e}  (U-shape)")
