"""Support vector machines from scratch, solved through the dual.

The SVM dual is

    maximise   W(a) = sum_i a_i - 1/2 sum_ij a_i a_j t_i t_j k(x_i, x_j)
    subject to 0 <= a_i <= C  and  sum_i a_i t_i = 0,

with decision function ``f(x) = sum_i a_i t_i k(x_i, x) + b``.  We solve it with
sequential minimal optimisation (SMO), read the support vectors off the KKT
conditions, and check the margin against the primal quantity ``2 / ||w||``.

Source: Bishop, *Pattern Recognition and Machine Learning*, chapter 7 (Sparse
Kernel Machines); the ideas are restated here, no text is copied.

Pure standard library: ``math`` and ``random`` (no numpy).
"""

import math
import random

# ---------------------------------------------------------------------------
# Kernels and the Gram matrix
# ---------------------------------------------------------------------------


def linear_kernel(variance=1.0, offset=0.0):
    """The linear kernel ``k(x, y) = variance * (x * y + offset)``."""

    def kernel(x, y):
        return variance * (x * y + offset)

    return kernel


def rbf_kernel(length_scale=1.0, variance=1.0):
    """The RBF kernel ``k(x, y) = variance * exp(-||x - y||^2 / (2 l^2))``."""

    def kernel(x, y):
        d = x - y
        return variance * math.exp(-d * d / (2.0 * length_scale * length_scale))

    return kernel


def gram(kernel, xs):
    """The symmetric Gram matrix ``K_ij = k(x_i, x_j)``."""
    n = len(xs)
    return [[kernel(xs[i], xs[j]) for j in range(n)] for i in range(n)]


# ---------------------------------------------------------------------------
# SMO
# ---------------------------------------------------------------------------


def _clip(value, lo, hi):
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _violates_kkt(i, alphas, ts, E_i, C, tol):
    """The KKT violation test for point ``i`` (with error ``E_i = f(x_i) - t_i``).

    The optimality conditions force ``t_i E_i >= 0`` for a point at ``a_i = 0``,
    ``t_i E_i <= 0`` for a point at the box bound ``a_i = C``, and ``t_i E_i = 0``
    for a free support vector.  The label ``t_i`` multiplies the error; dropping it
    is a classic bug.
    """
    return ((ts[i] * E_i < -tol and alphas[i] < C)
            or (ts[i] * E_i > tol and alphas[i] > 0.0))


def _bias_from_support_vectors(alphas, ts, K, C, tol=1e-7):
    """The bias from the KKT conditions, averaged over the free support vectors.

    For every free support vector (``0 < a_i < C``) the margin condition is
    ``t_i (sum_j a_j t_j k(x_j, x_i) + b) = 1``, so each one gives a candidate
    for ``b``; averaging the candidates is the numerically stable choice.
    """
    n = len(alphas)
    free = [i for i in range(n) if alphas[i] > tol and alphas[i] < C - tol]
    if not free:
        free = [i for i in range(n) if alphas[i] > tol]
    if not free:
        return 0.0
    total = 0.0
    for i in free:
        f = sum(alphas[j] * ts[j] * K[i][j] for j in range(n))
        total += ts[i] - f
    return total / len(free)


def smo(Xs, ts, C, kernel, tol=1e-3, maxit=10000):
    """Solve the SVM dual by sequential minimal optimisation.

    Returns ``(alphas, b)``.  ``C`` is the upper bound on each dual variable; the
    hard margin is the limit ``C = math.inf``.  A hard margin on non-separable
    data leaves the dual unbounded below, which shows up as non-convergence; we
    raise ``ValueError`` in that case.
    """
    n = len(Xs)
    if n == 0:
        return [], 0.0
    K = gram(kernel, Xs)
    alphas = [0.0] * n
    b = 0.0

    def decision(i):
        s = b
        for j in range(n):
            if alphas[j] != 0.0:
                s += alphas[j] * ts[j] * K[i][j]
        return s

    rng = random.Random(0xC0FFEE)
    max_passes = 50
    passes = 0
    it = 0
    while passes < max_passes and it < maxit:
        num_changed = 0
        for i in range(n):
            E_i = decision(i) - ts[i]
            if not _violates_kkt(i, alphas, ts, E_i, C, tol):
                continue
            # Second point: a random one different from i (Platt's simplified SMO).
            j = rng.randrange(n - 1)
            if j >= i:
                j += 1
            E_j = decision(j) - ts[j]
            ai_old, aj_old = alphas[i], alphas[j]
            if ts[i] != ts[j]:
                L = max(0.0, aj_old - ai_old)
                H = min(C, C + aj_old - ai_old)
            else:
                L = max(0.0, ai_old + aj_old - C)
                H = min(C, ai_old + aj_old)
            if L == H:
                continue
            eta = 2.0 * K[i][j] - K[i][i] - K[j][j]
            if eta >= 0.0:
                continue
            aj_new = _clip(aj_old - ts[j] * (E_i - E_j) / eta, L, H)
            if abs(aj_new - aj_old) < 1e-9:
                continue
            ai_new = _clip(ai_old + ts[i] * ts[j] * (aj_old - aj_new), 0.0, C)
            b1 = b - E_i - ts[i] * (ai_new - ai_old) * K[i][i] \
                - ts[j] * (aj_new - aj_old) * K[i][j]
            b2 = b - E_j - ts[i] * (ai_new - ai_old) * K[i][j] \
                - ts[j] * (aj_new - aj_old) * K[j][j]
            if 0.0 < ai_new < C:
                b = b1
            elif 0.0 < aj_new < C:
                b = b2
            else:
                b = 0.5 * (b1 + b2)
            alphas[i], alphas[j] = ai_new, aj_new
            num_changed += 1
            it += 1
            if it >= maxit:
                break
        if num_changed == 0:
            passes += 1
        else:
            passes = 0
    if C == math.inf and passes < max_passes:
        raise ValueError(
            "the hard margin is infeasible: the dual is unbounded below on "
            "non-separable data")
    return alphas, _bias_from_support_vectors(alphas, ts, K, C)


# ---------------------------------------------------------------------------
# Reading the answer off the KKT conditions
# ---------------------------------------------------------------------------


def support_vectors(alphas, tol=1e-5):
    """Indices of the support vectors: the points with ``a_i > tol``."""
    return [i for i, a in enumerate(alphas) if a > tol]


def decision_function(model, x):
    """The SVM decision value ``sum_i a_i t_i k(x_i, x) + b``."""
    alphas = model["alphas"]
    ts = model["ts"]
    Xs = model["Xs"]
    kernel = model["kernel"]
    s = model["b"]
    for i in range(len(alphas)):
        if alphas[i] != 0.0:
            s += alphas[i] * ts[i] * kernel(Xs[i], x)
    return s


def margin(model, Xs, ts):
    """The geometric margin ``2 / ||w||`` computed from the support vectors.

    In feature space ``||w||^2 = sum_ij a_i a_j t_i t_j k(x_i, x_j)``, the same
    expression for a linear or a non-linear kernel.
    """
    kernel = model["kernel"]
    alphas = model["alphas"]
    w2 = 0.0
    n = len(alphas)
    for i in range(n):
        for j in range(n):
            w2 += alphas[i] * alphas[j] * ts[i] * ts[j] * kernel(Xs[i], Xs[j])
    if w2 <= 0.0:
        return math.inf
    return 2.0 / math.sqrt(w2)


def dual_objective(alphas, Xs, ts, kernel):
    """The dual objective ``sum a_i - 1/2 sum_ij a_i a_j t_i t_j k(x_i, x_j)``."""
    K = gram(kernel, Xs)
    total = sum(alphas)
    quad = 0.0
    n = len(alphas)
    for i in range(n):
        for j in range(n):
            quad += alphas[i] * alphas[j] * ts[i] * ts[j] * K[i][j]
    return total - 0.5 * quad


# ---------------------------------------------------------------------------
# A small independent reference QP solver
# ---------------------------------------------------------------------------


def _project(alphas, ts, C):
    """Project onto ``{0 <= a <= C, sum_i t_i a_i = 0}``.

    For a multiplier ``mu`` the box-constrained minimiser is
    ``a_i(mu) = clip(a_i - mu t_i, 0, C)``; the residual ``sum_i t_i a_i(mu)``
    is non-increasing in ``mu``, so a bisection finds the multiplier that makes
    the equality hold.
    """
    n = len(alphas)
    lo, hi = -1e12, 1e12
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        residual = sum(ts[i] * _clip(alphas[i] - mid * ts[i], 0.0, C)
                       for i in range(n))
        if residual > 0.0:
            lo = mid
        else:
            hi = mid
    mu = 0.5 * (lo + hi)
    return [_clip(alphas[i] - mu * ts[i], 0.0, C) for i in range(n)]


def reference_qp(Xs, ts, C, kernel, iters=20000):
    """A generic projected-gradient solver for the SVM dual (cross-check only).

    This is a different algorithm from SMO: accelerated projected gradient with
    the step set by the largest eigenvalue of the quadratic form.
    """
    n = len(Xs)
    if n == 0:
        return [], 0.0
    K = gram(kernel, Xs)
    Q = [[ts[i] * ts[j] * K[i][j] for j in range(n)] for i in range(n)]

    # Power iteration for lambda_max(Q), used as the Lipschitz constant.
    v = [1.0 / math.sqrt(n)] * n
    lam = 0.0
    for _ in range(200):
        w = [sum(Q[i][j] * v[j] for j in range(n)) for i in range(n)]
        norm = math.sqrt(sum(x * x for x in w))
        if norm == 0.0:
            break
        v = [x / norm for x in w]
        lam = norm
    L = lam if lam > 1e-12 else 1.0

    a = [0.0] * n
    y = list(a)
    theta = 1.0
    for _ in range(iters):
        grad = [sum(Q[i][j] * y[j] for j in range(n)) - 1.0 for i in range(n)]
        a_new = _project([y[i] - grad[i] / L for i in range(n)], ts, C)
        theta_new = 0.5 * (1.0 + math.sqrt(1.0 + 4.0 * theta * theta))
        y = [a_new[i] + ((theta - 1.0) / theta_new) * (a_new[i] - a[i])
             for i in range(n)]
        a = a_new
        theta = theta_new
    return a, _bias_from_support_vectors(a, ts, K, C)


# ---------------------------------------------------------------------------
# Demo, and adaptation to the shared YAML/sklearn-style contract
# ---------------------------------------------------------------------------


def _model(Xs, ts, kernel, alphas, b, C):
    return {"Xs": Xs, "ts": ts, "kernel": kernel, "alphas": alphas,
            "b": b, "C": C}


def demo():
    """Train a few tiny SVMs and print the picture."""
    print("Separable set, soft margin C = 10, linear kernel")
    Xs = [-2.0, -1.0, 0.0, 1.0, 2.0]
    ts = [-1, -1, -1, 1, 1]
    kernel = linear_kernel()
    alphas, b = smo(Xs, ts, 10.0, kernel)
    model = _model(Xs, ts, kernel, alphas, b, 10.0)
    sv = support_vectors(alphas)
    print(f"  alphas = {[round(a, 6) for a in alphas]}")
    print(f"  support vectors = {sv}, b = {b:.6f}")
    print(f"  margin 2/||w|| = {margin(model, Xs, ts):.6f}")
    for i, x in enumerate(Xs):
        f = decision_function(model, x)
        print(f"  f({x:+.1f}) = {f:+.6f}   t = {ts[i]:+d}   "
              f"margin = {ts[i] * f:+.6f}")

    print("\nNon-separable set: hard versus soft margin")
    Xn = [0.0, 1.0, 2.0]
    tn = [1, -1, 1]
    try:
        smo(Xn, tn, math.inf, kernel)
        print("  hard margin: (unexpectedly) solved")
    except ValueError as exc:
        print(f"  hard margin: infeasible -> {exc}")
    an, bn = smo(Xn, tn, 1.0, kernel)
    mn = _model(Xn, tn, kernel, an, bn, 1.0)
    print(f"  soft margin C = 1: b = {bn:.6f}, margin = {margin(mn, Xn, tn):.6f}")
    print(f"  alphas = {[round(a, 6) for a in an]} "
          "(x = 1 saturates at C; x = 0, 2 are free on-margin support vectors)")


if __name__ == "__main__":
    demo()
