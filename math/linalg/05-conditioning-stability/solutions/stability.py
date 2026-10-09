"""Conditioning of problems and stability of algorithms, by hand.

Restated from Trefethen & Bau, *Numerical Linear Algebra*:

* lectures 12-15  -- the condition number of a problem versus the stability
  of an algorithm; forward error, backward error, and the inequality
  ``forward error <= condition number * backward error`` that separates the
  two ideas;
* lectures 20-21  -- Gaussian elimination, LU factorization, partial
  pivoting, and the growth factor that enters Wilkinson's backward-error
  bound.

Nothing here is copied: each construction is re-derived and then verified in
``check.py``.

DESIGN DECISION - which norm.  Conditioning is measured in the infinity norm
(max absolute row sum), the norm in which the backward-error bound of Gaussian
elimination is naturally stated and the cheapest to compute.  1-norm and
Frobenius norm are also provided so the point that *one* norm must be used on
both ``A`` and ``A^-1`` is testable.  Cost of the choice: an infinity-norm
condition number can differ from the 2-norm (singular-value) one by a factor
of up to ``n``.

DESIGN DECISION - permutation convention.  ``lu_partial_pivot`` returns
``(L, U, P)`` with ``P A = L U`` and ``P`` a full permutation matrix;
``lu_nopivot`` returns ``P = I``.  Representing ``P`` as a matrix (rather than
a list of row swaps) means ``A = P^T L U`` is one matrix product and the
reconstruction test needs no special case.  Cost: ``O(n^2)`` storage for what
an index vector would hold in ``O(n)``.

DESIGN DECISION - the inverse.  ``condition_number`` needs ``||A^-1||``.  It
is computed with Gauss-Jordan elimination with partial pivoting, written out
here, so the module is pure stdlib and ``check.py`` can reimplement the same
idea independently without importing this file.

DESIGN DECISION - the growth factor.  ``growth_factor`` runs the elimination
only far enough to read ``max |U_ij|`` and divides by ``max |A_ij|`` of the
*input*.  Dividing by ``max |U_ij|`` instead would make every growth factor
exactly 1 and hide the phenomenon; the whole point is the ratio between the
largest intermediate value and the largest input value.

DESIGN DECISION - the Wilkinson growth matrix.  The classic example is the
``gfpp`` matrix (Wilkinson 1961; Cleve Moler calls it ``gfpp``): unit
diagonal, ``-1`` in the strict lower triangle, and ``1`` in the entire last
column.  For this matrix partial pivoting does not swap, each step adds an
earlier row to the later ones, and the last column of ``U`` doubles to
``2^(n-1)``.  The looser description "ones on the diagonal, ``-1`` on the
subdiagonal, ``1`` in the top-right corner" is *not* the extremal matrix: it
has growth 2 (three diagonals only) or growth ``n`` (whole last column with
one subdiagonal), both verified during development, so the full strict lower
triangle is used here.
"""

import math
import random
import sys

EPS = sys.float_info.epsilon

# ---------------------------------------------------------------------------
# small dense helpers
# ---------------------------------------------------------------------------


def _identity(n):
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _transpose(A):
    return [list(row) for row in zip(*A)] if A else []


def _matmul(A, B):
    n, k, m = len(A), len(B), len(B[0])
    return [[sum(A[i][t] * B[t][j] for t in range(k)) for j in range(m)]
            for i in range(n)]


def _matvec(A, x):
    return [sum(A[i][j] * x[j] for j in range(len(x))) for i in range(len(A))]


def _vec_inf(x):
    return max(abs(v) for v in x) if x else 0.0


# ---------------------------------------------------------------------------
# norms
# ---------------------------------------------------------------------------


def norm_inf(A):
    """Infinity norm of a square matrix: the largest absolute row sum."""
    return max(sum(abs(v) for v in row) for row in A)


def norm_1(A):
    """1-norm of a matrix: the largest absolute column sum."""
    n, m = len(A), len(A[0])
    return max(sum(abs(A[i][j]) for i in range(n)) for j in range(m))


def norm_frobenius(A):
    """Frobenius norm: the Euclidean norm of the vector of all entries."""
    return math.sqrt(sum(v * v for row in A for v in row))


# ---------------------------------------------------------------------------
# LU factorization
# ---------------------------------------------------------------------------


def lu_nopivot(A):
    """Doolittle LU factorization without row interchanges.

    Returns ``(L, U, P)`` with ``L`` unit lower triangular, ``U`` upper
    triangular and ``P`` the identity, so ``A = P^T L U = L U``.  Raises
    ``ZeroDivisionError`` on an exactly zero pivot (the reason pivoting
    exists).
    """
    n = len(A)
    U = [row[:] for row in A]
    L = _identity(n)
    for k in range(n):
        if U[k][k] == 0.0:
            raise ZeroDivisionError("zero pivot in LU without pivoting")
        for i in range(k + 1, n):
            f = U[i][k] / U[k][k]
            L[i][k] = f
            for j in range(k, n):
                U[i][j] -= f * U[k][j]
    return L, U, _identity(n)


def lu_partial_pivot(A):
    """LU factorization with partial (row) pivoting.

    Returns ``(L, U, P)`` with ``L`` unit lower triangular, ``U`` upper
    triangular and ``P`` a permutation matrix such that ``P A = L U``, i.e.
    ``A = P^T L U``.  At step ``k`` the row of largest magnitude in column
    ``k`` below the diagonal is swapped into position ``k``.
    """
    n = len(A)
    U = [row[:] for row in A]
    L = _identity(n)
    P = _identity(n)
    for k in range(n):
        p = max(range(k, n), key=lambda i: abs(U[i][k]))
        if abs(U[p][k]) == 0.0:
            raise ZeroDivisionError("singular matrix in lu_partial_pivot")
        if p != k:
            U[k], U[p] = U[p], U[k]
            P[k], P[p] = P[p], P[k]
            for j in range(k):          # swap the multipliers found so far
                L[k][j], L[p][j] = L[p][j], L[k][j]
        for i in range(k + 1, n):
            f = U[i][k] / U[k][k]
            L[i][k] = f
            for j in range(k, n):
                U[i][j] -= f * U[k][j]
    return L, U, P


def lu_solve(A, b, pivot=True):
    """Solve ``A x = b`` from an LU factorization.

    With ``pivot=False`` it uses :func:`lu_nopivot`; with ``pivot=True`` it
    uses :func:`lu_partial_pivot`.  The permutation is applied to ``b`` before
    the forward substitution, then ``L y = P b`` and ``U x = y`` are solved.
    """
    L, U, P = lu_partial_pivot(A) if pivot else lu_nopivot(A)
    n = len(A)
    pb = _matvec(P, b)
    y = [0.0] * n
    for i in range(n):
        s = pb[i] - sum(L[i][j] * y[j] for j in range(i))
        y[i] = s / L[i][i]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = y[i] - sum(U[i][j] * x[j] for j in range(i + 1, n))
        x[i] = s / U[i][i]
    return x


# ---------------------------------------------------------------------------
# conditioning, errors, growth
# ---------------------------------------------------------------------------


def _inverse(A):
    """Matrix inverse by Gauss-Jordan elimination with partial pivoting."""
    n = len(A)
    M = [A[i][:] + _identity(n)[i] for i in range(n)]
    for k in range(n):
        p = max(range(k, n), key=lambda i: abs(M[i][k]))
        if abs(M[p][k]) < 1e-300:
            raise ZeroDivisionError("singular matrix in _inverse")
        M[k], M[p] = M[p], M[k]
        pv = M[k][k]
        for j in range(2 * n):
            M[k][j] /= pv
        for i in range(n):
            if i == k:
                continue
            f = M[i][k]
            if f != 0.0:
                for j in range(2 * n):
                    M[i][j] -= f * M[k][j]
    return [row[n:] for row in M]


def condition_number(A):
    """Infinity-norm condition number ``||A||_inf * ||A^-1||_inf``.

    Both factors use the *same* norm; mixing ``||A||_1`` with
    ``||A^-1||_inf`` inflates the result and silently weakens every bound
    that uses it.
    """
    return norm_inf(A) * norm_inf(_inverse(A))


def growth_factor(A, pivot):
    """``max |U_ij| / max |A_ij|`` after elimination.

    ``pivot`` selects partial pivoting (``True``) or no pivoting (``False``).
    The denominator is the largest entry of the *input* matrix: a growth
    factor normalised by ``max |U|`` would be identically 1.
    """
    n = len(A)
    U = [row[:] for row in A]
    for k in range(n):
        if pivot:
            p = max(range(k, n), key=lambda i: abs(U[i][k]))
            if p != k:
                U[k], U[p] = U[p], U[k]
        if U[k][k] == 0.0:
            raise ZeroDivisionError("zero pivot in growth_factor")
        for i in range(k + 1, n):
            f = U[i][k] / U[k][k]
            for j in range(k, n):
                U[i][j] -= f * U[k][j]
    max_a = max(abs(v) for row in A for v in row)
    max_u = max(abs(v) for row in U for v in row)
    return max_u / max_a


def backward_error(A, x, b):
    """Relative backward error of a computed ``x``: ``||A x - b|| / (||A|| ||x||)``.

    Using infinity norms throughout, this is the size of the perturbation
    ``dA`` for which the computed ``x`` is the exact solution of a nearby
    system.  Omitting the ``||A|| ||x||`` normalisation turns it into an
    absolute residual, which is not comparable across scalings.
    """
    residual = [sum(A[i][j] * x[j] for j in range(len(x))) - b[i]
                for i in range(len(A))]
    return _vec_inf(residual) / (norm_inf(A) * _vec_inf(x))


def forward_error(x, x_true):
    """Relative forward error ``||x - x_true|| / ||x_true||`` (infinity norm)."""
    d = [x[i] - x_true[i] for i in range(len(x))]
    return _vec_inf(d) / _vec_inf(x_true)


def perturbation_experiment(n, trials, rng):
    """Largest observed ``forward / (condition * backward)`` over random systems.

    For each trial a random ``A`` and a known ``x_true`` are drawn, ``b`` is
    formed exactly in floating point, and ``A x = b`` is solved with partial
    pivoting.  The returned maximum is the empirical sharpness of the bound
    ``forward error <= condition number * backward error``; it should sit just
    below 1 for a backward-stable solver.

    The denominator is floored at ``n * eps`` (the algorithm's backward-error
    floor).  The exact inequality is ``forward <= condition * backward *
    (1 + forward)``, so once the computed residual happens to round to a tiny
    fraction of ``eps`` a raw ratio ``forward / (condition * backward)`` can
    spike to a small multiple of 1 even though the solution is as accurate as
    the arithmetic allows.  The floor removes that rounding artefact without
    hiding any real loss of stability.
    """
    worst = 0.0
    for _ in range(trials):
        A = [[rng.uniform(-1.0, 1.0) for _ in range(n)] for _ in range(n)]
        x_true = [rng.uniform(-1.0, 1.0) for _ in range(n)]
        b = _matvec(A, x_true)
        x = lu_solve(A, b, pivot=True)
        cond = condition_number(A)
        back = backward_error(A, x, b)
        fwd = forward_error(x, x_true)
        denom = cond * (back + n * EPS)
        ratio = fwd / denom if denom > 0.0 else 0.0
        if ratio > worst:
            worst = ratio
    return worst


# ---------------------------------------------------------------------------
# the limit case: worst-case growth under partial pivoting
# ---------------------------------------------------------------------------


def wilkinson_growth(n):
    """The ``gfpp`` (Wilkinson) matrix with growth ``2^(n-1)``.

    Unit diagonal, ``-1`` in the strict lower triangle, and ``1`` in every row
    of the last column.  Under partial pivoting it never swaps; each stage
    adds a prior row to the later rows, and the last column of ``U`` becomes
    ``(1, 2, 4, ..., 2^(n-1))``.  See Trefethen & Bau lecture 21 and Moler's
    ``gfpp`` example.
    """
    A = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                A[i][j] = 1.0
            elif j == n - 1:
                A[i][j] = 1.0
            elif i > j:
                A[i][j] = -1.0
    return A


# ---------------------------------------------------------------------------
# demo
# ---------------------------------------------------------------------------


def _hilbert(n):
    return [[1.0 / (i + j + 1) for j in range(n)] for i in range(n)]


def demo():
    print("norm_inf([[1,2,3],[4,5,6],[7,8,10]]) =",
          norm_inf([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 10.0]]))
    print("condition number of I_4            =", condition_number(_identity(4)))
    print("condition number of Hilbert 8x8    = %.3e" % condition_number(_hilbert(8)))

    print("\ngrowth factor under partial pivoting")
    for n in (3, 4, 5, 6):
        print("  wilkinson_growth(%d): growth = %.1f  (2^(n-1) = %d)"
              % (n, growth_factor(wilkinson_growth(n), True), 2 ** (n - 1)))

    print("\nlimit case A = [[1e-18, 1], [1, 1]], x_true = [1, 1]")
    A = [[1e-18, 1.0], [1.0, 1.0]]
    b = _matvec(A, [1.0, 1.0])
    x_no = lu_solve(A, b, pivot=False)
    x_pi = lu_solve(A, b, pivot=True)
    print("  no pivot : x = %s  forward error = %.3e" % (x_no, forward_error(x_no, [1.0, 1.0])))
    print("  pivot    : x = %s  forward error = %.3e" % (x_pi, forward_error(x_pi, [1.0, 1.0])))

    rng = random.Random(20261008)
    print("\nmax forward / (condition * backward) over 100 random 6x6 systems =")
    print("  %.6f" % perturbation_experiment(6, 100, rng))


if __name__ == "__main__":
    demo()
