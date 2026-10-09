"""Support vector machines from scratch, solved through the dual.

The SVM dual is

    maximise   W(a) = sum_i a_i - 1/2 sum_ij a_i a_j t_i t_j k(x_i, x_j)
    subject to 0 <= a_i <= C  and  sum_i a_i t_i = 0,

with decision function ``f(x) = sum_i a_i t_i k(x_i, x) + b``.  We solve it with
sequential minimal optimisation (SMO), read the support vectors off the KKT
conditions, and check the margin against the primal quantity ``2 / ||w||``.

Pure standard library: ``math`` and ``random`` (no numpy).
"""

import math
import random

# ---------------------------------------------------------------------------
# Kernels and the Gram matrix
# ---------------------------------------------------------------------------


def linear_kernel(variance=1.0, offset=0.0):
    """The linear kernel ``k(x, y) = variance * (x * y + offset)``."""

    # TODO: k(x, y) = variance * (x y + offset). Return a closure `kernel(x, y)` capturing variance and offset.
    raise NotImplementedError("linear_kernel")


def rbf_kernel(length_scale=1.0, variance=1.0):
    """The RBF kernel ``k(x, y) = variance * exp(-||x - y||^2 / (2 l^2))``."""

    # TODO: k(x, y) = variance * exp(-(x - y)^2 / (2 length_scale^2)). The exponent is the SQUARED distance; return a closure `kernel(x, y)`.
    raise NotImplementedError("rbf_kernel")


def gram(kernel, xs):
    """The symmetric Gram matrix ``K_ij = k(x_i, x_j)``."""
    # TODO: Return an n x n list of lists with K[i][j] = kernel(xs[i], xs[j]). Fill both K[i][j] and K[j][i] from the same value so symmetry is exact.
    raise NotImplementedError("gram")


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
    # TODO: With E_i = f(x_i) - t_i, the soft-margin KKT conditions are: at a_i = 0, t_i E_i >= 0; at a_i = C, t_i E_i <= 0; for 0 < a_i < C, t_i E_i = 0. Report a violation when |t_i E_i| exceeds tol on the admissible side. The label t_i multiplies E_i, it is not optional.
    raise NotImplementedError("_violates_kkt")


def _bias_from_support_vectors(alphas, ts, K, C, tol=1e-7):
    """The bias from the KKT conditions, averaged over the free support vectors.

    For every free support vector (``0 < a_i < C``) the margin condition is
    ``t_i (sum_j a_j t_j k(x_j, x_i) + b) = 1``, so each one gives a candidate
    for ``b``; averaging the candidates is the numerically stable choice.
    """
    # TODO: For every free support vector (0 < a_i < C), t_i (sum_j a_j t_j k(x_j, x_i) + b) = 1, so b = t_i - sum_j a_j t_j k(x_i, x_j). Collect the candidates over all free support vectors and return their AVERAGE. If none is free, average over every support vector as a fallback.
    raise NotImplementedError("_bias_from_support_vectors")


def smo(Xs, ts, C, kernel, tol=1e-3, maxit=10000):
    """Solve the SVM dual by sequential minimal optimisation.

    Returns ``(alphas, b)``.  ``C`` is the upper bound on each dual variable; the
    hard margin is the limit ``C = math.inf``.  A hard margin on non-separable
    data leaves the dual unbounded below, which shows up as non-convergence; we
    raise ``ValueError`` in that case.
    """
    # TODO: Platt's simplified SMO. Keep alphas and b; repeat full passes until no pair changes for `max_passes` in a row. For a violating i, pick a random j != i, compute E_i, E_j, the bounds L = max(0, a_j - a_i), H = min(C, C + a_j - a_i) (same label: L = max(0, a_i + a_j - C), H = min(C, a_i + a_j)), eta = 2K_ij - K_ii - K_jj, then a_j <- clip(a_j - t_j (E_i - E_j) / eta, L, H) and a_i <- clip(a_i + t_i t_j (a_j^old - a_j), 0, C). Update b from the bound-free variable(s). On C = math.inf the dual is unbounded below unless the data are separable: if the passes never settle, raise ValueError.
    raise NotImplementedError("smo")


# ---------------------------------------------------------------------------
# Reading the answer off the KKT conditions
# ---------------------------------------------------------------------------


def support_vectors(alphas, tol=1e-5):
    """Indices of the support vectors: the points with ``a_i > tol``."""
    # TODO: Return the indices i with a_i > tol. The KKT conditions make a_i = 0 for every other point.
    raise NotImplementedError("support_vectors")


def decision_function(model, x):
    """The SVM decision value ``sum_i a_i t_i k(x_i, x) + b``."""
    # TODO: Return b + sum_i a_i t_i k(x_i, x) over the non-zero alphas. The model is a dict with keys 'alphas', 'b', 'Xs', 'ts', 'kernel'.
    raise NotImplementedError("decision_function")


def margin(model, Xs, ts):
    """The geometric margin ``2 / ||w||`` computed from the support vectors.

    In feature space ``||w||^2 = sum_ij a_i a_j t_i t_j k(x_i, x_j)``, the same
    expression for a linear or a non-linear kernel.
    """
    # TODO: The geometric margin is 2 / ||w||. In feature space ||w||^2 = sum_ij a_i a_j t_i t_j k(x_i, x_j); return 2 / sqrt of that (for a linear kernel this equals |sum_i a_i t_i x_i|). It is 2 / ||w||, not ||w||.
    raise NotImplementedError("margin")


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
    # TODO: An independent solver for the same dual, to cross-check SMO. Projected gradient: a <- proj(a - (Q a - 1) / L) with Q_ij = t_i t_j K_ij and L the largest eigenvalue of Q (power iteration). `_project` is given: it returns the closest point with 0 <= a <= C and sum_i t_i a_i = 0.
    raise NotImplementedError("reference_qp")


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
