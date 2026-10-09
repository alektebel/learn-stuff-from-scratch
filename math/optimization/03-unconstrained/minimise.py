"""Unconstrained minimisation from scratch: gradient descent and Newton's method.

Pure stdlib (``math`` only). A vector is a list of floats, a matrix is a list of
rows, a function ``f`` maps a list to a float. Implement the four functions below;
``solve`` and the small helpers are given scaffolding. See ``README.md`` for the
work and ``check.py`` for the grade.

    backtracking_line_search(f, grad, x, d, alpha=0.3, beta=0.8) -> t
    gradient_descent(f, grad, x0, tol, maxit) -> (x, f(x), history)
    newton_decrement(grad_vec, hess_mat) -> g^T H^{-1} g
    newton(f, grad, hess, x0, tol, maxit, line_search=True)
        -> (x, decrement_history, iterations)
"""

import math

__all__ = [
    "solve",
    "backtracking_line_search",
    "gradient_descent",
    "newton_decrement",
    "newton",
    "demo",
]

_SINGULAR_TOL = 1e-14


def solve(A, b):
    """Solve A x = b by Gaussian elimination with partial pivoting.

    ``A`` is an n x n list of rows, ``b`` a length-n list. Raises ``ValueError``
    if a pivot is (numerically) zero, i.e. the system is singular. Given.
    """
    n = len(A)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[pivot][col]) < _SINGULAR_TOL:
            raise ValueError("singular matrix in solve")
        M[col], M[pivot] = M[pivot], M[col]
        pv = M[col][col]
        for row in range(col + 1, n):
            factor = M[row][col] / pv
            if factor == 0.0:
                continue
            for c in range(col, n + 1):
                M[row][c] -= factor * M[col][c]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        acc = M[i][n] - sum(M[i][j] * x[j] for j in range(i + 1, n))
        x[i] = acc / M[i][i]
    return x


def _dot(u, v):
    return sum(u[i] * v[i] for i in range(len(u)))


def _norm(u):
    return math.sqrt(_dot(u, u))


def backtracking_line_search(f, grad, x, d, alpha=0.3, beta=0.8):
    """Armijo backtracking line search along ``d`` from ``x``.

    Start at t = 1 and shrink t by ``beta`` until

        f(x + t d) <= f(x) + alpha * t * grad(x)^T d.

    Return the accepted step size t (floor the search near 1e-16).
    """
    raise NotImplementedError("backtracking_line_search")


def gradient_descent(f, grad, x0, tol, maxit):
    """Steepest descent with backtracking. Return ``(x, f(x), history)``.

    ``history`` records f at the start of every iteration. Stop when the
    gradient norm is below ``tol`` or after ``maxit`` iterations.
    """
    raise NotImplementedError("gradient_descent")


def newton_decrement(grad_vec, hess_mat):
    """The squared Newton decrement ``g^T H^{-1} g``.

    Solve ``H y = g`` and return ``g^T y``. A singular H must be handled safely:
    add a growing ridge ``lam*I`` until the solve succeeds. For positive-definite
    H the result is positive and the stopping rule is ``decrement / 2 <= tol``.
    """
    raise NotImplementedError("newton_decrement")


def newton(f, grad, hess, x0, tol, maxit, line_search=True):
    """Newton's method. Return ``(x, decrement_history, iterations)``.

    Solve ``H y = g``, take the direction ``d = -y`` and, when ``line_search``
    is true, damp it with :func:`backtracking_line_search`. Stop as soon as
    ``decrement / 2 <= tol``.
    """
    raise NotImplementedError("newton")


def demo():
    """Run both methods on a quadratic, a non-quadratic and the limit case."""

    A = [[4.0, 1.0], [1.0, 3.0]]
    b = [1.0, 2.0]

    def qf(x):
        return 0.5 * (A[0][0] * x[0] * x[0] + 2 * A[0][1] * x[0] * x[1]
                      + A[1][1] * x[1] * x[1]) - (b[0] * x[0] + b[1] * x[1])

    def qg(x):
        return [A[0][0] * x[0] + A[0][1] * x[1] - b[0],
                A[1][0] * x[0] + A[1][1] * x[1] - b[1]]

    def qh(x):
        return [list(A[0]), list(A[1])]

    print("Convex quadratic")
    print(f"  optimum from solve: {[round(v, 6) for v in solve(A, b)]}")
    x_gd, _, hist = gradient_descent(qf, qg, [3.0, -2.0], 1e-8, 100000)
    print(f"  gradient descent:  {len(hist)} iterations -> "
          f"{[round(v, 6) for v in x_gd]}")
    x_nt, dec, it = newton(qf, qg, qh, [3.0, -2.0], 1e-10, 100)
    print(f"  Newton:            {it} iterations -> "
          f"{[round(v, 6) for v in x_nt]}, final decrement {dec[-1]:.2e}")

    def nf(x):
        return math.exp(x[0]) - x[0] + math.exp(x[1]) - x[1]

    def ng(x):
        return [math.exp(x[0]) - 1.0, math.exp(x[1]) - 1.0]

    def nh(x):
        return [[math.exp(x[0]), 0.0], [0.0, math.exp(x[1])]]

    print("Non-quadratic e^x - x (optimum (0, 0))")
    x_gd, _, hist = gradient_descent(nf, ng, [2.0, -1.0], 1e-8, 100000)
    print(f"  gradient descent:  {len(hist)} iterations")
    x_nt, dec, it = newton(nf, ng, nh, [2.0, -1.0], 1e-10, 100)
    exponent = (math.log(dec[-1]) / math.log(dec[-2])
                if len(dec) >= 2 and dec[-2] > 0 else float("nan"))
    print(f"  Newton:            {it} iterations, last log-ratio ~{exponent:.2f}")

    def sf(x):
        return math.sqrt(1.0 + x[0] * x[0])

    def sg(x):
        return [x[0] / math.sqrt(1.0 + x[0] * x[0])]

    def sh(x):
        return [[1.0 / (1.0 + x[0] * x[0]) ** 1.5]]

    print("Limit case sqrt(1 + x^2), start x = 2")
    far, _, _ = newton(sf, sg, sh, [2.0], 1e-10, 5, line_search=False)
    near, _, _ = newton(sf, sg, sh, [2.0], 1e-10, 100, line_search=True)
    print(f"  undamped Newton ran away to x = {far[0]:.3e}")
    print(f"  damped   Newton converged to  x = {near[0]:.3e}")


if __name__ == "__main__":
    demo()
