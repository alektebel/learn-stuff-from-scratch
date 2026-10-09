"""Matrix decompositions from scratch: Cholesky, power iteration, SVD.

Implements *Mathematics for Machine Learning* (Deisenroth, Faisal & Ong), chapter 4:
matrix decompositions and their use. Three mechanisms are built, in the order the
chapter depends on them:

* the **Cholesky decomposition** ``A = L Lᵀ`` for a symmetric positive definite matrix,
  which is the cheap, stable factorisation every covariance matrix admits;
* **power iteration with deflation** for the dominant eigenpairs of a symmetric matrix,
  which is how an eigendecomposition is computed when you only need the top few;
* the **SVD** ``A = U Σ Vᵀ`` from the eigendecomposition of ``AᵀA``, and the rank-k
  approximation it gives.

The theme of the chapter, and of this module: **the useful decompositions are the ones
whose factors are orthonormal or triangular**, and the price of getting them is
conditioning. Forming ``AᵀA`` is the standard way to get an SVD and the standard way to
square the condition number; the module makes you build it and then measure the damage.

    python3 decompositions.py      # prints the measurements this file promises
"""

import math

_EPS = 1e-12


class NotPositiveDefinite(Exception):
    """The matrix has no Cholesky factor: not symmetric, or a pivot is not positive."""


class NoConvergence(Exception):
    """Power iteration did not settle on an eigenvector (no unique dominant eigenvalue)."""


# ---------------------------------------------------------------------------
# Small helpers — provided, not part of the exercise.
# ---------------------------------------------------------------------------

def _dot(u, v):
    return sum(a * b for a, b in zip(u, v))


def _matvec(A, v):
    return [sum(A[i][j] * v[j] for j in range(len(v))) for i in range(len(A))]


def _matmul(A, B):
    return [[sum(A[i][t] * B[t][j] for t in range(len(B)))
             for j in range(len(B[0]))] for i in range(len(A))]


def _transpose(A):
    return [list(row) for row in zip(*A)]


def _norm(v):
    return math.sqrt(_dot(v, v))


def _normalize(v):
    n = _norm(v)
    if n == 0.0:
        raise ValueError("cannot normalise the zero vector")
    return [x / n for x in v]


def _start_vector(n, seed=20261007):
    """A deterministic, non-degenerate starting vector (a small LCG, no RNG state)."""
    v = []
    x = seed
    for _ in range(n):
        x = (1103515245 * x + 12345) % (2 ** 31)
        v.append(x / 2 ** 31 - 0.5)
    return v


# ---------------------------------------------------------------------------
# 1. Cholesky
# ---------------------------------------------------------------------------

def cholesky(A):
    """The Cholesky factor L of a symmetric positive definite matrix A = L Lᵀ.

    L is lower triangular with a strictly positive diagonal. This is the SPD test and
    the factorisation at once: the pivot on the diagonal is the squared length of the
    new direction, so ``pivot <= 0`` means some direction has no positive length and
    the matrix is not positive definite.

    Raises NotPositiveDefinite (never returns a NaN factor) when A is not square, is
    not symmetric, or has a non-positive pivot.

    DESIGN DECISION — test first, or factor and check the pivots as we go?
    Testing symmetry and positive definiteness separately duplicates the arithmetic and
    can disagree with the factorisation at the tolerance boundary. **Chosen: one pass
    that raises on the first bad pivot**, so "has a Cholesky factor" and "is SPD" are
    the same predicate, exactly as the SPD test in foundations-02.
    """
    # TODO: One pass over i >= j: s = A[i][j] − Σ_{k<j} L[i][k]L[j][k]. On the diagonal s is the squared pivot — raise NotPositiveDefinite if s <= 0, else L[i][i] = sqrt(s). Off-diagonal, L[i][j] = s / L[j][j]. Check squareness and symmetry first, so a non-SPD matrix raises instead of reaching math.sqrt with a negative.
    raise NotImplementedError("cholesky")


# ---------------------------------------------------------------------------
# 2. Power iteration and deflation
# ---------------------------------------------------------------------------

def power_iteration(A, iters=1000, tol=1e-7, start=None):
    """The dominant eigenpair (lambda, v) of a symmetric matrix A.

    Repeatedly multiplies a vector by A and normalises. When one eigenvalue is strictly
    larger in magnitude than all others, the direction converges to that eigenvector and
    the Rayleigh quotient ``vᵀAv`` converges to the eigenvalue.

    Raises NoConvergence when the iteration does not settle: the classic failure is two
    eigenvalues of *equal magnitude* (for example +1 and -1), where the vector oscillates
    and no eigenvector is singled out. A small change in the Rayleigh quotient is not
    enough to accept — the residual ``‖Av − λv‖`` is what decides, because the quotient
    can stand still while the vector alternates.

    DESIGN DECISION — what convergence test?
    A step-size test on ``λ`` alone accepts the oscillating ±λ case (λ is constant while v
    flips). **Chosen: a residual test at the end**, ``‖Av − λv‖ ≤ tol·max(1,|λ|)``, which
    is exactly the defining equation A v = λ v. The cost is one extra matrix-vector product.
    """
    # TODO: Normalise the start vector, then repeat: w = A·v, v = w/‖w‖, λ = vᵀAv. AFTER the loop, test the true residual ‖Av − λv‖ ≤ 1e-7·max(1,|λ|); if it is too large raise NoConvergence — a convergence test on λ alone accepts the +1/−1 oscillation where λ is constant but v flips.
    raise NotImplementedError("power_iteration")


def eigenpairs_symmetric(A, k):
    """The k largest-magnitude eigenpairs of a symmetric matrix, by power iteration + deflation.

    After the dominant pair ``(λ, v)`` is found, subtract ``λ v vᵀ`` from the working
    matrix. The deflated matrix has the same eigenvectors with ``λ`` replaced by 0, so its
    dominant pair is the next one. The eigenvector ``v`` is unchanged (it is an eigenvector
    with eigenvalue 0 of the deflated matrix).

    Returns a list of ``(lambda, v)`` in non-increasing |λ|, length exactly k.

    DESIGN DECISION — deflate by ``λ v vᵀ``, or re-orthogonalise the start vector?
    Re-orthogonalising is simpler to state but only works while the next eigenvalue is real
    and the running vectors stay independent; it accumulates error in the previous vectors.
    **Chosen: explicit deflation of the matrix**, which is the textbook construction and
    makes each subsequent dominant eigenpair a property of *this* matrix. Its cost is the
    ``O(n²)`` subtraction per pair — negligible for the small k it is meant for, and the
    reason a full spectrum uses QR iteration instead.
    """
    # TODO: Loop exactly k times: find (λ, v) with power_iteration on the working matrix M, append it, then deflate M ← M − λ v vᵀ. The subtracted matrix has the same eigenvectors with this λ replaced by 0, so the next dominant pair is the next eigenpair. Return list length k.
    raise NotImplementedError("eigenpairs_symmetric")


# ---------------------------------------------------------------------------
# 3. SVD from the eigendecomposition of AᵀA, and low-rank approximation
# ---------------------------------------------------------------------------

def svd_via_ata(A):
    """A thin SVD ``A = U Σ Vᵀ`` computed from the eigendecomposition of ``AᵀA``.

    ``AᵀA`` is symmetric positive semi-definite with eigenvalues ``σ_i²`` and eigenvectors
    ``v_i`` (the right singular vectors); the left singular vectors are ``u_i = A v_i / σ_i``.
    Returns ``(U, S, V)`` as lists of *columns*: ``U`` has one length-m vector per singular
    value, ``V`` one length-n orthonormal vector, ``S`` the singular values in decreasing
    order. Singular values that are numerically zero contribute a zero ``U`` column and a
    zero term, so the identity ``A = Σ σ_i u_i v_iᵀ`` still holds exactly for the pieces kept.

    DESIGN DECISION — eigendecompose ``AᵀA`` (n×n) or ``A Aᵀ`` (m×m)?
    ``A Aᵀ`` gives the left singular vectors directly and is cheaper for a tall matrix, but
    then the right vectors need a second solve and the zero singular values (for a
    rank-deficient or wide A) are the ones you must reconstruct by hand. **Chosen: ``AᵀA``**,
    because the right singular vectors — the ones the low-rank approximation keeps — come
    out directly, and the reconstruction formula is the one to be checked. The price is the
    squared condition number, which this module exists to expose.
    """
    # TODO: gram = AᵀA; its eigenvalues are σ² and its eigenvectors are the right singular vectors V. Use eigenpairs_symmetric(gram, n), sort by eigenvalue descending, σ = sqrt(max(λ,0)), and u = A·v/σ (zero column if σ is 0). Return (U, S, V) as lists of COLUMNS; A = Σ σ_i u_i v_iᵀ.
    raise NotImplementedError("svd_via_ata")


def low_rank_approx(A, k):
    """The best rank-k approximation of A in the spectral norm: keep the top k SVD terms.

    ``A_k = Σ_{i=1}^{k} σ_i u_i v_iᵀ``. By Eckart-Young it is the minimiser of
    ``‖A − B‖₂`` over all rank-k B, and the minimum equals the next singular value
    ``σ_{k+1}``. That equality is what the checker measures.

    DESIGN DECISION — accept a rank, or an error budget?
    An error budget (``keep σ_i > tol``) is what a numerical library exposes, but it makes
    the Eckart-Young identity awkward to state and the result dependent on the tolerance.
    **Chosen: an explicit rank k**, so ``k`` is exactly the number of terms and the check
    can compare the residual to the single value ``σ_{k+1}``.
    """
    # TODO: Compute the SVD, then sum the first k outer products: A_k = Σ_{t<k} S[t]·U[t]⊗V[t]. The number of terms is exactly k; the residual spectral norm is then σ_{k+1} (Eckart-Young).
    raise NotImplementedError("low_rank_approx")


if __name__ == "__main__":
    # A symmetric matrix with eigenvalues 5, 2, -1 (dominant 5).
    S = [[3.0, 1.0, 0.5], [1.0, 2.0, 0.25], [0.5, 0.25, 0.0]]

    # An SPD matrix for Cholesky (integer factor, so also checkable exactly).
    A = [[4.0, 12.0, -16.0], [12.0, 37.0, -43.0], [-16.0, -43.0, 98.0]]
    L = cholesky(A)
    rec = _matmul(L, _transpose(L))
    chol_err = max(abs(rec[i][j] - A[i][j]) for i in range(3) for j in range(3))

    pairs = eigenpairs_symmetric(S, 3)
    eig_res = max(_norm([_matvec(S, v)[i] - lam * v[i] for i in range(3)])
                  for lam, v in pairs)

    # A with known singular values, and the rank-2 approximation error (should be σ₃).
    U0 = [[1.0, 0.0, 0.0], [0.0, 0.6, 0.8], [0.0, 0.8, -0.6]]
    V0 = [[0.8, 0.6, 0.0], [-0.6, 0.8, 0.0], [0.0, 0.0, 1.0]]
    sig = [4.0, 2.0, 0.5]
    M = [[sum(sig[t] * U0[i][t] * V0[j][t] for t in range(3)) for j in range(3)]
         for i in range(3)]
    M2 = low_rank_approx(M, 2)
    eck = math.sqrt(sum((M[i][j] - M2[i][j]) ** 2 for i in range(3) for j in range(3)))

    # The condition-number loss: A with singular values 1 and 1e-10.
    theta, phi = 0.7, 1.1
    c1, s1, c2, s2 = math.cos(theta), math.sin(theta), math.cos(phi), math.sin(phi)
    D = [[c1, -s1], [s1, c1]]
    P = [[c2, -s2], [s2, c2]]
    scale = [1.0, 1e-7]
    _, Sgood, _ = svd_via_ata(M)
    ill = [[sum(D[i][t] * scale[t] * P[j][t] for t in range(2)) for j in range(2)]
           for i in range(2)]
    _, Sick, _ = svd_via_ata(ill)

    print("Matrix decompositions from scratch — measurements")
    print(f"  cholesky   max|A − LLᵀ| = {chol_err:.1e}   diagonal = "
          f"[{L[0][0]:.4f}, {L[1][1]:.4f}, {L[2][2]:.4f}]")
    print(f"  eigen      k = {len(pairs)}, eigenvalues = "
          f"[{', '.join(f'{lam:+.6f}' for lam, _ in pairs)}]")
    print(f"  eigen      max ‖Av − λv‖ = {eig_res:.2e}")
    print(f"  svd        σ = [{', '.join(f'{s:.6f}' for s in Sgood)}]   (known [4, 2, 0.5])")
    print(f"  eckart-you ‖M − M₂‖ = {eck:.6e}   (σ₃ = {sig[2]})")
    print(f"  condition  true σ₂ = 1e-07, Gram-SVD σ₂ = {Sick[-1]:.6e}"
          f"   (relative error {abs(Sick[-1] - 1e-7) / 1e-7:.2e})")
