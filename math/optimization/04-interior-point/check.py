"""
Progress checker for the interior-point templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The checker keeps its own arithmetic: it solves the KKT systems itself with ``_gauss``
and enumerates LP vertices itself with ``_enum_lp``, so a passing run means the learned
code agrees with numbers computed independently of it.
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

TOL = 1e-6


# ---------------------------------------------------------------------------
# The checker's own arithmetic (independent of the code under test)
# ---------------------------------------------------------------------------

def _gauss(A, b):
    """Solve A x = b by Gaussian elimination with partial pivoting."""
    n = len(A)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-13:
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


def _dot(u, v):
    return sum(a * b for a, b in zip(u, v))


def _norm(v):
    return math.sqrt(sum(a * a for a in v))


def _enum_lp(c, A_ub, b_ub):
    """Independent 2-D reference: best feasible vertex of {A_ub x <= b_ub}.

    Returns ``(x, c^T x)`` or ``(None, inf)`` when no vertex is feasible.
    """
    m = len(A_ub)
    best_x, best_val = None, float("inf")
    for i in range(m):
        for j in range(i + 1, m):
            det = A_ub[i][0] * A_ub[j][1] - A_ub[i][1] * A_ub[j][0]
            if abs(det) < 1e-12:
                continue
            x = [(b_ub[i] * A_ub[j][1] - b_ub[j] * A_ub[i][1]) / det,
                 (A_ub[i][0] * b_ub[j] - A_ub[j][0] * b_ub[i]) / det]
            if all(_dot(A_ub[k], x) <= b_ub[k] + 1e-9 for k in range(m)):
                val = _dot(c, x)
                if val < best_val - 1e-12:
                    best_x, best_val = x, val
    return best_x, best_val


# The teaching LP used by steps 2 and 3: min -x1 - x2 over a pentagon.
LP_C = [-1.0, -1.0]
LP_A = [[1.0, 2.0], [3.0, 2.0], [0.0, 1.0], [-1.0, 0.0], [0.0, -1.0]]
LP_B = [6.0, 12.0, 2.0, 0.0, 0.0]
LP_X0 = [0.5, 0.5]

# A degenerate cone LP: min x1 + x2 s.t. x1 >= 0, x2 >= 0. The origin is optimal
# with both constraints active, so the barrier suboptimality is exactly m/t = 2/t.
CONE_C = [1.0, 1.0]
CONE_A = [[-1.0, 0.0], [0.0, -1.0]]
CONE_B = [0.0, 0.0]
CONE_X0 = [1.0, 1.0]


# ---------------------------------------------------------------------------
# Step 1: equality-constrained Newton reaches the KKT point
# ---------------------------------------------------------------------------

def check_equality_newton() -> None:
    from interior import equality_constrained_newton

    def kkt_reference(Q, c, A, b):
        n, m = len(c), len(A)
        K = [list(Q[i]) + [A[k][i] for k in range(m)] for i in range(n)]
        for k in range(m):
            K.append(list(A[k]) + [0.0] * m)
        rhs = [-c[i] for i in range(n)] + [b[k] for k in range(m)]
        sol = _gauss(K, rhs)
        return sol[:n], sol[n:]

    # Quadratic on the line x1 + x2 = 3.
    Q = [[2.0, 0.0], [0.0, 2.0]]
    c = [-2.0, -3.0]
    A = [[1.0, 1.0]]
    b = [3.0]
    xref, lam = kkt_reference(Q, c, A, b)
    x, res = equality_constrained_newton(Q, c, A, b, [0.0, 0.0], 1e-10, 100)
    ax = sum(A[0][i] * x[i] for i in range(2))
    assert abs(ax - b[0]) < 1e-7, \
        f"the equality constraint must hold at the solution, got A x = {ax} vs b = {b[0]}; " \
        "the KKT system reached must include the A block, not just Q"
    g = [_matvec_row(Q, x, i) + c[i] for i in range(2)]
    reduced = [g[i] + sum(A[k][i] * lam[k] for k in range(1)) for i in range(2)]
    assert _norm(reduced) < 1e-6, \
        f"the reduced gradient must vanish at the solution, residual {reduced}; " \
        "an unconstrained step cannot satisfy the constraint and the gradient together"
    assert _norm([x[i] - xref[i] for i in range(2)]) < 1e-6, \
        f"the KKT point should be {xref}, got {x}; solve the full KKT system"
    assert res and res[-1] < 1e-6, \
        f"equality_constrained_newton must return a residual history ending near zero, got {res}"

    # Two equality constraints: A = I pins x = (1, 2).
    Q2 = [[2.0, 0.0], [0.0, 2.0]]
    c2 = [0.0, 0.0]
    A2 = [[1.0, 0.0], [0.0, 1.0]]
    b2 = [1.0, 2.0]
    x2, res2 = equality_constrained_newton(Q2, c2, A2, b2, [0.0, 0.0], 1e-10, 100)
    assert _norm([x2[0] - 1.0, x2[1] - 2.0]) < 1e-6, \
        f"with A = I the only feasible point is (1, 2), got {x2}"


def _matvec_row(M, v, i):
    return sum(M[i][j] * v[j] for j in range(len(v)))


# ---------------------------------------------------------------------------
# Step 2: the log-barrier LP converges to the enumeration optimum as t grows
# ---------------------------------------------------------------------------

def check_log_barrier() -> None:
    from interior import log_barrier_lp

    xref, pstar = _enum_lp(LP_C, LP_A, LP_B)
    assert abs(pstar + 4.5) < 1e-9, \
        f"the checker's own enumeration is wrong: expected -4.5, got {pstar}"

    objs = []
    for t in (1.0, 10.0, 100.0, 1000.0):
        x, _ = log_barrier_lp(LP_C, LP_A, LP_B, t, LP_X0)
        slacks = [LP_B[i] - _dot(LP_A[i], x) for i in range(len(LP_A))]
        assert all(s > -1e-9 for s in slacks), \
            f"the log-barrier iterate must stay feasible, slacks {slacks} at t = {t}"
        objs.append(_dot(LP_C, x))

    for k in range(1, len(objs)):
        assert objs[k] <= objs[k - 1] + 1e-8, \
            f"the barrier objective should fall toward p* as t grows, got {objs}; " \
            "a sign error in the -c term makes it climb the wrong way"
    assert abs(objs[-1] - pstar) < 0.02, \
        f"at t = 1000 the log-barrier value {objs[-1]:.5f} should be within 0.02 of " \
        f"the LP optimum {pstar}; the barrier subproblem must be solved by Newton"


# ---------------------------------------------------------------------------
# Step 3: ACCEPT -- the barrier duality gap tracks m/t
# ---------------------------------------------------------------------------

def check_duality_gap() -> None:
    from interior import barrier_method

    # The cone min x1 + x2 s.t. x1 >= 0, x2 >= 0 has its optimum at the origin and
    # both constraints active there, so the central point is (1/t, 1/t) and the
    # measured suboptimality equals m/t = 2/t exactly: ratio 1 at every round.
    c, A, b, x0 = CONE_C, CONE_A, CONE_B, CONE_X0
    _, pstar = _enum_lp(c, A, b)
    assert abs(pstar) < 1e-9, f"the checker's own enumeration is wrong: expected 0, got {pstar}"
    x, hist = barrier_method(c, A, b, t0=1.0, mu=10.0, tol=1e-7, maxit=30, x0=x0)
    assert len(hist) >= 3, \
        f"the outer loop ran only {len(hist)} rounds; it must keep raising t until m/t < tol"

    for k in range(1, len(hist)):
        assert hist[k]["gap"] < hist[k - 1]["gap"], \
            f"the theoretical gap m/t must shrink each round, got gaps " \
            f"{[h['gap'] for h in hist]}; barrier_method must multiply t by mu"

    measured = []
    for h in hist:
        gap = _dot(c, h["x"]) - pstar
        assert gap >= -1e-6, \
            f"the barrier objective must not beat the LP optimum, gap {gap} at t {h['t']}"
        measured.append(gap)
        ratio = gap / h["gap"] if h["gap"] else float("nan")
        assert 0.9 <= ratio <= 1.1, \
            f"the measured gap {gap:.3e} must track m/t = {h['gap']:.3e} (ratio {ratio:.3f}); " \
            "on this LP both constraints are active, so the barrier suboptimality is m/t"
    for k in range(1, len(measured)):
        assert measured[k] < 0.9 * measured[k - 1], \
            f"the measured gap must fall with t, got {measured}; if t never grows it " \
            "stays pinned at m/t0 and no longer tracks m/t"
    assert measured[-1] < 1e-5, \
        f"the final measured gap {measured[-1]:.3e} is too large; keep raising t"
    assert _dot(c, x) - pstar < 1e-5, \
        "barrier_method must return the point from its last (small-gap) round"

    # On the pentagon only two constraints are active, so the suboptimality is
    # below m/t; the theoretical gap remains a valid upper bound at every round.
    _, pstar2 = _enum_lp(LP_C, LP_A, LP_B)
    _, hist2 = barrier_method(LP_C, LP_A, LP_B, t0=1.0, mu=10.0, tol=1e-6,
                              maxit=30, x0=LP_X0)
    for h in hist2:
        gap2 = _dot(LP_C, h["x"]) - pstar2
        assert gap2 <= h["gap"] + 1e-6, \
            f"on the pentagon the suboptimality {gap2:.3e} must not exceed m/t = {h['gap']:.3e}"


# ---------------------------------------------------------------------------
# Step 4: ACCEPT -- the barrier matches BFS enumeration on random LPs
# ---------------------------------------------------------------------------

def _random_lp(rng):
    """A bounded 2-D LP with a guaranteed strictly feasible point p0."""
    U = rng.uniform(2.0, 5.0)
    p0 = [0.5 * U, 0.5 * U]
    A = [[-1.0, 0.0], [0.0, -1.0], [1.0, 0.0], [0.0, 1.0]]
    b = [0.0, 0.0, U, U]
    for _ in range(2):
        a = [rng.uniform(-1.0, 1.0), rng.uniform(-1.0, 1.0)]
        margin = rng.uniform(0.2, 1.0)
        A.append(a)
        b.append(a[0] * p0[0] + a[1] * p0[1] + margin)
    c = [rng.uniform(-1.0, 1.0), rng.uniform(-1.0, 1.0)]
    return c, A, b, p0


def check_matches_enumeration() -> None:
    from interior import barrier_method, simplex_lp

    # A LP where an infeasible pair of constraints meets at a cheaper value than
    # the true optimum: accepting it makes the reference report 0 instead of 1.5.
    c = [1.0, 1.0]
    A = [[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0], [0.0, -1.0], [-1.0, -1.0]]
    b = [1.0, 1.0, 0.0, 0.0, -1.5]
    xref, pref = _enum_lp(c, A, b)
    assert abs(pref - 1.5) < 1e-9, f"checker enumeration is wrong: expected 1.5, got {pref}"
    xr, pr = simplex_lp(c, A, b)
    assert pr is not None and abs(pr - pref) < 1e-6, \
        f"the enumeration reference must reject infeasible vertices: it returned {pr} " \
        f"for a LP whose optimum is {pref}; the feasibility test is being skipped"

    rng = random.Random(20240501)
    for trial in range(5):
        c, A, b, p0 = _random_lp(rng)
        xref, pref = _enum_lp(c, A, b)
        assert xref is not None, "the random LP must be feasible (built around p0)"
        xr, pr = simplex_lp(c, A, b)
        assert abs(pr - pref) < 1e-6, \
            f"trial {trial}: the BFS reference returned {pr}, independent enumeration {pref}"

        x, hist = barrier_method(c, A, b, t0=1.0, mu=10.0, tol=1e-7, maxit=30, x0=p0)
        got = _dot(c, x)
        assert abs(got - pref) < 1e-4, \
            f"trial {trial}: the barrier objective {got} should match the enumeration " \
            f"optimum {pref}; the barrier must solve the LP as t grows"


# ---------------------------------------------------------------------------
# Step 5: limit case -- phase-I detects an infeasible LP
# ---------------------------------------------------------------------------

def check_phase_one() -> None:
    from interior import phase_one

    # Feasible: the pentagon from step 2.
    assert phase_one(LP_A, LP_B) is True, \
        "phase_one must accept the feasible pentagon"

    # Infeasible: x1 + x2 <= 1 together with x1 + x2 >= 3.
    infeasible = phase_one([[1.0, 1.0], [-1.0, -1.0]], [1.0, -3.0])
    assert infeasible is False, \
        "phase_one must detect that {x1 + x2 <= 1, x1 + x2 >= 3} is empty; " \
        "returning True unconditionally misses the infeasibility limit case"

    # Another empty system: x1 <= -1 and x1 >= 1.
    assert phase_one([[1.0, 0.0], [-1.0, 0.0]], [-1.0, -1.0]) is False, \
        "phase_one must detect the empty strip x1 <= -1, x1 >= 1"


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("interior.py", "equality-constrained Newton reaches the KKT point",
     check_equality_newton),
    ("interior.py", "the log-barrier LP converges to the enumeration optimum",
     check_log_barrier),
    ("interior.py", "ACCEPT: the barrier duality gap tracks m/t",
     check_duality_gap),
    ("interior.py", "ACCEPT: the barrier matches BFS enumeration on random LPs",
     check_matches_enumeration),
    ("interior.py", "limit: phase-I detects an infeasible LP",
     check_phase_one),
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
    print(f"\n{BOLD}Interior-Point Methods From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built the interior-point solvers from scratch.{RESET}")
        print(f"  {GREY}Run solutions/interior.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
