"""
Interior-point methods from scratch: equality-constrained Newton and the log barrier.

Sources: Boyd & Vandenberghe, *Convex Optimization* (2004).
  * ch. 10 (equality-constrained minimisation) -- the KKT system and Newton's method
    on it;
  * ch. 11 (the interior-point / barrier method) -- minimise the LP
    min c^T x s.t. A_ub x <= b_ub by the sequence of smooth problems
    c^T x - (1/t) sum_i log(b_i - a_i x), raising t by a factor mu each round;
  * ch. 5 (LP duality) -- at a central point the dual point lambda_i = 1/(t s_i) is
    feasible, its dual value is g(lambda) = c^T x - m/t, so the suboptimality
    c^T x - p* is at most m/t and tends to it as t grows.

Everything is pure stdlib (``math`` only); the linear algebra is Gaussian
elimination written here.

DESIGN DECISION - how to start the barrier method.
    The barrier is only defined on strictly feasible points (every slack
    b_i - a_i x > 0). Following the textbook, ``barrier_method`` takes an optional
    strictly feasible ``x0``; when it is absent the helper ``_find_interior`` only
    can vouch for the trivial start 0 (all b_i > 0) and otherwise raises. The
    checker and demo always pass a genuine interior point, which keeps the method
    honest. The alternative -- an infeasible-start method -- needs its own phase-I
    machinery, which is exactly what ``phase_one`` is here for.

DESIGN DECISION - the phase-I test for feasibility.
    Minimise sum_i s_i subject to a_i x - s_i <= b_i and s_i >= 0. The minimum is
    exactly 0 when the original system is feasible (take s_i = 0) and strictly
    positive otherwise (s_i must cover the worst violation). We solve this LP with
    the very barrier method above, from the obviously interior start
    x = 0, s_i = 1 + max(0, -b_i).

DESIGN DECISION - the simplex reference is enumeration.
    For two variables the optimum of an LP lies at a vertex, and a vertex is the
    intersection of two constraint boundaries. ``simplex_lp`` enumerates every pair
    and keeps the feasible ones with the smallest cost. It is a slow but completely
    trustworthy reference used only by the demo and checker, not by the solver.
"""

import math


# ---------------------------------------------------------------------------
# Small dense linear algebra (pure Python)
# ---------------------------------------------------------------------------

def _dot(u, v):
    return sum(a * b for a, b in zip(u, v))


def _norm(v):
    return math.sqrt(sum(a * a for a in v))


def _matvec(M, v):
    return [sum(M[i][j] * v[j] for j in range(len(v))) for i in range(len(M))]


def _transpose(M):
    return [list(col) for col in zip(*M)]


def solve(A, b):
    """Solve A x = b by Gaussian elimination with partial pivoting.

    Raises ValueError when a pivot is (numerically) zero.
    """
    n = len(A)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-14:
            raise ValueError("singular system")
        M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        for row in range(col + 1, n):
            factor = M[row][col] / pv
            for c in range(col, n + 1):
                M[row][c] -= factor * M[col][c]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        acc = M[i][n] - sum(M[i][j] * x[j] for j in range(i + 1, n))
        x[i] = acc / M[i][i]
    return x


def _find_interior(A_ub, b_ub):
    """Return 0 when it strictly satisfies every row, else refuse."""
    x = [0.0] * len(A_ub[0])
    if all(_dot(A_ub[i], x) < b_ub[i] for i in range(len(A_ub))):
        return x
    raise ValueError("pass a strictly feasible x0 to the barrier method")


# ---------------------------------------------------------------------------
# Equality-constrained Newton
# ---------------------------------------------------------------------------

def equality_constrained_newton(Q, c, A, b, x0, tol=1e-9, maxit=100):
    """Minimise (1/2) x^T Q x + c^T x subject to A x = b by Newton on the KKT system.

    Stationarity and feasibility together are the linear system (retaining a
    Lagrange multiplier lambda):

        [ Q   A^T ] [ x ]   [ -c ]
        [ A   0   ] [ l ] = [  b ]

    Newton updates (x, lambda) from that system; return ``(x, residuals)`` where
    ``residuals[k]`` is ||Q x + c + A^T lambda|| + ||A x - b|| before step k.
    For a quadratic the first correct step lands on the solution.
    """
    # TODO: Build the KKT matrix [[Q, A^T], [A, 0]], solve it for (dx, dlambda), update and stop when ||Qx + c + A^T lambda|| + ||Ax - b|| < tol.
    raise NotImplementedError("equality_constrained_newton")


# ---------------------------------------------------------------------------
# Log-barrier for an LP
# ---------------------------------------------------------------------------

def log_barrier_lp(c, A_ub, b_ub, t, x0, tol=1e-10, maxit=100):
    """Minimise ``c^T x - (1/t) sum_i log(b_i - a_i x)`` by damped Newton.

    The Newton system is H dx = -g with, writing s_i = b_i - a_i x,

        g = c + (1/t) sum_i a_i / s_i ,
        H = (1/t) sum_i a_i a_i^T / s_i^2 .

    Backtracking keeps every slack positive. Returns ``(x, iterations)``. As
    t grows the minimiser approaches the LP optimum.
    """
    # TODO: Newton on c^T x - (1/t) sum log(b_i - a_i x): gradient c + (1/t) sum a_i/s_i, Hessian (1/t) sum a_i a_i^T/s_i^2, backtracking to keep every slack positive; stop on the Newton decrement.
    raise NotImplementedError("log_barrier_lp")


def barrier_method(c, A_ub, b_ub, t0=1.0, mu=10.0, tol=1e-7, maxit=50, x0=None):
    """Outer barrier loop: solve at t, record, then t <- mu*t until m/t < tol.

    Returns ``(x, history)``. Each ``history`` entry is a dict
    ``{"t", "objective", "gap", "x"}` where ``objective`` is c^T x at the central
    point, ``gap`` is the theoretical duality gap ``m/t`` (m = number of rows) and
    ``x`` is a copy of the iterate (so a caller can measure the true gap
    ``c^T x - p*`` against m/t).
    """
    # TODO: Solve the barrier at t, record c^T x and the gap m/t, then t <- mu*t; stop when m/t < tol and return the last point plus the history.
    raise NotImplementedError("barrier_method")


# ---------------------------------------------------------------------------
# Enumeration reference and phase-I feasibility test
# ---------------------------------------------------------------------------

def simplex_lp(c, A_ub, b_ub):
    """Two-variable LP reference: enumerate basic feasible solutions.

    Every vertex is the intersection of two constraint boundaries; keep the
    feasible intersections and return ``(x, c^T x)`` for the cheapest. Returns
    ``(None, float('inf'))`` when no vertex is feasible.
    """
    # TODO: A 2-D optimum is a vertex: intersect each pair of constraint boundaries, keep the intersections satisfying every row, and return the cheapest.
    raise NotImplementedError("simplex_lp")


def phase_one(A_ub, b_ub, tol=1e-6, maxit=40):
    """Return True iff {x : A_ub x <= b_ub} is non-empty.

    Phase-I LP: minimise sum_i s_i over (x, s) subject to
    a_i x - s_i <= b_i and s_i >= 0. Its optimum is 0 exactly when the original
    system is feasible. Solved with the barrier method from the interior start
    x = 0, s_i = 1 + max(0, -b_i).
    """
    # TODO: Phase-I LP: minimise sum s_i subject to a_i x - s_i <= b_i and s_i >= 0; the original system is feasible exactly when the minimum is 0.
    raise NotImplementedError("phase_one")


def demo():
    """Print one measurement per mechanism."""
    print("equality-constrained Newton")
    Q = [[2.0, 0.0], [0.0, 2.0]]
    c = [-2.0, -3.0]
    A = [[1.0, 1.0]]
    b = [3.0]
    x, res = equality_constrained_newton(Q, c, A, b, [0.0, 0.0])
    print("  x =", [round(v, 6) for v in x], " residual = %.2e" % res[-1])

    print("log-barrier LP (min -x1 - x2)")
    c = [-1.0, -1.0]
    A_ub = [[1.0, 2.0], [3.0, 2.0], [0.0, 1.0], [-1.0, 0.0], [0.0, -1.0]]
    b_ub = [6.0, 12.0, 2.0, 0.0, 0.0]
    x0 = [0.5, 0.5]
    _, pstar = simplex_lp(c, A_ub, b_ub)
    print("  enumeration optimum p* =", pstar)
    for t in (1.0, 10.0, 100.0, 1000.0):
        xt, _ = log_barrier_lp(c, A_ub, b_ub, t, x0)
        print("  t=%6g  c^T x = %+.6f  m/t = %.3g" % (t, _dot(c, xt), len(A_ub) / t))

    print("barrier outer loop: measured gap vs m/t")
    xb, hist = barrier_method(c, A_ub, b_ub, t0=1.0, mu=10.0, tol=1e-6,
                              maxit=30, x0=x0)
    for h in hist:
        measured = _dot(c, h["x"]) - pstar
        print("  t=%.0e  measured gap = %.3e  m/t = %.3e  ratio = %.3f"
              % (h["t"], measured, h["gap"],
                 measured / h["gap"] if h["gap"] else float("nan")))

    print("phase-I feasibility")
    print("  feasible LP  ->", phase_one(A_ub, b_ub))
    print("  infeasible LP->", phase_one([[1.0, 1.0], [-1.0, -1.0]], [1.0, -3.0]))

    print("m/t directly: cone min x1 + x2 s.t. x1 >= 0, x2 >= 0")
    cc = [1.0, 1.0]
    Ac = [[-1.0, 0.0], [0.0, -1.0]]
    bc = [0.0, 0.0]
    xc, hc = barrier_method(cc, Ac, bc, t0=1.0, mu=10.0, tol=1e-6, maxit=30,
                            x0=[1.0, 1.0])
    for h in hc:
        measured = _dot(cc, h["x"])          # p* = 0 at the origin
        print("  t=%.0e  gap = %.3e  m/t = %.3e  ratio = %.3f"
              % (h["t"], measured, h["gap"], measured / h["gap"]))


if __name__ == "__main__":
    demo()
