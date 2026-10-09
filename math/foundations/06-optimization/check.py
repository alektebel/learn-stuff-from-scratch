"""
Progress checker for the continuous-optimization templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

Every reference value is recomputed here — closed form where one exists, an independent
central difference or linear solve otherwise — so the checker never asks your own code
what the right answer is.
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


def _norm(u):
    return math.sqrt(_dot(u, u))


def _matvec(A, v):
    return [sum(A[i][j] * v[j] for j in range(len(v))) for i in range(len(A))]


def _matmul(A, B):
    return [[sum(A[i][t] * B[t][j] for t in range(len(B))) for j in range(len(B[0]))]
            for i in range(len(A))]


def _solve(M, v):
    """Gaussian elimination with partial pivoting (the checker's own linear solver)."""
    n = len(M)
    A = [list(M[i]) + [v[i]] for i in range(n)]
    for col in range(n):
        p = max(range(col, n), key=lambda i: abs(A[i][col]))
        if abs(A[p][col]) <= 1e-12:
            raise ValueError("singular")
        A[col], A[p] = A[p], A[col]
        pv = A[col][col]
        A[col] = [z / pv for z in A[col]]
        for i in range(n):
            if i != col:
                fac = A[i][col]
                if fac:
                    A[i] = [A[i][j] - fac * A[col][j] for j in range(n + 1)]
    return [A[i][n] for i in range(n)]


def _fd_gradient(f, x, h):
    """Central-difference gradient: an independent oracle for step 1."""
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


def _maxdiff(got, ref):
    return max(abs(a - b) for a, b in zip(got, ref))


def _quad(A, b):
    """The checker's own quadratic f and gradient, f(x) = ½xᵀAx − bᵀx."""
    f = lambda x: 0.5 * _dot(x, _matvec(A, x)) - _dot(b, x)
    g = lambda x: [sum(A[i][j] * x[j] for j in range(len(x))) - b[i]
                   for i in range(len(A))]
    return f, g


def _kkt_solve(Q, b, C, d):
    """Solve the KKT system [[Q, Cᵀ], [C, 0]][x; λ] = [−b; d]. Returns (x, λ)."""
    n, m = len(Q), len(C)
    K = [[0.0] * (n + m) for _ in range(n + m)]
    for i in range(n):
        for j in range(n):
            K[i][j] = Q[i][j]
        for k in range(m):
            K[i][n + k] = C[k][i]
    for k in range(m):
        for j in range(n):
            K[n + k][j] = C[k][j]
    z = _solve(K, [-b[i] for i in range(n)] + [d[k] for k in range(m)])
    return z[:n], z[n:]


def _converged(f, g, x, tol):
    return all(math.isfinite(v) for v in x) and _norm(g(x)) <= tol


# ---------------------------------------------------------------------------
# Step 1: ∇(½xᵀAx − bᵀx) = Ax − b
# ---------------------------------------------------------------------------

def check_quadratic_gradient() -> None:
    from optimization import quadratic_gradient

    A = [[2.0, 0.5], [0.5, 3.0]]          # symmetric positive definite
    b = [1.0, -1.0]
    x = [1.5, -2.0]
    got = quadratic_gradient(A, b, x)

    expected = [sum(A[i][j] * x[j] for j in range(2)) - b[i] for i in range(2)]
    assert _maxdiff(got, expected) < 1e-10, (
        f"quadratic_gradient = {got}, expected A x − b = {expected}: the gradient of "
        "½xᵀAx − bᵀx is Ax − b (the ½ cancels), so no factor of 2 belongs here")

    f = lambda v: 0.5 * _dot(v, _matvec(A, v)) - _dot(b, v)
    assert _rel(got, _fd_gradient(f, x, 1e-6)) < 1e-6, (
        "the quadratic gradient disagrees with central differences")

    t = 1e-3
    xm = [x[i] - t * got[i] for i in range(2)]
    assert f(xm) < f(x), (
        f"f(x − t∇f) = {f(xm):.6f} must be below f(x) = {f(x):.6f}: a gradient points "
        "uphill, so the sign is flipped")

    xstar = _solve(A, b)                    # optimum satisfies A x* = b
    assert _norm(quadratic_gradient(A, b, xstar)) < 1e-12, (
        "the gradient must vanish at the solution of A x = b")


# ---------------------------------------------------------------------------
# Step 2: fixed-step gradient descent converges and returns its trajectory
# ---------------------------------------------------------------------------

def check_gradient_descent() -> None:
    from optimization import gradient_descent, quadratic_gradient

    A = [[1.0, 0.0], [0.0, 4.0]]           # λ_max = 4
    b = [1.0, 2.0]
    f, g = _quad(A, b)
    x0 = [5.0, -3.0]
    step = 0.5 * (2.0 / 4.0)                 # half the stability limit

    x, it, history = gradient_descent(f, g, x0, step, tol=1e-9, max_iter=5000)
    assert history[0] == list(x0), (
        "the returned history must start at x0, so a caller can measure the trajectory")
    assert len(history) == it + 1, (
        f"history has {len(history)} points but iterations = {it}: they must satisfy "
        "len(history) = iterations + 1")
    assert history[-1] == x, "the last history point must be the returned x"

    xstar = _solve(A, b)                     # [1.0, 0.5]
    assert _maxdiff(x, xstar) < 1e-6, (
        f"fixed-step descent returned {x}, expected the minimum {xstar}: is the update "
        "x ← x − step·∇f (minus, not plus)?")

    # The iteration count must actually be finite (it converges, not hits max_iter).
    assert it < 5000, (
        "descent ran to max_iter: the step 0.25 is below 2/λ_max = 0.5, so it must "
        "converge")


# ---------------------------------------------------------------------------
# Step 3: Armijo backtracking accepts only a genuine decrease (limit case)
# ---------------------------------------------------------------------------

def check_backtracking_line_search() -> None:
    from optimization import backtracking_line_search

    A = [[100.0, 0.0], [0.0, 100.0]]
    f, g = _quad(A, [0.0, 0.0])
    x = [1.0, 1.0]
    direction = [-v for v in g(x)]           # steepest descent
    c = 1e-4
    alpha = backtracking_line_search(f, g, x, direction, alpha0=1.0, rho=0.5, c=c)

    xp = [x[i] + alpha * direction[i] for i in range(2)]
    gd = _dot(g(x), direction)
    assert f(xp) <= f(x) + c * alpha * gd + 1e-12, (
        f"alpha = {alpha} violates the Armijo condition f(x+αd) ≤ f(x) + c·α·∇fᵀd: "
        "the search must shrink the step until sufficient decrease holds")
    assert f(xp) < f(x), (
        f"the returned step increases f from {f(x):.3f} to {f(xp):.3f}: a line search "
        "must only ever accept a decreasing step")
    assert alpha < 1.0, (
        "with curvature 100 at x = (1, 1), alpha0 = 1 overshoots, so backtracking must "
        "return a smaller step")

    # It must be the *first* accepted step: alpha/rho is rejected.
    a_big = alpha / 0.5
    assert f([x[i] + a_big * direction[i] for i in range(2)]) > f(x) + c * a_big * gd, (
        f"alpha = {alpha} is not maximal: alpha/rho also satisfies Armijo, so the "
        "search stopped too early")

    try:
        backtracking_line_search(f, g, x, [1.0, 1.0])   # ascent direction
        raised = False
    except ValueError:
        raised = True
    assert raised, (
        "an ascent direction (∇fᵀd ≥ 0) has no Armijo-satisfying step; the search must "
        "reject it instead of looping forever")


# ---------------------------------------------------------------------------
# Step 4: backtracking descent converges where a fixed step diverges
# ---------------------------------------------------------------------------

def check_gradient_descent_backtracking() -> None:
    from optimization import gradient_descent, gradient_descent_backtracking

    A = [[1000.0, 0.0], [0.0, 1000.0]]       # λ_max = 1000; keep it isotropic so the
    f, g = _quad(A, [0.0, 0.0])              # line search itself converges quickly
    x0 = [1.0, 1.0]

    xf, _, _ = gradient_descent(f, g, x0, 1.0, tol=1e-8, max_iter=2000)
    assert not _converged(f, g, xf, 1e-8), (
        "the fixed step 1.0 exceeds 2/λ_max = 0.002 and must diverge; if it converged, "
        "the fixed-step update is wrong")

    x, it, history = gradient_descent_backtracking(
        f, g, x0, alpha0=1.0, tol=1e-8, max_iter=2000)
    assert _converged(f, g, x, 1e-8), (
        f"backtracking descent returned ‖∇f‖ = {_norm(g(x)):.3e} after {it} iterations: "
        "it must converge from a start where the full step diverges")
    assert f(x) < f(x0), "the line search must reduce the objective"

    for k in range(len(history) - 1):
        assert f(history[k + 1]) < f(history[k]), (
            f"f increased from {f(history[k]):.6e} to {f(history[k + 1]):.6e} between "
            "iterations: every accepted backtracking step must decrease f")


# ---------------------------------------------------------------------------
# Step 5: momentum is the heavy ball (βv + ∇f), not a restarted descent
# ---------------------------------------------------------------------------

def check_momentum() -> None:
    from optimization import gradient_descent, momentum

    A = [[2.0, 1.0], [1.0, 4.0]]
    b = [1.0, 0.0]
    f, g = _quad(A, b)
    x0 = [2.0, -1.0]
    step, beta, n = 0.2, 0.9, 20

    x, it, history = momentum(f, g, x0, step, beta, tol=0.0, max_iter=n)
    assert len(history) == n + 1, (
        f"with max_iter = {n} the history must hold n + 1 points, got {len(history)}")

    # Independent heavy-ball reference.
    ref_x = list(x0)
    ref_v = [0.0, 0.0]
    ref = [list(ref_x)]
    for _ in range(n):
        gg = g(ref_x)
        ref_v = [beta * ref_v[i] + gg[i] for i in range(2)]
        ref_x = [ref_x[i] - step * ref_v[i] for i in range(2)]
        ref.append(list(ref_x))
    for k in range(len(ref)):
        assert _maxdiff(history[k], ref[k]) < 1e-9, (
            f"momentum trajectory diverges from the heavy-ball recurrence at step {k}: "
            "v ← βv + ∇f(x), then x ← x − step·v. Dropping the βv term loses the "
            "inertia that defines momentum")

    # β = 0 must collapse to plain gradient descent.
    _, _, h_mom0 = momentum(f, g, x0, step, 0.0, tol=0.0, max_iter=n)
    _, _, h_gd = gradient_descent(f, g, x0, step, tol=0.0, max_iter=n)
    assert _maxdiff(h_mom0[-1], h_gd[-1]) < 1e-9, (
        "with β = 0 momentum must equal gradient descent")

    # And it must actually converge on a stable step.
    xc, itc, _ = momentum(f, g, x0, 0.3, 0.9, tol=1e-9, max_iter=5000)
    assert _converged(f, g, xc, 1e-9), "momentum failed to converge on a benign problem"


# ---------------------------------------------------------------------------
# Step 6: the fixed-step ceiling is 2/L, not 1/L or 4/L (limit case)
# ---------------------------------------------------------------------------

def check_step_ceiling() -> None:
    from optimization import gradient_descent, max_stable_step

    L = 100.0
    A = [[1.0, 0.0], [0.0, L]]
    f, g = _quad(A, [0.0, 0.0])
    x0 = [1.0, 1.0]
    tmax = max_stable_step(L)

    assert 1.5 / L < tmax < 3.0 / L, (
        f"max_stable_step({L}) = {tmax}: the ceiling is 2/L = {2.0 / L}, since "
        "|1 − tλ| < 1 for every eigenvalue λ ≤ L requires t < 2/L")

    xlo, itlo, _ = gradient_descent(f, g, x0, tmax * 0.99, tol=1e-8, max_iter=4000)
    assert _converged(f, g, xlo, 1e-8), (
        f"0.99 · max_stable_step = {tmax * 0.99} must converge: it is strictly inside "
        "the stability interval")

    xhi, ithi, _ = gradient_descent(f, g, x0, tmax * 1.01, tol=1e-8, max_iter=4000)
    assert not _converged(f, g, xhi, 1e-8), (
        f"1.01 · max_stable_step = {tmax * 1.01} must diverge: crossing 2/L makes "
        "|1 − tλ_max| > 1. If it converged, the ceiling is off by a factor")


# ---------------------------------------------------------------------------
# Step 7: iteration count grows with the condition number as predicted (accept)
# ---------------------------------------------------------------------------

def check_condition_number_growth() -> None:
    from optimization import gradient_descent

    measured = {}
    for kappa in (10, 100, 1000):
        L = float(kappa)
        A = [[1.0, 0.0], [0.0, L]]          # λ_min = 1, λ_max = κ
        f, g = _quad(A, [0.0, 0.0])
        x0 = [0.0, 1.0]                      # x0 − x* aligned with λ_max
        step = 2.0 / (1.0 + L)              # optimal fixed step
        tol = 1e-8
        rate = (kappa - 1.0) / (kappa + 1.0)  # exact per-step contraction on this ray
        g0 = _norm(g(x0))
        predicted = math.ceil(math.log(tol / g0) / math.log(rate))

        x, it, _ = gradient_descent(f, g, x0, step, tol=tol, max_iter=200000)
        assert _converged(f, g, x, tol), (
            f"κ = {kappa}: descent did not reach the tolerance; is the step "
            "2/(λ_min+λ_max)?")
        assert abs(it - predicted) <= 1, (
            f"κ = {kappa}: {it} iterations, the closed form predicts {predicted} "
            "(rate (κ−1)/(κ+1)). The iteration count must grow with the condition "
            "number as predicted, not by accident")
        measured[kappa] = it

    assert measured[10] < measured[100] < measured[1000], (
        f"iteration counts {measured} must increase with the condition number")
    assert measured[1000] > 4 * measured[10], (
        f"κ = 1000 needed {measured[1000]} iterations vs {measured[10]} at κ = 10: the "
        "growth is far weaker than the (κ−1)/(κ+1) rate predicts")


# ---------------------------------------------------------------------------
# Step 8: plain GD zig-zags on an ill-conditioned valley, momentum does not (limit)
# ---------------------------------------------------------------------------

def check_zigzag_vs_momentum() -> None:
    from optimization import gradient_descent, momentum

    L = 1000.0
    A = [[1.0, 0.0], [0.0, L]]
    f, g = _quad(A, [0.0, 0.0])
    x0 = [1.0, 1.0]
    step = 2.0 / (1.0 + L)
    tol = 1e-6

    xg, it_gd, hg = gradient_descent(f, g, x0, step, tol=tol, max_iter=50000)
    xm, it_mom, hm = momentum(f, g, x0, step, 0.9, tol=tol, max_iter=50000)
    assert _converged(f, g, xg, tol) and _converged(f, g, xm, tol), (
        "both methods must converge on this quadratic (their own checks cover the "
        "mechanics)")

    def path(h):
        return sum(_norm([h[k + 1][i] - h[k][i] for i in range(2)])
                   for k in range(len(h) - 1))

    def reversals(h):
        return sum(1 for k in range(1, len(h) - 1)
                   if (h[k + 1][1] - h[k][1]) * (h[k][1] - h[k - 1][1]) < 0)

    p_gd, p_mom = path(hg), path(hm)
    r_gd, r_mom = reversals(hg), reversals(hm)

    assert p_gd > 5.0 * p_mom, (
        f"plain GD travelled {p_gd:.1f} but momentum {p_mom:.1f}: on this narrow valley "
        "the steepest-descent path zig-zags across the valley, while momentum's inertia "
        "carries it along")
    assert r_gd > 5.0 * r_mom, (
        f"plain GD reversed direction {r_gd} times, momentum {r_mom}: the zig-zag is "
        "exactly this repeated reversal in the high-curvature coordinate")
    assert r_gd > 0.5 * it_gd, (
        f"plain GD must reverse on almost every step ({r_gd} of {it_gd}): with the "
        "optimal step the high-curvature mode's multiplier is negative")
    assert it_mom < it_gd, (
        f"momentum ({it_mom} iterations) must beat plain GD ({it_gd}) on this problem")


# ---------------------------------------------------------------------------
# Step 9: the constrained quadratic optimum satisfies KKT to 1e-8 (accept)
# ---------------------------------------------------------------------------

def check_lagrange_kkt() -> None:
    from optimization import lagrange_quadratic

    cases = [
        ([[2.0, 0.5], [0.5, 1.0]], [-1.0, 2.0], [[1.0, 1.0]], [1.0]),
        ([[4.0, 0.0, 0.0], [0.0, 4.0, 0.0], [0.0, 0.0, 4.0]],
         [0.0, 0.0, 0.0], [[1.0, 1.0, 1.0]], [3.0]),
    ]
    for Q, b, C, d in cases:
        x, lam = lagrange_quadratic(Q, b, C, d)
        n, m = len(x), len(lam)
        stationarity = _norm([sum(Q[i][j] * x[j] for j in range(n)) + b[i]
                              + sum(C[k][i] * lam[k] for k in range(m))
                              for i in range(n)])
        primal = _norm([sum(C[k][j] * x[j] for j in range(n)) - d[k]
                        for k in range(m)])
        assert stationarity < 1e-8, (
            f"‖Qx + b + Cᵀλ‖ = {stationarity:.2e}: the constrained optimum must satisfy "
            "stationarity to 1e-8. Check the Lagrangian sign (+λᵀ(Cx − d)) and that λ "
            "is returned, not dropped")
        assert primal < 1e-8, (
            f"‖Cx − d‖ = {primal:.2e}: the constrained optimum must be primal feasible "
            "to 1e-8; an unconstrained minimum generally is not")

        rx, rlam = _kkt_solve(Q, b, C, d)
        assert _maxdiff(x, rx) < 1e-9 and _maxdiff(lam, rlam) < 1e-9, (
            f"(x, λ) = ({x}, {lam}) but the KKT system gives ({rx}, {rlam}): the block "
            "system is [[Q, Cᵀ], [C, 0]] [x; λ] = [−b; d]")


# ---------------------------------------------------------------------------
# Step 10: the KKT residuals report BOTH stationarity and primal feasibility
# ---------------------------------------------------------------------------

def check_kkt_residuals() -> None:
    from optimization import kkt_residuals

    Q = [[2.0, 0.5], [0.5, 1.0]]
    b = [-1.0, 2.0]
    C = [[1.0, 1.0]]
    d = [1.0]
    xstar, lamstar = _kkt_solve(Q, b, C, d)

    st, pr = kkt_residuals(Q, b, C, d, xstar, lamstar)
    assert st < 1e-8 and pr < 1e-8, (
        f"the KKT residuals at the true optimum are ({st:.2e}, {pr:.2e}); both must "
        "vanish")

    # Feasible but not stationary: only the stationarity residual is nonzero.
    x_feas = [1.0, 0.0]
    st2, pr2 = kkt_residuals(Q, b, C, d, x_feas, [0.0])
    assert pr2 < 1e-12, "the test point (1, 0) is primal feasible"
    assert st2 > 1e-6, (
        f"at the feasible but non-stationary point {x_feas} the stationarity residual "
        f"is {st2:.2e}: kkt_residuals must compute ‖Qx + b + Cᵀλ‖, not only primal "
        "feasibility. Reporting it as zero hides a wrong answer")

    # Stationary but infeasible: only the primal residual is nonzero.
    xu = _solve(Q, [-b[0], -b[1]])           # unconstrained minimum
    st3, pr3 = kkt_residuals(Q, b, C, d, xu, [0.0])
    assert st3 < 1e-9, "the unconstrained minimum (λ = 0) is stationary"
    assert pr3 > 1e-6, (
        f"at the stationary but infeasible point {xu} the primal residual is "
        f"{pr3:.2e}: kkt_residuals must also compute ‖Cx − d‖")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("optimization.py", "∇(½xᵀAx − bᵀx) = Ax − b", check_quadratic_gradient),
    ("optimization.py", "fixed-step descent converges and returns its path", check_gradient_descent),
    ("optimization.py", "Armijo backtracking accepts only a decrease", check_backtracking_line_search),
    ("optimization.py", "backtracking descent beats a divergent fixed step", check_gradient_descent_backtracking),
    ("optimization.py", "momentum is the heavy ball (βv + ∇f)", check_momentum),
    ("optimization.py", "fixed-step ceiling is 2/L, not 1/L or 4/L", check_step_ceiling),
    ("optimization.py", "iterations grow with the condition number as predicted", check_condition_number_growth),
    ("optimization.py", "plain GD zig-zags, momentum does not", check_zigzag_vs_momentum),
    ("optimization.py", "constrained optimum satisfies KKT to 1e-8", check_lagrange_kkt),
    ("optimization.py", "KKT residuals keep both stationarity and feasibility", check_kkt_residuals),
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
    print(f"\n{BOLD}Continuous Optimization From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built continuous optimization from scratch.{RESET}")
        print(f"  {GREY}Run solutions/optimization.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
