"""Linear algebra from scratch: elimination, rank, null space, inverse, determinant.

Implements the material of *Mathematics for Machine Learning* (Deisenroth, Faisal & Ong),
chapter 2: systems of linear equations, Gaussian elimination, the inverse, and the
determinant — on nothing but Python floats.

Every operation reports its own numerical health instead of hiding it: pivoting is
partial (largest magnitude first), rank and singularity are decided against a tolerance
scaled to the matrix, and an inconsistent system raises rather than returning some
least-squares-looking vector that silently satisfies nothing.

DESIGN DECISION — partial pivoting, or divide by the diagonal?
A plain elimination divides by whatever sits on the diagonal: faster by a constant factor
and what the textbook notation suggests, but a small diagonal entry amplifies rounding
error without bound. Partial pivoting costs one pass per column to find the largest
magnitude and buys stability. **Chosen: partial pivoting, precisely because the limit
case is the lesson** — the demo prints a system where the naive version is wrong in the
first digit while the pivoted one is exact.

DESIGN DECISION — row echelon, or reduced row echelon?
Row echelon is enough to solve by back-substitution, but the null-space basis and the
particular/homogeneous split fall straight out of the reduced form. **Chosen: reduce
fully (Gauss-Jordan) for solve / null_space / general_solution; keep a forward-only pass
for the determinant, where the product of the pivots is all we need.**

DESIGN DECISION — how to signal "no solution", "many", "no inverse"?
Returning `None` or a sentinel forces the caller to guess which failure it got.
**Chosen: three named exceptions**, so a wrong call fails exactly where the assumption
was wrong, and a test can assert *which* failure occurred.

    python3 elimination.py      # prints the measurements this file promises
"""

_EPS = 1e-12


class InconsistentSystem(Exception):
    """Ax = b has no solution."""


class NotUnique(Exception):
    """Ax = b has infinitely many solutions; solve() requires exactly one."""


class SingularMatrix(Exception):
    """A square matrix has no inverse."""


def _scale(M):
    """Largest magnitude in M. The zero-tolerance is made relative to this."""
    return max((abs(v) for row in M for v in row), default=1.0) or 1.0


def _pivot_row(U, r, c):
    """The row in [r, len(U)) whose entry in column c has the largest magnitude."""
    return max(range(r, len(U)), key=lambda i: abs(U[i][c]))


def _forward(A):
    """Forward elimination with partial pivoting.

    Returns (U, pivots, swaps): a row-echelon copy of A, one pivot column per
    non-zero row, and how many row swaps were performed — the determinant's sign.
    """
    U = [[float(v) for v in row] for row in A]
    m = len(U)
    n = len(U[0]) if m else 0
    tol = _EPS * _scale(A)
    pivots, swaps, r = [], 0, 0
    for c in range(n):
        if r >= m:
            break
        p = _pivot_row(U, r, c)
        if abs(U[p][c]) <= tol:
            continue                      # no usable pivot in this column
        if p != r:
            U[r], U[p] = U[p], U[r]
            swaps += 1
        pivots.append(c)
        pivot = U[r][c]
        for i in range(r + 1, m):
            f = U[i][c] / pivot
            if f:
                U[i][c] = 0.0
                for j in range(c + 1, n):
                    U[i][j] -= f * U[r][j]
        r += 1
    return U, pivots, swaps


def row_echelon(A):
    """Row echelon form of A and its pivot columns: (U, pivots)."""
    U, pivots, _ = _forward(A)
    return U, pivots


def _reduce_aug(M, ncols):
    """Reduced row echelon form of an augmented matrix.

    Pivots only on the first `ncols` columns (the A part), so the trailing block
    (b, or the identity for an inverse) is carried along untouched. Returns
    (R, pivots, tol).
    """
    R = [[float(v) for v in row] for row in M]
    m = len(R)
    width = len(R[0]) if m else 0
    tol = _EPS * _scale(M)
    pivots, r = [], 0
    for c in range(ncols):
        if r >= m:
            break
        p = _pivot_row(R, r, c)
        if abs(R[p][c]) <= tol:
            continue
        R[r], R[p] = R[p], R[r]
        pivots.append(c)
        pv = R[r][c]
        R[r] = [v / pv for v in R[r]]         # normalize the pivot row
        for i in range(m):
            if i != r:
                f = R[i][c]
                if f:
                    R[i] = [a - f * b for a, b in zip(R[i], R[r])]
        r += 1
    return R, pivots, tol


def rank(A):
    """Number of linearly independent rows (= columns) of A."""
    ncols = len(A[0]) if A else 0
    _, pivots, _ = _reduce_aug(A, ncols)
    return len(pivots)


def null_space(A):
    """A basis of the null space {x : Ax = 0}; its length is n - rank(A)."""
    m = len(A)
    n = len(A[0]) if m else 0
    R, pivots, _ = _reduce_aug(A, n)
    free = [c for c in range(n) if c not in pivots]
    basis = []
    for c in free:
        v = [0.0] * n
        v[c] = 1.0
        for k, pc in enumerate(pivots):
            v[pc] = -R[k][c]                 # satisfy the pivot rows
        basis.append(v)
    return basis


def solve(A, b):
    """The unique x with Ax = b.

    Raises InconsistentSystem if no x exists, NotUnique if infinitely many do.
    """
    m = len(A)
    n = len(A[0]) if m else 0
    M = [list(A[i]) + [b[i]] for i in range(m)]
    R, pivots, tol = _reduce_aug(M, n)
    for i in range(len(pivots), m):
        if abs(R[i][n]) > tol:               # 0·x = nonzero: no solution
            raise InconsistentSystem("the augmented system has 0 = nonzero")
    if len(pivots) < n:                      # free variable left: not unique
        raise NotUnique(f"rank {len(pivots)} < {n} unknowns")
    x = [0.0] * n
    for k, c in enumerate(pivots):
        x[c] = R[k][n]
    return x


def general_solution(A, b):
    """(particular, basis): one solution of Ax = b plus a basis of the null space.

    Every solution is particular + a combination of basis. Raises
    InconsistentSystem as solve() does, but never NotUnique.
    """
    m = len(A)
    n = len(A[0]) if m else 0
    M = [list(A[i]) + [b[i]] for i in range(m)]
    R, pivots, tol = _reduce_aug(M, n)
    for i in range(len(pivots), m):
        if abs(R[i][n]) > tol:
            raise InconsistentSystem("the augmented system has 0 = nonzero")
    particular = [0.0] * n
    for k, c in enumerate(pivots):
        particular[c] = R[k][n]
    return particular, null_space(A)


def inverse(A):
    """The inverse of a square matrix, by Gauss-Jordan on [A | I].

    Raises SingularMatrix if A is not invertible.
    """
    n = len(A)
    if any(len(row) != n for row in A):
        raise ValueError("inverse() needs a square matrix")
    aug = [list(A[i]) + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    R, pivots, _ = _reduce_aug(aug, n)
    if len(pivots) < n:
        raise SingularMatrix(f"rank {len(pivots)} < {n}")
    return [[R[i][n + j] for j in range(n)] for i in range(n)]


def determinant(A):
    """The determinant of a square matrix, from the elimination it already does.

    det is the product of the pivots, times -1 for each row swap. A singular
    matrix has a zero pivot, so its determinant is zero.
    """
    n = len(A)
    if any(len(row) != n for row in A):
        raise ValueError("determinant() needs a square matrix")
    U, pivots, swaps = _forward(A)
    if len(pivots) < n:
        return 0.0
    det = 1.0
    for k, c in enumerate(pivots):
        det *= U[k][c]
    return -det if swaps % 2 else det


if __name__ == "__main__":
    def _no_pivot(M, r):
        """Forward elimination WITHOUT pivoting — the mistake the module exists to show."""
        U = [[float(v) for v in row] for row in M]
        r = [float(v) for v in r]
        m = len(U)
        for c in range(m):
            for i in range(c + 1, m):
                f = U[i][c] / U[c][c]
                for j in range(c, m):
                    U[i][j] -= f * U[c][j]
                r[i] -= f * r[c]
        out = [0.0] * m
        for i in reversed(range(m)):
            out[i] = (r[i] - sum(U[i][j] * out[j] for j in range(i + 1, m))) / U[i][i]
        return out

    A = [[2.0, 1.0, -1.0], [-3.0, -1.0, 2.0], [-2.0, 1.0, 2.0]]
    b = [8.0, -11.0, -3.0]
    x = solve(A, b)
    resid = max(abs(sum(A[i][j] * x[j] for j in range(3)) - b[i]) for i in range(3))

    deficient = [[1.0, 2.0, 3.0], [2.0, 4.0, 6.0]]
    basis = null_space(deficient)

    inv = inverse(A)
    ident = [[sum(A[i][k] * inv[k][j] for k in range(3)) for j in range(3)]
             for i in range(3)]
    eye_err = max(abs(ident[i][j] - (1.0 if i == j else 0.0))
                  for i in range(3) for j in range(3))

    small = [[1e-18, 1.0], [1.0, 1.0]]
    rhs = [1.0, 2.0]
    naive = _no_pivot(small, rhs)
    pivoted = solve(small, rhs)

    print("Linear algebra from scratch — measurements")
    print(f"  solve      x = {[round(v, 6) for v in x]}  residual {resid:.2e}")
    print(f"  rank       {rank(deficient)} of 2 rows, null-space dim {len(basis)}")
    print(f"  inverse    max|A·A⁻¹ − I| = {eye_err:.2e}")
    print(f"  det        {determinant(A):.6f}")
    print(f"  small pivot  naive x₁ = {naive[0]:.6f} (wrong) · pivoted x₁ = {pivoted[0]:.6f}")
