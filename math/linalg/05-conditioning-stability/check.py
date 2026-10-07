"""Progress checker for the conditioning / stability templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 2         # run only step 2
    python3 check.py 2 4       # run steps 2 through 4
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write.  Nothing here imports solutions/.  It tests YOUR code.

The checker carries its own arithmetic: its own matmul, its own Gaussian elimination
with partial pivoting and its own Gauss-Jordan inverse, so the condition numbers and
backward errors it compares against do not come from the code under test.  The accept
criterion is the empirical statement of Trefethen & Bau's central inequality,
``forward error <= condition number * backward error`` (up to the algorithm's
backward-error floor ``n * eps``); the growth step pins the classic ``gfpp`` matrix at
``2^(n-1)``; the limit step shows a well-conditioned problem that no-pivot LU still
gets badly wrong.
"""

import math
import pathlib
import shutil
import sys
import traceback
from typing import Callable, List, Tuple

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")
EPS = sys.float_info.epsilon


# ---------------------------------------------------------------------------
# the checker's own dense arithmetic (never the learner's)
# ---------------------------------------------------------------------------

def _identity(n):
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _matmul(A, B):
    n, k, m = len(A), len(B), len(B[0])
    return [[sum(A[i][t] * B[t][j] for t in range(k)) for j in range(m)]
            for i in range(n)]


def _transpose(A):
    return [list(row) for row in zip(*A)] if A else []


def _matvec(A, x):
    return [sum(A[i][j] * x[j] for j in range(len(x))) for i in range(len(A))]


def _norm_inf(A):
    return max(sum(abs(v) for v in row) for row in A)


def _vec_inf(x):
    return max(abs(v) for v in x) if x else 0.0


def _solve(A, b):
    """Gaussian elimination with partial pivoting (the checker's own)."""
    n = len(A)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda i: abs(M[i][col]))
        if abs(M[piv][col]) < 1e-300:
            raise ZeroDivisionError("singular system in check._solve")
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


def _inverse(A):
    """Gauss-Jordan inverse with partial pivoting (the checker's own)."""
    n = len(A)
    M = [A[i][:] + _identity(n)[i] for i in range(n)]
    for k in range(n):
        p = max(range(k, n), key=lambda i: abs(M[i][k]))
        if abs(M[p][k]) < 1e-300:
            raise ZeroDivisionError("singular matrix in check._inverse")
        M[k], M[p] = M[p], M[k]
        pv = M[k][k]
        for j in range(2 * n):
            M[k][j] /= pv
        for i in range(n):
            if i == k:
                continue
            f = M[i][k]
            if f != 0.0:
                for j in range(2 * n):
                    M[i][j] -= f * M[k][j]
    return [row[n:] for row in M]


def _max_abs_diff(A, B):
    return max(abs(A[i][j] - B[i][j]) for i in range(len(A)) for j in range(len(A[0])))


def _hilbert(n):
    return [[1.0 / (i + j + 1) for j in range(n)] for i in range(n)]


# ---------------------------------------------------------------------------
# Step 1: LU with and without pivoting reconstruct A and solve a known system
# ---------------------------------------------------------------------------

def check_lu_factorization() -> None:
    from stability import lu_nopivot, lu_partial_pivot, lu_solve

    # A system that needs a row swap (zero in the (0,0) position).
    A = [[0.0, 2.0], [3.0, 4.0]]
    b = [4.0, 11.0]
    x_true = [1.0, 2.0]
    L, U, P = lu_partial_pivot(A)
    n = len(A)
    for i in range(n):
        assert L[i][i] == 1.0, "L must be unit lower triangular (ones on its diagonal)"
        for j in range(i + 1, n):
            assert L[i][j] == 0.0, \
                "L must be lower triangular; an entry above the diagonal means the " \
                "multipliers and the pivot rows got out of step"
        for j in range(i):
            assert U[i][j] == 0.0, \
                "U must be upper triangular; an entry below the diagonal means " \
                "elimination did not clear column entries"
    recon = _matmul(_matmul(_transpose(P), L), U)
    err = _max_abs_diff(recon, A)
    assert err <= 1e-12, \
        (f"P^T L U must reconstruct A to 1e-12; it differs by {err:.3e} -- the "
         "permutation is applied inconsistently between L, U and P")
    x = lu_solve(A, b)
    assert max(abs(x[i] - x_true[i]) for i in range(2)) <= 1e-12, \
        f"lu_solve must solve [[0,2],[3,4]] x = [4,11] as [1,2], got {x}"

    # A system with no swap needed: LU without pivoting must reconstruct with P = I.
    A2 = [[4.0, 3.0], [6.0, 3.0]]
    b2 = [10.0, 12.0]
    L2, U2, P2 = lu_nopivot(A2)
    assert _max_abs_diff(P2, _identity(2)) == 0.0, \
        "lu_nopivot must return the identity permutation, not perform swaps"
    err2 = _max_abs_diff(_matmul(L2, U2), A2)
    assert err2 <= 1e-12, \
        f"lu_nopivot must reconstruct A = L U to 1e-12, differs by {err2:.3e}"
    x2 = lu_solve(A2, b2, pivot=False)
    assert max(abs(x2[i] - x_true[i]) for i in range(2)) <= 1e-12, \
        f"lu_solve(pivot=False) must solve [[4,3],[6,3]] x = [10,12] as [1,2], got {x2}"

    # Partial pivoting on the well-behaved matrix must agree too.
    x3 = lu_solve(A2, b2, pivot=True)
    assert max(abs(x3[i] - x_true[i]) for i in range(2)) <= 1e-12, \
        f"lu_solve(pivot=True) must solve the same system as [1,2], got {x3}"


# ---------------------------------------------------------------------------
# Step 2: the ACCEPT criterion -- forward <= condition * backward
# ---------------------------------------------------------------------------

def check_accept_criterion() -> None:
    import random

    from stability import (backward_error, condition_number, forward_error,
                           lu_solve, perturbation_experiment)

    # The backward error must be the *relative* quantity, not a raw residual.
    A = [[1e6, 0.0], [0.0, 2e6]]
    x_true = [3.0, 2.0]
    b = _matvec(A, x_true)
    x = [x_true[0] + 1e-3, x_true[1]]
    residual = [sum(A[i][j] * x[j] for j in range(2)) - b[i] for i in range(2)]
    ref_back = _vec_inf(residual) / (_norm_inf(A) * _vec_inf(x))
    got_back = backward_error(A, x, b)
    assert abs(got_back - ref_back) <= 1e-6 * ref_back, \
        (f"backward_error must equal ||Ax-b|| / (||A|| ||x||); got {got_back:.3e} "
         f"but the relative value is {ref_back:.3e} -- the ||A|| ||x|| normalisation "
         "is missing or wrong")

    # The condition number must use one norm consistently.
    B = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 10.0]]
    ref_cond = _norm_inf(B) * _norm_inf(_inverse(B))
    got_cond = condition_number(B)
    assert abs(got_cond - ref_cond) <= 1e-9 * ref_cond, \
        (f"condition_number must be ||A||_inf * ||A^-1||_inf; got {got_cond:.6e} "
         f"but the infinity-norm value is {ref_cond:.6e} -- the two factors are "
         "using different norms")
    diag = [[1e3, 0.0], [0.0, 1e-3]]
    assert abs(condition_number(diag) - 1e6) <= 1e-3, \
        f"condition_number of diag(1e3, 1e-3) must be 1e6, got {condition_number(diag):.6e}"

    # ACCEPT: on 100 random problems forward <= condition * backward, up to the
    # backward-error floor n * eps.
    rng = random.Random(20261008)
    worst = 0.0
    for _ in range(100):
        n = rng.randint(2, 6)
        M = [[rng.uniform(-1.0, 1.0) for _ in range(n)] for _ in range(n)]
        xt = [rng.uniform(-1.0, 1.0) for _ in range(n)]
        bb = _matvec(M, xt)
        xx = lu_solve(M, bb)
        fwd = forward_error(xx, xt)
        back = backward_error(M, xx, bb)
        cond = condition_number(M)
        bound = cond * (back + n * EPS) * 1.1
        assert fwd <= bound, \
            (f"forward error must be bounded by condition * backward error; on a "
             f"{n}x{n} random system forward = {fwd:.3e} exceeds cond*(backward+{n}eps)"
             f"*1.1 = {bound:.3e} -- the solver is not backward stable or the errors "
             "are computed with inconsistent norms")
        if bound > 0.0:
            worst = max(worst, fwd / bound)

    r = perturbation_experiment(6, 100, random.Random(999))
    assert r <= 1.0 + 1e-6, \
        (f"the largest forward/(condition*backward) over 100 random systems must be "
         f"about 1 (a backward-stable solver); got {r:.6f} -- a systematic factor > 1 "
         "means the errors are not being normalised, or wrong pivoting is used")


# ---------------------------------------------------------------------------
# Step 3: the classic Wilkinson growth matrix reaches 2^(n-1)
# ---------------------------------------------------------------------------

def check_growth_factor() -> None:
    from stability import growth_factor, wilkinson_growth

    for n in (3, 4, 5):
        A = wilkinson_growth(n)
        g = growth_factor(A, pivot=True)
        want = float(2 ** (n - 1))
        assert abs(g - want) <= 1e-9 * want, \
            (f"the gfpp matrix of order {n} has growth factor 2^(n-1) = {want:.0f} "
             f"under partial pivoting; growth_factor returned {g:.6g} -- either the "
             "last column is missing its ones, or the ratio is normalised by max|U| "
             "(which would always be 1)")

    # Form of the matrix: unit diagonal, -1 strict lower, 1 in the last column.
    A = wilkinson_growth(4)
    for i in range(4):
        assert A[i][i] == 1.0, "the gfpp matrix must have a unit diagonal"
        assert A[i][3] == 1.0, "every row of the gfpp matrix must have 1 in the last column"
        for j in range(4):
            if j != 3 and i > j:
                assert A[i][j] == -1.0, \
                    "the strict lower triangle of the gfpp matrix must be -1"
            if j != 3 and i < j:
                assert A[i][j] == 0.0, \
                    "the gfpp matrix has zeros above the diagonal except the last column"

    # A smaller matrix whose growth is 2 and not 2^(n-1): the ratio must be real.
    S = [[1.0, 0.0, 1.0], [-1.0, 1.0, 0.0], [0.0, -1.0, 1.0]]
    g = growth_factor(S, pivot=True)
    assert abs(g - 2.0) <= 1e-9, \
        (f"this matrix has growth factor 2; growth_factor returned {g:.6g} -- a "
         "ratio normalised by max|U| instead of max|A| would sit at 1")


# ---------------------------------------------------------------------------
# Step 4: limit case -- no-pivot LU is unstable on a well-conditioned problem
# ---------------------------------------------------------------------------

def check_nopivot_unstable() -> None:
    from stability import condition_number, forward_error, lu_solve

    # A tiny pivot makes the no-pivot multiplier 1e18; the problem itself is tame.
    A = [[1e-18, 1.0], [1.0, 1.0]]
    x_true = [1.0, 1.0]
    b = _matvec(A, x_true)

    cond = condition_number(A)
    assert cond < 100.0, \
        (f"this limit case must be well conditioned (condition number {cond:.3g}); "
         "the point is that the *algorithm*, not the problem, is unstable")

    x_no = lu_solve(A, b, pivot=False)
    x_pi = lu_solve(A, b, pivot=True)
    fe_no = forward_error(x_no, x_true)
    fe_pi = forward_error(x_pi, x_true)
    assert fe_no > 1e-2, \
        (f"LU without pivoting must be destroyed by the 1e-18 pivot (forward error "
         f"{fe_no:.3e}); an accidentally-swapped no-pivot path would keep it small")
    assert fe_pi < 1e-8, \
        (f"partial pivoting must recover full accuracy on the same problem (forward "
         f"error {fe_pi:.3e}) -- pivoting is not choosing the largest entry")


# ---------------------------------------------------------------------------
# Step 5: an ill-conditioned problem solved by a backward-stable algorithm
# ---------------------------------------------------------------------------

def check_illconditioned_but_stable() -> None:
    from stability import backward_error, condition_number, forward_error, lu_solve

    n = 8
    A = _hilbert(n)
    x_true = [1.0] * n
    b = _matvec(A, x_true)

    cond = condition_number(A)
    assert cond > 1e8, \
        (f"the 8x8 Hilbert matrix has condition number ~3e10, got {cond:.3e} -- "
         "condition_number is not seeing the ill-conditioning")

    x = lu_solve(A, b, pivot=True)
    back = backward_error(A, x, b)
    fwd = forward_error(x, x_true)

    assert back <= 1e-14, \
        (f"partial pivoting is backward stable on the Hilbert matrix, so the backward "
         f"error must be at the level of machine epsilon; got {back:.3e} -- a large "
         "backward error usually means the wrong pivoting was used")

    # Independent check of the backward error on the same data.
    residual = [sum(A[i][j] * x[j] for j in range(n)) - b[i] for i in range(n)]
    ref = _vec_inf(residual) / (_norm_inf(A) * _vec_inf(x))
    assert abs(back - ref) <= 1e-9 * ref + 1e-300, \
        (f"backward_error must be ||Ax-b||/(||A|| ||x||): got {back:.3e}, "
         f"the checker computes {ref:.3e}")

    assert fwd > 1e-9 and fwd > 1e6 * back, \
        (f"the ill-conditioned problem must lose forward accuracy even though the "
         f"algorithm is stable: forward {fwd:.3e}, backward {back:.3e} -- a tiny "
         "forward error would mean the condition number is being understated")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("stability.py", "LU with and without pivoting reconstruct and solve", check_lu_factorization),
    ("stability.py", "accept: forward <= condition * backward", check_accept_criterion),
    ("stability.py", "growth factor of the Wilkinson (gfpp) matrix is 2^(n-1)", check_growth_factor),
    ("stability.py", "limit case: no-pivot LU unstable, pivoting accurate", check_nopivot_unstable),
    ("stability.py", "ill-conditioned problem, backward-stable solve", check_illconditioned_but_stable),
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
    print(f"\n{BOLD}Conditioning and Stability From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<15} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<15} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<15} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built conditioning, pivoting and the growth factor.{RESET}")
        print(f"  {GREY}Run solutions/stability.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
