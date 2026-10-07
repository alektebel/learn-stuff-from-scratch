"""Lagrange duality from scratch: the dual of a convex QP and of an LP, the
Karush-Kuhn-Tucker residuals, and the weak/strong duality tests.

Implements chapter 5 of Boyd & Vandenberghe, *Convex Optimization* (Lagrange
duality, the dual function, weak duality, Slater's condition and strong
duality). The argument is restated here, never copied.

The Lagrangian of

    minimise    f0(x) = (1/2) x^T Q x + c^T x
    subject to  A x <= b

is L(x, lam) = (1/2) x^T Q x + c^T x + lam^T (A x - b), with lam >= 0. With
Q positive definite, stationarity gives x = -Q^{-1} (c + A^T lam), and
substituting it back leaves the *dual function*

    g(lam) = -(1/2) (c + A^T lam)^T Q^{-1} (c + A^T lam) - b^T lam,

a concave quadratic. The dual problem is max_{lam >= 0} g(lam). For a linear
programme the inner infimum is finite only on the affine set c + A^T lam = 0,
where g(lam) = -b^T lam; the dual is an LP again, and here it is solved by
enumerating its basic solutions (no simplex pivoting, no external solver).

Weak duality says g(lam) <= f0(x) for every feasible pair, so the dual never
overshoots the primal. Strong duality (equality at the optima) holds for the QP
because it is convex with a Slater point, and always for an LP when both
problems are feasible and bounded. The node's limit case is a convex problem
whose feasible set has empty relative interior, where Slater's condition fails
and a strictly positive gap survives.

    python3 duality.py      # prints the measurements this file promises
"""

import math
from itertools import combinations


# ---------------------------------------------------------------------------
# Dense linear algebra, stdlib only (dims are tiny: 1-D and 2-D problems)
# ---------------------------------------------------------------------------

def _matvec(M, v):
    return [sum(M[i][j] * v[j] for j in range(len(v))) for i in range(len(M))]


def _transpose(A):
    if not A:
        return []
    return [[A[i][j] for i in range(len(A))] for j in range(len(A[0]))]


def _matmul(A, B):
    Bt = _transpose(B)
    return [[sum(a * b for a, b in zip(row, col)) for col in Bt] for row in A]


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _invert(M, tol=1e-12):
    """Inverse of a square matrix by Gauss-Jordan with partial pivoting.

    Returns None when the matrix is (numerically) singular, so callers can skip
    a degenerate basis instead of dividing by a near-zero pivot.
    """
    n = len(M)
    aug = [list(M[i]) + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < tol:
            return None
        aug[col], aug[pivot] = aug[pivot], aug[col]
        scale = aug[col][col]
        aug[col] = [v / scale for v in aug[col]]
        for row in range(n):
            if row != col and aug[row][col] != 0.0:
                factor = aug[row][col]
                aug[row] = [a - factor * b for a, b in zip(aug[row], aug[col])]
    return [row[n:] for row in aug]


def _quad(v, M):
    return _dot(v, _matvec(M, v))


# ---------------------------------------------------------------------------
# The QP dual
# ---------------------------------------------------------------------------

def solve_qp_dual(Q, c, A, b, sweeps=50000, tol=1e-15):
    """Optimal value of the Lagrange dual of the convex QP, by coordinate ascent.

    DESIGN DECISION: maximise the dual quadratic in closed form per coordinate
    instead of running projected gradient ascent. The dual objective
    g(lam) = -1/2 lam^T H lam - d^T lam + const (H = A Q^{-1} A^T, d = b + A Q^{-1} c)
    is concave; fixing every other lam_j, the unconstrained maximiser in lam_i is
    -((H lam)^{-i}_i + d_i) / H_ii, clipped at 0. Cyclic coordinate ascent then
    converges to the global dual optimum without choosing a step size. A gradient
    method needs a step below 1/||H||; the closed-form coordinate step has none.
    H must have a positive diagonal (each constraint must bend the objective);
    a zero diagonal means that constraint carries no curvature, and the dual is
    handled by the LP route instead.
    """
    # TODO: g(lam) = -(1/2)(c + A^T lam)^T Q^{-1} (c + A^T lam) - b^T lam is concave. Expand it to -1/2 lam^T H lam - d^T lam + const with H = A Q^{-1} A^T, d = b + A Q^{-1} c, const = -1/2 c^T Q^{-1} c, then MAXIMISE by cyclic coordinate ascent: fixing the other lam_j, the best lam_i is -((d_i + sum_{j!=i} H_ij lam_j)) / H_ii, clipped at 0 (lam >= 0). The sign of d matters: d is b PLUS A Q^{-1} c, and the value is const - d^T lam - 1/2 lam^T H lam.
    raise NotImplementedError("solve_qp_dual")


# ---------------------------------------------------------------------------
# The LP dual
# ---------------------------------------------------------------------------

def solve_lp_dual(c, A, b):
    """Optimal value of the dual of {min c^T x : A x <= b}, x free.

    The dual is {max -b^T y : A^T y + c = 0, y >= 0}. It has as many variables
    as A has rows; with m primal variables an optimum sits at a basic solution
    with at most m nonzero y's. Enumerate every choice of m constraints, solve
    the square system A_S^T y = -c, keep the feasible y's, and take the best
    -b^T y. DESIGN DECISION: basis enumeration, not the simplex method. For the
    two-variable teaching cases it is exact and has no pivoting rules to debug;
    both primal and dual optima sit on vertices, so the best basic solution is
    the dual optimum.
    """
    # TODO: The dual of {min c^T x : A x <= b} is {max -b^T y : A^T y = -c, y >= 0}. It has one variable per constraint; with m primal variables an optimum is basic, so enumerate every choice of m rows of A, solve the square system A_S^T y = -c, keep the solutions with y >= 0, and return the LARGEST -b^T y. A singular basis is skipped. Never take the minimum.
    raise NotImplementedError("solve_lp_dual")


# ---------------------------------------------------------------------------
# KKT residuals
# ---------------------------------------------------------------------------

def kkt_residuals(Q, c, A, b, x, lam):
    """The four KKT residuals at a candidate (x, lam).

    Returns a dict with the positive-part violation of primal feasibility
    (A x <= b), the negative-part violation of dual feasibility (lam >= 0), the
    norm of the stationarity error Q x + c + A^T lam, and the largest
    complementary-slackness product lam_i (A x - b)_i. At an optimal pair every
    entry is zero; a scaled tolerance on these numbers is what "is a KKT point"
    means numerically.
    """
    # TODO: Four nonnegative numbers: primal feasibility max(0, max_i (A x - b)_i); dual feasibility max(0, max_i -lam_i); stationarity max_i |(Q x + c)_i + (A^T lam)_i|, including the A^T lam pull; complementary slackness max_i |lam_i (A x - b)_i|. Report all four, plus their maximum.
    raise NotImplementedError("kkt_residuals")


# ---------------------------------------------------------------------------
# Weak and strong duality
# ---------------------------------------------------------------------------

def weak_duality_gap(primal, dual):
    """The weak-duality gap primal - dual.

    Weak duality forces it to be >= 0 for any feasible pair; a negative number
    is a sign that a dual value has been maximised past its primal (the classic
    sign error). Zero means the pair is tight.
    """
    # TODO: Return primal - dual, never dual - primal. Weak duality guarantees it is >= 0 for a feasible pair; a negative value is the sign error that lets a dual overshoot its primal.
    raise NotImplementedError("weak_duality_gap")


def dual_value(Q, c, A, b):
    """The optimal QP dual value: g maximised over lam >= 0."""
    # TODO: The optimal dual value of the QP: g(lam) maximised over lam >= 0. Delegate to solve_qp_dual so the two cannot disagree.
    raise NotImplementedError("dual_value")


def strong_duality_holds(primal_value, dual_value, tol=1e-6):
    """True when the dual value equals the primal value within ``tol``.

    Equality is the content of strong duality; it is an *extra* hypothesis
    (Slater's condition, or feasibility plus boundedness for an LP), never
    something to assume. On a problem without it the gap is positive and this
    must return False.
    """
    # TODO: True iff |primal_value - dual_value| <= tol. Equality is an EXTRA hypothesis (Slater, or LP feasibility plus boundedness), so a positive gap must return False: never return True unconditionally.
    raise NotImplementedError("strong_duality_holds")


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo():
    """Print the dual values next to the known primal values."""
    # QP: minimise (1/2)(2 x1^2 + 2 x2^2) s.t. -x1 - x2 <= -1.
    Q = [[2.0, 0.0], [0.0, 2.0]]
    c = [0.0, 0.0]
    A = [[-1.0, -1.0]]
    b = [-1.0]
    p_qp, x_qp, lam_qp = 0.5, [0.5, 0.5], [1.0]
    d_qp = solve_qp_dual(Q, c, A, b)
    print("QP  minimise (1/2) x^T Q x s.t. x1 + x2 >= 1")
    print(f"  primal optimum {p_qp:.6f} at {x_qp}, lambda* = {lam_qp}")
    print(f"  dual   optimum {d_qp:.6f}   gap = {weak_duality_gap(p_qp, d_qp):+.3e}")

    # LP: minimise -x1 - x2 s.t. x1 <= 1, x2 <= 1, x1 + x2 <= 1.5.
    c_lp = [-1.0, -1.0]
    A_lp = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
    b_lp = [1.0, 1.0, 1.5]
    p_lp = -1.5
    d_lp = solve_lp_dual(c_lp, A_lp, b_lp)
    print("\nLP  minimise -x1 - x2 s.t. x1 <= 1, x2 <= 1, x1 + x2 <= 1.5")
    print(f"  primal optimum {p_lp:.6f}")
    print(f"  dual   optimum {d_lp:.6f}   gap = {weak_duality_gap(p_lp, d_lp):+.3e}")

    print("\nKKT residuals at the QP optimum:")
    for name, value in kkt_residuals(Q, c, A, b, x_qp, lam_qp).items():
        print(f"  {name:<24} {value:.3e}")

    print("\nLimit case (no Slater point: the feasible set is a single point):")
    p_lim, d_lim = 1.0, 0.0
    print("  minimise e^{-x} s.t. x^2 / y <= 0, y > 0")
    print(f"  primal optimum {p_lim:.6f}   dual optimum {d_lim:.6f}  "
          f"   gap = {weak_duality_gap(p_lim, d_lim):+.3e}")
    print(f"  strong duality holds: {strong_duality_holds(p_lim, d_lim)}")


if __name__ == "__main__":
    demo()
