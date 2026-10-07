"""Analytic geometry from scratch: inner products, projections, rotations, Gram-Schmidt.

Implements *Mathematics for Machine Learning* (Deisenroth, Faisal & Ong), chapter 3:
inner products and norms, orthogonal projections onto subspaces and affine subspaces,
Gram-Schmidt orthonormalisation, and rotation matrices in 2-D and 3-D.

The theme of the chapter is that geometry is what the inner product says it is. Change
the inner product (a symmetric positive definite matrix A) and distances, angles and
projections change with it. The module therefore builds every operation on top of one
inner product and refuses to run when the matrix does not define one.

DESIGN DECISION — one inner product, or a plain dot product plus variants?
Writing ``norm`` and ``angle`` with ordinary dot products is simpler and covers the
Euclidean case, which is most of practice. **Chosen: everything takes the SPD matrix A**,
because the whole point of the chapter is that the standard dot product is the special
case ``A = I``; a separate Euclidean code path would hide that and double the surface.

DESIGN DECISION — projection via the normal equations, or via an orthonormal basis?
An orthonormal basis Q gives ``P = Q Qᵀ`` in one multiplication, but it needs
Gram-Schmidt first and it fails silently if the basis is not actually orthonormal.
**Chosen: the textbook formula ``P = B (BᵀB)⁻¹ Bᵀ``**, which needs only a solve (from
foundations-01) and makes the dependence on ``BᵀB`` explicit. Gram-Schmidt is then a
separate tool with its own checks, not a hidden dependency of projection.

DESIGN DECISION — classical or modified Gram-Schmidt?
They are algebraically identical and numerically different: modified uses the already
updated vector in each inner product, classical uses the original. **Chosen: implement
both, selected by a flag.** They are the same function on well-conditioned input and
measurably different on nearly dependent vectors, and that gap is the lesson.

DESIGN DECISION — what counts as "not an inner product"?
A non-symmetric matrix, an indefinite one, or a singular one. **Chosen: a symmetric
matrix is accepted as an inner product only if its Cholesky factorisation exists with a
strictly positive diagonal**, reusing the positive-diagonal test rather than checking
leading principal minors (same criterion, one pass).

    python3 geometry.py      # prints the measurements this file promises
"""

import math

_EPS = 1e-12


class NotPositiveDefinite(Exception):
    """The matrix does not define an inner product (not symmetric, or not positive definite)."""


def _dot(u, v):
    return sum(a * b for a, b in zip(u, v))


def _matmul(A, B):
    return [[sum(A[i][t] * B[t][j] for t in range(len(B)))
             for j in range(len(B[0]))] for i in range(len(A))]


def _transpose(A):
    return [list(row) for row in zip(*A)]


def _identity(n):
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _solve(A, rhs_list):
    """Solve A x = b for several right-hand sides at once, by Gaussian elimination.

    This one function is the piece of foundations-01 (linear systems) that this module
    stands on; it is provided, not part of the lesson. Raises ValueError if A is
    singular, which for a projection means the spanning vectors are dependent.
    """
    n = len(A)
    width = n + len(rhs_list)
    M = [list(A[i]) + [rhs_list[c][i] for c in range(len(rhs_list))] for i in range(n)]
    scale = max(1.0, max(abs(v) for row in M for v in row))
    for col in range(n):
        p = max(range(col, n), key=lambda i: abs(M[i][col]))
        if abs(M[p][col]) <= 1e-12 * scale:
            raise ValueError("singular system: the spanning vectors are linearly dependent")
        M[col], M[p] = M[p], M[col]
        pv = M[col][col]
        M[col] = [v / pv for v in M[col]]
        for i in range(n):
            if i != col:
                f = M[i][col]
                if f:
                    M[i] = [a - f * b for a, b in zip(M[i], M[col])]
    return [[M[i][n + c] for i in range(n)] for c in range(len(rhs_list))]


def is_symmetric(A):
    """True if A is square and A[i][j] == A[j][i] (relative tolerance 1e-12)."""
    n = len(A)
    if any(len(row) != n for row in A):
        return False
    scale = max(1.0, max(abs(v) for row in A for v in row))
    return all(abs(A[i][j] - A[j][i]) <= _EPS * scale for i in range(n) for j in range(n))


def is_spd(A):
    """True if A is symmetric and positive definite, decided by Cholesky.

    A symmetric matrix is positive definite exactly when it has a Cholesky
    factorisation A = L Lᵀ with a strictly positive diagonal. The pivot s on the
    diagonal is the squared length of the new basis direction; if it is not positive,
    some direction has non-positive "length" and this is not an inner product.
    """
    if not is_symmetric(A):
        return False
    n = len(A)
    L = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = A[i][j] - sum(L[i][k] * L[j][k] for k in range(j))
            if i == j:
                if s <= 0.0:
                    return False
                L[i][i] = math.sqrt(s)
            else:
                L[i][j] = s / L[j][j]
    return True


def inner(A, u, v):
    """The inner product <u, v>_A = uᵀ A v induced by the SPD matrix A."""
    if not is_spd(A):
        raise NotPositiveDefinite("A is not symmetric positive definite")
    Av = [sum(A[i][j] * v[j] for j in range(len(v))) for i in range(len(A))]
    return _dot(u, Av)


def norm(A, u):
    """The norm induced by A: the square root of <u, u>_A."""
    return math.sqrt(inner(A, u, u))


def angle(A, u, v):
    """The angle between u and v under A, in radians, in [0, pi]."""
    denom = norm(A, u) * norm(A, v)
    if denom == 0.0:
        raise ValueError("angle is undefined for a zero vector")
    cos = inner(A, u, v) / denom
    return math.acos(max(-1.0, min(1.0, cos)))


def projection_matrix(B):
    """The orthogonal projection matrix onto span(B).

    B is a list of spanning vectors in R^m (linearly independent). Returns the m×m
    matrix P = B (BᵀB)⁻¹ Bᵀ, where B here means the matrix whose columns are the
    vectors. P is symmetric and idempotent: P² = P and Pᵀ = P.
    """
    k = len(B)
    m = len(B[0]) if k else 0
    G = [[_dot(B[t], B[s]) for s in range(k)] for t in range(k)]        # BᵀB
    rhs = [[B[t][j] for t in range(k)] for j in range(m)]              # rows of Bᵀ
    Y = _solve(G, rhs)                                                 # Y = (BᵀB)⁻¹Bᵀ
    return [[sum(B[t][i] * Y[j][t] for t in range(k)) for j in range(m)]
            for i in range(m)]


def project(B, x):
    """The orthogonal projection of x onto the linear subspace span(B)."""
    P = projection_matrix(B)
    return [sum(P[i][j] * x[j] for j in range(len(x))) for i in range(len(P))]


def affine_project(B, x0, x):
    """The orthogonal projection of x onto the affine subspace x0 + span(B)."""
    P = projection_matrix(B)
    d = [x[i] - x0[i] for i in range(len(x0))]
    return [x0[i] + sum(P[i][j] * d[j] for j in range(len(d))) for i in range(len(x0))]


def gram_schmidt(vectors, modified=False):
    """An orthonormal basis for span(vectors), by classical or modified Gram-Schmidt.

    Classical computes every coefficient against the original vector; modified uses the
    partially reduced vector, which keeps the arithmetic well-conditioned. They agree on
    well-conditioned input and diverge on nearly dependent vectors (see the demo).
    A vector that is (numerically) dependent on the previous ones contributes nothing
    and is skipped.
    """
    basis = []
    for v in vectors:
        w = list(v)
        for q in basis:
            r = _dot(w if modified else v, q)
            w = [w[i] - r * q[i] for i in range(len(w))]
        nrm = math.sqrt(_dot(w, w))
        if nrm > 1e-12 * (math.sqrt(_dot(v, v)) or 1.0):
            basis.append([x / nrm for x in w])
    return basis


def rotation_2d(theta):
    """The 2-D rotation matrix by angle theta (counter-clockwise)."""
    c, s = math.cos(theta), math.sin(theta)
    return [[c, -s], [s, c]]


def rotation_3d(axis, theta):
    """The 3-D rotation matrix by theta about the line spanned by `axis` (Rodrigues).

    R = I + sin(theta) K + (1 - cos(theta)) K², where K is the skew-symmetric matrix of
    the unit axis, so that K v = axis × v. The result is a proper rotation: orthogonal
    with determinant +1.
    """
    nrm = math.sqrt(_dot(axis, axis))
    if nrm <= 0.0:
        raise ValueError("axis must be non-zero")
    x, y, z = (a / nrm for a in axis)
    c, s = math.cos(theta), math.sin(theta)
    K = [[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]]
    K2 = _matmul(K, K)
    return [[(1.0 if i == j else 0.0) + s * K[i][j] + (1 - c) * K2[i][j]
             for j in range(3)] for i in range(3)]


if __name__ == "__main__":
    def _maxabs(M):
        return max(abs(v) for row in M for v in row)

    def _norm_cols(Q):
        k = len(Q)
        worst = 0.0
        for a in range(k):
            for b in range(k):
                got = _dot(Q[a], Q[b])
                worst = max(worst, abs(got - (1.0 if a == b else 0.0)))
        return worst

    A = [[2.0, 1.0], [1.0, 2.0]]
    deg = math.degrees(angle(A, [1.0, 0.0], [0.0, 1.0]))

    B = [[1.0, 1.0, 0.0], [1.0, 0.0, 1.0]]
    P = projection_matrix(B)
    P2 = _matmul(P, P)
    x = [2.0, -1.0, 4.0]
    r = [x[i] - sum(P[i][j] * x[j] for j in range(3)) for i in range(3)]

    well = [[1.0, 0.5, 0.2], [0.3, 1.1, -0.4], [0.2, 0.7, 1.5]]
    Q = gram_schmidt([[well[i][j] for i in range(3)] for j in range(3)])

    eps = 1e-8
    lauchli = [[1.0, 1.0, 1.0], [eps, 0.0, 0.0], [0.0, eps, 0.0], [0.0, 0.0, eps]]
    cols = [[lauchli[i][j] for i in range(4)] for j in range(3)]
    Qc = gram_schmidt(cols, modified=False)
    Qm = gram_schmidt(cols, modified=True)

    R2 = rotation_2d(0.7)
    R3 = rotation_3d([1.0, 2.0, 3.0], 1.1)
    v = [1.0, -2.0, 0.5]
    Rv = [sum(R3[i][j] * v[j] for j in range(3)) for i in range(3)]

    def _det3(M):
        return (M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1])
                - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
                + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]))

    print("Analytic geometry from scratch — measurements")
    print(f"  inner      <e₁,e₂>_A = {inner(A, [1, 0], [0, 1]):.3f}  angle = {deg:.3f}°")
    print(f"  project    max|P²−P| = {_maxabs([[P2[i][j]-P[i][j] for j in range(3)] for i in range(3)]):.2e}"
          f"  max|P−Pᵀ| = {_maxabs([[P[i][j]-P[j][i] for j in range(3)] for i in range(3)]):.2e}"
          f"  max|Bᵀr| = {max(abs(_dot(B[t], r)) for t in range(2)):.2e}")
    print(f"  gram-schm  max|QᵀQ−I| = {_norm_cols(Q):.2e}")
    print(f"  CGS vs MGS max|QᵀQ−I| = {_norm_cols(Qc):.2e}  vs  {_norm_cols(Qm):.2e}")
    print(f"  rotations  det R₂ = {R2[0][0]*R2[1][1]-R2[0][1]*R2[1][0]:.6f}"
          f"  det R₃ = {_det3(R3):.6f}"
          f"  |R₃v|−|v| = {math.sqrt(_dot(Rv, Rv)) - math.sqrt(_dot(v, v)):.1e}")
