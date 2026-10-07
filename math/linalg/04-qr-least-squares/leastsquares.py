"""Householder QR and the three least-squares routes, from scratch.

Householder QR, and the three standard ways to solve the linear least-squares
problem ``min_x ||A x - b||_2``, restated from Gilbert Strang's *Linear Algebra
and Its Applications* lectures 6-11 (``strang:6`` .. ``strang:11``; the same
material is in Trefethen & Bau, *Numerical Linear Algebra*, lectures 6-11,
``trefethen-bau:6`` .. ``trefethen-bau:11``):

* ``householder_qr`` -- factor ``A = Q R`` with ``Q`` orthogonal and ``R`` upper
  triangular, by applying a sequence of Householder reflectors to ``A``;
* ``normal_equations`` -- solve ``A^T A x = A^T b`` with a general square solver;
* ``qr_least_squares`` -- ``x = R^{-1} Q^T b`` (the first ``n`` rows, since the
  trailing rows of ``R`` are zero for a tall ``A``);
* ``svd_least_squares`` -- ``x = V Sigma^+ U^T b`` using the module's own SVD.

Everything is standard library (``math``, ``fractions``) in double precision.
``fractions.Fraction`` supplies an exact high-precision reference for integer or
rational inputs, so the accuracy of the floating-point routes can be measured
instead of guessed.

DESIGN DECISION -- Householder reflectors, not classical Gram-Schmidt?
Classical Gram-Schmidt builds ``Q`` by subtracting projections; for an
ill-conditioned ``A`` the columns of the computed ``Q`` drift away from
orthonormality, sometimes by a factor of the condition number. Householder
applies a product of *orthogonal* reflectors, so the computed ``Q`` is orthogonal
to working precision whatever the conditioning -- that is the accept criterion of
this node. **Chosen: Householder.** The cost is that ``Q`` is not returned in a
form that reads column-by-column (each column is a product of reflectors',
i.e. it is accumulated as a matrix), which is more work but exactly the point.

DESIGN DECISION -- three least-squares routes, and why keep all three?
They trade accuracy against work in a way that a single interface hides. The
normal equations square the condition number (relative error about
``cond(A)^2 * eps``), but they are the fastest and the cheapest to differentiate.
QR keeps the condition number (about ``cond(A) * eps``) and is the workhorse. The
SVD is the most robust and the only one that degrades gracefully on a
rank-deficient ``A`` (via the pseudo-inverse), at the highest cost. **Chosen:
implement all three** so the node can demonstrate, with a measurement, *why* the
normal equations are the naive route. The cost is duplicated linear algebra; the
exact ``Fraction`` reference makes the comparison meaningful rather than a
matter of opinion.

DESIGN DECISION -- the SVD is exact-linear-algebra, not a squaring victory?
The module's SVD is built from the eigendecomposition of the symmetric positive
semidefinite matrix ``A^T A`` (a cyclic Jacobi eigensolver, the same pattern as
the spectral-theorem node; copied here so this module is standalone). That route
also squares the condition number while forming ``A^T A``, so it is not the best
reference for the *error* comparison -- the ``Fraction`` solver is. **Chosen:
Jacobi-on-``A^T A`` for the SVD, ``Fraction`` for the reference.** The cost is
that the SVD route's own accuracy is limited on the extreme limit case, which the
README states plainly.

DESIGN DECISION -- an exact reference instead of a trusted float answer?
Floating point cannot decide which of two float answers is closer to the truth;
that needs a computation with no round-off. Integer/rational ``A`` and ``b`` let
``A^T A x = A^T b`` be solved in exact rational arithmetic, giving the true
minimiser. **Chosen: ``exact_least_squares`` with ``Fraction``.** The cost is
that the reference only exists for rational inputs; the checker constructs the
limit case with a Hilbert matrix, whose entries are rational by construction.

    python3 leastsquares.py     # prints the measurements this file promises
"""

import math
from fractions import Fraction


# ---------------------------------------------------------------------------
# Small dense arithmetic plumbing (provided; not the lesson)
# ---------------------------------------------------------------------------

def _identity(n):
    """The n x n identity as floats."""
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _transpose(A):
    """Transpose: rows become columns (works for floats and Fractions)."""
    return [list(row) for row in zip(*A)] if A else []


def _matmul(A, B):
    """Matrix product; generic over float and Fraction."""
    n, k, m = len(A), len(B), len(B[0])
    return [[sum(A[i][t] * B[t][j] for t in range(k)) for j in range(m)]
            for i in range(n)]


def _matvec(A, v):
    """Matrix-vector product; generic over float and Fraction."""
    return [sum(A[i][j] * v[j] for j in range(len(v))) for i in range(len(A))]


def _dot(u, v):
    """Inner product of two equal-length vectors."""
    return sum(a * b for a, b in zip(u, v))


def _norm(v):
    """Euclidean norm of a vector."""
    return math.sqrt(sum(x * x for x in v))


def _solve(A, b):
    """Solve the square system ``A x = b`` by Gaussian elimination.

    Partial pivoting; generic over float and Fraction, which is what lets the
    same routine serve both the floating-point normal equations and the exact
    ``Fraction`` reference.
    """
    n = len(A)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda i: abs(M[i][col]))
        if abs(M[piv][col]) < 1e-300:
            raise ZeroDivisionError("singular system in _solve")
        M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        for i in range(col + 1, n):
            f = M[i][col] / pv
            for j in range(col, n + 1):
                M[i][j] -= f * M[col][j]
    x = [M[i][n] for i in range(n)]
    for i in range(n - 1, -1, -1):
        s = x[i] - sum(M[i][j] * x[j] for j in range(i + 1, n))
        x[i] = s / M[i][i]
    return x


def _solve_upper(R, b):
    """Back-substitute an upper-triangular ``R x = b``."""
    n = len(R)
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = b[i] - sum(R[i][j] * x[j] for j in range(i + 1, n))
        x[i] = s / R[i][i]
    return x


def _gram_schmidt(vectors, n):
    """Orthonormalise a list of length-n vectors (modified Gram-Schmidt)."""
    out = []
    for v in vectors:
        w = [float(x) for x in v]
        for u in out:
            d = _dot(w, u)
            w = [w[i] - d * u[i] for i in range(n)]
        nrm = _norm(w)
        if nrm < 1e-14:
            raise ValueError("the supplied vectors are linearly dependent")
        out.append([x / nrm for x in w])
    return out


def _complement_vector(used, m):
    """A unit vector in R^m orthogonal to every vector in ``used``."""
    for i in range(m):
        v = [1.0 if j == i else 0.0 for j in range(m)]
        for u in used:
            d = _dot(v, u)
            v = [v[t] - d * u[t] for t in range(m)]
        if _norm(v) > 1e-9:
            nrm = _norm(v)
            return [x / nrm for x in v]
    raise ValueError("no orthonormal complement left in R^%d" % m)


# ---------------------------------------------------------------------------
# The SVD engine (provided plumbing, copied in pattern from the spectral node)
# ---------------------------------------------------------------------------

def _jacobi_eigh(A):
    """Eigenvalues (ascending) and an orthonormal eigenbasis of symmetric ``A``.

    Cyclic Jacobi; each plane rotation annihilates one off-diagonal entry and the
    same rotation accumulates into ``Q``, so ``Q`` stays orthonormal.
    """
    n = len(A)
    M = [[float(A[i][j]) for j in range(n)] for i in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            avg = 0.5 * (M[i][j] + M[j][i])
            M[i][j] = M[j][i] = avg
    Q = _identity(n)
    if n == 0:
        return [], []
    scale = 1.0 + max((abs(M[i][j]) for i in range(n) for j in range(n)), default=0.0)
    for _ in range(100):
        off = math.sqrt(sum(M[i][j] * M[i][j] for i in range(n) for j in range(n)
                            if i != j))
        if off <= 1e-15 * scale:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                apq = M[p][q]
                if apq == 0.0:
                    continue
                app, aqq = M[p][p], M[q][q]
                tau = (aqq - app) / (2.0 * apq)
                t = (math.copysign(1.0, tau) / (abs(tau) + math.sqrt(1.0 + tau * tau))
                     if tau != 0.0 else 1.0)
                c = 1.0 / math.sqrt(1.0 + t * t)
                s = t * c
                for k in range(n):
                    mkp, mkq = M[k][p], M[k][q]
                    M[k][p] = c * mkp - s * mkq
                    M[k][q] = s * mkp + c * mkq
                for k in range(n):
                    mpk, mqk = M[p][k], M[q][k]
                    M[p][k] = c * mpk - s * mqk
                    M[q][k] = s * mpk + c * mqk
                for k in range(n):
                    qkp, qkq = Q[k][p], Q[k][q]
                    Q[k][p] = c * qkp - s * qkq
                    Q[k][q] = s * qkp + c * qkq
    order = sorted(range(n), key=lambda i: M[i][i])
    evals = [M[i][i] for i in order]
    Qs = [[Q[r][order[j]] for j in range(n)] for r in range(n)]
    return evals, Qs


def _svd(A):
    """Thin SVD ``(U, S, Vt)`` with ``A = U diag(S) V^T`` for ``m >= n``.

    Singular values descend; ``U`` is m x n with orthonormal columns and ``Vt``
    is n x n orthogonal. A zero singular value is completed to an orthonormal
    column rather than dividing by (near) zero.
    """
    m = len(A)
    n = len(A[0]) if m else 0
    if n > m:
        raise ValueError("_svd expects m >= n (tall or square); got %d x %d" % (m, n))
    C = _matmul(_transpose(A), A)
    evals, V = _jacobi_eigh(C)
    order = sorted(range(n), key=lambda i: -evals[i])
    evals = [evals[i] for i in order]
    V = [[V[r][order[j]] for j in range(n)] for r in range(n)]
    S = [math.sqrt(e) if e > 0.0 else 0.0 for e in evals]
    U = [[0.0] * n for _ in range(m)]
    used = []
    for k in range(n):
        if S[k] > 1e-12:
            col = [sum(A[i][t] * V[t][k] for t in range(n)) / S[k] for i in range(m)]
        else:
            col = _complement_vector(used, m)
        for u in used:
            d = _dot(col, u)
            col = [col[i] - d * u[i] for i in range(m)]
        nrm = _norm(col)
        if nrm > 1e-14:
            col = [x / nrm for x in col]
        for i in range(m):
            U[i][k] = col[i]
        used.append(col)
    return U, S, _transpose(V)


# ---------------------------------------------------------------------------
# Step 1: Householder QR
# ---------------------------------------------------------------------------

def householder_qr(A):
    """Factor ``A`` (m x n, ``m >= n``) as ``A = Q R``.

    Returns ``(Q, R)`` with ``Q`` m x m orthogonal and ``R`` m x n upper
    triangular (its first n rows hold the triangular factor, its last m-n rows
    are zero). Each column of ``A`` is reduced with a Householder reflector
    ``H_k = I - 2 v v^T`` built from the sub-column below the diagonal; the
    reflector is applied to ``R`` from the left and accumulated into ``Q``, so
    ``Q = H_1 H_2 ... H_n`` is a product of orthogonal matrices.

    DESIGN DECISION -- accumulate ``Q`` as a full m x m product, not as a list
    of reflector vectors. Storing the reflectors and applying them lazily would
    save memory, but the checker's accept criterion is ``Q^T Q = I``, so ``Q``
    must exist as a matrix. **Chosen: accumulate.** The cost is O(m^2 n) work
    and memory that a production LAPACK routine expends only on request.
    """
    # TODO: For column k build the reflector H = I - 2 v v^T from the sub-column, apply it to R from the left, and accumulate Q <- Q H.
    raise NotImplementedError("householder_qr")


# ---------------------------------------------------------------------------
# Step 2: least squares by the normal equations
# ---------------------------------------------------------------------------

def normal_equations(A, b):
    """Least squares ``x`` by solving ``A^T A x = A^T b``.

    This is the calculus route: setting the gradient of ``||A x - b||^2`` to
    zero gives the normal equations. It is correct and cheap, but forming
    ``A^T A`` squares the condition number, so about twice as many digits are
    lost as with QR -- the limit case this node exists to demonstrate.
    """
    # TODO: Form C = A^T A and rhs = A^T b, then solve the square system C x = rhs.
    raise NotImplementedError("normal_equations")


# ---------------------------------------------------------------------------
# Step 3: least squares by QR
# ---------------------------------------------------------------------------

def qr_least_squares(A, b):
    """Least squares ``x = R^{-1} Q^T b`` from the Householder QR factor.

    For ``A = Q R`` with ``Q`` orthogonal, ``||A x - b|| = ||R x - Q^T b||``
    because orthogonal maps preserve length. The bottom ``m - n`` rows of ``R``
    are zero, so only the first ``n`` rows and the first ``n`` entries of
    ``Q^T b`` matter, leaving a triangular system to back-substitute.
    """
    # TODO: From A = Q R, solve R x = Q^T b using the first n rows of R and the first n entries of Q^T b.
    raise NotImplementedError("qr_least_squares")


# ---------------------------------------------------------------------------
# Step 4: least squares by the SVD (pseudo-inverse)
# ---------------------------------------------------------------------------

def svd_least_squares(A, b, tol=1e-12):
    """Least squares via the pseudo-inverse ``x = V Sigma^+ U^T b``.

    Singular values at or below ``tol`` times the largest are treated as zero
    and their reciprocal is taken as zero, which is what makes this route handle
    a rank-deficient ``A`` where the other two fail.
    """
    # TODO: With A = U diag(S) V^T, x = V diag(1/S) U^T b, taking 1/S = 0 for singular values at or below tol * S[0].
    raise NotImplementedError("svd_least_squares")


# ---------------------------------------------------------------------------
# Step 5: the residual and the condition number
# ---------------------------------------------------------------------------

def residual_norm(A, b, x):
    """The Euclidean norm of the residual ``A x - b``."""
    # TODO: Return ||A x - b||_2: form the residual vector, then its Euclidean norm.
    raise NotImplementedError("residual_norm")


def condition_number(A):
    """The 2-norm condition number: largest over smallest singular value.

    The ratio of the diagonal entries of ``A`` is *not* the condition number --
    diagonal entries are basis-dependent and can be all equal while ``A`` is
    nearly singular -- so this reads the singular values from the module's SVD.
    An exactly singular ``A`` returns ``inf``.
    """
    # TODO: Take the largest over the smallest singular value from the SVD; not the ratio of the diagonal entries.
    raise NotImplementedError("condition_number")


# ---------------------------------------------------------------------------
# Step 6: the exact rational reference
# ---------------------------------------------------------------------------

def exact_least_squares(A, b):
    """The true least-squares minimiser in exact rational arithmetic.

    ``A`` and ``b`` are integer or rational; every operation is a
    ``fractions.Fraction``, so the normal equations are solved with no round-off
    and the result is the exact minimiser. This is the high-precision reference
    the floating-point routes are measured against. Returns Fractions.
    """
    # TODO: Convert A and b to Fraction, solve A^T A x = A^T b exactly, and return Fractions.
    raise NotImplementedError("exact_least_squares")


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def _hilbert(m, n):
    """The m x n Hilbert matrix ``H[i][j] = 1 / (i + j + 1)`` as floats.

    Its singular values decay geometrically, so it is the classic ill-conditioned
    test matrix; a tall version keeps a genuine least-squares residual.
    """
    return [[1.0 / (i + j + 1) for j in range(n)] for i in range(m)]


def _rel_err(a, b):
    """Relative error between two solution vectors (``b`` the reference)."""
    num = math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(len(b))))
    den = math.sqrt(sum(b[i] ** 2 for i in range(len(b))))
    return num / den if den > 0.0 else num


def demo():
    """Print one measurement per claim this module makes."""
    print("Householder QR and the three least-squares routes — measurements")

    A_well = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
    b_well = [1.0, 1.0, 1.0]

    # Householder Q orthogonality on a well- and an ill-conditioned A.
    for label, A in (("well-conditioned", A_well),
                     ("Hilbert 7", _hilbert(7, 7))):
        Q, R = householder_qr(A)
        gram = _matmul(_transpose(Q), Q)
        err_orth = max(abs(gram[i][j] - (1.0 if i == j else 0.0))
                       for i in range(len(gram)) for j in range(len(gram)))
        recon = _matmul(Q, R)
        err_recon = max(abs(recon[i][j] - A[i][j])
                        for i in range(len(A)) for j in range(len(A[0])))
        print(f"  {label:16s} Q^T Q - I max = {err_orth:.3e}"
              f"   max|A - Q R| = {err_recon:.3e}")

    # The three methods agree on a well-conditioned problem.
    x_ne = normal_equations(A_well, b_well)
    x_qr = qr_least_squares(A_well, b_well)
    x_svd = svd_least_squares(A_well, b_well)
    print(f"  well-conditioned: max|normal - qr| = "
          f"{max(abs(x_ne[i]-x_qr[i]) for i in range(2)):.3e}"
          f"   max|svd - qr| = "
          f"{max(abs(x_svd[i]-x_qr[i]) for i in range(2)):.3e}")

    # The exact Fraction reference agrees with QR.
    A_int = [[1, 2], [3, 4], [5, 6]]
    b_int = [1, 1, 1]
    x_exact = exact_least_squares(A_int, b_int)
    err_exact = max(abs(float(x_exact[i]) - x_qr[i]) for i in range(2))
    print(f"  exact Fraction reference vs QR: max error = {err_exact:.3e}")

    # The limit case: normal equations lose about twice as many digits as QR.
    m, n = 7, 6
    Ah = _hilbert(m, n)
    bh = [1.0 / (i + 1) for i in range(m)]
    Ahi = [[Fraction(1, i + j + 1) for j in range(n)] for i in range(m)]
    bhi = [Fraction(1, i + 1) for i in range(m)]
    x_ref = [float(t) for t in exact_least_squares(Ahi, bhi)]
    e_ne = _rel_err(normal_equations(Ah, bh), x_ref)
    e_qr = _rel_err(qr_least_squares(Ah, bh), x_ref)
    print(f"  Hilbert {m}x{n}: condition number = {condition_number(Ah):.3e}")
    print(f"    normal-equations error = {e_ne:.3e}"
          f"   QR error = {e_qr:.3e}   ratio = {e_ne/e_qr:.3e}")

    # The residual is (near-)minimal: A^T (A x - b) ~ 0.
    r = [b_well[i] - sum(A_well[i][j] * x_qr[j] for j in range(2))
         for i in range(3)]
    grads = [sum(A_well[i][j] * r[i] for i in range(3)) for j in range(2)]
    print(f"  residual optimality: max|A^T (A x - b)| = "
          f"{max(abs(g) for g in grads):.3e}   residual norm = "
          f"{residual_norm(A_well, b_well, x_qr):.3e}")


if __name__ == "__main__":
    demo()
