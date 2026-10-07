"""
Progress checker for the linear-algebra templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The reference answer is computed independently of your code. numpy is used when it is
installed; when it is not, an exact rational oracle (fractions.Fraction) computes the
reference, so this module runs with no dependencies and no floating-point oracle.
"""

import pathlib
import random
import shutil
import sys
import traceback
from fractions import Fraction

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")

try:                                                       # oracle, when available
    import numpy as _np
except Exception:                                          # noqa: BLE001
    _np = None


# ---------------------------------------------------------------------------
# An independent oracle. Exact rational elimination: it shares no rounding with the
# learner's float code, so "they agree" means the answer is right, not that the same
# mistake was made twice.
# ---------------------------------------------------------------------------

def _frac_elim(M, ncols):
    """Exact Gauss-Jordan over Fractions; pivots on the first `ncols` columns."""
    R = [[Fraction(v) for v in row] for row in M]
    m = len(R)
    pivots, r = [], 0
    for c in range(ncols):
        if r >= m:
            break
        p = next((i for i in range(r, m) if R[i][c] != 0), None)
        if p is None:
            continue
        R[r], R[p] = R[p], R[r]
        pv = R[r][c]
        R[r] = [v / pv for v in R[r]]
        for i in range(m):
            if i != r and R[i][c] != 0:
                f = R[i][c]
                R[i] = [a - f * b for a, b in zip(R[i], R[r])]
        pivots.append(c)
        r += 1
    return R, pivots


def _ref_solve(A, b):
    if _np is not None:
        return [float(v) for v in _np.linalg.solve(_np.array(A, float), _np.array(b, float))]
    n = len(A)
    R, pivots = _frac_elim([list(A[i]) + [b[i]] for i in range(n)], n)
    assert len(pivots) == n, "oracle: the reference system is not uniquely solvable"
    x = [Fraction(0)] * n
    for k, c in enumerate(pivots):
        x[c] = R[k][n]
    return [float(v) for v in x]


def _ref_inverse(A):
    if _np is not None:
        return _np.linalg.inv(_np.array(A, float)).tolist()
    n = len(A)
    aug = [list(A[i]) + [1 if i == j else 0 for j in range(n)] for i in range(n)]
    R, pivots = _frac_elim(aug, n)
    if len(pivots) < n:
        return None
    return [[float(R[i][n + j]) for j in range(n)] for i in range(n)]


def _ref_det(A):
    if _np is not None:
        return float(_np.linalg.det(_np.array(A, float)))
    n = len(A)
    R = [[Fraction(v) for v in row] for row in A]
    swaps, det = 0, Fraction(1)
    for c in range(n):
        p = next((i for i in range(c, n) if R[i][c] != 0), None)
        if p is None:
            return 0.0
        if p != c:
            R[c], R[p] = R[p], R[c]
            swaps += 1
        det *= R[c][c]
        for i in range(c + 1, n):
            if R[i][c] != 0:
                f = R[i][c] / R[c][c]
                for j in range(c, n):
                    R[i][j] -= f * R[c][j]
    return float(-det if swaps % 2 else det)


def _ref_rank(A):
    if not A:
        return 0
    _, pivots = _frac_elim(A, len(A[0]))
    return len(pivots)


def _matvec(A, v):
    return [sum(A[i][j] * v[j] for j in range(len(v))) for i in range(len(A))]


def _close(got, want, atol=1e-8, rtol=1e-6):
    flat_got = [v for row in got for v in row] if got and isinstance(got[0], list) else list(got)
    flat_want = [v for row in want for v in row] if want and isinstance(want[0], list) else list(want)
    return (len(flat_got) == len(flat_want)
            and all(abs(g - w) <= atol + rtol * abs(w) for g, w in zip(flat_got, flat_want)))


def _well_conditioned(rng: random.Random, n: int):
    """A diagonally dominant matrix: honest to invert, so the comparison is meaningful."""
    A = [[rng.uniform(-1.0, 1.0) for _ in range(n)] for _ in range(n)]
    for i in range(n):
        A[i][i] += n * 2.0
    return A


# ---------------------------------------------------------------------------
# Step 1: row_echelon — and the zero pivot partial pivoting must swap around
# ---------------------------------------------------------------------------

def check_row_echelon() -> None:
    from elimination import row_echelon

    A = [[0.0, 2.0], [3.0, 4.0]]
    U, pivots = row_echelon(A)
    assert pivots == [0, 1], f"pivots {pivots}: a zero pivot must be swapped away, not skipped"
    assert abs(U[0][0] - 3.0) < 1e-12, (
        f"the first row after elimination starts with {U[0][0]}: partial pivoting must put "
        "the largest-magnitude entry of the column on the pivot")
    assert abs(U[1][0]) < 1e-12, "the entry below the first pivot was not eliminated"

    R = [[1.0, 2.0, 3.0], [2.0, 4.0, 6.0], [0.0, 1.0, 1.0]]
    _, pivots = row_echelon(R)
    assert pivots == [0, 1], f"pivots {pivots}: expected [0, 1] for this rank-2 matrix"

    P = [[0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [1.0, 0.0, 0.0]]
    _, pivots = row_echelon(P)
    assert pivots == [0, 1, 2], f"pivots {pivots}: a permutation matrix is full rank"


# ---------------------------------------------------------------------------
# Step 2: rank
# ---------------------------------------------------------------------------

def check_rank() -> None:
    from elimination import rank

    assert rank([[1.0, 2.0], [3.0, 4.0]]) == 2
    assert rank([[1.0, 2.0], [2.0, 4.0]]) == 1
    assert rank([[0.0, 0.0], [0.0, 0.0]]) == 0
    assert rank([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]) == 2, "rows are dependent"
    assert rank([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]) == 2, "rank cannot exceed min(rows, cols)"


# ---------------------------------------------------------------------------
# Step 3: solve matches the reference on 200 systems (accept criterion)
# ---------------------------------------------------------------------------

def check_solve_matches_reference() -> None:
    from elimination import solve

    rng = random.Random(7)
    for _ in range(200):
        n = rng.randint(1, 6)
        A = _well_conditioned(rng, n)
        b = [rng.uniform(-5.0, 5.0) for _ in range(n)]
        got = solve(A, b)
        want = _ref_solve(A, b)
        assert len(got) == n, f"solve returned {len(got)} values for {n} unknowns"
        assert _close(got, want), f"n={n}: got {got}, reference says {[round(w, 9) for w in want]}"


# ---------------------------------------------------------------------------
# Step 4: an inconsistent system is reported, not solved (accept criterion)
# ---------------------------------------------------------------------------

def check_inconsistent() -> None:
    from elimination import InconsistentSystem, NotUnique, solve, general_solution

    # x + y = 1 and x + y = 2: parallel lines.
    for fn in (solve, general_solution):
        try:
            fn([[1.0, 1.0], [1.0, 1.0]], [1.0, 2.0])
            raise AssertionError(
                "an inconsistent system was solved instead of raising InconsistentSystem")
        except InconsistentSystem:
            pass
    # A dependent system that IS consistent has infinitely many solutions: solve must
    # say NotUnique, not pretend it found one.
    try:
        solve([[1.0, 1.0], [2.0, 2.0]], [1.0, 2.0])
        raise AssertionError(
            "a consistent underdetermined system was reported as having a unique solution")
    except NotUnique:
        pass
    # general_solution must still return one, plus the free directions.
    particular, basis = general_solution([[1.0, 1.0], [2.0, 2.0]], [1.0, 2.0])
    assert abs(sum(particular) - 1.0) < 1e-12 and len(basis) == 1


# ---------------------------------------------------------------------------
# Step 5: null space — A n = 0 and the basis size is n - rank (accept criterion)
# ---------------------------------------------------------------------------

def check_null_space() -> None:
    from elimination import null_space, rank

    rng = random.Random(11)
    for _ in range(60):
        m, n = rng.randint(1, 5), rng.randint(1, 6)
        A = [[rng.uniform(-3.0, 3.0) for _ in range(n)] for _ in range(m)]
        basis = null_space(A)
        assert len(basis) == n - _ref_rank(A), (
            f"null-space dim {len(basis)}, but n - rank = {n} - {_ref_rank(A)}")
        for v in basis:
            assert len(v) == n, f"basis vector has length {len(v)}, expected {n}"
            residual = _matvec(A, v)
            assert _close(residual, [0.0] * m, atol=1e-8), (
                f"A·n = {residual}, not 0: the basis vector is not in the null space")


# ---------------------------------------------------------------------------
# Step 6: particular + homogeneous solutions
# ---------------------------------------------------------------------------

def check_general_solution() -> None:
    from elimination import general_solution

    # Rank 1, consistent: one particular solution plus a two-dimensional null space.
    A = [[1.0, 2.0, 3.0], [2.0, 4.0, 6.0]]
    b = [1.0, 2.0]
    particular, basis = general_solution(A, b)
    assert _close(_matvec(A, particular), b, atol=1e-9), (
        "the particular solution does not satisfy A·x = b")
    assert len(basis) == 2, f"null-space dim {len(basis)}, expected 2"
    for v in basis:
        assert _close(_matvec(A, v), [0.0, 0.0], atol=1e-9), (
            "a homogeneous basis vector does not satisfy A·x = 0")

    # Full rank: the null space is empty and there is exactly one solution.
    particular, basis = general_solution([[2.0, 0.0], [0.0, 3.0]], [4.0, 9.0])
    assert basis == [], "a full-rank system has only the trivial null space"
    assert _close(particular, [2.0, 3.0], atol=1e-12)


# ---------------------------------------------------------------------------
# Step 7: inverse by Gauss-Jordan matches the reference
# ---------------------------------------------------------------------------

def check_inverse_matches_reference() -> None:
    from elimination import inverse

    rng = random.Random(13)
    for _ in range(100):
        n = rng.randint(1, 5)
        A = _well_conditioned(rng, n)
        inv = inverse(A)
        want = _ref_inverse(A)
        assert _close(inv, want), (
            f"n={n}: inverse is wrong\n  got  {[[round(v, 6) for v in r] for r in inv]}"
            f"\n  want {[[round(v, 6) for v in r] for r in want]}")
        prod = [[sum(A[i][k] * inv[k][j] for k in range(n)) for j in range(n)]
                for i in range(n)]
        eye = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
        assert _close(prod, eye, atol=1e-8), "A·A⁻¹ is not the identity"


# ---------------------------------------------------------------------------
# Step 8: a singular matrix has no inverse (limit case)
# ---------------------------------------------------------------------------

def check_singular_inverse() -> None:
    from elimination import SingularMatrix, inverse

    cases = [
        [[1.0, 2.0], [2.0, 4.0]],
        [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]],
        [[0.0, 0.0], [0.0, 0.0]],
    ]
    for A in cases:
        try:
            inverse(A)
            raise AssertionError(
                f"inverse() returned a result for the singular matrix {A}; it must raise "
                "SingularMatrix (a zero pivot is a rank deficiency, not a small number)")
        except SingularMatrix:
            pass


# ---------------------------------------------------------------------------
# Step 9: determinant from the elimination
# ---------------------------------------------------------------------------

def check_determinant() -> None:
    from elimination import determinant

    rng = random.Random(17)
    for _ in range(100):
        n = rng.randint(1, 5)
        A = _well_conditioned(rng, n)
        got = determinant(A)
        want = _ref_det(A)
        assert abs(got - want) <= 1e-6 * max(1.0, abs(want)), (
            f"n={n}: determinant {got}, reference says {want}")
    assert abs(determinant([[1.0, 2.0], [3.0, 4.0]]) + 2.0) < 1e-12
    assert determinant([[1.0, 2.0], [2.0, 4.0]]) == 0.0, "a singular matrix has determinant 0"
    assert abs(determinant([[0.0, 1.0], [1.0, 0.0]]) + 1.0) < 1e-12, (
        "det of a swap matrix is -1: the row-swap sign was not applied")


# ---------------------------------------------------------------------------
# Step 10: the small pivot partial pivoting exists to fix (limit case)
# ---------------------------------------------------------------------------

def check_small_pivot() -> None:
    from elimination import solve

    # Without pivoting, 1e-18 is used as a pivot and destroys the answer.
    A = [[1e-18, 1.0], [1.0, 1.0]]
    b = [1.0, 2.0]
    x = solve(A, b)
    want = _ref_solve(A, b)
    assert abs(x[0] - 1.0) < 1e-6, (
        f"x₁ = {x[0]}: a tiny pivot was used instead of the larger one in the column — "
        "partial pivoting must choose the largest magnitude")
    assert _close(x, want, atol=1e-6), f"got {x}, reference says {want}"

    # The same failure, one magnitude larger, to be sure it is not luck.
    A = [[1e-12, 1.0, 1.0], [1.0, 1.0, 0.0], [1.0, 0.0, 1.0]]
    b = [3.0, 2.0, 2.0]
    x = solve(A, b)
    want = _ref_solve(A, b)
    assert _close(x, want, atol=1e-6), (
        f"got {x}, reference says {want}: pivoting is not being applied")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("elimination.py", "row echelon and a zero pivot", check_row_echelon),
    ("elimination.py", "rank", check_rank),
    ("elimination.py", "solve matches the reference, 200 systems", check_solve_matches_reference),
    ("elimination.py", "inconsistent system is reported", check_inconsistent),
    ("elimination.py", "null space: A·n = 0, size n - rank", check_null_space),
    ("elimination.py", "particular + homogeneous solution", check_general_solution),
    ("elimination.py", "inverse matches the reference", check_inverse_matches_reference),
    ("elimination.py", "singular matrix has no inverse", check_singular_inverse),
    ("elimination.py", "determinant, and the row-swap sign", check_determinant),
    ("elimination.py", "small pivot: pivoting saves the answer", check_small_pivot),
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
    print(f"\n{BOLD}Linear Algebra From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<14} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<14} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<14} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built elimination from scratch.{RESET}")
        print(f"  {GREY}Run solutions/elimination.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
