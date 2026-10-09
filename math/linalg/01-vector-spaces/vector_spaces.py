"""Vector spaces and linear maps from scratch: bases, rank-nullity, change of basis.

Implements *Linear Algebra Done Right* (Sheldon Axler), chapters 1-3, restated:

- ch. 1-2: vector spaces, span, linear independence, bases and dimension. Once a basis
  is fixed, every vector of the space *is* its coordinate vector, and the running example
  is P_n, the polynomials of degree at most n. In the monomial basis 1, x, ..., x^n a
  polynomial is exactly a list of n+1 rationals. This module never manipulates
  polynomials as symbolic objects; it manipulates those coordinate vectors, which is the
  point of the chapter (a basis is a choice of coordinates, nothing more).
- ch. 3: linear maps, their null spaces and their ranges. The *fundamental theorem of
  linear maps* states dim V = dim null T + dim range T for every linear map T: V -> W,
  and it is checked here on 100 random maps between spaces of different dimensions.
- the matrix of T is not intrinsic: it depends on the bases chosen. If B is a basis of V,
  C a basis of W and A is the matrix of T in the standard bases, then the matrix of T in
  the bases B and C is C^{-1} A B. With V = W and C = B = S it becomes S^{-1} A S.

Everything is exact. Matrices hold ``fractions.Fraction``, so ranks, null spaces, change
of basis and nilpotency are decided with zero floating-point error. That exactness is the
standard-library substitute for the numpy oracle this kind of module would otherwise use.

DESIGN DECISION — floating point or ``Fraction``?
A float implementation is shorter and matches what numerical libraries do, but every
accept criterion here is an *equality*: S^{-1} A S equals the returned matrix, rank
equals n minus nullity, D^{n+1} equals the zero matrix. With floats those become
threshold decisions and a bug can hide under the threshold. **Chosen: exact rational
arithmetic**, which makes each acceptance test a plain ``==``. The cost is speed and the
absence of a condition-number lesson; that belongs to the numerical modules.

DESIGN DECISION — represent a linear map how, and pass bases how?
Alternatives: (a) a callable T plus a way to feed it basis vectors, (b) the matrix of T
in the standard bases plus each basis as a list of *coordinate* vectors. **Chosen: (b),
with the basis vectors passed as the columns of a matrix.** Then the whole of change of
basis is one product, ``C^{-1} A B``, and the check can verify it by pushing a vector
through B, then A, then C^{-1}. A callable would move the same product into every test
and make the bases harder to compare.

DESIGN DECISION — Gaussian elimination provided, or graded here?
``_rref`` and ``_inverse`` are left implemented, like ``_solve`` in
foundations-02-analytic-geometry. The prerequisite node foundations-01-linear-algebra
has already built them; grading them again would duplicate that module and bury the
lesson (bases, rank-nullity, change of basis) under arithmetic. The lesson starts once a
matrix can be reduced.

DESIGN DECISION — differentiation as P_n -> P_n, or P_n -> P_{n-1}?
The honest map drops the degree by one, so as a map between *different* spaces it is not
square and cannot be raised to a power. **Chosen: the same rule with codomain P_n**, i.e.
the derivative padded with a zero coordinate, giving an (n+1)x(n+1) matrix. This is the
only version on which the nilpotency limit case (D^{n+1} = 0, D^n != 0) is even a
statement about matrix powers. The cost is one convention to state: P_n is mapped into
itself and high-degree images are simply zero.

    python3 vector_spaces.py      # prints the measurements this file promises
"""

from fractions import Fraction


# ---------------------------------------------------------------------------
# Exact arithmetic helpers (the piece of foundations-01 this module stands on)
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

    Provided, not graded (foundations-01): Gaussian elimination with every pivot scaled
    to 1 and every other entry of a pivot column cleared, so the pivot columns of R are
    the standard basis vectors.
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
    """Inverse of a square matrix over Q (ValueError if singular), via _rref.

    Provided, not graded: the change-of-basis formula is the lesson, inverting a matrix
    is the prerequisite.
    """
    n = len(A)
    aug = [list(map(_F, A[i])) + _identity(n)[i] for i in range(n)]
    R, pivots = _rref(aug)
    if pivots[:n] != list(range(n)):
        raise ValueError("singular matrix has no inverse")
    return [row[n:] for row in R]


def apply(matrix, vector):
    """The image T(v): the matrix of T times the coordinate vector v. Provided."""
    return [sum((matrix[i][j] * _F(vector[j]) for j in range(len(vector))), Fraction(0))
            for i in range(len(matrix))]


# ---------------------------------------------------------------------------
# Chapter 1-2: rank, null space, range
# ---------------------------------------------------------------------------

def rank(matrix):
    """The dimension of the span of the columns of ``matrix`` (= of its rows).

    DESIGN DECISION — rank by row reduction, not by determinants of minors. The
    determinant definition (largest non-vanishing minor) is the textbook one and is
    O(n!) if read literally; RREF gives the pivot count in one pass and, over Q, exactly.
    **Chosen: the number of pivots of the RREF.**
    """
    # TODO: Reduce the matrix with _rref and return the number of pivot columns.
    raise NotImplementedError("rank")


def null_space_basis(matrix):
    """A basis of the null space {x : matrix @ x = 0}, as a list of column vectors.

    DESIGN DECISION — read the basis off the free columns of the RREF, rather than
    solving matrix @ x = 0 once per free variable. Each free column f gives one basis
    vector: a 1 in position f, and in every pivot position p the value -R[pivot_row][f].
    **Chosen: that direct read-off**, because it produces the standard basis in the free
    variables and never has to re-run elimination.
    """
    # TODO: RREF, then for each free column f build a vector with 1 at f and -R[i][f] at each pivot column pivots[i].
    raise NotImplementedError("null_space_basis")


def column_space_basis(matrix):
    """A basis of the range (the column space): the pivot columns of the matrix itself.

    Row operations preserve the *dependencies* among columns, so the pivot columns of
    the RREF tell which columns of the original matrix form a basis. Taking the columns
    of the RREF instead would be wrong: those are coordinate vectors in a reduced frame,
    not spanning vectors of the original space.
    """
    # TODO: RREF for the pivot columns, then return those columns OF THE ORIGINAL matrix (the columns are the rows of _transpose(matrix)).
    raise NotImplementedError("column_space_basis")


# ---------------------------------------------------------------------------
# Chapter 3: the matrix of a linear map and change of basis
# ---------------------------------------------------------------------------

def matrix_of_map(A, domain_basis, codomain_basis):
    """The matrix of the linear map A in the bases (domain_basis, codomain_basis).

    ``A`` is the matrix of T: V -> W in the standard bases, of shape m x n.
    ``domain_basis`` is a list of n vectors of length n (a basis of V); ``codomain_basis``
    is a list of m vectors of length m (a basis of W). The returned matrix has the
    columns as coordinates in ``codomain_basis`` of the images of the ``domain_basis``
    vectors, i.e. ``C^{-1} A B`` where B, C have the basis vectors as columns.

    DESIGN DECISION — the coordinate formula C^{-1} A B, derived once, versus building
    each column by solving. Solving C y = A b_j for every j is what the formula means and
    is a fine check, but it is O(n) eliminations. **Chosen: the single product
    C^{-1} A B**, and the checker verifies it by pushing vectors through B, A, C^{-1}.
    With V = W and codomain_basis = domain_basis = S this is S^{-1} A S.
    """
    # TODO: B = columns of domain_basis, C = columns of codomain_basis; return C^-1 A B (the inverse is first, on the left).
    raise NotImplementedError("matrix_of_map")


# ---------------------------------------------------------------------------
# The running example P_n and its differentiation map
# ---------------------------------------------------------------------------

def differentiation_matrix(n):
    """The matrix of d/dx on P_n (degree <= n) in the monomial basis 1, x, ..., x^n.

    d/dx x^k = k x^{k-1}, so column k (the image of x^k) has the single entry k in row
    k-1. The matrix is (n+1)x(n+1), strictly triangular with zero diagonal, hence
    nilpotent with index n+1.

    DESIGN DECISION — pad the derivative so the map is P_n -> P_n. The true derivative
    lands in P_{n-1}; padding with a zero coordinate is what makes D a square matrix and
    makes "D^{n+1} = 0" a matrix-power statement. **Chosen: the padded square matrix.**
    """
    # TODO: (n+1)x(n+1) zero matrix; for k = 1..n set row k-1, column k to k.
    raise NotImplementedError("differentiation_matrix")


def matrix_power(M, k):
    """M raised to the k-th power over Q, with M^0 = I (k a non-negative integer)."""
    # TODO: Repeated exact multiplication, starting from the identity for k = 0.
    raise NotImplementedError("matrix_power")


def nilpotency_index(M, max_power):
    """The least k >= 1 with M^k = 0, or None if M^k != 0 for every k <= max_power.

    DESIGN DECISION — detect nilpotency by multiplication, not by the characteristic
    polynomial. Over Q the eigenvalues are exactly the diagonal of a triangular form, and
    "all zero" would be a shorter test, but it would need a form the module does not
    build. **Chosen: form the successive powers and compare to zero**, which is O(k)
    matrix products and directly mirrors the definition D^{n+1} = 0.
    """
    # TODO: Multiply up from the identity; return the first k in 1..max_power with power == 0, else None.
    raise NotImplementedError("nilpotency_index")


def fundamental_theorem(A):
    """Return (dim V, dim null T, dim range T) for the map T: V -> W with matrix A.

    This is Axler's fundamental theorem of linear maps, dim V = dim null T + dim range T,
    reported as three numbers so the checker can verify the equality and each dimension
    independently. dim V is the number of *columns* of A (the dimension of the domain),
    dim range T is rank(A), and dim null T is the dimension of the null space.
    """
    # TODO: n = number of columns; dim null = len(null_space_basis(A)); dim range = rank(A); return (n, dim null, dim range).
    raise NotImplementedError("fundamental_theorem")


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import random

    def _show(M):
        return [[str(x) for x in row] for row in M]

    print("Vector spaces and linear maps from scratch — measurements")

    # Differentiation on P_n is nilpotent with index n+1.
    for n in (2, 4):
        D = differentiation_matrix(n)
        print(f"  d/dx on P_{n}: D^{n} nonzero = {not _is_zero(matrix_power(D, n))}"
              f"  D^{n + 1} zero = {_is_zero(matrix_power(D, n + 1))}"
              f"  nilpotency index = {nilpotency_index(D, n + 1)}")

    # P_4 as coordinate vectors: p = 3 + 2x + 5x^2 - x^4 -> p' = 2 + 10x - 4x^3.
    D = differentiation_matrix(4)
    p = [3, 2, 5, 0, -1]
    print(f"  d/dx (3 + 2x + 5x^2 - x^4) = {[int(x) for x in apply(D, p)]}"
          f"  (expected [2, 10, 0, -4, 0])")

    # Change of basis: S^{-1} A S, and how far the wrong order S A S^{-1} is.
    rng = random.Random(1)
    A = [[0, 1, 0], [0, 0, 1], [1, 0, 0]]
    while True:
        S = [[Fraction(rng.randint(-2, 2)) for _ in range(3)] for _ in range(3)]
        try:
            Sinv = _inverse(S)
            break
        except ValueError:
            continue
    basis = _transpose(S)                      # the columns of S are the new basis vectors
    M = matrix_of_map(A, basis, basis)         # S^-1 A S
    wrong = _matmul(_matmul(S, A), Sinv)       # S A S^-1, deliberately wrong
    diff = max(abs(M[i][j] - wrong[i][j]) for i in range(3) for j in range(3))
    print(f"  change of basis max|S^-1 A S - S A S^-1| = {diff}")

    # Rank-nullity on random maps between spaces of different dimension.
    held = 0
    rng = random.Random(5)
    for _ in range(100):
        ncol, nrow = rng.randint(1, 5), rng.randint(1, 5)
        if nrow == ncol:
            nrow = 6 - ncol                      # force genuinely different dimensions
        M = [[Fraction(rng.randint(-3, 3)) for _ in range(ncol)] for _ in range(nrow)]
        dim_v, nullity, range_dim = fundamental_theorem(M)
        if dim_v == nullity + range_dim:
            held += 1
    print(f"  rank-nullity dim V = dim null + dim range: {held}/100 random maps")
