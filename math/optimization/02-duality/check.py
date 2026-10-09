"""
Progress checker for the duality templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The checker keeps its own arithmetic: it hard-codes the known primal optima of the
teaching problems and solves the limit-case dual itself (``_limit_dual``), so a
passing run means the learned code agrees with numbers computed independently of it.
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
# The teaching problems, with their known primal optima (reference arithmetic)
# ---------------------------------------------------------------------------

# QP: minimise (1/2)(2 x1^2 + 2 x2^2) s.t. -x1 - x2 <= -1.
# The optimum is x = (1/2, 1/2), lambda = 1, value 1/2.
QP_Q = [[2.0, 0.0], [0.0, 2.0]]
QP_c = [0.0, 0.0]
QP_A = [[-1.0, -1.0]]
QP_b = [-1.0]
QP_PRIMAL = 0.5
QP_X = [0.5, 0.5]
QP_LAM = [1.0]

# A second QP: minimise (1/2)(x1^2 + x2^2) s.t. -x1 <= -2. Optimum (2, 0), value 2.
QP2_Q = [[1.0, 0.0], [0.0, 1.0]]
QP2_c = [0.0, 0.0]
QP2_A = [[-1.0, 0.0]]
QP2_b = [-2.0]
QP2_PRIMAL = 2.0

# LP: minimise -x1 - x2 s.t. x1 <= 1, x2 <= 1, x1 + x2 <= 1.5. Optimum -1.5.
LP_c = [-1.0, -1.0]
LP_A = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
LP_b = [1.0, 1.0, 1.5]
LP_PRIMAL = -1.5

# A second LP: minimise -x1 - x2 s.t. x1 <= 2, x2 <= 2. Optimum -4.
LP2_c = [-1.0, -1.0]
LP2_A = [[1.0, 0.0], [0.0, 1.0]]
LP2_b = [2.0, 2.0]
LP2_PRIMAL = -4.0


def _limit_dual(lam, steps=4001, span=200.0, y=1e8):
    """The checker's own dual function of the no-Slater problem, on a grid.

    Primal: minimise e^{-x} s.t. x^2 / y <= 0, y > 0. The feasible set is the
    single point x = 0, so the primal optimum is e^0 = 1. The dual function is
    g(lam) = inf_{x, y>0} e^{-x} + lam x^2 / y; taking y -> infinity kills the
    second term, so g(lam) = inf_x e^{-x} = 0 for every lam >= 0 and the dual
    optimum is 0. The grid below evaluates that infimum without relying on the
    solver under test.
    """
    xs = [i * (span / (steps - 1)) for i in range(steps)]
    return min(math.exp(-x) + lam * x * x / y for x in xs)


# ---------------------------------------------------------------------------
# Step 1: the QP dual equals the known primal optimum
# ---------------------------------------------------------------------------

def check_qp_dual() -> None:
    from duality import solve_qp_dual, dual_value

    got = solve_qp_dual(QP_Q, QP_c, QP_A, QP_b)
    assert got <= QP_PRIMAL + TOL, \
        f"weak duality is violated: the QP dual {got} exceeds the primal {QP_PRIMAL}; " \
        "the dual is a MAXIMUM of a concave function, check the sign of the linear term"
    assert abs(got - QP_PRIMAL) < TOL, \
        f"QP dual should be {QP_PRIMAL}, got {got}; expand (c + A^T lam)^T Q^-1 (c + A^T lam) " \
        "carefully, especially the b^T lam and the 1/2"

    got2 = solve_qp_dual(QP2_Q, QP2_c, QP2_A, QP2_b)
    assert abs(got2 - QP2_PRIMAL) < TOL, \
        f"second QP dual should be {QP2_PRIMAL}, got {got2}"

    wrapper = dual_value(QP_Q, QP_c, QP_A, QP_b)
    assert abs(wrapper - got) < 1e-12, \
        "dual_value must return the same QP dual optimum as solve_qp_dual"


# ---------------------------------------------------------------------------
# Step 2: an LP and its dual agree
# ---------------------------------------------------------------------------

def check_lp_dual() -> None:
    from duality import solve_lp_dual

    got = solve_lp_dual(LP_c, LP_A, LP_b)
    assert got <= LP_PRIMAL + TOL, \
        f"LP dual {got} exceeds primal {LP_PRIMAL}: the dual maximises -b^T y, " \
        "it does not minimise it"
    assert abs(got - LP_PRIMAL) < TOL, \
        f"LP dual should be {LP_PRIMAL}, got {got}; the dual constraints are A^T y = -c, y >= 0"

    got2 = solve_lp_dual(LP2_c, LP2_A, LP2_b)
    assert abs(got2 - LP2_PRIMAL) < TOL, \
        f"second LP dual should be {LP2_PRIMAL}, got {got2}"


# ---------------------------------------------------------------------------
# Step 3: the KKT residuals accept an optimum and reject a perturbation
# ---------------------------------------------------------------------------

def check_kkt() -> None:
    from duality import kkt_residuals

    at_opt = kkt_residuals(QP_Q, QP_c, QP_A, QP_b, QP_X, QP_LAM)
    for name, value in at_opt.items():
        assert value < 1e-8, \
            f"KKT residual {name} = {value} at the optimum (x = {QP_X}, lam = {QP_LAM}); " \
            "all four must vanish, including stationarity Q x + c + A^T lam"

    # x is feasible but off the stationarity point: the dual is not responding.
    perturbed_x = kkt_residuals(QP_Q, QP_c, QP_A, QP_b, [0.6, 0.6], QP_LAM)
    assert perturbed_x["stationarity"] > TOL, \
        "a perturbed x must break stationarity; if it does not, A^T lam has been dropped"

    # lam = 0 leaves the primal constraint's pull out of stationarity.
    perturbed_lam = kkt_residuals(QP_Q, QP_c, QP_A, QP_b, QP_X, [0.0])
    assert perturbed_lam["stationarity"] > TOL, \
        "with lam = 0 stationarity is Q x + c != 0; the perturbation must be rejected"

    # An x that violates the constraint must show a positive primal residual.
    infeasible = kkt_residuals(QP_Q, QP_c, QP_A, QP_b, [0.2, 0.2], [0.0])
    assert infeasible["primal_feasibility"] > TOL, \
        "x = (0.2, 0.2) violates x1 + x2 >= 1; primal feasibility must be positive"


# ---------------------------------------------------------------------------
# Step 4: weak duality, dual <= primal, on the tested problems
# ---------------------------------------------------------------------------

def check_weak_duality() -> None:
    from duality import solve_qp_dual, solve_lp_dual, weak_duality_gap

    gap = weak_duality_gap(QP_PRIMAL, solve_qp_dual(QP_Q, QP_c, QP_A, QP_b))
    assert gap >= -TOL, f"the QP gap primal - dual = {gap} must be >= 0"

    gap = weak_duality_gap(LP_PRIMAL, solve_lp_dual(LP_c, LP_A, LP_b))
    assert gap >= -TOL, f"the LP gap primal - dual = {gap} must be >= 0"

    # A pair with a known strictly positive gap: primal 10, dual 7.
    gap = weak_duality_gap(10.0, 7.0)
    assert gap >= -TOL, \
        f"weak duality says the gap primal - dual >= 0, got {gap}; the sign is flipped"
    assert abs(gap - 3.0) < 1e-9, \
        f"the known pair (10, 7) has gap 3, got {gap}; it is primal - dual, not dual - primal"


# ---------------------------------------------------------------------------
# Step 5: the limit case, a positive gap with no Slater point
# ---------------------------------------------------------------------------

def check_limit_case() -> None:
    from duality import weak_duality_gap, strong_duality_holds

    # The checker's own dual optimum for the no-Slater problem is ~0 ...
    dual_opt = max(_limit_dual(lam) for lam in (0.0, 0.1, 1.0, 10.0))
    assert dual_opt < 1e-3, f"the limit dual should be ~0, the grid gave {dual_opt}"
    primal_opt = 1.0
    gap = weak_duality_gap(primal_opt, dual_opt)
    assert gap > 0.5, f"this problem has a positive duality gap, got {gap}"

    # ... so strong duality fails, and the test must not paper over it.
    assert not strong_duality_holds(primal_opt, dual_opt), \
        "the no-Slater problem has a positive gap: strong_duality_holds must return False, " \
        "never assume strong duality always holds"
    assert strong_duality_holds(0.5, 0.5), \
        "a zero gap is strong duality; the test must still recognise it"


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("duality.py", "the QP dual matches the known primal value", check_qp_dual),
    ("duality.py", "an LP and its dual agree", check_lp_dual),
    ("duality.py", "the KKT residuals accept an optimum, reject a perturbation", check_kkt),
    ("duality.py", "weak duality: dual <= primal", check_weak_duality),
    ("duality.py", "the limit case has a positive duality gap", check_limit_case),
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
    print(f"\n{BOLD}Lagrange Duality From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built duality from scratch.{RESET}")
        print(f"  {GREY}Run solutions/duality.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
