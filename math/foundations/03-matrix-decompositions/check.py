"""
Progress checker for the matrix-decompositions templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

All reference values are computed here, independently of your code: exact rational
arithmetic (`fractions.Fraction`) for the integer Cholesky factor, and a 60-digit
`decimal` Jacobi eigensolver for the condition-number measurement. The spec's
`numpy.linalg.svd` comparison is impossible in this repository (no numpy, no pip, no
network); the high-precision Jacobi oracle replaces it and the README says why.
"""

import math
import pathlib
import random
import shutil
import sys
import traceback
from decimal import Decimal, getcontext
from fractions import Fraction

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


# ---------------------------------------------------------------------------
# This file's own arithmetic — never asks the learner's code for a reference.
# ---------------------------------------------------------------------------

def _dot(u, v):
    return sum(a * b for a, b in zip(u, v))


def _matvec(A, v):
    return [sum(A[i][j] * v[j] for j in range(len(v))) for i in range(len(A))]


def _matmul(A, B):
    return [[sum(A[i][t] * B[t][j] for t in range(len(B)))
             for j in range(len(B[0]))] for i in range(len(A))]


def _transpose(A):
    return [list(row) for row in zip(*A)]


def _norm(v):
    return math.sqrt(_dot(v, v))


def _maxabs(A):
    return max(abs(v) for row in A for v in row)


def _orthogonality_error(vectors):
    k = len(vectors)
    worst = 0.0
    for a in range(k):
        for b in range(k):
            worst = max(worst, abs(_dot(vectors[a], vectors[b]) - (1.0 if a == b else 0.0)))
    return worst


def _rand_spd(rng, n):
    """A well-conditioned random SPD matrix: B Bᵀ + n·I."""
    B = [[rng.uniform(-1, 1) for _ in range(n)] for _ in range(n)]
    A = _matmul(B, _transpose(B))
    for i in range(n):
        A[i][i] += n
    return A


def _spectral_norm(M, iters=2000):
    """Largest singular value of M, by this file's own power iteration on MᵀM."""
    G = _matmul(_transpose(M), M)
    n = len(G)
    v = [1.0 + 0.1 * i for i in range(n)]
    v = [x / _norm(v) for x in v]
    for _ in range(iters):
        w = _matvec(G, v)
        nw = _norm(w)
        if nw == 0.0:
            return 0.0
        v = [x / nw for x in w]
    return math.sqrt(max(0.0, _dot(v, _matvec(G, v))))


def _fraction_cholesky(A):
    """Exact Cholesky over Q, for an integer SPD matrix. Raises on a non-positive pivot."""
    n = len(A)
    L = [[Fraction(0)] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = Fraction(A[i][j]) - sum(L[i][k] * L[j][k] for k in range(j))
            if i == j:
                if s <= 0:
                    raise ValueError("not SPD")
                L[i][i] = _frac_sqrt(s)
            else:
                L[i][j] = s / L[j][j]
    return L


def _frac_sqrt(x):
    num = math.isqrt(x.numerator)
    den = math.isqrt(x.denominator)
    if num * num == x.numerator and den * den == x.denominator:
        return Fraction(num, den)
    raise ValueError("pivot is not a perfect square; use a different exact example")


def _decimal_eigenvalues(M, sweeps=200):
    """Eigenvalues of a symmetric matrix, in 60-digit decimal arithmetic (Jacobi).

    This is the high-precision oracle that replaces the spec's ``numpy.linalg.svd``:
    each float entry is converted exactly to Decimal, so the oracle answers for the
    matrix the program actually holds, to 60 significant digits.
    """
    getcontext().prec = 60
    n = len(M)
    A = [[Decimal(M[i][j]) for j in range(n)] for i in range(n)]
    one, two = Decimal(1), Decimal(2)
    for _ in range(sweeps):
        off = sum(A[i][j] * A[i][j] for i in range(n) for j in range(n) if i != j)
        if off < Decimal(10) ** -90:
            break
        for p in range(n):
            for q in range(p + 1, n):
                if A[p][q] == 0:
                    continue
                theta = (A[q][q] - A[p][p]) / (two * A[p][q])
                t = (one if theta >= 0 else -one) / (abs(theta) + (theta * theta + one).sqrt())
                c = one / (t * t + one).sqrt()
                s = t * c
                for k in range(n):
                    akp, akq = A[k][p], A[k][q]
                    A[k][p], A[k][q] = c * akp - s * akq, s * akp + c * akq
                for k in range(n):
                    apk, aqk = A[p][k], A[q][k]
                    A[p][k], A[q][k] = c * apk - s * aqk, s * apk + c * aqk
    return sorted((A[i][i] for i in range(n)), reverse=True)


# ---------------------------------------------------------------------------
# Step 1: Cholesky reconstructs an SPD matrix (accept criterion)
# ---------------------------------------------------------------------------

def check_cholesky_reconstructs() -> None:
    from decompositions import cholesky

    rng = random.Random(11)
    for n in (1, 2, 3, 5):
        A = _rand_spd(rng, n)
        L = cholesky(A)
        assert len(L) == n and all(len(row) == n for row in L), "L must be n×n"
        assert all(L[i][j] == 0.0 for i in range(n) for j in range(i + 1, n)), (
            "L must be lower triangular (zero above the diagonal)")
        assert all(L[i][i] > 0.0 for i in range(n)), (
            "the Cholesky diagonal must stay strictly positive")
        rec = _matmul(L, _transpose(L))
        err = _maxabs([[rec[i][j] - A[i][j] for j in range(n)] for i in range(n)])
        assert err < 1e-10, (
            f"max|A − LLᵀ| = {err:.2e} for n={n}, expected < 1e-10: L is not the "
            "Cholesky factor (check the order of the inner sum and the division by L[j][j])")

    # Exact oracle: this integer matrix has the integer factor L = [[2,0,0],[6,1,0],[-8,5,3]].
    A_int = [[4, 12, -16], [12, 37, -43], [-16, -43, 98]]
    L = cholesky([[float(v) for v in row] for row in A_int])
    Lex = _fraction_cholesky(A_int)
    err = max(abs(L[i][j] - float(Lex[i][j])) for i in range(3) for j in range(3))
    assert err < 1e-12, (
        f"the integer test matrix should give L = {[[str(Lex[i][j]) for j in range(3)] for i in range(3)]}, "
        f"got a factor off by {err:.2e}: check the pivot recurrence")


# ---------------------------------------------------------------------------
# Step 2: Cholesky refuses a non-SPD matrix, with no NaN (limit case)
# ---------------------------------------------------------------------------

def check_cholesky_rejects_non_spd() -> None:
    from decompositions import NotPositiveDefinite, cholesky

    bad = {
        "indefinite": [[1.0, 0.0], [0.0, -1.0]],
        "singular (PSD but not PD)": [[1.0, 1.0], [1.0, 1.0]],
        "non-symmetric": [[1.0, 2.0], [3.0, 4.0]],
        "non-square": [[1.0, 0.0], [0.0, 1.0], [0.0, 1.0]],
        "zero pivot": [[0.0, 0.0], [0.0, 1.0]],
    }
    for name, A in bad.items():
        try:
            L = cholesky(A)
        except NotPositiveDefinite:
            continue
        assert L is not None
        flat = [v for row in L for v in row]
        assert not any(math.isnan(v) for v in flat), (
            f"cholesky({A}) returned a NaN factor for a {name} matrix instead of raising "
            "NotPositiveDefinite: the positive-pivot test must come before math.sqrt")
        raise AssertionError(
            f"cholesky accepted a {name} matrix ({A}); a matrix with a non-positive pivot "
            "has no real Cholesky factor and must raise NotPositiveDefinite")


# ---------------------------------------------------------------------------
# Step 3: power iteration returns the dominant eigenpair (accept criterion)
# ---------------------------------------------------------------------------

def check_power_iteration_dominant() -> None:
    from decompositions import power_iteration

    # Eigenvalues 4, 2, 1; dominant 4 with eigenvector (1,1,0)/√2.
    A = [[3.0, 1.0, 0.0], [1.0, 3.0, 0.0], [0.0, 0.0, 1.0]]
    lam, v = power_iteration(A)
    assert abs(lam - 4.0) < 1e-8, (
        f"power iteration returned λ = {lam}, expected the dominant eigenvalue 4: "
        "did you divide by the eigenvalue instead of the vector norm?")
    assert abs(_norm(v) - 1.0) < 1e-9, "the eigenvector must be normalised"
    resid = _norm([_matvec(A, v)[i] - lam * v[i] for i in range(3)])
    assert resid < 1e-8, (
        f"‖Av − λv‖ = {resid:.2e}: the returned pair does not satisfy A v = λ v")

    B = [[2.0, -1.0], [-1.0, 2.0]]           # eigenvalues 3, 1; dominant 3
    lam, v = power_iteration(B)
    assert abs(lam - 3.0) < 1e-8, f"second matrix: λ = {lam}, expected 3"


# ---------------------------------------------------------------------------
# Step 4: equal-magnitude eigenvalues are detected, not papered over (limit case)
# ---------------------------------------------------------------------------

def check_power_iteration_no_convergence() -> None:
    from decompositions import NoConvergence, power_iteration

    # +1 and -1: equal magnitude. The Rayleigh quotient stands still while the vector
    # alternates, so a step-size test passes and only a residual test catches it.
    cases = [
        ([[1.0, 0.0], [0.0, -1.0]], [1.0, 1.0]),
        ([[0.0, 1.0], [1.0, 0.0]], [1.0, 0.3]),
        ([[2.0, 0.0, 0.0], [0.0, -2.0, 0.0], [0.0, 0.0, 0.5]], [1.0, 1.0, 1.0]),
    ]
    for A, start in cases:
        try:
            lam, v = power_iteration(A, start=start)
        except NoConvergence:
            continue
        # If it did not raise, it must at least satisfy the eigenpair equation.
        resid = _norm([_matvec(A, v)[i] - lam * v[i] for i in range(len(A))])
        raise AssertionError(
            f"power iteration returned (λ={lam:.4f}) for {A} with no dominant eigenvalue "
            f"(residual {resid:.2e}); the two largest eigenvalues have equal magnitude, so "
            "it must raise NoConvergence. A convergence test on λ alone misses this.")


# ---------------------------------------------------------------------------
# Step 5: deflation yields the whole spectrum (accept criterion + off-by-one)
# ---------------------------------------------------------------------------

def check_eigenpairs_symmetric() -> None:
    from decompositions import eigenpairs_symmetric

    A = [[3.0, 1.0, 0.5], [1.0, 2.0, 0.25], [0.5, 0.25, 0.0]]
    pairs = eigenpairs_symmetric(A, 3)
    assert len(pairs) == 3, (
        f"asked for 3 eigenpairs, got {len(pairs)}: the deflation loop must run exactly k "
        "times (an off-by-one here silently drops or duplicates a pair)")

    vectors = [v for _, v in pairs]
    oerr = _orthogonality_error(vectors)
    assert oerr < 1e-6, (
        f"max|VᵀV − I| = {oerr:.2e}: deflated eigenvectors must stay orthonormal; forgetting "
        "to subtract λ v vᵀ leaves the previous eigenvector dominant again")

    for lam, v in pairs:
        resid = _norm([_matvec(A, v)[i] - lam * v[i] for i in range(3)])
        assert resid < 1e-7, (
            f"eigenpair (λ={lam:.6f}) fails A v = λ v (residual {resid:.2e})")

    trace = sum(pairs[i][0] for i in range(3))
    ref = [float(x) for x in _decimal_eigenvalues(A)]
    assert abs(trace - sum(ref)) < 1e-8, (
        f"the eigenvalues sum to {trace}, but the trace is {sum(ref)}: deflation returned "
        "the wrong spectrum")
    got = sorted((lam for lam, _ in pairs), reverse=True)
    assert max(abs(got[i] - ref[i]) for i in range(3)) < 1e-6, (
        f"eigenvalues {got} do not match the reference {ref}: deflation is not removing "
        "the eigenpair it just found")


# ---------------------------------------------------------------------------
# Step 6: the SVD reconstructs A and its singular values are the spectrum of AᵀA
# ---------------------------------------------------------------------------

def check_svd_reconstructs() -> None:
    from decompositions import svd_via_ata

    U0 = [[1.0, 0.0, 0.0], [0.0, 0.6, 0.8], [0.0, 0.8, -0.6]]
    V0 = [[0.8, 0.6, 0.0], [-0.6, 0.8, 0.0], [0.0, 0.0, 1.0]]
    sig = [4.0, 2.0, 0.5]
    M = [[sum(sig[t] * U0[i][t] * V0[j][t] for t in range(3)) for j in range(3)]
         for i in range(3)]

    U, S, V = svd_via_ata(M)
    assert len(S) == 3, f"expected 3 singular values, got {len(S)}"
    assert all(S[i] >= S[i + 1] - 1e-12 for i in range(len(S) - 1)), (
        f"singular values {S} must come out in non-increasing order")
    assert max(abs(S[i] - sig[i]) for i in range(3)) < 1e-6, (
        f"singular values {S}, expected {sig}: they are sqrt(eigenvalues of AᵀA); "
        "did you forget the square root (or take a square)?")

    recon = [[sum(S[t] * U[t][i] * V[t][j] for t in range(len(S))) for j in range(3)]
             for i in range(3)]
    err = _maxabs([[recon[i][j] - M[i][j] for j in range(3)] for i in range(3)])
    assert err < 1e-8, (
        f"max|A − UΣVᵀ| = {err:.2e}: check that U[i] = A·V[i]/σ_i and that V is the "
        "eigenvector matrix of AᵀA")
    assert _orthogonality_error(V) < 1e-6, "V (right singular vectors) must be orthonormal"
    assert _orthogonality_error(U) < 1e-6, "U (left singular vectors) must be orthonormal"


# ---------------------------------------------------------------------------
# Step 7: Eckart-Young — rank-k error is the (k+1)-th singular value
# ---------------------------------------------------------------------------

def check_eckart_young() -> None:
    from decompositions import low_rank_approx

    U0 = [[1.0, 0.0, 0.0], [0.0, 0.6, 0.8], [0.0, 0.8, -0.6]]
    V0 = [[0.8, 0.6, 0.0], [-0.6, 0.8, 0.0], [0.0, 0.0, 1.0]]
    sig = [4.0, 2.0, 0.5]
    M = [[sum(sig[t] * U0[i][t] * V0[j][t] for t in range(3)) for j in range(3)]
         for i in range(3)]

    for k in (1, 2):
        Ak = low_rank_approx(M, k)
        R = [[M[i][j] - Ak[i][j] for j in range(3)] for i in range(3)]
        got = _spectral_norm(R)
        want = sig[k]                       # σ_{k+1}, with 0-based indexing
        assert abs(got - want) < 1e-6, (
            f"rank-{k} approximation error ‖A − A_{k}‖₂ = {got:.6e}, but Eckart-Young says "
            f"it must equal σ_{k + 1} = {want}: the approximation is keeping the wrong "
            "number of SVD terms (an off-by-one in k)")
    # k = 3 is exact.
    assert _maxabs([[low_rank_approx(M, 3)[i][j] - M[i][j] for j in range(3)]
                    for i in range(3)]) < 1e-8, "the full-rank approximation must be exact"


# ---------------------------------------------------------------------------
# Step 8: forming AᵀA squares the condition number (limit case, high-precision oracle)
# ---------------------------------------------------------------------------

def _ill_conditioned_pair():
    """A 2×2 matrix with singular values [1, 1e-7] (condition number 1e7)."""
    theta, phi, tiny = 0.7, 1.1, 1e-7
    c1, s1, c2, s2 = math.cos(theta), math.sin(theta), math.cos(phi), math.sin(phi)
    D = [[c1, -s1], [s1, c1]]
    P = [[c2, -s2], [s2, c2]]
    A = [[sum(D[i][t] * (1.0 if t == 0 else tiny) * P[j][t] for t in range(2))
          for j in range(2)] for i in range(2)]
    return A, tiny


def check_condition_number_loss() -> None:
    from decompositions import svd_via_ata

    A, tiny = _ill_conditioned_pair()
    gram = _matmul(_transpose(A), A)
    oracle = [math.sqrt(float(x)) if x > 0 else 0.0 for x in _decimal_eigenvalues(gram)]

    U, S, V = svd_via_ata(A)
    assert len(S) == 2, (
        f"expected 2 singular values, got {len(S)}: a computed singular value near zero was "
        "probably discarded, which hides exactly the loss this check measures")
    assert S[-1] > 0.0, (
        "the small singular value came back as 0: forming AᵀA squared the condition number "
        "(now 1e14), so the small eigenvalue is lost entirely — report the tiny value rather "
        "than clamping it to zero, and the check measures how wrong it is")

    rel_big = abs(S[0] - oracle[0]) / oracle[0]
    rel_small = abs(S[-1] - oracle[-1]) / oracle[-1]
    assert rel_big < 1e-12, (
        f"the large singular value is off by {rel_big:.2e}; even the well-separated one "
        "should be accurate")
    assert rel_small > 1e-5, (
        f"the small singular value has relative error {rel_small:.2e}. It should be "
        "catastrophically worse than the big one: AᵀA squares the condition number "
        "(κ(AᵀA) = κ(A)² = 1e14), so about κ²·ε ≈ 1e-2 relative error is expected. If it is "
        "accurate, you are not forming AᵀA or you are hiding the loss.")

    # A well-conditioned matrix is still accurate through the same path.
    U0 = [[1.0, 0.0, 0.0], [0.0, 0.6, 0.8], [0.0, 0.8, -0.6]]
    V0 = [[0.8, 0.6, 0.0], [-0.6, 0.8, 0.0], [0.0, 0.0, 1.0]]
    sig = [4.0, 2.0, 1.0]
    M = [[sum(sig[t] * U0[i][t] * V0[j][t] for t in range(3)) for j in range(3)]
         for i in range(3)]
    _, Sw, _ = svd_via_ata(M)
    assert max(abs(Sw[i] - sig[i]) for i in range(3)) < 1e-8, (
        f"well-conditioned singular values {Sw} should be accurate to 1e-8, got {Sw}")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("decompositions.py", "Cholesky reconstructs A = LLᵀ", check_cholesky_reconstructs),
    ("decompositions.py", "Cholesky rejects non-SPD (no NaN)", check_cholesky_rejects_non_spd),
    ("decompositions.py", "power iteration: dominant eigenpair A v = λ v", check_power_iteration_dominant),
    ("decompositions.py", "power iteration detects equal-magnitude eigenvalues", check_power_iteration_no_convergence),
    ("decompositions.py", "deflation yields the whole orthonormal spectrum", check_eigenpairs_symmetric),
    ("decompositions.py", "SVD reconstructs A and σ² = eig(AᵀA)", check_svd_reconstructs),
    ("decompositions.py", "Eckart-Young: rank-k error = σ_{k+1}", check_eckart_young),
    ("decompositions.py", "AᵀA squares the condition number (precision loss)", check_condition_number_loss),
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
    print(f"\n{BOLD}Matrix Decompositions From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built the decompositions from scratch.{RESET}")
        print(f"  {GREY}Run solutions/decompositions.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
