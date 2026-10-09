"""
Progress checker for the vector-calculus templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

Every reference value is recomputed here — closed form where one exists, otherwise an
independent central difference — so the checker never asks your own code what the right
answer is.
"""

import math
import pathlib
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
# This file's own arithmetic (independent of the learner's)
# ---------------------------------------------------------------------------

def _dot(u, v):
    return sum(a * b for a, b in zip(u, v))


def _matvec(A, v):
    return [sum(A[i][j] * v[j] for j in range(len(v))) for i in range(len(A))]


def _matmul(A, B):
    return [[sum(A[i][t] * B[t][j] for t in range(len(B))) for j in range(len(B[0]))]
            for i in range(len(A))]


def _transpose(A):
    return [list(row) for row in zip(*A)]


def _maxabs(M):
    return max(abs(v) for row in M for v in row)


def _diff(A, B):
    return max(abs(A[i][j] - B[i][j]) for i in range(len(A)) for j in range(len(A[0])))


def _add(A, B):
    return [[A[i][j] + B[i][j] for j in range(len(A[0]))] for i in range(len(A))]


def _scale(A, s):
    return [[s * A[i][j] for j in range(len(A[0]))] for i in range(len(A))]


def _det(A):
    n = len(A)
    M = [list(row) for row in A]
    det = 1.0
    for col in range(n):
        p = max(range(col, n), key=lambda i: abs(M[i][col]))
        if abs(M[p][col]) <= 1e-12:
            return 0.0
        if p != col:
            M[col], M[p] = M[p], M[col]
            det = -det
        det *= M[col][col]
        for i in range(col + 1, n):
            f = M[i][col] / M[col][col]
            M[i] = [M[i][j] - f * M[col][j] for j in range(n)]
    return det


def _inverse(A):
    n = len(A)
    M = [list(A[i]) + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for col in range(n):
        p = max(range(col, n), key=lambda i: abs(M[i][col]))
        if abs(M[p][col]) <= 1e-12:
            raise ValueError("singular")
        M[col], M[p] = M[p], M[col]
        pv = M[col][col]
        M[col] = [v / pv for v in M[col]]
        for i in range(n):
            if i != col:
                f = M[i][col]
                if f:
                    M[i] = [a - f * b for a, b in zip(M[i], M[col])]
    return [row[n:] for row in M]


def _fd_gradient(f, x, h):
    """The checker's own central-difference gradient (and the reference formula)."""
    grad = []
    for j in range(len(x)):
        xp = list(x)
        xp[j] += h
        xm = list(x)
        xm[j] -= h
        grad.append((f(xp) - f(xm)) / (2.0 * h))
    return grad


def _rel(got, ref):
    scale = max(1e-12, max(abs(v) for v in ref))
    return max(abs(a - b) for a, b in zip(got, ref)) / scale


# ---------------------------------------------------------------------------
# Step 1: gradient of xᵀAx is (A + Aᵀ)x, also for non-symmetric A (limit case)
# ---------------------------------------------------------------------------

def check_quadratic_gradient() -> None:
    from vector_calculus import quadratic_gradient

    A = [[2.0, 5.0], [1.0, 3.0]]          # deliberately non-symmetric
    x = [1.5, -2.0]
    got = quadratic_gradient(A, x)

    S = [[A[i][j] + A[j][i] for j in range(2)] for i in range(2)]
    expected = _matvec(S, x)
    assert max(abs(got[i] - expected[i]) for i in range(2)) < 1e-10, (
        f"quadratic_gradient(A, x) = {got}, expected (A + Aᵀ)x = {expected}. "
        "The gradient of xᵀAx is (A + Aᵀ)x for ANY square A, not 2Ax.")

    twice = [2.0 * v for v in _matvec(A, x)]
    assert max(abs(got[i] - twice[i]) for i in range(2)) > 1e-6, (
        "for this non-symmetric A the result equals 2Ax: the symmetrisation term "
        "(A + Aᵀ)x is missing (it coincides with 2Ax only when A is symmetric)")

    Sym = [[2.0, 1.0], [1.0, 4.0]]
    gs = quadratic_gradient(Sym, x)
    twice_s = [2.0 * v for v in _matvec(Sym, x)]
    assert max(abs(gs[i] - twice_s[i]) for i in range(2)) < 1e-10, (
        "for a symmetric A the gradient must reduce to 2Ax")

    f = lambda v: _dot(v, _matvec(A, v))
    assert _rel(got, _fd_gradient(f, x, 1e-6)) < 1e-6, (
        "the quadratic gradient disagrees with central differences")


# ---------------------------------------------------------------------------
# Step 2: gradient of ‖Ax − b‖², and its sign
# ---------------------------------------------------------------------------

def check_least_squares_gradient() -> None:
    from vector_calculus import least_squares_gradient

    A = [[1.0, 2.0], [0.0, 1.0], [2.0, -1.0]]     # 3×2, so Aᵀ is really used
    b = [1.0, -1.0, 2.0]
    x = [0.5, 1.5]
    got = least_squares_gradient(A, b, x)

    r = [sum(A[i][j] * x[j] for j in range(2)) - b[i] for i in range(3)]
    expected = [2.0 * sum(A[i][j] * r[i] for i in range(3)) for j in range(2)]
    assert max(abs(got[j] - expected[j]) for j in range(2)) < 1e-10, (
        f"least_squares_gradient = {got}, expected 2Aᵀ(Ax − b) = {expected}: "
        "the residual must be A x − b, not b − A x")

    f = lambda v: sum((sum(A[i][j] * v[j] for j in range(2)) - b[i]) ** 2
                      for i in range(3))
    assert _rel(got, _fd_gradient(f, x, 1e-6)) < 1e-6, (
        "the least-squares gradient disagrees with central differences")

    t = 1e-3
    xm = [x[j] - t * got[j] for j in range(2)]
    xp = [x[j] + t * got[j] for j in range(2)]
    assert f(xm) < f(x) < f(xp), (
        f"f(x − t∇f) = {f(xm):.6f} must be below f(x) = {f(x):.6f}: the gradient sign "
        "is flipped (a gradient points uphill)")


# ---------------------------------------------------------------------------
# Step 3: gradient of log det X is X⁻ᵀ (transpose matters for non-symmetric X)
# ---------------------------------------------------------------------------

def check_logdet_gradient() -> None:
    from vector_calculus import logdet_gradient

    X = [[2.0, 1.0, 0.0], [0.5, 3.0, 1.0], [0.0, 1.5, 2.0]]   # non-symmetric, det = 8
    assert _det(X) > 0.0, "the test matrix must have positive determinant"
    got = logdet_gradient(X)

    ref = _transpose(_inverse(X))
    err = _diff(got, ref)
    assert err < 1e-9, (
        f"logdet_gradient wrong by {err:.2e}; expected X⁻ᵀ, the transpose of the inverse "
        "(which differs from X⁻¹ unless X is symmetric)")

    E = [[0.3, -0.7, 0.2], [0.5, 0.1, -0.4], [-0.2, 0.6, 0.9]]
    h = 1e-6
    Xp = _add(X, _scale(E, h))
    Xm = _add(X, _scale(E, -h))
    num = (math.log(_det(Xp)) - math.log(_det(Xm))) / (2.0 * h)
    ana = sum(got[i][j] * E[i][j] for i in range(3) for j in range(3))
    rel = abs(num - ana) / max(1.0, abs(ana))
    assert rel < 1e-6, (
        f"the log-det gradient fails the directional central difference (rel {rel:.2e})")


# ---------------------------------------------------------------------------
# Step 4: gradient of tr(A X) is Aᵀ
# ---------------------------------------------------------------------------

def check_trace_linear_gradient() -> None:
    from vector_calculus import trace_linear_gradient

    A = [[2.0, 5.0], [1.0, 3.0]]          # non-symmetric
    got = trace_linear_gradient(A)
    assert _diff(got, _transpose(A)) < 1e-12, (
        f"gradient of tr(AX) w.r.t. X is Aᵀ = {_transpose(A)}, not A = {A}: "
        "the transpose is required when A is not symmetric")

    X = [[0.7, -0.3], [0.4, 1.2]]
    E = [[0.5, 0.9], [-0.2, 0.3]]
    h = 1e-6
    f = lambda M: sum(A[i][j] * M[j][i] for i in range(2) for j in range(2))
    num = (f(_add(X, _scale(E, h))) - f(_add(X, _scale(E, -h)))) / (2.0 * h)
    ana = sum(got[i][j] * E[i][j] for i in range(2) for j in range(2))
    assert abs(num - ana) / max(1.0, abs(ana)) < 1e-6, (
        "the trace-linear gradient fails the directional central difference")


# ---------------------------------------------------------------------------
# Step 5: gradient of tr(XᵀA X) is (A + Aᵀ)X
# ---------------------------------------------------------------------------

def check_trace_quadratic_gradient() -> None:
    from vector_calculus import trace_quadratic_gradient

    A = [[2.0, 5.0], [1.0, 3.0]]          # non-symmetric
    X = [[0.7, -0.3], [0.4, 1.2]]
    got = trace_quadratic_gradient(A, X)

    S = [[A[i][j] + A[j][i] for j in range(2)] for i in range(2)]
    expected = _matmul(S, X)
    assert _diff(got, expected) < 1e-10, (
        f"gradient of tr(XᵀAX) = {got}, expected (A + Aᵀ)X = {expected}")

    AX = _matmul(A, X)
    assert _diff(got, AX) > 1e-6, (
        "the result equals AX: the symmetrisation term (A + Aᵀ) is missing")

    E = [[0.5, 0.9], [-0.2, 0.3]]
    h = 1e-6
    f = lambda M: sum(M[i][k] * A[i][j] * M[j][k]
                      for i in range(2) for j in range(2) for k in range(2))
    num = (f(_add(X, _scale(E, h))) - f(_add(X, _scale(E, -h)))) / (2.0 * h)
    ana = sum(got[i][j] * E[i][j] for i in range(2) for j in range(2))
    assert abs(num - ana) / max(1.0, abs(ana)) < 1e-6, (
        "the trace-quadratic gradient fails the directional central difference")


# ---------------------------------------------------------------------------
# Step 6: the shared central-difference checker (accept: relative error 1e-6)
# ---------------------------------------------------------------------------

def check_finite_difference_accuracy() -> None:
    from vector_calculus import (central_difference, relative_gradient_error,
                                 quadratic_gradient, least_squares_gradient)

    def cubic(x):
        return sum(v ** 3 for v in x) / 3.0

    def cubic_grad(x):
        return [v * v for v in x]

    x = [1.5, -2.0, 0.5]
    h = 1e-6
    got = central_difference(cubic, x, h)
    ref = _fd_gradient(cubic, x, h)
    assert max(abs(a - b) for a, b in zip(got, ref)) < 1e-12, (
        f"central_difference = {got} does not match the central-difference definition "
        f"{ref}: it looks like a one-sided (forward/backward) difference")

    err = relative_gradient_error(cubic, cubic_grad, x, 1e-5)
    assert err < 1e-7, (
        f"relative error {err:.2e} at h=1e-5: central differences are O(h²) (≈1e-11), "
        "whereas forward differences are O(h) (≈1e-5). Check the sign in the second "
        "function evaluation of central_difference.")

    A = [[2.0, 5.0], [1.0, 3.0]]
    xq = [1.5, -2.0]
    fq = lambda v: _dot(v, _matvec(A, v))
    gq = lambda v: quadratic_gradient(A, v)
    assert relative_gradient_error(fq, gq, xq, 1e-6) < 1e-6, (
        "the quadratic-form gradient does not match central differences to 1e-6")

    A2 = [[1.0, 2.0], [0.0, 1.0], [2.0, -1.0]]
    b2 = [1.0, -1.0, 2.0]
    xl = [0.5, 1.5]
    fl = lambda v: sum((sum(A2[i][j] * v[j] for j in range(2)) - b2[i]) ** 2
                       for i in range(3))
    gl = lambda v: least_squares_gradient(A2, b2, v)
    assert relative_gradient_error(fl, gl, xl, 1e-6) < 1e-6, (
        "the least-squares gradient does not match central differences to 1e-6")


# ---------------------------------------------------------------------------
# Step 7: the Hessian of xᵀAx is A + Aᵀ
# ---------------------------------------------------------------------------

def check_quadratic_hessian() -> None:
    from vector_calculus import quadratic_gradient, quadratic_hessian

    A = [[2.0, 5.0], [1.0, 3.0]]          # non-symmetric
    got = quadratic_hessian(A)
    ref = [[A[i][j] + A[j][i] for j in range(2)] for i in range(2)]
    assert _diff(got, ref) < 1e-12, (
        f"quadratic_hessian(A) = {got}, expected A + Aᵀ = {ref}")

    assert _diff(got, A) > 1e-6, (
        "the Hessian equals A: the symmetrisation term was dropped (a Hessian is "
        "always symmetric)")

    x = [1.5, -2.0]
    h = 1e-4
    num = [[0.0, 0.0], [0.0, 0.0]]
    for j in range(2):
        xp = list(x)
        xp[j] += h
        xm = list(x)
        xm[j] -= h
        gp = quadratic_gradient(A, xp)
        gm = quadratic_gradient(A, xm)
        for i in range(2):
            num[i][j] = (gp[i] - gm[i]) / (2.0 * h)
    assert _diff(got, num) < 1e-6, (
        f"the analytic Hessian {got} disagrees with central differences of the "
        f"gradient {num}")


# ---------------------------------------------------------------------------
# Step 8: second-order Taylor remainder shrinks as h³ (accept criterion)
# ---------------------------------------------------------------------------

def check_second_order_taylor() -> None:
    from vector_calculus import taylor_second_order

    def f(x):
        return sum(v ** 3 for v in x) / 3.0

    def g(x):
        return [v * v for v in x]

    def H(x):
        return [[2.0 * v if i == j else 0.0 for j, v in enumerate(x)]
                for i in range(len(x))]

    x = [1.5, -2.0, 0.5]
    d = [0.7, -0.4, 0.9]

    def err(h):
        p = [h * c for c in d]
        return abs(f([x[i] + p[i] for i in range(3)])
                   - taylor_second_order(f, g, H, x, p))

    e1, e2, e3 = err(0.05), err(0.025), err(0.1)
    assert e2 < e1 < e3, (
        f"the Taylor remainder must grow with h: err(0.025) = {e2:.2e}, "
        f"err(0.05) = {e1:.2e}, err(0.1) = {e3:.2e}")
    ratio = e1 / e2
    assert 7.0 < ratio < 9.0, (
        f"err(0.05)/err(0.025) = {ratio:.3f}, expected ≈ 8: the remainder of a "
        "second-order Taylor expansion is O(h³). Missing the ½ in the quadratic term "
        "(or dropping it) leaves an O(h²) remainder, whose ratio is ≈ 4.")

    # For a quadratic form the second-order expansion is exact.
    A = [[2.0, 1.0], [1.0, 3.0]]
    S = [[A[i][j] + A[j][i] for j in range(2)] for i in range(2)]
    fq = lambda v: _dot(v, _matvec(A, v))
    gq = lambda v: _matvec(S, v)
    Hq = lambda v: S
    xx, pp = [0.8, -1.3], [0.11, -0.07]
    exact = fq([xx[i] + pp[i] for i in range(2)])
    approx = taylor_second_order(fq, gq, Hq, xx, pp)
    assert abs(exact - approx) < 1e-10, (
        "for a quadratic form the second-order Taylor expansion must be exact")


# ---------------------------------------------------------------------------
# Step 9: the U-shaped finite-difference error over h (limit case)
# ---------------------------------------------------------------------------

def check_error_curve_u_shaped() -> None:
    from vector_calculus import error_curve

    def f(x):
        return sum(v ** 3 for v in x) / 3.0

    def g(x):
        return [v * v for v in x]

    x = [1.5, -2.0, 0.5]
    hs = [1e-12, 1e-10, 1e-8, 1e-6, 1e-5, 1e-4, 1e-2, 1e-1]
    curve = error_curve(f, g, x, hs)
    assert [h for h, _ in curve] == hs, (
        "error_curve must return one (h, error) pair per requested h, in order")
    errs = {h: e for h, e in curve}

    best = min(curve, key=lambda pair: pair[1])[0]
    assert best not in (hs[0], hs[-1]), (
        f"the smallest error sits at h={best}: the sweep must have an interior minimum, "
        "with round-off dominating for tiny h and truncation for large h")

    assert errs[1e-5] < errs[1e-12], (
        f"error at h=1e-12 ({errs[1e-12]:.2e}) should exceed h=1e-5 "
        f"({errs[1e-5]:.2e}): for h too small, f(x+h) − f(x−h) cancels and round-off "
        "O(ε/h) dominates")
    assert errs[1e-5] < errs[1e-1], (
        f"error at h=1e-1 ({errs[1e-1]:.2e}) should exceed h=1e-5 "
        f"({errs[1e-5]:.2e}): for h too large the O(h²) truncation error dominates")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("vector_calculus.py", "∇(xᵀAx) = (A + Aᵀ)x, non-symmetric A", check_quadratic_gradient),
    ("vector_calculus.py", "∇‖Ax − b‖² = 2Aᵀ(Ax − b) and its sign", check_least_squares_gradient),
    ("vector_calculus.py", "∇ log det X = X⁻ᵀ", check_logdet_gradient),
    ("vector_calculus.py", "∇ tr(A X) = Aᵀ", check_trace_linear_gradient),
    ("vector_calculus.py", "∇ tr(XᵀA X) = (A + Aᵀ)X", check_trace_quadratic_gradient),
    ("vector_calculus.py", "central differences match every gradient to 1e-6", check_finite_difference_accuracy),
    ("vector_calculus.py", "Hessian of xᵀAx is A + Aᵀ", check_quadratic_hessian),
    ("vector_calculus.py", "second-order Taylor remainder shrinks as h³", check_second_order_taylor),
    ("vector_calculus.py", "finite-difference error is U-shaped in h", check_error_curve_u_shaped),
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
    print(f"\n{BOLD}Vector Calculus From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<16} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<16} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<16} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built vector calculus from scratch.{RESET}")
        print(f"  {GREY}Run solutions/vector_calculus.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
