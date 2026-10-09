"""
Progress checker for the eigenvalues templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

Every exact reference value is computed here, with this file's own rational arithmetic,
so the checker never asks your code what the right answer is. The characteristic
polynomial is recomputed by cofactor expansion of det(x I - A), a method independent of
the Faddeev-LeVerrier recurrence the template asks for. The numerical checks use a
tolerance, named at the assertion.
"""

import cmath
import math
import pathlib
import random
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from fractions import Fraction  # noqa: E402
from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


# ---------------------------------------------------------------------------
# This file's own exact linear algebra and polynomial arithmetic
# ---------------------------------------------------------------------------

def _F(x):
    return x if isinstance(x, Fraction) else Fraction(x)


def _matmul(A, B):
    n, k, m = len(A), len(B), len(B[0])
    return [[sum((A[i][t] * B[t][j] for t in range(k)), Fraction(0))
             for j in range(m)] for i in range(n)]


def _matvec(A, v):
    return [sum((A[i][j] * _F(v[j]) for j in range(len(v))), Fraction(0))
            for i in range(len(A))]


def _transpose(A):
    return [list(row) for row in zip(*A)]


def _columns(A):
    return [list(col) for col in zip(*A)]


def _columns_to_matrix(vectors):
    if not vectors:
        return []
    return [[_F(v[i]) for v in vectors] for i in range(len(vectors[0]))]


def _identity(n):
    return [[Fraction(1) if i == j else Fraction(0) for j in range(n)] for i in range(n)]


def _rref(matrix):
    R = [[_F(x) for x in row] for row in matrix]
    rows = len(R)
    cols = len(R[0]) if rows else 0
    pivots = []
    r = 0
    for c in range(cols):
        pr = None
        for i in range(r, rows):
            if R[i][c] != 0:
                pr = i
                break
        if pr is None:
            continue
        R[r], R[pr] = R[pr], R[r]
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


def _rank(matrix):
    if not matrix or not matrix[0]:
        return 0
    return len(_rref(matrix)[1])


def _inverse(A):
    n = len(A)
    aug = [list(map(_F, A[i])) + _identity(n)[i] for i in range(n)]
    R, pivots = _rref(aug)
    if pivots[:n] != list(range(n)):
        raise ValueError("singular matrix")
    return [row[n:] for row in R]


def _poly_add(p, q):
    n = max(len(p), len(q))
    p = [Fraction(0)] * (n - len(p)) + list(p)
    q = [Fraction(0)] * (n - len(q)) + list(q)
    return [a + b for a, b in zip(p, q)]


def _poly_sub(p, q):
    n = max(len(p), len(q))
    p = [Fraction(0)] * (n - len(p)) + list(p)
    q = [Fraction(0)] * (n - len(q)) + list(q)
    return [a - b for a, b in zip(p, q)]


def _poly_mul(p, q):
    out = [Fraction(0)] * (len(p) + len(q) - 1)
    for i, a in enumerate(p):
        for j, b in enumerate(q):
            out[i + j] += a * b
    return out


def _det_poly(M):
    """Determinant of a matrix whose entries are polynomials, by cofactor expansion."""
    n = len(M)
    if n == 0:
        return [Fraction(1)]
    if n == 1:
        return list(M[0][0])
    total = [Fraction(0)]
    for j in range(n):
        minor = [[M[i][k] for k in range(n) if k != j] for i in range(1, n)]
        term = _poly_mul(M[0][j], _det_poly(minor))
        total = _poly_add(total, term) if j % 2 == 0 else _poly_sub(total, term)
    return total


def _char_poly_reference(A):
    """det(x I - A) by cofactor expansion, independent of Faddeev-LeVerrier."""
    n = len(A)
    M = [[([Fraction(1), -_F(A[i][j])] if i == j else [-_F(A[i][j])])
          for j in range(n)] for i in range(n)]
    p = _det_poly(M)
    while len(p) > 1 and p[0] == 0:
        p.pop(0)
    return p


def _wilkinson_reference(n):
    p = [Fraction(1)]
    for k in range(1, n + 1):
        p = _poly_mul(p, [Fraction(1), Fraction(-k)])
    return p


def _close_multiset(got, expected, tol):
    """Greedy nearest-match of two multisets of numbers within a tolerance."""
    if len(got) != len(expected):
        return False
    remaining = [complex(e) for e in expected]
    for g in got:
        g = complex(g)
        best = min(range(len(remaining)), key=lambda i: abs(remaining[i] - g))
        if abs(remaining[best] - g) > tol:
            return False
        remaining.pop(best)
    return True


def _random_int_matrix(rng, n, lo=-4, hi=4):
    return [[Fraction(rng.randint(lo, hi)) for _ in range(n)] for _ in range(n)]


# ---------------------------------------------------------------------------
# Step 1: the characteristic polynomial (accept: independent cofactor reference)
# ---------------------------------------------------------------------------

def check_characteristic_polynomial() -> None:
    from eigenvalues import characteristic_polynomial

    cases = [
        ([[5]], [1, -5]),
        ([[2, 0], [0, 3]], [1, -5, 6]),
        ([[2, 1], [0, 2]], [1, -4, 4]),                     # Jordan block: (x-2)^2
        ([[0, 1], [1, 0]], [1, 0, -1]),
        ([[1, 0, 0], [0, 1, 0], [0, 0, 1]], [1, -3, 3, -1]),
        ([[1, 2, 3], [4, 5, 6], [7, 8, 10]], None),
    ]
    for A, expected in cases:
        got = characteristic_polynomial(A)
        reference = _char_poly_reference(A)
        assert [Fraction(c) for c in got] == reference, (
            f"characteristic_polynomial({A}) = {got}, but det(x I - A) = {reference}: "
            "every coefficient must match, so a wrong sign in the Faddeev-LeVerrier "
            "recurrence a_k = -(1/k) tr(A M_k) shows up here")
        assert len(got) == len(A) + 1 and got[0] == 1, (
            f"characteristic_polynomial({A}) = {got} is not monic of degree n = {len(A)}")
        if expected is not None:
            assert [Fraction(c) for c in got] == [Fraction(c) for c in expected], (
                f"characteristic_polynomial({A}) = {got}, expected {expected}")

    rng = random.Random(101)
    for _ in range(40):
        n = rng.randint(1, 4)
        A = _random_int_matrix(rng, n)
        got = [Fraction(c) for c in characteristic_polynomial(A)]
        reference = _char_poly_reference(A)
        assert got == reference, (
            f"characteristic_polynomial({A}) = {got}, expected det(x I - A) = {reference}")


# ---------------------------------------------------------------------------
# Step 2: Horner evaluation and rational roots (accept: exact factorisation)
# ---------------------------------------------------------------------------

def check_evaluation_and_rational_roots() -> None:
    from eigenvalues import evaluate_polynomial, rational_roots

    assert evaluate_polynomial([1, -3, 2], 1) == 0
    assert evaluate_polynomial([1, -3, 2], 3) == 2
    assert evaluate_polynomial([1, 0, -1], Fraction(1, 2)) == Fraction(-3, 4)

    cases = [
        ([1, -3, 2], [1, 2]),                    # (x-1)(x-2)
        ([1, -4, 4], [2, 2]),                    # (x-2)^2, multiplicity kept
        ([1, 0, 1], []),                         # irreducible over Q
        ([1, -6, 11, -6], [1, 2, 3]),            # (x-1)(x-2)(x-3)
        ([1, -4, 4, 0], [0, 2, 2]),              # x (x-2)^2, the zero root included
        ([2, -4, 2], [1, 1]),                    # non-monic: leading 2
        ([1, 0, -1], [-1, 1]),
    ]
    for coeffs, expected in cases:
        got = rational_roots(coeffs)
        assert [Fraction(r) for r in got] == [Fraction(r) for r in expected], (
            f"rational_roots({coeffs}) = {got}, expected {expected}: the rational root "
            "theorem gives candidates p/q with p | constant and q | leading coefficient")
        for r in got:
            assert evaluate_polynomial(coeffs, Fraction(r)) == 0, (
                f"rational_roots({coeffs}) returned {r}, but the polynomial does not "
                "vanish there")


# ---------------------------------------------------------------------------
# Step 3: exact eigenvalues and eigenspaces (accept: A v = lambda v, independent)
# ---------------------------------------------------------------------------

def check_eigenvalues_and_eigenspaces() -> None:
    from eigenvalues import eigenvalues_exact, eigenspace_basis

    J = [[2, 1], [0, 2]]
    assert [Fraction(x) for x in eigenvalues_exact(J)] == [Fraction(2), Fraction(2)], (
        "the eigenvalues of the Jordan block are 2 with algebraic multiplicity 2")
    basis = eigenspace_basis(J, 2)
    assert len(basis) == 1, (
        f"the eigenspace of the Jordan block is 1-dimensional, got {len(basis)}: "
        "the geometric multiplicity is dim null(A - lambda I), which is 1 here")
    for v in basis:
        assert _matvec(J, v) == [Fraction(2) * x for x in v], (
            f"{v} is in the returned basis but A v != 2 v: the eigenspace is the null "
            "space of A - lambda I, not of A + lambda I")
    assert _rank(_columns_to_matrix(basis)) == len(basis), "eigenvectors are dependent"

    I3 = _identity(3)
    assert [Fraction(x) for x in eigenvalues_exact(I3)] == [Fraction(1)] * 3
    ident_basis = eigenspace_basis(I3, 1)
    assert len(ident_basis) == 3 and _rank(_columns_to_matrix(ident_basis)) == 3, (
        "every vector is an eigenvector of the identity, so its eigenspace is 3-dimensional")

    D = [[2, 0], [0, 3]]
    assert [Fraction(x) for x in eigenvalues_exact(D)] == [Fraction(2), Fraction(3)]

    rng = random.Random(103)
    for _ in range(20):
        # a diagonalisable matrix built as S D S^-1 with rational S, integer diagonal
        n = rng.randint(1, 3)
        eigenvalues = [rng.randint(-3, 3) for _ in range(n)]
        while _rank(_random_int_matrix(rng, n)) != n:
            pass
        S = _random_int_matrix(rng, n)
        if _rank(S) != n:
            continue
        Diag = [[Fraction(eigenvalues[i]) if i == j else Fraction(0) for j in range(n)]
                for i in range(n)]
        A = _matmul(_matmul(S, Diag), _inverse(S))
        got = sorted(Fraction(x) for x in eigenvalues_exact(A))
        assert got == sorted(Fraction(e) for e in eigenvalues), (
            f"eigenvalues_exact(A) = {got}, expected {sorted(Fraction(e) for e in eigenvalues)}")


# ---------------------------------------------------------------------------
# Step 4: diagonalisability is n independent eigenvectors (accept criterion)
# ---------------------------------------------------------------------------

def check_diagonalizable() -> None:
    from eigenvalues import eigenvalues_exact, is_diagonalizable

    cases = [
        ([[5, 0], [0, 5]], True, "repeated eigenvalue, diagonalisable"),
        ([[2, 1], [0, 2]], False, "the Jordan block is defective"),
        ([[2, 0], [0, 3]], True, "distinct eigenvalues"),
        ([[0, 1], [1, 0]], True, "distinct eigenvalues -1 and 1"),
        ([[2, 1, 0], [0, 2, 1], [0, 0, 2]], False, "3x3 Jordan block"),
        ([[0, 0, 0], [0, 0, 0], [0, 0, 0]], True, "the zero matrix is diagonal (0)"),
    ]
    for A, expected, why in cases:
        got = is_diagonalizable(A)
        assert got == expected, (
            f"is_diagonalizable({A}) = {got}, expected {expected} ({why}): diagonalisable "
            "means the geometric multiplicities (eigenspace dimensions) sum to n, not that "
            "the eigenvalues are distinct and not that the algebraic multiplicities sum to n")

    # Discriminating case: the identity has ONE distinct eigenvalue but IS diagonalisable.
    # A checker that counts distinct eigenvalues would call it defective here.
    ident = [[5, 0], [0, 5]]
    assert len(set(eigenvalues_exact(ident))) < len(ident) and is_diagonalizable(ident), (
        "this suite must contain a matrix with a repeated eigenvalue that is still "
        "diagonalisable, so that counting distinct eigenvalues is distinguishable from "
        "counting independent eigenvectors")


# ---------------------------------------------------------------------------
# Step 5: diagonalisation A = P D P^-1 (accept: exact reconstruction)
# ---------------------------------------------------------------------------

def check_diagonalize() -> None:
    from eigenvalues import diagonalize

    for A, expected in [
        ([[2, 0], [0, 3]], {Fraction(2), Fraction(3)}),
        ([[5, 0], [0, 5]], {Fraction(5)}),
        ([[0, 1], [1, 0]], {Fraction(-1), Fraction(1)}),
        ([[1, 2], [2, 1]], {Fraction(-1), Fraction(3)}),
    ]:
        result = diagonalize(A)
        assert result is not None, (
            f"diagonalize({A}) returned None, but A is diagonalisable")
        D, P = result
        n = len(A)
        assert len(P) == n and all(len(row) == n for row in P), "P must be n x n"
        assert all(D[i][j] == 0 for i in range(n) for j in range(n) if i != j), (
            "D must be diagonal")
        assert {D[i][i] for i in range(n)} == expected, (
            f"the diagonal of D is {[D[i][i] for i in range(n)]}, expected the eigenvalues {expected}")
        assert _matmul(_matmul(P, D), _inverse(P)) == [[_F(x) for x in row] for row in A], (
            f"P D P^-1 != A for {A}: the columns of P must be independent eigenvectors and "
            "D the matching eigenvalues")

    assert diagonalize([[2, 1], [0, 2]]) is None, (
        "the Jordan block is defective, so diagonalize must return None rather than fill "
        "in a missing eigenvector")


# ---------------------------------------------------------------------------
# Step 6: Householder QR (accept: A = QR and Q orthogonal)
# ---------------------------------------------------------------------------

def check_qr_decomposition() -> None:
    from eigenvalues import qr_decompose

    rng = random.Random(107)
    matrices = [
        [[4.0, 3.0], [6.0, 3.0]],
        [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 10.0]],
        [[1.0, 0.5, 1.0 / 3.0], [0.5, 1.0 / 3.0, 0.25], [1.0 / 3.0, 0.25, 0.2]],
        [[float(rng.randint(-9, 9)) for _ in range(4)] for _ in range(4)],
    ]
    for A in matrices:
        n = len(A)
        Q, R = qr_decompose(A)
        product = [[sum(Q[i][t] * R[t][j] for t in range(n)) for j in range(n)] for i in range(n)]
        err = max(abs(product[i][j] - A[i][j]) for i in range(n) for j in range(n))
        assert err < 1e-9, (
            f"QR is not A: max|Q R - A| = {err:.3e}. Householder cannot skip a reflector "
            "or use the wrong sign")
        orth = max(abs(sum(Q[k][i] * Q[k][j] for k in range(n)) - (1.0 if i == j else 0.0))
                   for i in range(n) for j in range(n))
        assert orth < 1e-12, (
            f"Q is not orthogonal: max|Q^T Q - I| = {orth:.3e}; Householder reflectors "
            "are orthogonal by construction")
        tri = max(abs(R[i][j]) for i in range(n) for j in range(i))
        assert tri < 1e-12, f"R is not upper triangular: max below-diagonal entry {tri:.3e}"


# ---------------------------------------------------------------------------
# Step 7: the QR eigensolver (accept: known spectra, real and complex)
# ---------------------------------------------------------------------------

def check_qr_eigenvalues() -> None:
    from eigenvalues import qr_eigenvalues

    cases = [
        ([[1.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 3.0]], [1.0, 2.0, 3.0], 1e-9),
        ([[2.0, 1.0], [1.0, 2.0]], [1.0, 3.0], 1e-9),
        ([[2.0, 1.0], [0.0, 2.0]], [2.0, 2.0], 1e-8),
        ([[2.0, 1.0, 0.0], [1.0, 2.0, 1.0], [0.0, 1.0, 2.0]],
         [2.0 + math.sqrt(2.0), 2.0, 2.0 - math.sqrt(2.0)], 1e-8),
        ([[0.0, -1.0], [1.0, 0.0]], [1j, -1j], 1e-9),
    ]
    for A, expected, tol in cases:
        got = qr_eigenvalues(A)
        assert _close_multiset(got, expected, tol), (
            f"qr_eigenvalues({A}) = {got}, expected {expected} (tol {tol}): the iteration "
            "must run on the off-diagonal block, not just read the diagonal of A")


# ---------------------------------------------------------------------------
# Step 8: Wilkinson's polynomial and its companion matrix
# ---------------------------------------------------------------------------

def check_wilkinson_polynomial() -> None:
    from eigenvalues import companion_matrix, wilkinson_polynomial

    for n in range(1, 9):
        got = [Fraction(c) for c in wilkinson_polynomial(n)]
        reference = _wilkinson_reference(n)
        assert got == reference, (
            f"wilkinson_polynomial({n}) = {got}, expected (x-1)...(x-{n}) = {reference}: "
            "the product must run over exactly 1..n")
        assert got[0] == 1 and len(got) == n + 1

    coeffs = [Fraction(1), Fraction(-6), Fraction(11), Fraction(-6)]   # (x-1)(x-2)(x-3)
    C = companion_matrix(coeffs)
    n = len(coeffs) - 1
    assert len(C) == n and all(len(row) == n for row in C), "companion matrix must be n x n"
    for i in range(n):
        for j in range(n - 1):                      # all columns but the last
            expected_value = 1.0 if j == i - 1 else 0.0
            assert abs(C[i][j] - expected_value) < 1e-15, (
                f"companion subdiagonal wrong at ({i},{j}): {C[i][j]}")
    for i in range(n):
        assert abs(C[i][n - 1] - (-float(coeffs[n - i]) / float(coeffs[0]))) < 1e-15, (
            f"companion last column wrong at row {i}: {C[i][n - 1]}")


# ---------------------------------------------------------------------------
# Step 9: the Wilkinson limit case (root-finding versus a QR eigensolver)
# ---------------------------------------------------------------------------

def check_wilkinson_limit_case() -> None:
    from eigenvalues import wilkinson_experiment, wilkinson_polynomial

    n = 20
    exact = _wilkinson_reference(n)
    assert [Fraction(c) for c in wilkinson_polynomial(n)] == exact, (
        "the limit case needs the exact Wilkinson polynomial W_20")

    poly_error, qr_error = wilkinson_experiment(n)
    assert poly_error > 0.1, (
        f"the polynomial root finder reports an error of only {poly_error:.3e}: on "
        "Wilkinson's polynomial the coefficient route must lose accuracy, so this "
        "measurement is claiming the naive route is accurate when it is not")
    assert qr_error < 0.1, (
        f"the QR eigensolver error is {qr_error:.3e}: it works on the matrix without "
        "forming the ill-conditioned coefficients and must stay small")
    assert poly_error > 5.0 * qr_error, (
        f"the polynomial route ({poly_error:.3e}) is not clearly worse than QR "
        f"({qr_error:.3e}): the stable path is the matrix one, and the reported errors "
        "must show that (a swap of the two numbers claims the opposite)")


def check_numerical_eigenvectors() -> None:
    from eigenvalues import numerical_eigenvectors, qr_eigenvalues

    def norm(v):
        return math.sqrt(sum(abs(t) ** 2 for t in v))

    def cosangle(u, v):
        inner = sum(a.conjugate() * b for a, b in zip(u, v))
        return abs(inner) / (norm(u) * norm(v))

    # Limit case: a defective Jordan block. Its repeated eigenvalue has a
    # one-dimensional eigenspace, so the numerical eigenvectors are nearly parallel.
    J = [[2.0, 1.0], [0.0, 2.0]]
    vecs = numerical_eigenvectors(J)
    assert len(vecs) == 2, f"one vector per eigenvalue, got {len(vecs)}"
    for v, lam in zip(vecs, qr_eigenvalues(J)):
        Av = [sum(J[i][j] * v[j] for j in range(2)) for i in range(2)]
        residual = math.sqrt(sum(abs(Av[i] - lam * v[i]) ** 2 for i in range(2)))
        assert residual < 1e-6, f"numerical eigenvector residual {residual:.2e} for lambda {lam}"
    assert cosangle(vecs[0], vecs[1]) > 0.999, (
        "the two numerical eigenvectors of a defective matrix must be nearly parallel, "
        f"got cos = {cosangle(vecs[0], vecs[1]):.4f}")

    # A diagonalisable matrix with distinct eigenvalues gives orthogonal vectors instead.
    D = [[2.0, 0.0], [0.0, 3.0]]
    vecs = numerical_eigenvectors(D)
    assert cosangle(vecs[0], vecs[1]) < 1e-3, (
        "distinct eigenvalues give orthogonal numerical eigenvectors, "
        f"got cos = {cosangle(vecs[0], vecs[1]):.4f}")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("eigenvalues.py", "the characteristic polynomial", check_characteristic_polynomial),
    ("eigenvalues.py", "Horner and exact rational roots", check_evaluation_and_rational_roots),
    ("eigenvalues.py", "exact eigenvalues and eigenspaces", check_eigenvalues_and_eigenspaces),
    ("eigenvalues.py", "diagonalisable iff n independent eigenvectors", check_diagonalizable),
    ("eigenvalues.py", "diagonalisation P D P^-1", check_diagonalize),
    ("eigenvalues.py", "Householder QR decomposition", check_qr_decomposition),
    ("eigenvalues.py", "the QR eigensolver", check_qr_eigenvalues),
    ("eigenvalues.py", "Wilkinson's polynomial and companion", check_wilkinson_polynomial),
    ("eigenvalues.py", "root-finding versus QR (limit case)", check_wilkinson_limit_case),
    ("eigenvalues.py", "nearly parallel numerical eigenvectors of a defective matrix", check_numerical_eigenvectors),
]


def run_one(check: Callable[[], None]) -> Tuple[str, str]:
    try:
        check()
        return PASS, ""
    except NotImplementedError as exc:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, (str(exc) or where)
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:  # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = f"\n      at {frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))
    print(f"\n{BOLD}Eigenvalues From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<18} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<18} {title}")
            print(f"      {GREY}not implemented yet{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<18} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")
    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()
    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built eigenvalues from scratch.{RESET}")
        print(f"  {GREY}Run solutions/eigenvalues.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
