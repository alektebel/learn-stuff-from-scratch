"""
Progress checker for the Householder-QR / least-squares templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The checker carries its own arithmetic: its own matrix product, its own orthonormality
test (`_gram_ok`), its own Gaussian elimination and its own exact
`fractions.Fraction` least-squares reference. The accept criteria are checked as
invariants -- `Q^T Q = I` to 1e-14 on a well- *and* an ill-conditioned matrix,
`A = Q R`, the three routes agreeing, the exact reference matching QR, and the
normal equations losing about twice as many digits as QR on a Hilbert limit case.
"""

import math
import pathlib
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
EPS = sys.float_info.epsilon


# ---------------------------------------------------------------------------
# The checker's own dense arithmetic (never the learner's)
# ---------------------------------------------------------------------------

def _mm(A, B):
    n, k, m = len(A), len(B), len(B[0])
    return [[sum(A[i][t] * B[t][j] for t in range(k)) for j in range(m)]
            for i in range(n)]


def _mt(A):
    return [list(row) for row in zip(*A)] if A else []


def _mv(A, v):
    return [sum(A[i][j] * v[j] for j in range(len(v))) for i in range(len(A))]


def _norm(v):
    return math.sqrt(sum(x * x for x in v))


def _solve(A, b):
    """Gaussian elimination with partial pivoting; works for Fraction too."""
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


def _gram_ok(Q, tol):
    """True iff the columns of Q are orthonormal, to tol (the checker's own test)."""
    if not Q:
        return True
    m, k = len(Q), len(Q[0])
    for i in range(k):
        for j in range(k):
            dot = sum(Q[r][i] * Q[r][j] for r in range(m))
            want = 1.0 if i == j else 0.0
            if abs(dot - want) > tol:
                return False
    return True


def _max_abs(A, B):
    return max(abs(A[i][j] - B[i][j]) for i in range(len(A)) for j in range(len(A[0])))


def _rel_err(a, b):
    num = math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(len(b))))
    den = math.sqrt(sum(b[i] ** 2 for i in range(len(b))))
    return num / den if den > 0.0 else num


def _digits_lost(err):
    """Decimal digits lost relative to machine precision (``err / eps``)."""
    return math.log10(err / EPS)


def _hilbert(m, n):
    """The m x n Hilbert matrix ``1 / (i + j + 1)`` as floats."""
    return [[1.0 / (i + j + 1) for j in range(n)] for i in range(m)]


def _hilbert_frac(m, n):
    """The m x n Hilbert matrix as exact Fractions."""
    return [[Fraction(1, i + j + 1) for j in range(n)] for i in range(m)]


def _exact_ls(A, b):
    """The exact rational least-squares minimiser (checker's own reference).

    ``A`` and ``b`` are integer or rational; exact arithmetic makes the normal
    equations exact, so this is the true minimiser regardless of conditioning.
    """
    Af = [[Fraction(x) for x in row] for row in A]
    bf = [Fraction(x) for x in b]
    At = _mt(Af)
    C = _mm(At, Af)
    rhs = _mv(At, bf)
    return _solve(C, rhs)


# ---------------------------------------------------------------------------
# Step 1: Householder QR
# ---------------------------------------------------------------------------

def check_householder_qr() -> None:
    from leastsquares import householder_qr

    for label, A in (("well-conditioned", [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]),
                     ("ill-conditioned Hilbert 6x6", _hilbert(6, 6))):
        m, n = len(A), len(A[0])
        Q, R = householder_qr(A)
        assert len(Q) == m and all(len(row) == m for row in Q), \
            f"{label}: Q must be m x m ({m}), got {len(Q)} x {len(Q[0]) if Q else 0}"
        assert _gram_ok(Q, 1e-14), \
            (f"{label}: Q^T Q = I must hold to 1e-14 -- Householder Q is a product of "
             "orthogonal reflectors, so an accumulation mistake (a dropped factor or a "
             "reflector applied to the wrong side) is the likely cause")
        assert _max_abs(_mm(Q, R), A) <= 1e-12, \
            f"{label}: A = Q R must reconstruct A"


# ---------------------------------------------------------------------------
# Step 2: the three least-squares routes agree
# ---------------------------------------------------------------------------

def check_three_methods_agree() -> None:
    from leastsquares import normal_equations, qr_least_squares, svd_least_squares

    A = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
    b = [1.0, 2.0, 0.5]
    x_qr = qr_least_squares(A, b)
    assert len(x_qr) == 2, f"the solution for a 2-column A must have 2 entries, got {len(x_qr)}"
    for name, x in (("normal equations", normal_equations(A, b)),
                    ("SVD", svd_least_squares(A, b))):
        assert len(x) == 2, f"{name}: the solution must have 2 entries, got {len(x)}"
        d = max(abs(x[i] - x_qr[i]) for i in range(2))
        assert d <= 1e-8, \
            (f"{name} and QR must agree on a well-conditioned problem to 1e-8; "
             f"they differ by {d:.3e} -- check which system each one actually solves")


# ---------------------------------------------------------------------------
# Step 3: the exact Fraction reference matches QR
# ---------------------------------------------------------------------------

def check_exact_reference() -> None:
    from leastsquares import exact_least_squares, qr_least_squares

    A = [[1, 2], [3, 4], [5, 6]]
    b = [1, 1, 1]
    got = exact_least_squares(A, b)
    assert len(got) == 2 and all(isinstance(v, Fraction) for v in got), \
        "exact_least_squares must return Fractions (exact rational arithmetic)"
    ref = _exact_ls(A, b)
    assert all(got[i] == ref[i] for i in range(2)), \
        "exact_least_squares must equal the exact rational minimiser of A^T A x = A^T b"

    x_qr = qr_least_squares([[float(x) for x in row] for row in A],
                            [float(x) for x in b])
    err = max(abs(float(got[i]) - x_qr[i]) for i in range(2))
    assert err <= 1e-8, \
        (f"the exact rational reference must match the QR solution on integer data; "
         f"they differ by {err:.3e} -- check the QR solve, not the reference")


# ---------------------------------------------------------------------------
# Step 4: the limit case -- the normal equations lose ~twice the digits of QR
# ---------------------------------------------------------------------------

def check_limit_case() -> None:
    from leastsquares import normal_equations, qr_least_squares, condition_number

    m, n = 7, 6
    A = _hilbert(m, n)
    b = [1.0 / (i + 1) for i in range(m)]
    ref = [float(t) for t in
           _exact_ls(_hilbert_frac(m, n), [Fraction(1, i + 1) for i in range(m)])]

    cond = condition_number(A)
    assert cond > 1e5, \
        (f"the 2-norm condition number of the Hilbert {m}x{n} matrix is ~7e6, got "
         f"{cond:.3e} -- condition_number must use the ratio of singular values, not "
         "the diagonal entries")

    e_ne = _rel_err(normal_equations(A, b), ref)
    e_qr = _rel_err(qr_least_squares(A, b), ref)
    assert e_qr > 0.0, "the QR error must be nonzero on a genuinely ill-conditioned problem"
    assert e_ne >= 10.0 * e_qr, \
        (f"the normal equations must lose far more accuracy than QR on this ill-conditioned "
         f"problem; normal-equations error {e_ne:.3e} vs QR error {e_qr:.3e} -- "
         "normal_equations must solve A^T A x = A^T b, not produce the QR answer")

    d_ne, d_qr = _digits_lost(e_ne), _digits_lost(e_qr)
    assert d_ne >= 1.5 * d_qr, \
        (f"the normal equations should lose about twice as many digits as QR "
         f"(condition number squared); lost {d_ne:.1f} vs {d_qr:.1f} digits")


# ---------------------------------------------------------------------------
# Step 5: the residual is (near-)minimal
# ---------------------------------------------------------------------------

def check_residual_optimality() -> None:
    from leastsquares import (normal_equations, qr_least_squares,
                              svd_least_squares, residual_norm)

    A = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
    b = [1.0, 2.0, 0.5]
    At = _mt(A)
    for name, x in (("normal equations", normal_equations(A, b)),
                    ("QR", qr_least_squares(A, b)),
                    ("SVD", svd_least_squares(A, b))):
        r = [b[i] - sum(A[i][j] * x[j] for j in range(2)) for i in range(3)]
        grad = _mv(At, r)
        g = max(abs(v) for v in grad)
        assert g <= 1e-8, \
            (f"the least-squares residual must satisfy A^T (A x - b) = 0; {name} gives "
             f"max|A^T r| = {g:.3e} -- this is not the minimiser")
        rn = residual_norm(A, b, x)
        assert abs(rn - _norm(r)) <= 1e-10, \
            (f"residual_norm must equal ||A x - b||; {name} gives {rn:.3e} vs "
             f"{_norm(r):.3e}")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("leastsquares.py", "Householder QR is orthogonal, A = Q R", check_householder_qr),
    ("leastsquares.py", "the three least-squares routes agree", check_three_methods_agree),
    ("leastsquares.py", "the exact Fraction reference matches QR", check_exact_reference),
    ("leastsquares.py", "limit case: normal equations lose ~2x digits", check_limit_case),
    ("leastsquares.py", "the residual is (near-)minimal", check_residual_optimality),
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
    print(f"\n{BOLD}QR and Least Squares From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built QR and its least-squares routes.{RESET}")
        print(f"  {GREY}Run solutions/leastsquares.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
