"""Reference solution: unconstrained minimisation from scratch.

Two methods, pure stdlib (``math`` only). A vector is a list of floats, a matrix
is a list of rows, a function ``f`` maps a list to a float.

    backtracking_line_search(f, grad, x, d, alpha, beta) -> step size t
        Armijo sufficient-decrease search along the descent direction ``d``.

    gradient_descent(f, grad, x0, tol, maxit) -> (x, f(x), history)
        Steepest descent with the backtracking step. Stops when the gradient
        norm drops below ``tol`` or after ``maxit`` iterations.

    newton_decrement(grad_vec, hess_mat) -> g^T H^{-1} g
        The squared Newton decrement: solve H y = g and return g^T y. A singular
        H is handled by adding a growing ridge lam*I until the solve succeeds.

    newton(f, grad, hess, x0, tol, maxit, line_search=True)
        -> (x, decrement_history, iterations)
        Newton's method. Stops when the decrement/2 is below ``tol`` (the Newton
        decrement stopping criterion). With ``line_search=False`` it takes the
        raw Newton step, which can diverge from a far start.

``solve(A, b)`` is the provided Gaussian-elimination helper.
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
    if a pivot is (numerically) zero, i.e. the system is singular.
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
    """Armijo backtracking line search along direction ``d`` from ``x``.

    Starts at t = 1 and shrinks t by ``beta`` until

        f(x + t d) <= f(x) + alpha * t * grad(x)^T d.

    Returns the accepted step size t (never zero: it floors near 1e-16).
    """
    g = grad(x)
    slope = _dot(g, d)
    fx = f(x)
    t = 1.0
    while f([x[i] + t * d[i] for i in range(len(x))]) > fx + alpha * t * slope:
        t *= beta
        if t < 1e-16:
            break
    return t


def gradient_descent(f, grad, x0, tol, maxit):
    """Steepest descent with backtracking. Returns (x, f(x), history).

    ``history`` records f at the start of every iteration.
    """
    x = list(x0)
    history = []
    for _ in range(maxit):
        history.append(f(x))
        g = grad(x)
        if _norm(g) < tol:
            break
        d = [-gi for gi in g]
        t = backtracking_line_search(f, grad, x, d)
        x = [x[i] + t * d[i] for i in range(len(x))]
    return x, f(x), history


def _solve_regularized(g, H):
    """Return y with (H + lam I) y = g, growing lam only when H is singular."""
    n = len(g)
    lam = 0.0
    for _ in range(60):
        M = [[H[i][j] + (lam if i == j else 0.0) for j in range(n)] for i in range(n)]
        try:
            return solve(M, g)
        except ValueError:
            lam = 1e-8 if lam == 0.0 else lam * 10.0
    return list(g)  # last-resort descent direction


def newton_decrement(grad_vec, hess_mat):
    """The squared Newton decrement g^T H^{-1} g, safe on a singular H.

    Solving H y = g and returning g^T y; if H is singular the solve is retried
    on H + lam*I with lam growing until it succeeds. For a positive-definite H
    the result is positive and measures how close x is to the optimum: the
    stopping rule is decrement / 2 <= tol.
    """
    y = _solve_regularized(grad_vec, hess_mat)
    return _dot(grad_vec, y)


def newton(f, grad, hess, x0, tol, maxit, line_search=True):
    """Newton's method. Returns (x, decrement_history, iterations).

    At each step solve H y = g, form the Newton direction d = -y and, when
    ``line_search`` is true, damp it with :func:`backtracking_line_search`. The
    loop stops as soon as decrement / 2 <= tol, the Newton-decrement criterion.
    """
    x = list(x0)
    decrement_history = []
    iterations = 0
    for _ in range(maxit):
        g = grad(x)
        H = hess(x)
        y = _solve_regularized(g, H)
        decrement = _dot(g, y)
        decrement_history.append(decrement)
        if decrement / 2.0 <= tol:
            break
        d = [-yi for yi in y]
        if line_search:
            t = backtracking_line_search(f, grad, x, d)
        else:
            t = 1.0
        x = [x[i] + t * d[i] for i in range(len(x))]
        iterations += 1
    return x, decrement_history, iterations


def demo():
    """Run both methods on a quadratic, a non-quadratic and the limit case."""

    # A convex quadratic: f = 1/2 x^T A x - b^T x.
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

    x_star = solve(A, b)
    print("Convex quadratic")
    print(f"  optimum from solve: {[round(v, 6) for v in x_star]}")

    x_gd, f_gd, hist = gradient_descent(qf, qg, [3.0, -2.0], 1e-8, 100000)
    print(f"  gradient descent:  {hist.__len__()} iterations -> "
          f"{[round(v, 6) for v in x_gd]}")

    x_nt, dec, it = newton(qf, qg, qh, [3.0, -2.0], 1e-10, 100)
    print(f"  Newton:            {it} iterations -> "
          f"{[round(v, 6) for v in x_nt]}, final decrement {dec[-1]:.2e}")

    # A non-quadratic convex function: f = e^x1 - x1 + e^x2 - x2, optimum (0, 0).
    def nf(x):
        return math.exp(x[0]) - x[0] + math.exp(x[1]) - x[1]

    def ng(x):
        return [math.exp(x[0]) - 1.0, math.exp(x[1]) - 1.0]

    def nh(x):
        return [[math.exp(x[0]), 0.0], [0.0, math.exp(x[1])]]

    print("Non-quadratic e^x - x (optimum (0, 0))")
    x_gd, f_gd, hist = gradient_descent(nf, ng, [2.0, -1.0], 1e-8, 100000)
    print(f"  gradient descent:  {hist.__len__()} iterations")
    x_nt, dec, it = newton(nf, ng, nh, [2.0, -1.0], 1e-10, 100)
    exponent = (math.log(dec[-1]) / math.log(dec[-2])
                if len(dec) >= 2 and dec[-2] > 0 else float("nan"))
    print(f"  Newton:            {it} iterations, last log-ratio ~{exponent:.2f}")

    # The limit case: f = sqrt(1 + x^2), undamped Newton diverges from x = 2.
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
