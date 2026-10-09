"""
Progress checker for the unconstrained-minimisation templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The checker keeps its own arithmetic: it solves the teaching quadratics itself
(``_gauss``) and knows the analytic optimum of every other problem, so a passing run
means the learned code agrees with numbers computed independently of it.
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

TOL = 1e-6


# ---------------------------------------------------------------------------
# The checker's own Gaussian elimination (reference arithmetic)
# ---------------------------------------------------------------------------

def _gauss(A, b):
    """Solve A x = b by Gaussian elimination with partial pivoting."""
    n = len(A)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-14:
            raise ValueError("singular")
        M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        for row in range(col + 1, n):
            factor = M[row][col] / pv
            for c in range(col, n + 1):
                M[row][c] -= factor * M[col][c]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        acc = M[i][n] - sum(M[i][j] * x[j] for j in range(i + 1, n))
        x[i] = acc / M[i][i]
    return x


# ---------------------------------------------------------------------------
# Teaching problems with known optima (reference arithmetic)
# ---------------------------------------------------------------------------

# Convex quadratic: f(x) = 1/2 x^T A x - b^T x, positive definite A.
QA = [[4.0, 1.0], [1.0, 3.0]]
QB = [1.0, 2.0]
QX = _gauss(QA, QB)                      # the exact minimiser
QF = 0.5 * (QA[0][0] * QX[0] ** 2 + 2 * QA[0][1] * QX[0] * QX[1]
            + QA[1][1] * QX[1] ** 2) - (QB[0] * QX[0] + QB[1] * QX[1])


def _quad_f(x):
    return 0.5 * (QA[0][0] * x[0] ** 2 + 2 * QA[0][1] * x[0] * x[1]
                  + QA[1][1] * x[1] ** 2) - (QB[0] * x[0] + QB[1] * x[1])


def _quad_grad(x):
    return [QA[0][0] * x[0] + QA[0][1] * x[1] - QB[0],
            QA[1][0] * x[0] + QA[1][1] * x[1] - QB[1]]


def _quad_hess(_x):
    return [list(QA[0]), list(QA[1])]


# Non-quadratic convex: f(x) = e^x1 - x1 + e^x2 - x2, optimum (0, 0) with value 2.
NX, NF = [0.0, 0.0], 2.0


def _exp_f(x):
    return math.exp(x[0]) - x[0] + math.exp(x[1]) - x[1]


def _exp_grad(x):
    return [math.exp(x[0]) - 1.0, math.exp(x[1]) - 1.0]


def _exp_hess(x):
    return [[math.exp(x[0]), 0.0], [0.0, math.exp(x[1])]]


# An ill-conditioned quadratic, where gradient descent crawls and Newton flies.
# f(x) = 1/2 (100 x1^2 + x2^2), optimum (0, 0).
def _ill_f(x):
    return 0.5 * (100.0 * x[0] * x[0] + x[1] * x[1])


def _ill_grad(x):
    return [100.0 * x[0], x[1]]


def _ill_hess(_x):
    return [[100.0, 0.0], [0.0, 1.0]]


# 1-D non-quadratic used to watch the quadratic convergence rate.
def _sqexp_f(x):
    return math.exp(x[0]) - x[0]


def _sqexp_grad(x):
    return [math.exp(x[0]) - 1.0]


def _sqexp_hess(x):
    return [[math.exp(x[0])]]


# 1-D limit case: f(x) = sqrt(1 + x^2), optimum 0. Undamped Newton from x = 2
# maps x -> -x^3 and runs away; damping brings it back.
def _root_f(x):
    return math.sqrt(1.0 + x[0] * x[0])


def _root_grad(x):
    return [x[0] / math.sqrt(1.0 + x[0] * x[0])]


def _root_hess(x):
    return [[1.0 / (1.0 + x[0] * x[0]) ** 1.5]]


# Singular Hessian everywhere: f(x) = 1/2 (x1 + x2)^2.
def _flat_f(x):
    s = x[0] + x[1]
    return 0.5 * s * s


def _flat_grad(x):
    s = x[0] + x[1]
    return [s, s]


def _flat_hess(_x):
    return [[1.0, 1.0], [1.0, 1.0]]


def _norm(u):
    return math.sqrt(sum(v * v for v in u))


# ---------------------------------------------------------------------------
# Step 1: gradient descent with backtracking minimises to tolerance
# ---------------------------------------------------------------------------

def check_gradient_descent() -> None:
    from minimise import backtracking_line_search, gradient_descent

    # The backtracking step must satisfy sufficient decrease (Armijo).
    x0 = [3.0, -2.0]
    g0 = _quad_grad(x0)
    d = [-gi for gi in g0]
    t = backtracking_line_search(_quad_f, _quad_grad, x0, d)
    moved = [x0[i] + t * d[i] for i in range(2)]
    slope = sum(g0[i] * d[i] for i in range(2))
    assert _quad_f(moved) <= _quad_f(x0) + 0.3 * t * slope + 1e-12, \
        "backtracking returned a step that does not decrease f enough: the Armijo " \
        "test f(x + t d) <= f(x) + alpha t g^T d has been dropped"

    # A convex quadratic, from a start away from the optimum.
    got, fval, history = gradient_descent(_quad_f, _quad_grad, [3.0, -2.0], 1e-8, 200000)
    assert _norm([got[i] - QX[i] for i in range(2)]) < 1e-4, \
        f"gradient descent on the quadratic should reach {QX}, got {got}; check the " \
        "direction is -grad and the backtracking step is actually used"
    assert abs(fval - QF) < TOL, f"the quadratic optimum value should be {QF}, got {fval}"
    assert len(history) >= 1, "gradient_descent must return an f-value history"

    # A non-quadratic convex function.
    got2, fval2, _ = gradient_descent(_exp_f, _exp_grad, [2.0, -1.0], 1e-8, 200000)
    assert _norm([got2[i] - NX[i] for i in range(2)]) < 1e-4, \
        f"gradient descent on e^x - x should reach (0, 0), got {got2}"
    assert abs(fval2 - NF) < TOL, f"the e^x - x optimum value should be {NF}, got {fval2}"


# ---------------------------------------------------------------------------
# Step 2: ACCEPT -- Newton's decrement sequence shows quadratic convergence
# ---------------------------------------------------------------------------

def check_quadratic_convergence() -> None:
    from minimise import newton

    x, dec, it = newton(_sqexp_f, _sqexp_grad, _sqexp_hess, [1.0], 1e-10, 100)
    assert abs(x[0]) < 1e-4, f"Newton on e^x - x should reach 0, got x = {x[0]}"
    assert len(dec) >= 4, \
        "Newton stopped after too few iterations to show quadratic convergence; the " \
        "decrement/2 <= tol test must be tight enough to iterate into the near-optimum regime"

    # Near the optimum lambda_{k+1} ~ c * lambda_k^2, so on a log-log plot the
    # points fall on a line of slope 2. Measure it from the small decrements.
    pairs = [(dec[k], dec[k + 1]) for k in range(len(dec) - 1)
             if 1e-11 < dec[k] < 1e-1 and dec[k + 1] > 0.0]
    assert len(pairs) >= 2, \
        f"only {len(pairs)} usable decrement pairs {dec}; Newton did not run long enough " \
        "near the optimum for the quadratic regime to appear"
    exps = sorted(math.log(b) / math.log(a) for a, b in pairs)
    exponent = exps[len(exps) // 2]
    assert 1.5 <= exponent <= 3.0, \
        f"the Newton error exponent is {exponent:.2f}, not ~2; the error sequence should " \
        f"square each step (decrements {dec}). A nearly quadratic method doubles the " \
        "correct digits per iteration"


# ---------------------------------------------------------------------------
# Step 3: Newton needs far fewer iterations than gradient descent
# ---------------------------------------------------------------------------

def check_iteration_count() -> None:
    from minimise import gradient_descent, newton

    tol = 1e-8
    _, _, gd_hist = gradient_descent(_ill_f, _ill_grad, [1.0, -1.0], tol, 200000)
    gd_iters = len(gd_hist)
    _, _, nt_iters = newton(_ill_f, _ill_grad, _ill_hess, [1.0, -1.0], tol, 200)
    assert 0 < nt_iters <= 10, \
        f"Newton on a quadratic should converge in a handful of iterations, took {nt_iters}; " \
        "a step with no curvature falls back to gradient descent's crawl"
    assert nt_iters * 3 < gd_iters, \
        f"Newton took {nt_iters} iterations and gradient descent {gd_iters} at tol {tol}: " \
        "Newton should be far smaller because it uses curvature, not just the slope"


# ---------------------------------------------------------------------------
# Step 4: limit case -- undamped Newton diverges, damped Newton converges
# ---------------------------------------------------------------------------

def check_limit_case() -> None:
    from minimise import newton

    # Undamped Newton on sqrt(1 + x^2) maps x -> -x^3, so from x = 2 it runs away.
    far, _, far_iters = newton(_root_f, _root_grad, _root_hess, [2.0], 1e-10, 5,
                               line_search=False)
    assert math.isfinite(far[0]) and abs(far[0]) > 1e6, \
        f"undamped Newton from x = 2 should run far away, ended at x = {far[0]}; " \
        "the raw Newton step has no safeguard against overshoot"

    # Damping with backtracking tames the same start.
    near, near_dec, near_iters = newton(_root_f, _root_grad, _root_hess, [2.0], 1e-10, 100,
                                        line_search=True)
    assert math.isfinite(near[0]) and abs(near[0]) < 1e-4, \
        f"damped Newton should return to x = 0, ended at x = {near[0]}; the backtracking " \
        "step must shorten the Newton step until f decreases"


# ---------------------------------------------------------------------------
# Step 5: a singular-Hessian start is handled safely
# ---------------------------------------------------------------------------

def check_singular_hessian() -> None:
    from minimise import newton, newton_decrement

    # The squared decrement on a singular Hessian must stay finite and positive,
    # rather than dividing by zero or raising.
    dec = newton_decrement([2.0, 2.0], [[1.0, 1.0], [1.0, 1.0]])
    assert math.isfinite(dec) and dec > 0.0, \
        f"newton_decrement on a singular Hessian should be finite and positive, got {dec}; " \
        "a ridge lam*I must be added until H y = g can be solved"

    # Starting at (2, -1) the Hessian is singular. Damping and the decrement
    # test must still drive x to the flat valley x1 + x2 = 0.
    x, history, iters = newton(_flat_f, _flat_grad, _flat_hess, [2.0, -1.0], 1e-8, 200,
                               line_search=True)
    g = _flat_grad(x)
    assert _norm(g) < 1e-5, \
        f"Newton on 1/2 (x1+x2)^2 should stop with a near-zero gradient, got {g} at {x}; " \
        "the regularised solve and the decrement stopping rule together keep it safe"
    assert abs(x[0] + x[1]) < 1e-5, \
        f"the minimiser must lie on x1 + x2 = 0, got {x} (sum {x[0] + x[1]})"
    assert all(math.isfinite(v) for v in history), "the decrement history must stay finite"


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("minimise.py", "gradient descent with backtracking minimises to tolerance",
     check_gradient_descent),
    ("minimise.py", "Newton's error exponent is ~2 (quadratic convergence)",
     check_quadratic_convergence),
    ("minimise.py", "Newton takes far fewer iterations than gradient descent",
     check_iteration_count),
    ("minimise.py", "undamped Newton diverges, damped Newton converges",
     check_limit_case),
    ("minimise.py", "a singular-Hessian start is handled safely",
     check_singular_hessian),
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
    print(f"\n{BOLD}Unconstrained Minimisation From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<12} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<12} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<12} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built the unconstrained solvers from scratch.{RESET}")
        print(f"  {GREY}Run solutions/minimise.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
