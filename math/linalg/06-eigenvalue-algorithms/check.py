"""
Progress checker for the eigenvalue-algorithms templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

Every reference value is computed here, independently of the code under test. The
checker carries its own cyclic Jacobi symmetric eigensolver as the numerical oracle and
its own exact linear algebra; it never calls the solution's ``jacobi_reference``.

ENVIRONMENT ADAPTATION (named, not silent). The skill-tree node's acceptance line asks
that eigenvalues match ``numpy.linalg.eigvalsh`` to 1e-10; numpy is not available here.
The numpy oracle is therefore replaced by (a) this file's own cyclic Jacobi solver run at
1e-15, and (b) a small set of symmetric matrices whose spectra are known exactly
(rational) and are stated in the checks. The 1e-10 agreement requirement is unchanged.
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


# ---------------------------------------------------------------------------
# This file's own linear algebra (independent of the code under test)
# ---------------------------------------------------------------------------

def _matmul(A, B):
    n, k, m = len(A), len(B), len(B[0])
    return [[sum(A[i][t] * B[t][j] for t in range(k)) for j in range(m)] for i in range(n)]


def _transpose(A):
    return [list(row) for row in zip(*A)]


def _matvec(A, v):
    return [sum(A[i][j] * v[j] for j in range(len(v))) for i in range(len(A))]


def _norm(v):
    return math.sqrt(sum(x * x for x in v))


def _max_abs(M):
    return max((abs(x) for row in M for x in row), default=0.0)


def _identity(n):
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _jacobi_eigenvalues(A, tol=1e-15, maxit=300):
    """Cyclic Jacobi eigenvalues of a symmetric matrix, ascending (this file's oracle).

    Independent of the QR iteration being tested: it is a different algorithm, taken to a
    tolerance tight enough to serve as a reference at 1e-10. The stopping rule is on the
    off-diagonal norm relative to the diagonal scale.
    """
    n = len(A)
    a = [list(map(float, row)) for row in A]
    for i in range(n):
        for j in range(i + 1, n):
            avg = 0.5 * (a[i][j] + a[j][i])
            a[i][j] = a[j][i] = avg
    for _ in range(maxit):
        off = math.sqrt(sum(a[i][j] ** 2 for i in range(n) for j in range(n) if i != j))
        diag = max((abs(a[i][i]) for i in range(n)), default=1.0) or 1.0
        if off <= tol * diag:
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


def _close_multiset(got, expected, tol):
    """Greedy nearest-match of two multisets within a tolerance."""
    if len(got) != len(expected):
        return False
    remaining = list(expected)
    for g in got:
        best = min(range(len(remaining)), key=lambda i: abs(remaining[i] - g))
        if abs(remaining[best] - g) > tol:
            return False
        remaining.pop(best)
    return True


def _random_matrix(rng, n, lo=-9, hi=9):
    return [[float(rng.randint(lo, hi)) for _ in range(n)] for _ in range(n)]


def _random_symmetric(rng, n, lo=-9, hi=9):
    M = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i, n):
            M[i][j] = M[j][i] = float(rng.randint(lo, hi))
    return M


def _tail_exponent(errors):
    """The last local exponent ``log e_{k+1} / log e_k`` in the asymptotic range.

    For a cubically convergent sequence this tends to 3; for a linearly convergent one it
    stays near 1. The checker keeps the positives above the rounding floor and below 1,
    and returns the ratio at the largest such k.
    """
    e = [x for x in errors if x > 1e-12]
    ratios = []
    for k in range(len(e) - 1):
        if e[k] < 1.0 and e[k + 1] < e[k]:
            ratios.append(math.log(e[k + 1]) / math.log(e[k]))
    return ratios[-1] if ratios else float("nan")


# ---------------------------------------------------------------------------
# Step 1: reduction to upper Hessenberg form (accept: exact similarity + orthogonality)
# ---------------------------------------------------------------------------

def check_hessenberg() -> None:
    from eigenalg import hessenberg

    rng = random.Random(1101)
    matrices = [
        [[4.0, 1.0, -2.0, 2.0], [1.0, 2.0, 0.0, 1.0],
         [-2.0, 0.0, 3.0, -2.0], [2.0, 1.0, -2.0, -1.0]],
        [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 10.0]],
        [[0.0, 0.0, 0.0], [1.0, 2.0, 0.0], [0.0, 3.0, 4.0]],   # zero first column
    ]
    for _ in range(8):
        matrices.append(_random_matrix(rng, rng.randint(3, 6)))

    for A in matrices:
        n = len(A)
        Q, H = hessenberg(A)
        assert len(H) == n and all(len(row) == n for row in H), "H must be n x n"
        assert len(Q) == n and all(len(row) == n for row in Q), "Q must be n x n"
        orth = _max_abs([[sum(Q[k][i] * Q[k][j] for k in range(n)) - (1.0 if i == j else 0.0)
                          for j in range(n)] for i in range(n)])
        assert orth < 1e-12, (
            f"Q is not orthogonal: max|Q^T Q - I| = {orth:.3e}. Householder reflectors are "
            "orthogonal by construction, so the accumulated Q has lost a reflector or the "
            "wrong sign was used")
        below = max((abs(H[i][j]) for i in range(n) for j in range(n) if i > j + 1),
                    default=0.0)
        assert below < 1e-12, (
            f"H is not upper Hessenberg: max entry below the subdiagonal is {below:.3e}. "
            "Every column must be annihilated below row k+1")
        recon = _matmul(_matmul(Q, H), _transpose(Q))
        err = max(abs(recon[i][j] - A[i][j]) for i in range(n) for j in range(n))
        assert err < 1e-12, (
            f"Q H Q^T != A: max|Q H Q^T - A| = {err:.3e}. This is a SIMILARITY, so the "
            "reflector must be applied on BOTH sides (H <- H_k A H_k); applying it on one "
            "side only gives an orthogonal but non-similar reduction")


# ---------------------------------------------------------------------------
# Step 2: symmetric reduction to tridiagonal form
# ---------------------------------------------------------------------------

def check_tridiagonalize() -> None:
    from eigenalg import tridiagonalize

    rng = random.Random(1202)
    matrices = [
        [[4.0, 1.0, -2.0, 2.0], [1.0, 2.0, 0.0, 1.0],
         [-2.0, 0.0, 3.0, -2.0], [2.0, 1.0, -2.0, -1.0]],
        [[2.0, 1.0, 0.0], [1.0, 3.0, 1.0], [0.0, 1.0, 4.0]],
    ]
    for _ in range(8):
        matrices.append(_random_symmetric(rng, rng.randint(3, 6)))

    for A in matrices:
        n = len(A)
        Q, T = tridiagonalize(A)
        assert len(T) == n and all(len(row) == n for row in T), "T must be n x n"
        orth = _max_abs([[sum(Q[k][i] * Q[k][j] for k in range(n)) - (1.0 if i == j else 0.0)
                          for j in range(n)] for i in range(n)])
        assert orth < 1e-12, f"Q is not orthogonal: max|Q^T Q - I| = {orth:.3e}"
        sym = max(abs(T[i][j] - T[j][i]) for i in range(n) for j in range(n))
        assert sym < 1e-12, (
            f"T is not symmetric: max|T - T^T| = {sym:.3e}. A symmetric input under an "
            "orthogonal similarity stays symmetric")
        off = max((abs(T[i][j]) for i in range(n) for j in range(n) if abs(i - j) > 1),
                  default=0.0)
        assert off < 1e-12, (
            f"T is not tridiagonal: max entry with |i-j| > 1 is {off:.3e}. Every reflector "
            "from k = 0 to n-3 must be applied; skipping the last one leaves an entry below "
            "the subdiagonal in the final column")
        recon = _matmul(_matmul(Q, T), _transpose(Q))
        err = max(abs(recon[i][j] - A[i][j]) for i in range(n) for j in range(n))
        assert err < 1e-12, f"Q T Q^T != A: max error {err:.3e}"


# ---------------------------------------------------------------------------
# Step 3: the shifted QR algorithm (accept: independent reference to 1e-10)
# ---------------------------------------------------------------------------

def check_qr_eigenvalues() -> None:
    from eigenalg import qr_algorithm

    # Known exact spectra (rational), independent of any solver.
    known = [
        ([[2.0, 1.0, 1.0], [1.0, 2.0, 1.0], [1.0, 1.0, 2.0]], [4.0, 1.0, 1.0]),
        ([[0.0, 1.0], [1.0, 0.0]], [-1.0, 1.0]),
        ([[1.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 3.0]], [1.0, 2.0, 3.0]),
    ]
    for A, expected in known:
        got, _ = qr_algorithm(A, "wilkinson", maxit=2000)
        assert _close_multiset(got, expected, 1e-10), (
            f"qr_algorithm({A}, 'wilkinson') = {got}, expected the exact spectrum "
            f"{expected}: the iteration must run on the off-diagonal block, not read the "
            "diagonal of A")

    rng = random.Random(1303)
    worst = 0.0
    for _ in range(40):
        n = rng.randint(3, 6)
        A = _random_symmetric(rng, n)
        got, iters = qr_algorithm(A, "wilkinson", maxit=3000)
        ref = _jacobi_eigenvalues(A)
        assert len(got) == n, f"expected {n} eigenvalues, got {len(got)}"
        err = max(abs(g - r) for g, r in zip(sorted(got), ref))
        worst = max(worst, err)
        assert err < 1e-10, (
            f"shifted QR eigenvalue error {err:.3e} on random symmetric {A} exceeds 1e-10 "
            f"(got {got}, independent Jacobi reference {ref}). The agreement with an "
            "independent symmetric solver to 1e-10 is the ACCEPT line of this node "
            "(numpy.linalg.eigvalsh replaced by this checker's own Jacobi oracle)")
    assert worst < 1e-10


# ---------------------------------------------------------------------------
# Step 4: Rayleigh quotient iteration (ACCEPT: local cubic convergence)
# ---------------------------------------------------------------------------

def check_rayleigh_cubic() -> None:
    from eigenalg import rayleigh_quotient_iteration

    cases = [
        ([[1.0, 1.0, 0.0, 0.0], [1.0, 2.0, 1.0, 0.0],
          [0.0, 1.0, 3.0, 1.0], [0.0, 0.0, 1.0, 4.0]], [1.0, 1.0, 1.0, 1.0]),
        ([[2.0, 1.0, 0.0], [1.0, 3.0, 1.0], [0.0, 1.0, 4.0]], [1.0, 1.0, 1.0]),
        ([[2.0, 1.0], [1.0, 2.0]], [1.0, 0.3]),
    ]
    exponents = []
    for A, v0 in cases:
        lam, v, errors = rayleigh_quotient_iteration(A, v0)
        n = len(A)
        assert len(v) == n, f"eigenvector must have length {n}, got {len(v)}"
        vn = _norm(v)
        assert abs(vn - 1.0) < 1e-9, f"eigenvector must be a unit vector, norm {vn:.6f}"
        Av = _matvec(A, v)
        residual = _norm([Av[i] - lam * v[i] for i in range(n)])
        assert residual < 1e-8, (
            f"Rayleigh quotient iteration returned lambda = {lam} with residual "
            f"{residual:.3e}: v must be an eigenvector, so A v = lambda v")
        ref = _jacobi_eigenvalues(A)
        nearest = min(ref, key=lambda r: abs(r - lam))
        assert abs(lam - nearest) < 1e-8, (
            f"Rayleigh quotient {lam} is not an eigenvalue (nearest independent value "
            f"{nearest}): the iteration must update the shift to the current quotient, "
            "not keep a fixed one")

        pos = [e for e in errors if e > 1e-12]
        assert len(pos) >= 3, (
            f"the error sequence {errors} has fewer than three terms above the rounding "
            "floor, so the convergence rate cannot be measured")
        decreasing = all(pos[k + 1] < pos[k] for k in range(len(pos) - 1))
        assert decreasing, f"the error sequence must decrease, got {errors}"

        exponent = _tail_exponent(errors)
        assert exponent == exponent, f"no usable error ratios in {errors}"
        exponents.append(exponent)

    best = max(exponents)
    assert best >= 2.5, (
        f"the observed convergence exponent is {best:.2f}; Rayleigh quotient iteration is "
        "CUBIC, so log e_{k+1} / log e_k must approach 3 (a fixed step, i.e. no quotient "
        f"update, is only linear and gives ~1). Error exponents: "
        f"{[round(x, 2) for x in exponents]}")
    assert best <= 6.0, (
        f"the observed exponent {best:.2f} is implausibly large; the error sequence is not "
        "in the asymptotic regime")


# ---------------------------------------------------------------------------
# Step 5: the limit case — unshifted QR stalls, the Wilkinson shift fixes it
# ---------------------------------------------------------------------------

def check_limit_case_equal_magnitude() -> None:
    from eigenalg import qr_algorithm

    # Eigenvalues come in equal-magnitude pairs (1, -1) and (2, -2); the unshifted QR
    # iteration has no reason to separate either pair and stalls indefinitely.
    A = [[0.0, 1.0, 0.0, 0.0],
         [1.0, 0.0, 0.0, 0.0],
         [0.0, 0.0, 0.0, 2.0],
         [0.0, 0.0, 2.0, 0.0]]
    expected = [-2.0, -1.0, 1.0, 2.0]

    un_eigs, un_iters = qr_algorithm(A, "none", maxit=200)
    sh_eigs, sh_iters = qr_algorithm(A, "wilkinson", maxit=200)

    assert _close_multiset(sh_eigs, expected, 1e-8), (
        f"the Wilkinson shift failed to find the eigenvalues {expected}; got {sh_eigs}")
    assert sh_iters <= 20, (
        f"the Wilkinson shift took {sh_iters} sweeps on equal-magnitude eigenvalues; it "
        "should converge in a handful")
    assert un_iters >= 5 * max(sh_iters, 1), (
        f"the UNshifted QR iteration used only {un_iters} sweeps versus {sh_iters} for the "
        "Wilkinson shift. On equal-magnitude eigenvalues the unshifted iteration stalls "
        "(it is (strongly) linearly convergent at best), so it must need far more sweeps; "
        "a checker -- or an implementation -- that reports it as fast has erased the very "
        "limit case this node is about")
    assert un_iters >= 100, (
        f"the unshifted iteration converged in {un_iters} sweeps on equal-magnitude "
        "eigenvalues, but it should stall for the whole budget of 200")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("eigenalg.py", "Householder reduction to Hessenberg", check_hessenberg),
    ("eigenalg.py", "symmetric reduction to tridiagonal", check_tridiagonalize),
    ("eigenalg.py", "shifted QR eigenvalues vs independent reference", check_qr_eigenvalues),
    ("eigenalg.py", "Rayleigh quotient iteration converges cubically", check_rayleigh_cubic),
    ("eigenalg.py", "equal-magnitude stall vs the Wilkinson shift", check_limit_case_equal_magnitude),
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
    print(f"\n{BOLD}Eigenvalue Algorithms From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built the eigenvalue algorithms from scratch.{RESET}")
        print(f"  {GREY}Run solutions/eigenalg.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
