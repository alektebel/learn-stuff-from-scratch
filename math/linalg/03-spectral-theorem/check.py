"""
Progress checker for the spectral-theorem templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The checker carries its own arithmetic: its own matrix product, its own
orthonormality test (`_gram_ok`), its own `A = Q diag(lambda) Q^T` reconstruction and
its own randomised PSD probe. The accept criteria of the node are checked as
invariants -- `Q^T Q = I` to 1e-10, `A = Q P` with `Q` orthogonal and `P` PSD -- and
never by comparing to a fixed eigenvector basis, because at a repeated eigenvalue the
basis is not unique (that is the node's limit case).
"""

import math
import pathlib
import random
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")

TOL = 1e-10


# ---------------------------------------------------------------------------
# The checker's own dense arithmetic (never the learner's)
# ---------------------------------------------------------------------------

def _mm(A, B):
    n, k, m = len(A), len(B), len(B[0])
    return [[sum(A[i][t] * B[t][j] for t in range(k)) for j in range(m)] for i in range(n)]


def _mt(A):
    return [list(row) for row in zip(*A)] if A else []


def _diag(evals):
    n = len(evals)
    return [[evals[i] if i == j else 0.0 for j in range(n)] for i in range(n)]


def _gram_ok(Q, tol=TOL):
    """True iff the columns of Q are orthonormal, to tol (the checker's own test)."""
    if not Q:
        return True
    m, k = len(Q), len(Q[0])
    for i in range(k):
        for j in range(i, k):
            dot = sum(Q[r][i] * Q[r][j] for r in range(m))
            want = 1.0 if i == j else 0.0
            if abs(dot - want) > tol:
                return False
    return True


def _max_abs(A, B):
    return max(abs(A[i][j] - B[i][j]) for i in range(len(A)) for j in range(len(A[0])))


def _recon_cols(recon, A, tol=TOL):
    return _max_abs(recon, A) <= tol


def _symmetric(P, tol=TOL):
    n = len(P)
    return max(abs(P[i][j] - P[j][i]) for i in range(n) for j in range(n)) <= tol


def _psd_probe(P, seed=0, tol=1e-9):
    """v^T P v >= -tol for many random unit vectors v (the checker's PSD test)."""
    rng = random.Random(seed)
    n = len(P)
    for _ in range(200):
        v = [rng.uniform(-1.0, 1.0) for _ in range(n)]
        nrm = math.sqrt(sum(x * x for x in v))
        if nrm < 1e-12:
            continue
        v = [x / nrm for x in v]
        q = sum(v[i] * P[i][j] * v[j] for i in range(n) for j in range(n))
        if q < -tol:
            return False
    return True


def _rotated_repeated():
    """R diag(2,1,1) R^T: a NON-DIAGONAL symmetric matrix with a repeated eigenvalue.

    The rotation mixes the distinct eigenvalue 2 with one of the repeated 1s, so the
    product is genuinely off-diagonal and the solver must pick a basis inside the
    two-dimensional eigenspace of 1. (Rotating ``diag(1,1,2)`` instead would be a no-op,
    because the rotation would lie inside that eigenspace.)
    """
    s = 1.0 / math.sqrt(2.0)
    R = [[s, -s, 0.0], [s, s, 0.0], [0.0, 0.0, 1.0]]
    A = _mm(_mm(R, _diag([2.0, 1.0, 1.0])), _mt(R))
    return A, [1.0, 1.0, 2.0]


# ---------------------------------------------------------------------------
# Step 1: the symmetric eigendecomposition
# ---------------------------------------------------------------------------

def check_symmetric_eigen() -> None:
    from spectral import jacobi_eigh

    A = [[2.0, 1.0], [1.0, 2.0]]
    evals, Q = jacobi_eigh(A)
    assert len(evals) == 2, f"expected 2 eigenvalues, got {len(evals)}"
    assert all(evals[i] <= evals[i + 1] + 1e-12 for i in range(len(evals) - 1)), \
        f"eigenvalues must ascend, got {evals}"
    assert abs(evals[0] - 1.0) < 1e-9 and abs(evals[1] - 3.0) < 1e-9, \
        f"eigenvalues of [[2,1],[1,2]] are 1 and 3, got {evals}"
    assert _gram_ok(Q), "the eigenvector matrix Q must have orthonormal columns"
    assert _recon_cols(_mm(_mm(Q, _diag(evals)), _mt(Q)), A, 1e-9), \
        "A = Q diag(evals) Q^T must reconstruct A"

    B = [[2.0, 1.0, 0.0], [1.0, 2.0, 1.0], [0.0, 1.0, 2.0]]
    evals, Q = jacobi_eigh(B)
    assert abs(sum(evals) - 6.0) < 1e-9, f"the trace is the eigenvalue sum, got {sum(evals)}"
    assert _gram_ok(Q), "Q must stay orthonormal on a 3x3"
    assert _recon_cols(_mm(_mm(Q, _diag(evals)), _mt(Q)), B, 1e-9), \
        "A = Q diag(evals) Q^T must hold for a 3x3"


# ---------------------------------------------------------------------------
# Step 2: an orthonormal eigenbasis, and the orthogonality test
# ---------------------------------------------------------------------------

def check_orthonormal_basis() -> None:
    from spectral import orthonormal_eigenbasis, is_orthogonal

    A = [[2.0, 1.0], [1.0, 2.0]]
    evals, Q = orthonormal_eigenbasis(A)
    assert _gram_ok(Q, TOL), "eigenvectors must be orthonormal to 1e-10"
    assert is_orthogonal(Q), "is_orthogonal must agree that Q is orthogonal"
    assert _recon_cols(_mm(_mm(Q, _diag(evals)), _mt(Q)), A, 1e-9), \
        "A = Q diag(evals) Q^T must hold"

    # The test itself: not everything orthogonal-looking is orthogonal.
    assert is_orthogonal([[1.0, 0.0], [0.0, 1.0]]) is True, "the identity is orthogonal"
    assert is_orthogonal([[1.0, 1.0], [1.0, 1.0]]) is False, \
        "a matrix whose columns are not orthonormal must be rejected"


# ---------------------------------------------------------------------------
# Step 3: a repeated eigenvalue (the limit case)
# ---------------------------------------------------------------------------

def check_repeated_eigenvalue() -> None:
    from spectral import orthonormal_eigenbasis, is_orthogonal

    A, expected = _rotated_repeated()
    evals, Q = orthonormal_eigenbasis(A)
    # The eigenvalue MULTISET must match; the basis must not be assumed fixed.
    assert all(abs(evals[i] - expected[i]) < 1e-9 for i in range(3)), \
        f"eigenvalues must be {expected}, got {evals}"
    # The repeated eigenvalue 1 has multiplicity 2.
    mult = sum(1 for e in evals if abs(e - 1.0) < 1e-9)
    assert mult == 2, f"eigenvalue 1 must have multiplicity 2, got {mult}"
    assert is_orthogonal(Q) and _gram_ok(Q), \
        "on a repeated eigenvalue the returned basis must still be orthonormal"
    assert _recon_cols(_mm(_mm(Q, _diag(evals)), _mt(Q)), A, 1e-9), \
        "A = Q diag(evals) Q^T must hold; the basis is valid even if it is not the one you expected"


# ---------------------------------------------------------------------------
# Step 4: positive operators and square roots
# ---------------------------------------------------------------------------

def check_positive_sqrt() -> None:
    from spectral import positive_sqrt

    A = [[4.0, 2.0], [2.0, 3.0]]
    root = positive_sqrt(A)
    assert _symmetric(root, 1e-9), "the square root must be symmetric"
    assert _recon_cols(_mm(root, root), A, 1e-9), "sqrt(A) sqrt(A) must be A"
    assert _psd_probe(root), "the square root of a PSD matrix must be PSD"

    # A genuinely negative eigenvalue must raise, not be silently absolutised.
    raised = False
    try:
        positive_sqrt([[1.0, 0.0], [0.0, -1.0]])
    except ValueError:
        raised = True
    assert raised, "a matrix with a negative eigenvalue is not PSD and must raise ValueError"


# ---------------------------------------------------------------------------
# Step 5: the polar decomposition
# ---------------------------------------------------------------------------

def check_polar() -> None:
    from spectral import polar_decomposition

    for A in ([[3.0, 1.0], [1.0, 2.0]], [[1.0, 2.0], [3.0, 4.0]]):
        Q, P = polar_decomposition(A)
        assert _gram_ok(Q, TOL), "Q must be orthogonal to 1e-10"
        assert _symmetric(P, 1e-9), "P must be symmetric"
        assert _psd_probe(P), "P must be positive semidefinite"
        assert _recon_cols(_mm(Q, P), A, 1e-9), "A = Q P must reconstruct A"


# ---------------------------------------------------------------------------
# Step 6: the singular value decomposition
# ---------------------------------------------------------------------------

def check_svd() -> None:
    from spectral import svd

    A = [[3.0, 1.0], [1.0, 3.0]]
    U, S, Vt = svd(A)
    assert all(S[i] >= S[i + 1] - 1e-12 for i in range(len(S) - 1)), \
        f"singular values must descend, got {S}"
    assert _gram_ok(U, TOL), "U must have orthonormal columns"
    assert _gram_ok(Vt, TOL), "V (the rows of Vt) must be orthonormal"
    # A = U diag(S) V^T with U m x n, diag(S) n x n, Vt n x n.
    recon = _mm(U, _mm(_diag(S), Vt))
    assert _max_abs(recon, A) <= 1e-9, "A = U diag(S) V^T must reconstruct A"
    assert abs(S[0] - 4.0) < 1e-8, \
        f"largest singular value of [[3,1],[1,3]] is 4, got {S[0]}"

    # A rank-deficient matrix: the zero singular value must not produce a NaN in U.
    R = [[1.0, 1.0], [1.0, 1.0]]
    U, S, Vt = svd(R)
    assert abs(S[0] - 2.0) < 1e-9 and abs(S[1]) < 1e-9, f"singular values of rank-1 must be [2, 0], got {S}"
    assert _gram_ok(U, TOL), "U must be orthonormal even with a zero singular value"
    recon = _mm(U, _mm(_diag(S), Vt))
    assert _max_abs(recon, R) <= 1e-9, "the rank-deficient factorisation must still reconstruct A"


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("spectral.py", "the symmetric eigendecomposition", check_symmetric_eigen),
    ("spectral.py", "an orthonormal eigenbasis, and the orthogonality test", check_orthonormal_basis),
    ("spectral.py", "a repeated eigenvalue (any basis of the eigenspace)", check_repeated_eigenvalue),
    ("spectral.py", "positive operators and square roots", check_positive_sqrt),
    ("spectral.py", "the polar decomposition A = Q P", check_polar),
    ("spectral.py", "the singular value decomposition", check_svd),
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
    print(f"\n{BOLD}The Spectral Theorem From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built the spectral theorem from scratch.{RESET}")
        print(f"  {GREY}Run solutions/spectral.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
