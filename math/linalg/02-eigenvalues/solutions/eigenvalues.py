"""Eigenvalues, eigenvectors and diagonalisability from scratch.

Implements *Linear Algebra Done Right* (Sheldon Axler), chapter 5, restated: an
eigenvalue of T is a scalar ``lambda`` for which ``T - lambda I`` is not injective, an
eigenvector is a nonzero vector killed by ``T - lambda I``, and the eigenvectors of
distinct eigenvalues are linearly independent. The module builds two roads to the
spectrum and puts them next to each other:

* an **exact** road, over ``fractions.Fraction``: the characteristic polynomial by
  Faddeev-LeVerrier, its rational roots by the rational root theorem, eigenspaces as
  null spaces of ``A - lambda I``, and diagonalisability as the accept criterion of the
  node -- *a matrix is diagonalisable iff it has n independent eigenvectors*, i.e. the
  geometric multiplicities of its eigenvalues sum to n;
* a **numerical** road in double precision: a Householder QR decomposition and a
  shifted QR eigensolver, written here rather than imported, so the limit cases of the
  node can be measured at all.

Axler proves diagonalisability *without* the characteristic polynomial (chapter 8's
trace and determinant are deliberately late in the book). The exact road below does use
it, because over Q it is checkable arithmetic and makes every acceptance test an
exact equality; the check compares the polynomial against an independent determinant
expansion, so a sign error cannot hide.

DESIGN DECISION — exact rational arithmetic first, numerical second?
Over Q the whole eigen-story is decidable exactly for rational spectra: eigenvalues are
rational roots of a rational polynomial, eigenspaces are null spaces, and "n independent
eigenvectors" is a rank comparison. Floats would turn all of those into tolerance calls
and let the planted bugs of this module hide. **Chosen: exact Fractions for the
qualitative questions (roots, eigenspaces, diagonalisability, diagonalisation), and
floats only where the node asks for a numerical eigensolver and its conditioning
lesson.** The cost is that a matrix with an irrational or complex spectrum has no exact
diagonalisability report; the numerical eigensolver still computes its spectrum. A
matrix with rational entries but irrational eigenvalues is out of scope for the exact
road and raises ``ValueError``.

DESIGN DECISION — how is the characteristic polynomial computed?
Alternatives: (a) the definition, det(x I - A), by cofactor expansion -- O(n!) and
symbolic; (b) interpolation of det(t I - A) at n+1 integer points -- n+1 exact
determinants plus a Vandermonde solve; (c) Faddeev-LeVerrier, a recurrence on the
traces. **Chosen: Faddeev-LeVerrier**, which forms the coefficients in O(n^4) exact
rational operations and never builds a symbolic matrix. The checker does not trust it:
it recomputes det(x I - A) by cofactor expansion for n <= 4 and compares coefficients,
so a wrong sign is not a matter of taste.

DESIGN DECISION — diagonalisable, decided how?
Counting *distinct* eigenvalues is wrong: the identity has one distinct eigenvalue and
is diagonalisable, while a Jordan block has one distinct eigenvalue and is not.
Counting algebraic multiplicities is also wrong: they always sum to n, so a Jordan
block would pass. **Chosen: sum the dimensions of the eigenspaces (the geometric
multiplicities) and compare to n.** That is exactly Axler's criterion, and it is the
only count that separates the identity from the Jordan block.

DESIGN DECISION — QR by Householder or by Gram-Schmidt?
Classical Gram-Schmidt loses orthogonality quickly and modified Gram-Schmidt is better
but still needs reorthogonalisation for ill-conditioned input. Householder reflectors
are orthogonal to working precision by construction, and the checker can assert
``Q^T Q = I`` to 1e-12 on every decomposition. **Chosen: Householder**, with the
eigensolver reducing to Hessenberg form first and then running the shifted QR iteration
with the Wilkinson shift, deflating one eigenvalue at a time.

DESIGN DECISION — how does the Wilkinson limit case get measured?
The polynomial route forms the coefficients and then finds roots; the matrix route runs
QR on the companion matrix without ever forming the coefficients. To keep the
comparison deterministic and honest, the root finder here is the textbook naive one --
Newton's method with forward deflation -- and the experiment reports the largest root
error of each route. The cost of the choice is one fragility: a *better* root finder
would narrow the gap, but the module's point is that the coefficient route is the
fragile one, and Newton-with-deflation makes that visible.

    python3 eigenvalues.py      # prints the measurements this file promises
"""

import cmath
import math
from fractions import Fraction


# ---------------------------------------------------------------------------
# Exact arithmetic helpers (the piece of linalg-01 this module stands on)
# ---------------------------------------------------------------------------

def _F(x):
    """Coerce a number to Fraction, exactly."""
    return x if isinstance(x, Fraction) else Fraction(x)


def _matmul(A, B):
    """Matrix product over Q."""
    n, k, m = len(A), len(B), len(B[0])
    return [[sum((A[i][t] * B[t][j] for t in range(k)), Fraction(0))
             for j in range(m)] for i in range(n)]


def _transpose(A):
    """Transpose (rows become columns)."""
    return [list(row) for row in zip(*A)]


def _identity(n):
    """The n x n identity over Q."""
    return [[Fraction(1) if i == j else Fraction(0) for j in range(n)] for i in range(n)]


def _is_zero(A):
    """True if every entry is exactly zero."""
    return all(x == 0 for row in A for x in row)


def _columns_to_matrix(vectors):
    """Stack the given vectors as the columns of a matrix."""
    if not vectors:
        return []
    return [[_F(v[i]) for v in vectors] for i in range(len(vectors[0]))]


def _rref(matrix):
    """Reduced row echelon form over Q. Returns (R, pivot_columns).

    Provided, not graded (linalg-01): Gaussian elimination with every pivot scaled to 1
    and every other entry of a pivot column cleared.
    """
    R = [[_F(x) for x in row] for row in matrix]
    rows = len(R)
    cols = len(R[0]) if rows else 0
    pivots = []
    r = 0
    for c in range(cols):
        pivot_row = None
        for i in range(r, rows):
            if R[i][c] != 0:
                pivot_row = i
                break
        if pivot_row is None:
            continue
        R[r], R[pivot_row] = R[pivot_row], R[r]
        lead = R[r][c]
        R[r] = [x / lead for x in R[r]]
        for i in range(rows):
            if i != r and R[i][c] != 0:
                f = R[i][c]
                R[i] = [a - f * b for a, b in zip(R[i], R[r])]
        pivots.append(c)
        r += 1
        if r == rows:
            break
    return R, pivots


def _inverse(A):
    """Inverse of a square matrix over Q (ValueError if singular), via _rref."""
    n = len(A)
    aug = [list(map(_F, A[i])) + _identity(n)[i] for i in range(n)]
    R, pivots = _rref(aug)
    if pivots[:n] != list(range(n)):
        raise ValueError("singular matrix has no inverse")
    return [row[n:] for row in R]


def _null_space_basis(matrix):
    """A basis of {x : matrix @ x = 0}, read off the free columns of the RREF.

    Provided, not graded (linalg-01). Each free column f gives one basis vector: a 1 in
    position f, and -R[i][f] at each pivot position.
    """
    if not matrix or not matrix[0]:
        return []
    R, pivots = _rref(matrix)
    cols = len(R[0])
    free = [c for c in range(cols) if c not in pivots]
    basis = []
    for f in free:
        v = [Fraction(0)] * cols
        v[f] = Fraction(1)
        for i, p in enumerate(pivots):
            v[p] = -R[i][f]
        basis.append(v)
    return basis


# ---------------------------------------------------------------------------
# Exact polynomial helpers (provided; the graded step is the recurrence)
# ---------------------------------------------------------------------------

def _integer_divisors(m):
    """The positive divisors of |m| as a sorted list (m != 0)."""
    m = abs(int(m))
    if m == 0:
        return [0]
    out = set()
    i = 1
    while i * i <= m:
        if m % i == 0:
            out.add(i)
            out.add(m // i)
        i += 1
    return sorted(out)


def _clear_denominators(coeffs):
    """Scale a rational polynomial to primitive integer coefficients."""
    den = 1
    for x in coeffs:
        den = den * x.denominator // math.gcd(den, x.denominator)
    return [int(x * den) for x in coeffs]


def _poly_eval_exact(coeffs, x):
    """Evaluate a coefficient list (high -> low) with exact arithmetic."""
    result = Fraction(0)
    for a in coeffs:
        result = result * x + a
    return result


def _synthetic_divide(coeffs, root):
    """Divide the polynomial (high -> low) by (x - root); return the quotient."""
    out = [Fraction(coeffs[0])]
    for k in range(1, len(coeffs)):
        out.append(Fraction(coeffs[k]) + root * out[-1])
    return out[:-1]


# ---------------------------------------------------------------------------
# Numerical helpers (provided; the graded steps are qr_decompose/qr_eigenvalues)
# ---------------------------------------------------------------------------

def _identity_float(n):
    """The n x n identity as floats."""
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _matmul_float(A, B):
    """Matrix product in double precision."""
    n, k, m = len(A), len(B), len(B[0])
    return [[sum(A[i][t] * B[t][j] for t in range(k)) for j in range(m)] for i in range(n)]


def _poly_eval_complex(coeffs, x):
    """Evaluate a coefficient list (high -> low) at a complex number."""
    result = 0j
    for a in coeffs:
        result = result * x + a
    return result


def _poly_derivative_complex(coeffs):
    """The derivative of a coefficient list (high -> low), as a coefficient list."""
    n = len(coeffs) - 1
    return [coeffs[i] * (n - i) for i in range(n)]


def hessenberg(A):
    """Reduce A to upper Hessenberg form by an orthogonal similarity (provided).

    H = Q^T A Q with Q orthogonal, H[i][j] = 0 for i > j + 1. The QR eigensolver below
    assumes this form; reducing first keeps each QR step O(m^2) of the active block's
    off-diagonal instead of touching the whole matrix.
    """
    n = len(A)
    H = [list(map(float, row)) for row in A]
    for k in range(n - 2):
        x = [H[i][k] for i in range(k + 1, n)]
        nrm = math.sqrt(sum(v * v for v in x))
        if nrm == 0.0:
            continue
        alpha = -math.copysign(nrm, x[0])
        v = x[:]
        v[0] -= alpha
        vn = math.sqrt(sum(t * t for t in v))
        if vn == 0.0:
            continue
        v = [t / vn for t in v]
        for j in range(n):
            s = sum(v[i] * H[k + 1 + i][j] for i in range(len(v)))
            for i in range(len(v)):
                H[k + 1 + i][j] -= 2.0 * v[i] * s
        for i in range(n):
            s = sum(H[i][k + 1 + j] * v[j] for j in range(len(v)))
            for j in range(len(v)):
                H[i][k + 1 + j] -= 2.0 * v[j] * s
    return H


# ---------------------------------------------------------------------------
# Step 1: the characteristic polynomial, exactly
# ---------------------------------------------------------------------------

def characteristic_polynomial(A):
    """The coefficients of det(x I - A), high to low, monic, as Fractions.

    Returns ``[1, a_1, ..., a_n]`` for ``x^n + a_1 x^{n-1} + ... + a_n``.

    DESIGN DECISION — Faddeev-LeVerrier, not cofactor expansion or interpolation. The
    recurrence ``M_k = A M_{k-1} + a_{k-1} I``, ``a_k = -(1/k) tr(A M_k)`` costs O(n^4)
    exact operations and is easy to grade; cofactor expansion is O(n!) and interpolation
    needs a Vandermonde solve. **Chosen: Faddeev-LeVerrier.** The checker recomputes
    det(x I - A) by cofactor expansion for small n, so the recurrence is not
    self-certifying.
    """
    n = len(A)
    if n == 0:
        return [Fraction(1)]
    M = [[Fraction(0)] * n for _ in range(n)]          # M_0 = 0
    coeffs = [Fraction(1)]                             # a_0 = 1
    for k in range(1, n + 1):
        AM = _matmul(A, M)
        M = [[AM[i][j] + (coeffs[k - 1] if i == j else Fraction(0))
              for j in range(n)] for i in range(n)]    # M_k = A M_{k-1} + a_{k-1} I
        trace = sum((A[i][t] * M[t][i] for i in range(n) for t in range(n)), Fraction(0))
        coeffs.append(-trace / k)                      # a_k = -(1/k) tr(A M_k)
    return coeffs


def evaluate_polynomial(coeffs, x):
    """Horner evaluation of a coefficient list (high -> low) at ``x``.

    Works unchanged for Fractions, floats and complex numbers, which is why the
    checker can reuse it to probe the coefficients the recurrence produced.
    """
    result = 0
    for a in coeffs:
        result = result * x + a
    return result


# ---------------------------------------------------------------------------
# Step 2-3: exact eigenvalues and eigenspaces
# ---------------------------------------------------------------------------

def rational_roots(coeffs):
    """All rational roots of a rational polynomial, with multiplicity, sorted.

    DESIGN DECISION — rational root theorem plus synthetic division, not a numerical
    scan. A rational root p/q of an integer polynomial has p dividing the constant term
    and q dividing the leading coefficient, so the candidate set is finite and exact;
    each hit is divided out to collect its multiplicity. **Chosen: this.** A numeric
    root finder would make the exact road depend on tolerances.
    """
    coeffs = [_F(x) for x in coeffs]
    while len(coeffs) > 1 and coeffs[0] == 0:
        coeffs.pop(0)
    if len(coeffs) <= 1:
        return []
    roots = []
    poly = coeffs
    while len(poly) > 1:
        poly = [Fraction(x) for x in _clear_denominators(poly)]
        if poly[-1] == 0:                              # a factor of x
            roots.append(Fraction(0))
            poly = poly[:-1]
            continue
        lead, const = poly[0], poly[-1]
        found = False
        candidates = sorted({Fraction(s * p, q)
                             for p in _integer_divisors(const)
                             for q in _integer_divisors(lead)
                             for s in (1, -1)})
        for cand in candidates:
            if _poly_eval_exact(poly, cand) == 0:
                poly = _synthetic_divide(poly, cand)
                roots.append(cand)
                found = True
                break
        if not found:
            break                                      # remaining factor is irrational
    return sorted(roots)


def eigenvalues_exact(A):
    """The eigenvalues of A, with algebraic multiplicity, exactly (rational spectra).

    DESIGN DECISION — ``lambda`` is a root of the characteristic polynomial, so the
    exact spectrum is exactly the rational roots of that polynomial. **Chosen:
    ``rational_roots(characteristic_polynomial(A))``.** Eigenvectors are *not* used to
    discover eigenvalues (that would be circular); they are used only to test
    diagonalisability, which is a separate question.
    """
    return rational_roots(characteristic_polynomial(A))


def eigenspace_basis(A, eigenvalue):
    """A basis of the eigenspace of ``eigenvalue``: the null space of ``A - lambda I``.

    DESIGN DECISION — reuse the exact null space of linalg-01 instead of solving
    ``A v = lambda v`` afresh. The definition of an eigenvector *is* a nonzero vector in
    that null space, so the geometric multiplicity is exactly the dimension of the null
    space. **Chosen: ``_null_space_basis(A - lambda I)``.**
    """
    n = len(A)
    lam = _F(eigenvalue)
    shifted = [[_F(A[i][j]) - (lam if i == j else Fraction(0)) for j in range(n)]
               for i in range(n)]
    return _null_space_basis(shifted)


# ---------------------------------------------------------------------------
# Step 4-5: diagonalisability and diagonalisation (the accept criterion)
# ---------------------------------------------------------------------------

def is_diagonalizable(A):
    """True iff A has n independent eigenvectors, exactly (rational spectra).

    This is the accept criterion of the node. The number of independent eigenvectors is
    the sum of the geometric multiplicities, i.e. the dimension of each eigenspace; A is
    diagonalisable iff that sum is n.

    DESIGN DECISION — geometry, not distinctness and not algebra. Distinct *eigenvalues*
    undercount: the identity is diagonalisable with a single distinct eigenvalue.
    Algebraic multiplicities overcount: they sum to n even for a Jordan block. **Chosen:
    sum the eigenspace dimensions and compare to n.** A rational spectrum is required,
    so a non-rational one raises ``ValueError`` rather than guessing.
    """
    n = len(A)
    if n == 0:
        return True
    spectrum = eigenvalues_exact(A)
    if len(spectrum) != n:
        raise ValueError(
            "the exact road needs a rational spectrum; this matrix has a non-rational "
            "or complex eigenvalue, use qr_eigenvalues for its numerical spectrum")
    total = 0
    for lam in sorted(set(spectrum)):
        total += len(eigenspace_basis(A, lam))
    return total == n


def diagonalize(A):
    """Return (D, P) with ``A = P D P^-1`` and D diagonal, or None if defective.

    ``P`` holds n independent eigenvectors as columns and ``D`` the matching eigenvalues.
    DESIGN DECISION — build P from the eigenspaces and refuse unless they supply n
    columns. It is tempting to fill the missing columns arbitrarily; that produces a
    non-invertible P and a fake factorisation. **Chosen: return None when the
    eigenvectors fall short**, so the caller cannot mistake a Jordan block for a
    diagonalisable matrix.
    """
    n = len(A)
    spectrum = eigenvalues_exact(A)
    if len(spectrum) != n:
        raise ValueError("the exact road needs a rational spectrum")
    columns = []
    diagonal = []
    for lam in sorted(set(spectrum)):
        for v in eigenspace_basis(A, lam):
            columns.append(v)
            diagonal.append(lam)
    if len(columns) != n:
        return None
    P = _columns_to_matrix(columns)
    D = [[Fraction(0)] * n for _ in range(n)]
    for i in range(n):
        D[i][i] = diagonal[i]
    return D, P


# ---------------------------------------------------------------------------
# Step 6-7: the numerical eigensolver
# ---------------------------------------------------------------------------

def qr_decompose(A):
    """Householder QR: return (Q, R) with ``A = Q R``, Q orthogonal, R upper triangular.

    DESIGN DECISION — Householder reflectors, not Gram-Schmidt. Each reflector is
    orthogonal to working precision, so Q stays orthogonal even for ill-conditioned A;
    classical Gram-Schmidt would need reorthogonalisation and the checker's ``Q^T Q = I``
    test would be the thing that fails. **Chosen: Householder.**
    """
    n = len(A)
    R = [[float(x) for x in row] for row in A]
    Q = _identity_float(n)
    for k in range(n - 1):
        x = [R[i][k] for i in range(k, n)]
        nrm = math.sqrt(sum(v * v for v in x))
        if nrm == 0.0:
            continue
        alpha = -math.copysign(nrm, x[0])
        v = x[:]
        v[0] -= alpha
        vn = math.sqrt(sum(t * t for t in v))
        if vn == 0.0:
            continue
        v = [t / vn for t in v]
        for j in range(n):
            s = sum(v[i] * R[k + i][j] for i in range(len(v)))
            for i in range(len(v)):
                R[k + i][j] -= 2.0 * v[i] * s
        for j in range(n):
            s = sum(Q[j][k + i] * v[i] for i in range(len(v)))
            for i in range(len(v)):
                Q[j][k + i] -= 2.0 * v[i] * s
    return Q, R


def qr_eigenvalues(A):
    """The eigenvalues of A by the shifted QR algorithm (floats, complex allowed).

    Reduces to Hessenberg form with ``hessenberg``, then runs the QR iteration with the
    Wilkinson shift on the active leading block, deflating one eigenvalue at a time.
    A trailing 2x2 block is solved in closed form, which is where a complex-conjugate
    pair is produced.

    DESIGN DECISION — Wilkinson shift and Hessenberg reduction, not the plain unshifted
    iteration. Unshifted QR converges only linearly and can stall on a real matrix with a
    complex pair; the Wilkinson shift accelerates the real simple case and the closed
    form 2x2 handles the pair. **Chosen: Hessenberg + Wilkinson shift + 2x2 close.** The
    remaining cost is that the iteration is written for small dense matrices, which is
    all this node needs.
    """
    n = len(A)
    if n == 0:
        return []
    H = hessenberg([[float(x) for x in row] for row in A])
    eigs = []
    m = n
    iterations = 0
    max_iter = 5000
    tol = 1e-14
    while m > 1 and iterations < max_iter:
        if m == 2:
            a, b, c, d = H[0][0], H[0][1], H[1][0], H[1][1]
            trace, det = a + d, a * d - b * c
            disc = trace * trace - 4.0 * det
            if disc >= 0.0:
                s = math.sqrt(disc)
                eigs.append((trace + s) / 2.0)
                eigs.append((trace - s) / 2.0)
            else:
                s = math.sqrt(-disc)
                eigs.append(complex(trace / 2.0, s / 2.0))
                eigs.append(complex(trace / 2.0, -s / 2.0))
            m = 0
            break
        if abs(H[m - 1][m - 2]) <= tol * (abs(H[m - 2][m - 2]) + abs(H[m - 1][m - 1]) + 1e-300):
            eigs.append(H[m - 1][m - 1])
            m -= 1
            continue
        a, b, c, d = H[m - 2][m - 2], H[m - 2][m - 1], H[m - 1][m - 2], H[m - 1][m - 1]
        trace, det = a + d, a * d - b * c
        disc = trace * trace - 4.0 * det
        if disc >= 0.0:
            s = math.sqrt(disc)
            s1, s2 = (trace + s) / 2.0, (trace - s) / 2.0
            mu = s1 if abs(s1 - d) < abs(s2 - d) else s2
        else:
            mu = d
        for i in range(m):
            H[i][i] -= mu
        sub = [row[:m] for row in H[:m]]
        Q, R = qr_decompose(sub)
        updated = _matmul_float(R, Q)
        for i in range(m):
            for j in range(m):
                H[i][j] = updated[i][j]
        for i in range(m):
            H[i][i] += mu
        iterations += 1
    if m == 1:
        eigs.append(H[0][0])
    return sorted(eigs, key=lambda z: (z.real, z.imag))


# ---------------------------------------------------------------------------
# Step 8-9: Wilkinson's polynomial and the conditioning limit case
# ---------------------------------------------------------------------------

def wilkinson_polynomial(n):
    """The coefficients of ``W_n(x) = (x - 1)(x - 2) ... (x - n)``, exact, high to low.

    This is Wilkinson's polynomial. Its roots 1, 2, ..., n are simple but severely
    ill-conditioned with respect to the coefficients: a perturbation of a middle
    coefficient by a relative machine epsilon can move a root by O(1). That is the
    subject of the two limit cases below.
    """
    coeffs = [Fraction(1)]
    for k in range(1, n + 1):
        expanded = [Fraction(0)] * (len(coeffs) + 1)
        for i, a in enumerate(coeffs):
            expanded[i] += a
            expanded[i + 1] -= k * a
        coeffs = expanded
    return coeffs


def companion_matrix(coeffs):
    """The companion matrix of a monic polynomial (floats), whose eigenvalues are its roots.

    ``coeffs`` is high to low and monic. The matrix has 1s on the subdiagonal and the
    negated coefficients (except the leading 1) down the last column. DESIGN DECISION —
    the standard companion form, so the checker can read the structure directly and so
    the characteristic polynomial of the integer version is exactly ``coeffs``.
    """
    c = [float(x) / float(coeffs[0]) for x in coeffs]
    n = len(c) - 1
    A = [[0.0] * n for _ in range(n)]
    for i in range(1, n):
        A[i][i - 1] = 1.0
    for i in range(n):
        A[i][n - 1] = -c[n - i]
    return A


def roots_newton_deflation(coeffs):
    """Find all roots of a polynomial by Newton's method with forward deflation.

    Roots are peeled from the highest index down: each Newton iteration runs on the
    current (deflated) polynomial, then the found root is divided out. This is the
    textbook *naive* coefficient route. DESIGN DECISION — deflate in decreasing order and
    start near the true integer root ``k + 0.1i``. That is deliberately the fragile
    version whose error the limit case measures; a better simultaneous iteration would
    narrow the gap the module exists to show. **Chosen: Newton + forward deflation.**
    """
    coeffs = [complex(x) for x in coeffs]
    n = len(coeffs) - 1
    roots = []
    for k in range(n, 0, -1):
        x = complex(k, 0.1)
        for _ in range(200):
            p = _poly_eval_complex(coeffs, x)
            dp = _poly_eval_complex(_poly_derivative_complex(coeffs), x)
            if dp == 0:
                break
            step = p / dp
            x -= step
            if abs(step) <= 1e-14 * (abs(x) + 1e-300):
                break
        roots.append(x)
        quotient = [coeffs[0]]
        for i in range(1, len(coeffs)):
            quotient.append(coeffs[i] + x * quotient[-1])
        coeffs = quotient[:-1]
    return roots


def wilkinson_experiment(n=20):
    """Compare the two roads on Wilkinson's polynomial; return (poly_error, qr_error).

    ``poly_error``: largest distance of a root found by ``roots_newton_deflation`` from
    the true root set {1, ..., n}. ``qr_error``: largest distance of an eigenvalue from
    ``qr_eigenvalues(companion_matrix(coeffs))``. Both errors are measured by nearest
    match, so complex drift is not hidden.

    DESIGN DECISION — measure both routes and report both numbers, rather than assert a
    conclusion inside the function. The checker decides whether the polynomial route is
    the unstable one; the function only produces the evidence.
    """
    coeffs = wilkinson_polynomial(n)
    truth = [complex(k) for k in range(1, n + 1)]
    roots = roots_newton_deflation(coeffs)
    poly_error = max(min(abs(r - t) for r in roots) for t in truth)
    numerical = qr_eigenvalues(companion_matrix(coeffs))
    qr_error = max(min(abs(complex(z) - t) for z in numerical) for t in truth)
    return float(poly_error), float(qr_error)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    def _show(M):
        return [[str(x) for x in row] for row in M]

    print("Eigenvalues, eigenvectors and diagonalisability — measurements")

    A = [[2, 1], [0, 2]]
    print(f"  characteristic polynomial of {A}: {[str(c) for c in characteristic_polynomial(A)]}"
          f"  (expected ['1', '-4', '4'])")
    print(f"  eigenvalues of the Jordan block: {[str(c) for c in eigenvalues_exact(A)]}"
          f"  eigenspace dimension = {len(eigenspace_basis(A, 2))}")
    print(f"  Jordan block diagonalisable = {is_diagonalizable(A)}"
          f"   identity 2x2 diagonalisable = {is_diagonalizable([[5, 0], [0, 5]])}")

    D, P = diagonalize([[0, 1], [1, 0]])
    print(f"  [[0,1],[1,0]] = P D P^-1 with D = {_show(D)}")

    B = [[2, 1], [1, 2]]
    print(f"  QR eigenvalues of {B}: {[round(z, 10) for z in qr_eigenvalues(B)]}"
          f"  (expected [1, 3])")

    poly_error, qr_error = wilkinson_experiment(20)
    print(f"  Wilkinson W_20: Newton+deflation error = {poly_error:.3e}"
          f"  QR companion error = {qr_error:.3e}")
    print(f"  the polynomial route is {'worse' if poly_error > qr_error else 'better'}"
          f" by a factor {poly_error / max(qr_error, 1e-300):.3g}")
