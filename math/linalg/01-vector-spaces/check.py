"""
Progress checker for the vector-spaces templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

Every reference value is computed here, with this file's own exact rational arithmetic,
so the checker never asks your own code what the right answer is. Fractions make every
acceptance test an equality, not a tolerance.
"""

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
# This file's own exact linear algebra over Q (independent of vector_spaces.py)
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
    """The columns of A, as a list of vectors."""
    return [list(col) for col in zip(*A)]


def _columns_to_matrix(vectors):
    if not vectors:
        return []
    return [[_F(v[i]) for v in vectors] for i in range(len(vectors[0]))]


def _identity(n):
    return [[Fraction(1) if i == j else Fraction(0) for j in range(n)] for i in range(n)]


def _is_zero(A):
    return all(x == 0 for row in A for x in row)


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


def _random_invertible(rng, n, lo=-3, hi=3):
    while True:
        M = [[Fraction(rng.randint(lo, hi)) for _ in range(n)] for _ in range(n)]
        if _rank(M) == n:
            return M


# ---------------------------------------------------------------------------
# Step 1: rank is the number of pivots (accept: exact on known and random matrices)
# ---------------------------------------------------------------------------

def check_rank() -> None:
    from vector_spaces import rank

    cases = [
        ([[1, 2], [3, 4]], 2),
        ([[1, 2], [2, 4]], 1),
        ([[0, 0], [0, 0]], 0),
        ([[1, 2, 3], [4, 5, 6], [7, 8, 9]], 2),      # rows are dependent
        ([[1, 2, 3], [2, 4, 6]], 1),                  # 2x3, one independent row
        ([[1, 2], [2, 4], [3, 6]], 1),                # 3x2, columns dependent
        ([[1, 0, 0], [0, 1, 0], [0, 0, 1]], 3),
        ([[1, 2, 3], [4, 5, 6]], 2),                  # 2x3, full row rank
        ([[2, 4], [1, 2], [0, 1]], 2),
    ]
    for M, expected in cases:
        got = rank(M)
        assert got == expected, (
            f"rank({M}) = {got}, expected {expected}: rank is the number of pivot columns "
            "of the row-reduced matrix, not the number of rows or columns")

    rng = random.Random(11)
    for _ in range(50):
        m, n = rng.randint(1, 5), rng.randint(1, 5)
        M = [[Fraction(rng.randint(-3, 3)) for _ in range(n)] for _ in range(m)]
        got = rank(M)
        ref = _rank(M)
        assert got == ref, (
            f"rank({M}) = {got}, but an independent elimination gives {ref}: "
            "rank is the pivot count over Q")


# ---------------------------------------------------------------------------
# Step 2: a basis of the null space (accept: maps to 0, right size, independent)
# ---------------------------------------------------------------------------

def check_null_space() -> None:
    from vector_spaces import null_space_basis

    # dim null = 3 - rank 1 = 2.
    A = [[1, 2, 3], [2, 4, 6]]
    basis = null_space_basis(A)
    assert len(basis) == 2, (
        f"null_space_basis({A}) returned {len(basis)} vectors, expected 3 - rank = 2")
    for v in basis:
        assert all(x == 0 for x in _matvec(A, v)), (
            f"{v} is an output basis vector but A v != 0: the null space is defined by A x = 0")
    assert _rank(_columns_to_matrix(basis)) == len(basis), (
        "the returned null-space vectors are not linearly independent, so they are not a basis")

    rng = random.Random(13)
    for _ in range(50):
        m, n = rng.randint(1, 5), rng.randint(1, 5)
        M = [[Fraction(rng.randint(-3, 3)) for _ in range(n)] for _ in range(m)]
        B = null_space_basis(M)
        ref_rank = _rank(M)
        assert len(B) == n - ref_rank, (
            f"null_space_basis(M) has {len(B)} vectors but dim null = n - rank = "
            f"{n} - {ref_rank} = {n - ref_rank}: the free columns are being miscounted")
        for v in B:
            assert all(x == 0 for x in _matvec(M, v)), (
                f"null-space vector {v} does not satisfy M v = 0 (a free column was "
                "given the wrong sign, or the free variable was not set to 1)")
        if B:
            assert _rank(_columns_to_matrix(B)) == len(B), "null-space vectors are dependent"


# ---------------------------------------------------------------------------
# Step 3: a basis of the range = the column space (accept: in the span, right size)
# ---------------------------------------------------------------------------

def check_column_space() -> None:
    from vector_spaces import column_space_basis

    rng = random.Random(17)
    for _ in range(50):
        m, n = rng.randint(1, 5), rng.randint(1, 5)
        M = [[Fraction(rng.randint(-3, 3)) for _ in range(n)] for _ in range(m)]
        B = column_space_basis(M)
        ref_rank = _rank(M)
        assert len(B) == ref_rank, (
            f"column_space_basis(M) has {len(B)} vectors, expected rank = {ref_rank}: "
            "the range is spanned by the pivot columns of M")
        if B:
            assert _rank(_columns_to_matrix(B)) == len(B), (
                "the returned range vectors are dependent, so they are not a basis")
            for v in B:
                aug = [list(M[i]) + [_F(v[i])] for i in range(m)]
                assert _rank(aug) == ref_rank, (
                    f"{v} is not in the column space of M: a range basis must span the "
                    "actual columns, not the rows or the reduced frame")


# ---------------------------------------------------------------------------
# Step 4: change of basis is S^-1 A S (accept criterion, on random bases)
# ---------------------------------------------------------------------------

def check_change_of_basis() -> None:
    from vector_spaces import matrix_of_map

    rng = random.Random(23)
    discriminating = 0
    for _ in range(30):
        n = rng.randint(1, 4)
        S = _random_invertible(rng, n)
        A = [[Fraction(rng.randint(-3, 3)) for _ in range(n)] for _ in range(n)]
        Sinv = _inverse(S)
        reference = _matmul(_matmul(Sinv, A), S)          # S^-1 A S
        got = matrix_of_map(A, _columns(S), _columns(S))
        assert got == reference, (
            f"matrix of A in the new basis is {got}, expected S^-1 A S = {reference}: "
            "the change of basis is S^-1 A S — the inverse is FIRST, on the left, not "
            "S A S^-1 and not A S S^-1 = A")
        if reference != _matmul(_matmul(S, A), Sinv):
            discriminating += 1
    assert discriminating > 0, (
        "no test case had S^-1 A S different from S A S^-1, so the check cannot tell the "
        "two orders apart: the random bases must include a non-commuting A and S")


# ---------------------------------------------------------------------------
# Step 5: the matrix of a map in two bases (accept: it represents the map)
# ---------------------------------------------------------------------------

def check_matrix_of_map_two_bases() -> None:
    from vector_spaces import matrix_of_map

    rng = random.Random(29)
    for _ in range(30):
        n = rng.randint(1, 4)
        m = rng.randint(1, 4)
        A = [[Fraction(rng.randint(-3, 3)) for _ in range(n)] for _ in range(m)]
        B = _random_invertible(rng, n)                    # domain basis, columns
        C = _random_invertible(rng, m)                    # codomain basis, columns
        M = matrix_of_map(A, _columns(B), _columns(C))
        for _ in range(3):
            x = [Fraction(rng.randint(-3, 3)) for _ in range(n)]
            standard = _matvec(B, x)                      # v in standard coords
            image = _matvec(A, standard)                  # T(v) in standard coords
            expected = _matvec(_inverse(C), image)        # coords in C
            got = _matvec(M, x)
            assert got == expected, (
                f"M x = {got} but the map applied through B, A, C^-1 gives {expected}: "
                "the matrix in bases (B, C) is C^-1 A B and must represent T on "
                "coordinates")


# ---------------------------------------------------------------------------
# Step 6: the differentiation matrix (accept: d/dx x^k = k x^(k-1), exactly)
# ---------------------------------------------------------------------------

def check_differentiation() -> None:
    from vector_spaces import apply, differentiation_matrix

    for n in range(0, 6):
        D = differentiation_matrix(n)
        assert len(D) == n + 1 and all(len(row) == n + 1 for row in D), (
            f"differentiation_matrix({n}) must be (n+1)x(n+1) = {n + 1}x{n + 1}")
        for k in range(n + 1):
            column = [D[i][k] for i in range(n + 1)]
            expected = [Fraction(0)] * (n + 1)
            if k > 0:
                expected[k - 1] = Fraction(k)
            assert column == expected, (
                f"column {k} of D is {column}, expected {expected}: the derivative of "
                "x^k is k·x^(k-1), so the coefficient is the INPUT power k (not 1, and "
                "not the output power k-1) in row k-1")

    # On a concrete polynomial in P_4: (3 + 2x + 5x^2 - x^4)' = 2 + 10x - 4x^3.
    D = differentiation_matrix(4)
    got = apply(D, [3, 2, 5, 0, -1])
    assert got == [2, 10, 0, -4, 0], (
        f"D applied to (3, 2, 5, 0, -1) gave {got}, expected [2, 10, 0, -4, 0]")


# ---------------------------------------------------------------------------
# Step 7: the fundamental theorem, dim V = dim null + dim range (accept criterion)
# ---------------------------------------------------------------------------

def check_rank_nullity() -> None:
    from vector_spaces import fundamental_theorem

    rng = random.Random(37)
    checked = 0
    for _ in range(100):
        n = rng.randint(1, 5)                              # dim domain V
        m = rng.randint(1, 5)                              # dim codomain W
        if m == n:
            m = 6 - n                                      # force different dimensions
        A = [[Fraction(rng.randint(-3, 3)) for _ in range(n)] for _ in range(m)]
        dim_v, nullity, range_dim = fundamental_theorem(A)
        ref_rank = _rank(A)
        assert dim_v == n, (
            f"dim V = {dim_v}, expected {n}: dim V is the number of COLUMNS of the matrix")
        assert range_dim == ref_rank, (
            f"dim range = {range_dim}, expected rank = {ref_rank}: the range dimension is "
            "the rank of the map, not the number of rows")
        assert nullity == n - ref_rank, (
            f"dim null = {nullity}, expected n - rank = {n - ref_rank}")
        assert dim_v == nullity + range_dim, (
            f"rank-nullity fails: dim V = {dim_v} but dim null + dim range = "
            f"{nullity} + {range_dim} = {nullity + range_dim}")
        checked += 1
    assert checked == 100, "the suite must check 100 random maps"

    # Deterministic rectangular, rank-deficient cases; the last has range_dim < nrows, so
    # reporting the number of rows as dim range is impossible to miss.
    cases = [
        ([[1, 2, 3], [2, 4, 6]], 3, 1),
        ([[1, 0], [0, 1], [0, 0]], 2, 2),
        ([[0, 0], [0, 0]], 2, 0),
    ]
    for M, n, ref_rank in cases:
        dim_v, nullity, range_dim = fundamental_theorem(M)
        assert (dim_v, nullity, range_dim) == (n, n - ref_rank, ref_rank), (
            f"fundamental_theorem({M}) = {(dim_v, nullity, range_dim)}, expected "
            f"{(n, n - ref_rank, ref_rank)}")


# ---------------------------------------------------------------------------
# Step 8: differentiation on P_n is nilpotent with index n+1 (limit case)
# ---------------------------------------------------------------------------

def check_nilpotency() -> None:
    from vector_spaces import differentiation_matrix, matrix_power, nilpotency_index

    A = [[1, 2], [3, 4]]
    assert matrix_power(A, 0) == _identity(2), "M^0 must be the identity"
    assert matrix_power(A, 1) == A, "M^1 must be M"
    assert matrix_power(A, 2) == _matmul(A, A), "M^2 must be M·M"

    for n in range(0, 6):
        D = differentiation_matrix(n)
        assert not _is_zero(matrix_power(D, n)), (
            f"on P_{n}, D^{n} is zero, but it must NOT be: D^n maps x^n to n! != 0")
        assert _is_zero(matrix_power(D, n + 1)), (
            f"on P_{n}, D^{n + 1} is not zero, but it must be: differentiation lowers the "
            "degree by one, so after n+1 steps every monomial is gone")
        idx = nilpotency_index(D, n + 1)
        assert idx == n + 1, (
            f"nilpotency index of differentiation on P_{n} is {idx}, expected {n + 1}: "
            "D^{n} != 0 so the index is n+1. Searching only up to power n misses it")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("vector_spaces.py", "rank is the pivot count", check_rank),
    ("vector_spaces.py", "a basis of the null space", check_null_space),
    ("vector_spaces.py", "a basis of the range (column space)", check_column_space),
    ("vector_spaces.py", "change of basis is S^-1 A S", check_change_of_basis),
    ("vector_spaces.py", "the matrix of a map in two bases", check_matrix_of_map_two_bases),
    ("vector_spaces.py", "the differentiation matrix", check_differentiation),
    ("vector_spaces.py", "rank-nullity on 100 random maps", check_rank_nullity),
    ("vector_spaces.py", "differentiation is nilpotent (index n+1)", check_nilpotency),
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
    print(f"\n{BOLD}Vector Spaces From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built vector spaces and linear maps from scratch.{RESET}")
        print(f"  {GREY}Run solutions/vector_spaces.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
