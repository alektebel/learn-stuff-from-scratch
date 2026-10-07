"""The spectral theorem, polar decomposition and the SVD from scratch.

Implements the real spectral theorem and its consequences, restated from *Linear
Algebra Done Right* (Sheldon Axler), chapters 6 and 7 (`axler:6`, `axler:7`):

* every self-adjoint (real symmetric) operator on an inner product space has an
  orthonormal eigenbasis, and its eigenvalues are all real (the spectral theorem);
* a positive operator is self-adjoint with non-negative eigenvalues and has a
  positive square root;
* every operator factors as ``A = Q P`` with ``Q`` orthogonal and ``P`` positive
  semidefinite (polar decomposition);
* every operator has a singular value decomposition ``A = U Sigma V^T``, obtained
  here from the spectral theorem applied to the positive operator ``A^T A``.

Everything is written from the standard library (``math`` only) in double
precision. A single numerical engine -- the cyclic Jacobi eigenvalue algorithm for
symmetric matrices -- drives all four constructions, so the module has one thing to
get right instead of four.

DESIGN DECISION -- Jacobi rotations, not QR iteration, for symmetric matrices?
For a symmetric matrix the Jacobi method repeatedly annihilates the largest-ish
off-diagonal entry with a plane rotation; each rotation is orthogonal, so the
accumulated ``Q`` is orthonormal to working precision by construction, which is
exactly the accept criterion of this node (``Q^T Q = I`` to 1e-10). A shifted QR
iteration would need a separate symmetric (Wilkinson shift) path and a deflation
schedule, and its eigenvectors would have to be accumulated anyway. **Chosen: cyclic
Jacobi.** The cost is O(n^2) rotations per sweep and a few sweeps per spectrum; for
the small dense matrices of this node that is negligible.

DESIGN DECISION -- how is a repeated eigenvalue handled?
When an eigenvalue has multiplicity m > 1 the eigenspace is m-dimensional and *any*
orthonormal basis of it is a valid answer; the eigenbasis is simply not unique. This
module therefore never compares a computed eigenvector to a fixed expected vector,
and ``orthonormal_eigenbasis`` groups eigenvalues that agree to a tolerance and
re-orthonormalises each group's span, so the result is an orthonormal basis of the
whole eigenspace rather than an arbitrary set of columns. **Chosen: never fix a
basis; validate by ``Q^T Q = I``, ``A = Q diag(evals) Q^T`` and the eigenvalue
multiset.** The cost is that the checker must be written as an invariant test; a
cheaper "compare to the answer key" check would be wrong on every repeated
eigenvalue, which is the limit case this node exists to expose.

DESIGN DECISION -- the SVD from ``A^T A`` or from ``A A^T``?
The spectral theorem is applied to the symmetric PSD matrix ``A^T A``: its
eigenvalues are the squared singular values and its eigenvectors are the right
singular vectors ``V``. The left singular vectors are then ``u_i = A v_i / s_i``,
and the zero singular values are completed to an orthonormal basis so that ``U`` is
orthonormal even when ``A`` is rank-deficient. **Chosen: the ``A^T A`` route.** The
cost is one squaring of the condition number: tiny singular values are computed as
square roots of tiny eigenvalues and lose half their relative precision. The route
``A A^T`` has the same problem; a bidiagonal SVD would avoid it but is a different
node.

DESIGN DECISION -- which decomposition does ``polar_decomposition`` build?
The right polar decomposition ``A = Q P`` with ``Q`` orthogonal and ``P`` PSD uses
the SVD ``A = U Sigma V^T``: ``Q = U V^T`` and ``P = V Sigma V^T``. The tempting
shortcut ``Q = U``, ``P = Sigma V^T`` looks close but produces ``Q P = U Sigma V^T
= A`` with a *non-symmetric* ``P`` when written left-to-right as ``U`` times
``Sigma V^T`` -- and more importantly it is the wrong factorisation shape: it does
not isolate the rotational part ``U V^T``. **Chosen: ``Q = U V^T``, ``P = V Sigma
V^T``.** The checker verifies ``A = Q P`` *and* that ``Q`` is orthogonal *and* that
``P`` is symmetric PSD, so a swap of the two factors cannot pass.

    python3 spectral.py     # prints the measurements this file promises
"""

import math


# ---------------------------------------------------------------------------
# Small dense arithmetic helpers (provided; they are plumbing, not the lesson)
# ---------------------------------------------------------------------------

def _identity(n):
    """The n x n identity as floats."""
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _transpose(A):
    """Transpose: rows become columns."""
    return [list(row) for row in zip(*A)] if A else []


def _matmul(A, B):
    """Matrix product in double precision."""
    n, k, m = len(A), len(B), len(B[0])
    return [[sum(A[i][t] * B[t][j] for t in range(k)) for j in range(m)]
            for i in range(n)]


def _matvec(A, v):
    """Matrix-vector product in double precision."""
    return [sum(A[i][j] * v[j] for j in range(len(v))) for i in range(len(A))]


def _dot(u, v):
    """Inner product of two equal-length vectors."""
    return sum(a * b for a, b in zip(u, v))


def _norm(v):
    """Euclidean norm of a vector."""
    return math.sqrt(sum(x * x for x in v))


def _gram_schmidt(vectors, n):
    """Orthonormalise a list of length-n vectors (modified Gram-Schmidt).

    Returns one vector per input. Used to rebuild an orthonormal basis of an
    eigenspace from a set of spanning vectors, which is what makes the module
    independent of *which* basis the eigensolver happens to return.
    """
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
    """A unit vector in R^m orthogonal to every vector in ``used``.

    Tries the standard basis in order and Gram-Schmidt's each candidate against
    ``used``. Raises ``ValueError`` when ``used`` already spans R^m (no complement
    exists), which can only happen if the caller asked for too many columns.
    """
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
# Step 1-2: the symmetric eigendecomposition (cyclic Jacobi)
# ---------------------------------------------------------------------------

def jacobi_eigh(A):
    """Eigenvalues (ascending) and an orthonormal eigenbasis of symmetric ``A``.

    Returns ``(evals, Q)`` with ``evals`` a list of length n sorted ascending and
    ``Q`` an n x n matrix whose columns are orthonormal eigenvectors, so that
    ``A = Q diag(evals) Q^T``.

    Cyclic Jacobi: each sweep visits every off-diagonal pair ``(p, q)`` in turn and
    applies the plane rotation that annihilates ``A[p][q]``. The same rotation
    accumulates into ``Q``, so the columns of ``Q`` stay orthonormal to working
    precision. The sweep loop stops when the off-diagonal mass is negligible
    relative to the size of the matrix.

    DESIGN DECISION -- a fixed rotation formula and a cyclic sweep, not a
    largest-element pivot. Cyclic is deterministic and has a known quadratic
    convergence; the pivot search costs more than it saves on small matrices and
    makes the iterates harder to reason about. **Chosen: cyclic.**
    """
    # TODO: Cyclic Jacobi on the symmetric A: sweep the pairs p<q, zero A[p][q] with the rotation tau=(A[q][q]-A[p][p])/(2 A[p][q]), t=sign(tau)/(|tau|+sqrt(1+tau^2)), c=1/sqrt(1+t^2), s=t c; apply the same rotation to A (M<-MJ then M<-J^T M) and accumulate it into Q (Q<-QJ). Return (eigenvalues ascending, Q) so that A = Q diag(evals) Q^T.
    raise NotImplementedError("jacobi_eigh")


def orthonormal_eigenbasis(A, tol=1e-10):
    """``(evals ascending, Q)`` with the columns of ``Q`` an orthonormal basis.

    Same contract as :func:`jacobi_eigh`, plus one thing that only matters at a
    repeated eigenvalue: eigenvalues that agree within ``tol`` are grouped and the
    span of their columns is re-orthonormalised. So the returned basis is a valid
    orthonormal basis of each eigenspace even when that eigenspace has dimension
    greater than one.

    DESIGN DECISION -- group and re-orthonormalise, rather than trust the columns
    as they come. On a repeated eigenvalue the choice of eigenvectors is not
    unique, so a valid answer is a *subspace*, not a list of vectors. Grouping by ``tol`` makes
    the function's contract "an orthonormal basis of each eigenspace", which is
    what the checker can actually verify without fixing a basis. **Chosen: group +
    Gram-Schmidt.** The cost is that the split between two nearby but *distinct*
    eigenvalues is a tolerance call; ``tol=1e-10`` is far below the separation the
    node's matrices ever need.
    """
    # TODO: (evals ascending, Q) as jacobi_eigh, but when eigenvalues agree within tol, re-orthonormalise the span of their columns so the answer is an orthonormal basis of each eigenspace. Never fix which basis: any orthonormal basis of the eigenspace is valid.
    raise NotImplementedError("orthonormal_eigenbasis")


def is_orthogonal(Q, tol=1e-10):
    """True iff the columns of ``Q`` are orthonormal (``Q^T Q = I``).

    For a square matrix this is the usual ``Q Q^T = I``; the column-oriented form
    also covers the rectangular ``U`` of an SVD. The tolerance is absolute in the
    entries of the Gram matrix.
    """
    # TODO: True iff the columns are orthonormal: for every pair (i, j), the dot product of column i and column j of Q is 1 when i==j and 0 otherwise, within tol. This covers the rectangular U of an SVD too.
    raise NotImplementedError("is_orthogonal")


# ---------------------------------------------------------------------------
# Step 4: positive operators and their square roots
# ---------------------------------------------------------------------------

def positive_sqrt(A, tol=1e-10):
    """The positive semidefinite square root of a symmetric PSD matrix ``A``.

    By the spectral theorem ``A = Q diag(evals) Q^T`` with ``evals >= 0``; the
    square root is ``Q diag(sqrt(evals)) Q^T``, which is itself symmetric PSD and
    squares back to ``A``. An eigenvalue below ``-tol`` means ``A`` is not PSD and
    raises ``ValueError`` rather than returning a complex or absolute-valued lie.

    DESIGN DECISION -- clamp round-off, reject a genuine negative. A true PSD
    matrix can have an eigenvalue at ``-1e-16`` from round-off; clamping that to
    zero is honest. A negative eigenvalue of size ``-1e-2`` is a real property of
    the matrix and must raise. **Chosen: threshold at ``-tol``.** The cost is a
    tolerance call at the boundary, which is unavoidable in floating point.
    """
    # TODO: Symmetric PSD square root via A = Q diag(evals) Q^T: return Q diag(sqrt(evals)) Q^T, clamping a round-off eigenvalue to 0 but RAISING ValueError for a genuinely negative eigenvalue. Returns a symmetric PSD matrix whose square is A.
    raise NotImplementedError("positive_sqrt")


# ---------------------------------------------------------------------------
# Step 6: the singular value decomposition (from A^T A)
# ---------------------------------------------------------------------------

def svd(A):
    """Return ``(U, S, Vt)`` with ``A = U diag(S) V^T``.

    ``A`` is m x n with ``m >= n``. ``S`` holds the singular values in descending
    order, ``Vt`` is the transpose of the n x n orthogonal matrix of right singular
    vectors, and ``U`` is m x n with orthonormal columns. Singular values are the
    square roots of the eigenvalues of ``A^T A``; the left singular vectors are
    ``A v_i / s_i``, and the zero singular values are completed to an orthonormal
    basis.

    DESIGN DECISION -- complete the basis for a zero singular value instead of
    dividing by (near) zero. ``A v / 0`` is the classic way a rank-deficient SVD
    produces ``NaN``. **Chosen: when ``s_i`` is below the tolerance, take the next
    standard basis vector orthogonal to the columns already chosen.** The cost is
    that ``U`` for a rank-deficient ``A`` is not unique -- exactly as the limit case
    of the node says -- so the checker verifies the factorisation, not the vectors.
    """
    # TODO: Return (U, S, Vt) with A = U diag(S) V^T, S descending. From the spectral theorem applied to A^T A: its eigenvalues are the squared singular values and its eigenvectors are V; the left singular vectors are A v / s, and a zero singular value is COMPLETED to an orthonormal basis instead of dividing by zero.
    raise NotImplementedError("svd")


# ---------------------------------------------------------------------------
# Step 5: the polar decomposition
# ---------------------------------------------------------------------------

def polar_decomposition(A, tol=1e-10):
    """Return ``(Q, P)`` with ``A = Q P``, ``Q`` orthogonal, ``P`` symmetric PSD.

    Uses the SVD ``A = U diag(S) V^T``: ``Q = U V^T`` is orthogonal and ``P = V
    diag(S) V^T`` is symmetric PSD, and ``Q P = U diag(S) V^T = A``. This is the
    matrix analogue of writing a complex number as ``z = e^{i theta} |z|``.
    """
    # TODO: Return (Q, P) with A = Q P, Q orthogonal and P symmetric PSD, from the SVD A = U diag(S) V^T: Q = U V^T and P = V diag(S) V^T. Do not use Q = U.
    raise NotImplementedError("polar_decomposition")


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo():
    """Print one measurement per construction this module promises."""
    print("The spectral theorem, polar decomposition and SVD — measurements")

    A = [[2.0, 1.0], [1.0, 2.0]]
    evals, Q = orthonormal_eigenbasis(A)
    print(f"  symmetric [[2,1],[1,2]]: eigenvalues {[round(e, 6) for e in evals]}"
          f"  (expected [1, 3])")
    print(f"    Q orthogonal = {is_orthogonal(Q)}")

    R = [[3.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    s = 1.0 / math.sqrt(2.0)
    rot = [[s, -s, 0.0], [s, s, 0.0], [0.0, 0.0, 1.0]]
    rotated = _matmul(_matmul(rot, R), _transpose(rot))
    evals_r, Qr = orthonormal_eigenbasis(rotated)
    print(f"  rotated diag(3,1,1): eigenvalues {[round(e, 6) for e in evals_r]}"
          f"  Q orthogonal = {is_orthogonal(Qr)} (basis-independent)")

    P_psd = [[4.0, 2.0], [2.0, 3.0]]
    root = positive_sqrt(P_psd)
    print(f"  positive_sqrt([[4,2],[2,3]]) squared residual = "
          f"{max(abs(_matmul(root, root)[i][j] - P_psd[i][j]) for i in range(2) for j in range(2)):.3e}")

    M = [[3.0, 1.0], [1.0, 2.0]]
    Qp, Pp = polar_decomposition(M)
    resid = max(abs(_matmul(Qp, Pp)[i][j] - M[i][j]) for i in range(2) for j in range(2))
    print(f"  polar [[3,1],[1,2]]: Q orthogonal = {is_orthogonal(Qp)}, "
          f"max|A - Q P| = {resid:.3e}")

    U, S, Vt = svd([[3.0, 0.0], [0.0, 2.0]])
    print(f"  svd diag(3,2): S = {[round(x, 6) for x in S]} descending = "
          f"{all(S[i] >= S[i + 1] for i in range(len(S) - 1))}, "
          f"U orthogonal = {is_orthogonal(U)}, V orthogonal = {is_orthogonal(Vt)}")

    rank1 = [[1.0, 1.0], [1.0, 1.0]]
    U1, S1, Vt1 = svd(rank1)
    print(f"  svd rank-1 [[1,1],[1,1]]: S = {[round(x, 6) for x in S1]}, "
          f"U orthogonal = {is_orthogonal(U1)} (zero singular value completed)")


if __name__ == "__main__":
    demo()
