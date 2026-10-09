"""Eigenvalue algorithms from scratch: reduction, Rayleigh quotient, and QR.

Implements Trefethen & Bau, *Numerical Linear Algebra*, lectures 25-29, restated:
Householder reduction to Hessenberg and (for symmetric matrices) to tridiagonal form
(lectures 25-26), Rayleigh quotient iteration and its local cubic convergence
(lecture 27), and the unshifted and Wilkinson-shifted QR algorithms (lectures 28-29).
Nothing is copied; only the ideas are restated.

The module is the numerical half of the eigen-story: given a real matrix, it reduces it
to a form where each QR step is cheap, runs shifted QR to find every eigenvalue, and
solves one eigenpair to high accuracy with Rayleigh quotient iteration. It is pure
standard library (``math`` and ``random``); there is no numpy.

ENVIRONMENT ADAPTATION (named, not silent). The skill-tree node's acceptance line reads
"eigenvalues match ``numpy.linalg.eigvalsh`` on random symmetric matrices to 1e-10".
numpy is not available in this repository, so that oracle is replaced by two independent
references inside the checker: (a) known exact spectra stated as literals for the small
symmetric matrices (e.g. ``[[2,1],[1,2]] -> [1,3]``), and (b) the checker's own
high-accuracy cyclic Jacobi solver. The 1e-10 agreement requirement is kept unchanged;
only the source of the reference changed. The checker carries its own copy of both
references, so it never asks this module what the right answer is.

    python3 eigenalg.py      # prints the measurements this file promises
"""

import math
import random


# ---------------------------------------------------------------------------
# Small vector and matrix helpers (provided; the graded steps are below)
# ---------------------------------------------------------------------------

def _identity(n):
    """The n x n identity as floats."""
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _matmul(A, B):
    """Matrix product in double precision."""
    n, k, m = len(A), len(B), len(B[0])
    return [[sum(A[i][t] * B[t][j] for t in range(k)) for j in range(m)]
            for i in range(n)]


def _transpose(A):
    """Transpose (rows become columns)."""
    return [list(row) for row in zip(*A)]


def _matvec(A, v):
    """Matrix-vector product."""
    return [sum(A[i][j] * v[j] for j in range(len(v))) for i in range(len(A))]


def _dot(u, v):
    """Euclidean inner product."""
    return sum(a * b for a, b in zip(u, v))


def _norm(v):
    """Euclidean norm."""
    return math.sqrt(sum(x * x for x in v))


def _normalize(v):
    """Unit vector in the direction of v (unchanged if v is the zero vector)."""
    nrm = _norm(v)
    return [x / nrm for x in v] if nrm else list(v)


def _qr_factor(A):
    """Householder QR factorization: return (Q, R) with A = Q R, Q orthogonal.

    Provided, not graded (it is the QR decomposition of the linalg-02 prerequisite). Each
    column is annihilated below the diagonal by a reflector H = I - 2 v v^T, built with
    the sign that avoids cancellation: v = x - alpha e_1, alpha = -sign(x_0) ||x||.
    """
    n, m = len(A), len(A[0])
    R = [list(map(float, row)) for row in A]
    Q = _identity(n)
    for k in range(min(n, m)):
        x = [R[i][k] for i in range(k, n)]
        nrm = _norm(x)
        if nrm == 0.0:
            continue
        alpha = -math.copysign(nrm, x[0])
        v = x[:]
        v[0] -= alpha
        vn = _norm(v)
        if vn == 0.0:
            continue
        v = [t / vn for t in v]
        for j in range(m):                                    # R <- H R
            s = sum(v[i] * R[k + i][j] for i in range(len(v)))
            for i in range(len(v)):
                R[k + i][j] -= 2.0 * v[i] * s
        for i in range(n):                                    # Q <- Q H
            s = sum(Q[i][k + j] * v[j] for j in range(len(v)))
            for j in range(len(v)):
                Q[i][k + j] -= 2.0 * v[j] * s
    return Q, R


def _solve(M, b):
    """Solve the real linear system ``M x = b`` by Gaussian elimination.

    Partial pivoting; a pivot that has collapsed to near zero is nudged by a tiny
    multiple of the matrix scale, which is what lets Rayleigh quotient iteration survive
    the moment when ``A - rho I`` is nearly singular -- that near-singularity is the whole
    mechanism, not a failure.
    """
    n = len(M)
    A = [list(map(float, row)) for row in M]
    x = list(map(float, b))
    scale = max((abs(A[i][j]) for i in range(n) for j in range(n)), default=1.0)
    if scale == 0.0:
        scale = 1.0
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(A[r][col]))
        if abs(A[piv][col]) < 1e-14 * scale:
            A[col][col] += 1e-13 * scale
            piv = col
        A[col], A[piv] = A[piv], A[col]
        x[col], x[piv] = x[piv], x[col]
        for r in range(col + 1, n):
            f = A[r][col] / A[col][col]
            for k in range(col, n):
                A[r][k] -= f * A[col][k]
            x[r] -= f * x[col]
    out = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = x[i] - sum(A[i][j] * out[j] for j in range(i + 1, n))
        out[i] = s / A[i][i]
    return out


def _error_exponent(errors):
    """The observed convergence exponent from a decreasing error sequence.

    For errors obeying ``e_{k+1} ~ e_k**p`` the ratio ``log e_{k+1} / log e_k`` tends to
    ``p`` as the errors shrink. Here we keep the positives and return the *last* ratio in
    the asymptotic range (the largest ``k`` with ``e_{k+1} < e_k < 1`` and ``e_k`` above
    the rounding floor), which is the estimate of the exponent itself. Used by the demo;
    the checker computes its own measurement.
    """
    e = [x for x in errors if x > 1e-12]
    ratios = []
    for k in range(len(e) - 1):
        if e[k] < 1.0 and e[k + 1] < e[k]:
            ratios.append(math.log(e[k + 1]) / math.log(e[k]))
    return ratios[-1] if ratios else float("nan")


# ---------------------------------------------------------------------------
# Step 1: orthogonal reduction to upper Hessenberg form
# ---------------------------------------------------------------------------

def hessenberg(A):
    """Reduce A to upper Hessenberg form by an orthogonal similarity: return (Q, H).

    ``H = Q^T A Q`` with ``Q`` orthogonal and ``H[i][j] = 0`` for ``i > j + 1``.

    DESIGN DECISION — reduce first, then iterate. Each QR step costs O(n^3) on a full
    matrix but O(n^2) on an upper Hessenberg matrix, because only the subdiagonal needs
    to be restored; and the reduction is a one-off O(n^3). **Chosen: Householder
    similarity to Hessenberg before the QR iteration**, exactly the order in Trefethen &
    Bau lectures 25-28. The alternative, iterating on A directly, is correct but does
    ``n`` times the work and blurs where the algorithm's structure lives.

    DESIGN DECISION — Householder reflectors, not Gram-Schmidt elimination. A reflector
    is orthogonal to working precision, so the similarity preserves the spectrum and the
    checker can test ``Q^T Q = I`` at 1e-12 and ``Q H Q^T = A`` at 1e-12. An elimination
    by elementary (non-orthogonal) matrices would preserve the spectrum in exact
    arithmetic but destroy symmetry and conditioning in floating point. **Chosen:
    Householder.** The cost is that the accumulated Q must be formed explicitly, O(n^3)
    storage and work, which is affordable at this size.
    """
    # TODO: for k in 0..n-3 build the Householder vector from column k below the subdiagonal and apply H = I - 2 v v^T on BOTH sides, H <- H_k A H_k, accumulating Q <- Q H_k.
    raise NotImplementedError("hessenberg")


# ---------------------------------------------------------------------------
# Step 2: symmetric reduction to tridiagonal form
# ---------------------------------------------------------------------------

def tridiagonalize(A):
    """Reduce symmetric A to tridiagonal form by an orthogonal similarity: (Q, T).

    ``T = Q^T A Q`` is symmetric and tridiagonal (``T[i][j] = 0`` for ``|i - j| > 1``).

    DESIGN DECISION — a dedicated symmetric reduction, not ``hessenberg`` reused. For a
    symmetric matrix an upper Hessenberg form is automatically symmetric, hence
    tridiagonal, so in exact arithmetic the two routines agree; writing the symmetric
    version separately makes the invariance explicit and lets the checker demand
    symmetry and the tridiagonal pattern of ``T`` rather than only the Hessenberg
    pattern of ``H``. **Chosen: the symmetric version**, which is the form the symmetric
    QR iteration and the Jacobi reference both want. The cost is a little duplicated
    code for a genuine structural guarantee.
    """
    # TODO: the same Householder similarity as hessenberg, but exploit symmetry: zero column k below row k+1 for k in 0..n-3, T <- H_k T H_k, re-symmetrise, and accumulate Q.
    raise NotImplementedError("tridiagonalize")


# ---------------------------------------------------------------------------
# Step 3: the unshifted and shifted QR algorithm
# ---------------------------------------------------------------------------

def _wilkinson_shift(H, m):
    """The Wilkinson shift for the trailing 2x2 block of the active m x m block.

    The eigenvalue of ``[[a, b], [c, d]]`` (the trailing block) closest to ``d``; computed
    from the stable quadratic formula ``mu = d - b^2 / (delta + sign(delta) sqrt(delta^2
    + b^2))`` with ``delta = (a - d)/2``. Provided, not graded: the graded step is that
    ``qr_algorithm`` uses it only under the ``"wilkinson"`` strategy.
    """
    a, b = H[m - 2][m - 2], H[m - 2][m - 1]
    c, d = H[m - 1][m - 2], H[m - 1][m - 1]
    delta = 0.5 * (a - d)
    if delta == 0.0 and b == 0.0:
        return d
    return d - (b * b) / (delta + math.copysign(math.sqrt(delta * delta + b * b), delta))


def qr_algorithm(A, shift="none", tol=1e-12, maxit=1000):
    """Eigenvalues of A by QR iteration; return ``(eigenvalues, iterations)``.

    ``shift`` selects the strategy: ``"none"`` for the unshifted iteration and
    ``"wilkinson"`` for the Wilkinson shift. Reduces to Hessenberg form first, then runs
    QR steps on the active leading block, deflating the trailing eigenvalue whenever the
    subdiagonal entry has fallen below ``tol`` times the local scale. The returned count
    is the number of QR sweeps actually performed.

    DESIGN DECISION — deflation with a relative test, and a hard ``maxit``. The
    subdiagonal entry is declared zero when ``|H[m-1][m-2]| <= tol (|H[m-2][m-2]| +
    |H[m-1][m-1]|)``; an absolute test would misfire on matrices of large or small norm.
    The iteration stops at ``maxit`` and reports the count, so the limit case -- the
    unshifted iteration stalling on equal-magnitude eigenvalues -- is *measured* rather
    than hidden behind a non-convergence exception. **Chosen: relative deflation and a
    counted budget.**

    DESIGN DECISION — Wilkinson shift, not the Rayleigh shift ``A[n-1][n-1]`` and not
    none. Unshifted QR converges linearly (and stalls outright when two eigenvalues have
    equal magnitude); the Rayleigh shift converges quadratically but can fail on a
    complex-conjugate pair; the Wilkinson shift is the eigenvalue of the trailing 2x2
    closest to its corner, converges cubically on real spectra, and driven with a
    closed-form trailing block also handles complex pairs. **Chosen: the Wilkinson
    shift**, and the ``"none"`` branch exists precisely so the checker can exhibit the
    stall it fixes.
    """
    # TODO: hessenberg(A) to H; while the active block has size m > 1, deflate when |H[m-1][m-2]| is below tol*scale, otherwise take the shift (0 for "none", the Wilkinson shift for "wilkinson"), do one QR step H = R Q + mu I on the active block, and count sweeps.
    raise NotImplementedError("qr_algorithm")


# ---------------------------------------------------------------------------
# Step 4: Rayleigh quotient iteration (the accept: local cubic convergence)
# ---------------------------------------------------------------------------

def rayleigh_quotient_iteration(A, v0, tol=1e-12, maxit=50):
    """One eigenpair by Rayleigh quotient iteration; return ``(lam, v, errors)``.

    ``lam`` is the Rayleigh quotient of the final unit vector ``v``, and ``errors`` is
    the sequence of ``|rho_k - lam|``, one per iteration (the last entry is therefore 0).

    Each step computes the Rayleigh quotient ``rho = v^T A v / v^T v`` and solves
    ``(A - rho I) w = v`` for the next eigenvector direction. The shift being the current
    best eigenvalue is what makes the method Newton-like on the eigenvector and cubically
    convergent on the eigenvalue.

    DESIGN DECISION — the error sequence is measured against the iteration's own final
    Rayleigh quotient. The method does not know the true eigenvalue, so it cannot report
    the true error; the converged quotient is the honest stand-in and is what makes the
    cubic rate observable without the caller handing in the answer. **Chosen: relative to
    the final quotient.** The cost is that the last entry is zero by construction and the
    checker must ignore it and the last floating-point-digit pair.

    DESIGN DECISION — solve the shifted system directly (Gaussian elimination) and accept
    its near-singularity, instead of adding a fixed regularisation. The near-singularity
    of ``A - rho I`` is exactly the amplification that produces cubic convergence; adding
    a fat regulariser would turn the method back into a linearly convergent shifted
    inverse iteration. **Chosen: a partial-pivoted solve with only a tiny scale-aware
    nudge when a pivot vanishes.** The cost is that on a multiple eigenvalue the iterate
    may pick one direction or wander between them, which is correct: a repeated eigenvalue
    has no unique eigenvector.
    """
    # TODO: rho = Rayleigh quotient of v; solve (A - rho I) w = v; renormalise w, fix its sign, record |rho_k - lam| each step, and stop on a relative change below tol.
    raise NotImplementedError("rayleigh_quotient_iteration")


# ---------------------------------------------------------------------------
# Independent high-accuracy reference (only for this file's demo)
# ---------------------------------------------------------------------------

def jacobi_reference(A, tol=1e-15, maxit=100):
    """Eigenvalues of a symmetric matrix by the cyclic Jacobi algorithm, ascending.

    The classic Jacobi method repeatedly applies plane rotations that annihilate one
    off-diagonal pair, sweeping until the off-diagonal norm is below ``tol``. It converges
    quadratically and is backward stable, so at ``tol = 1e-15`` it is a high-accuracy
    reference for the QR iteration. It is used by this file's demo only; the checker
    carries its own copy so it never trusts this one.
    """
    n = len(A)
    a = [list(map(float, row)) for row in A]
    for i in range(n):
        for j in range(i + 1, n):
            avg = 0.5 * (a[i][j] + a[j][i])
            a[i][j] = a[j][i] = avg
    for _ in range(maxit):
        off = math.sqrt(sum(a[i][j] ** 2 for i in range(n) for j in range(n) if i != j))
        if off < tol:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                if a[p][q] == 0.0:
                    continue
                theta = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
                t = math.copysign(1.0, theta) / (abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p] = c * akp - s * akq
                    a[k][q] = s * akp + c * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k] = c * apk - s * aqk
                    a[q][k] = s * apk + c * aqk
    return sorted(a[i][i] for i in range(n))


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def _random_symmetric(rng, n, lo=-9, hi=9):
    """A random symmetric integer matrix (off-diagonal entries copied)."""
    M = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i, n):
            M[i][j] = M[j][i] = float(rng.randint(lo, hi))
    return M


def _max_abs_diff(X, Y):
    return max(abs(X[i][j] - Y[i][j]) for i in range(len(X)) for j in range(len(X)))


if __name__ == "__main__":
    rng = random.Random(20261008)

    print("Eigenvalue algorithms — measurements")

    # 1. Hessenberg reduction: Q H Q^T = A and Q orthogonal.
    A = [[4.0, 1.0, -2.0, 2.0],
         [1.0, 2.0, 0.0, 1.0],
         [-2.0, 0.0, 3.0, -2.0],
         [2.0, 1.0, -2.0, -1.0]]
    Q, H = hessenberg(A)
    recon = _matmul(_matmul(Q, H), _transpose(Q))
    orth = _max_abs_diff(_matmul(_transpose(Q), Q), _identity(4))
    below = max((abs(H[i][j]) for i in range(4) for j in range(4) if i > j + 1), default=0.0)
    print(f"  hessenberg: max|Q H Q^T - A| = {_max_abs_diff(recon, A):.2e}"
          f"  max|Q^T Q - I| = {orth:.2e}  max below-subdiagonal |H| = {below:.2e}")

    # 2. Tridiagonal reduction of a symmetric matrix.
    S = _random_symmetric(rng, 6)
    Q, T = tridiagonalize(S)
    recon = _matmul(_matmul(Q, T), _transpose(Q))
    off = max((abs(T[i][j]) for i in range(6) for j in range(6) if abs(i - j) > 1), default=0.0)
    print(f"  tridiagonalize: max|Q T Q^T - A| = {_max_abs_diff(recon, S):.2e}"
          f"  max off-tridiagonal |T| = {off:.2e}")

    # 3. Shifted QR against the independent Jacobi reference, 1e-10.
    worst = 0.0
    for _ in range(25):
        n = rng.randint(3, 6)
        M = _random_symmetric(rng, n)
        got = qr_algorithm(M, "wilkinson", maxit=2000)[0]
        ref = jacobi_reference(M)
        err = max(abs(g - r) for g, r in zip(sorted(got), ref))
        worst = max(worst, err)
    print(f"  shifted QR vs Jacobi reference: worst eigenvalue error over 25 random"
          f" symmetric matrices = {worst:.2e}  (accept < 1e-10)")

    # 4. Rayleigh quotient iteration: cubic convergence from the error sequence.
    M = [[1.0, 1.0, 0.0, 0.0],
         [1.0, 2.0, 1.0, 0.0],
         [0.0, 1.0, 3.0, 1.0],
         [0.0, 0.0, 1.0, 4.0]]
    lam, vec, errors = rayleigh_quotient_iteration(M, [1.0, 1.0, 1.0, 1.0])
    ref = jacobi_reference(M)
    nearest = min(ref, key=lambda r: abs(r - lam))
    print(f"  Rayleigh quotient iteration: lambda = {lam:.15f}"
          f"  (reference {nearest:.15f}, residual {abs(lam - nearest):.2e})")
    print(f"    error sequence: {[f'{e:.2e}' for e in errors]}")
    print(f"    observed convergence exponent = {_error_exponent(errors):.2f}  (cubic is 3)")

    # 5. The limit case: unshifted QR stalls on equal-magnitude eigenvalues; Wilkinson fixes it.
    E = [[0.0, 1.0, 0.0, 0.0],
         [1.0, 0.0, 0.0, 0.0],
         [0.0, 0.0, 0.0, 2.0],
         [0.0, 0.0, 2.0, 0.0]]
    unshifted_eigs, unshifted_iters = qr_algorithm(E, "none", maxit=200)
    shifted_eigs, shifted_iters = qr_algorithm(E, "wilkinson", maxit=200)
    print(f"  equal-magnitude eigenvalues {sorted([1.0, -1.0, 2.0, -2.0])}:")
    print(f"    unshifted QR: {unshifted_iters} sweeps,"
          f" eigenvalues {[round(z, 6) for z in sorted(unshifted_eigs)]}")
    print(f"    Wilkinson QR: {shifted_iters} sweeps,"
          f" eigenvalues {[round(z, 6) for z in sorted(shifted_eigs)]}")
