"""
Progress checker for the PRML support-vector-machine templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The checker carries its own kernel values, its own Gram matrix and its own independent
dual solver (accelerated projected gradient), so the numeric comparisons are not a
restatement of the learner's SMO. The accept criteria are: only the support vectors
carry non-zero weight and the margin read off the KKT conditions equals the primal
2 / ||w||; and the learner's dual objective matches the checker's own QP reference on
small problems.
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
# The checker's own references (never the learner's)
# ---------------------------------------------------------------------------

def _ref_linear(variance=1.0, offset=0.0):
    return lambda x, y: variance * (x * y + offset)


def _ref_rbf(length_scale=1.0, variance=1.0):
    def kernel(x, y):
        d = x - y
        return variance * math.exp(-d * d / (2.0 * length_scale * length_scale))
    return kernel


def _gram_ref(kernel, xs):
    n = len(xs)
    return [[kernel(xs[i], xs[j]) for j in range(n)] for i in range(n)]


def _clip_ref(value, lo, hi):
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _project_ref(alphas, ts, C):
    """Project onto ``{0 <= a <= C, sum_i t_i a_i = 0}`` by bisecting the multiplier."""
    n = len(alphas)
    lo, hi = -1e12, 1e12
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        residual = sum(ts[i] * _clip_ref(alphas[i] - mid * ts[i], 0.0, C)
                       for i in range(n))
        if residual > 0.0:
            lo = mid
        else:
            hi = mid
    mu = 0.5 * (lo + hi)
    return [_clip_ref(alphas[i] - mu * ts[i], 0.0, C) for i in range(n)]


def _reference_qp(kernel, xs, ts, C, iters=30000):
    """The checker's independent dual solver: accelerated projected gradient."""
    n = len(xs)
    K = _gram_ref(kernel, xs)
    Q = [[ts[i] * ts[j] * K[i][j] for j in range(n)] for i in range(n)]

    v = [1.0 / math.sqrt(n)] * n
    lam = 0.0
    for _ in range(200):
        w = [sum(Q[i][j] * v[j] for j in range(n)) for i in range(n)]
        norm = math.sqrt(sum(x * x for x in w))
        if norm == 0.0:
            break
        v = [x / norm for x in w]
        lam = norm
    L = lam if lam > 1e-12 else 1.0

    a = [0.0] * n
    y = list(a)
    theta = 1.0
    for _ in range(iters):
        grad = [sum(Q[i][j] * y[j] for j in range(n)) - 1.0 for i in range(n)]
        a_new = _project_ref([y[i] - grad[i] / L for i in range(n)], ts, C)
        theta_new = 0.5 * (1.0 + math.sqrt(1.0 + 4.0 * theta * theta))
        y = [a_new[i] + ((theta - 1.0) / theta_new) * (a_new[i] - a[i])
             for i in range(n)]
        a = a_new
        theta = theta_new
    return a


def _dual(Q, alphas):
    """``sum_i a_i - 1/2 a^T Q a``, the quantity the dual maximises."""
    quad = 0.0
    n = len(alphas)
    for i in range(n):
        for j in range(n):
            quad += alphas[i] * Q[i][j] * alphas[j]
    return sum(alphas) - 0.5 * quad


def _Q_ref(kernel, xs, ts):
    K = _gram_ref(kernel, xs)
    n = len(xs)
    return [[ts[i] * ts[j] * K[i][j] for j in range(n)] for i in range(n)]


def _close(a, b, tol):
    return abs(a - b) <= tol


def _feasible(alphas, ts, C, tol=1e-6):
    if any(a < -tol for a in alphas):
        return False
    if C != math.inf and any(a > C + tol for a in alphas):
        return False
    return abs(sum(alphas[i] * ts[i] for i in range(len(alphas)))) <= 1e-5


# ---------------------------------------------------------------------------
# Step 1: SMO finds a feasible, correct solution on separable data
# ---------------------------------------------------------------------------

def check_smo_feasible() -> None:
    from svm import decision_function, linear_kernel, smo

    xs = [-2.0, -1.0, 0.0, 1.0, 2.0]
    ts = [-1, -1, -1, 1, 1]
    C = 10.0
    kernel = linear_kernel()
    alphas, b = smo(xs, ts, C, kernel)

    assert len(alphas) == len(xs), "smo must return one dual variable per input"
    for i, a in enumerate(alphas):
        assert -1e-9 <= a <= C + 1e-9, (
            f"every dual variable must satisfy 0 <= a_i <= C; a_{i} = {a!r} with "
            f"C = {C}. The box constraint is part of the soft-margin dual.")
    total = sum(alphas[i] * ts[i] for i in range(len(xs)))
    assert abs(total) < 1e-6, (
        "the dual optimum must satisfy sum_i a_i t_i = 0 (the equality that comes "
        f"from the bias); got {total:.3e}. Each term carries the label t_i.")

    model = {"Xs": xs, "ts": ts, "kernel": kernel, "alphas": alphas, "b": b}
    for i, x in enumerate(xs):
        f = decision_function(model, x)
        assert ts[i] * f > 0.0, (
            f"on this separable set the trained SVM must classify every point: at "
            f"x = {x} with t = {ts[i]:+d} the decision value is {f!r} (sign wrong). "
            "The bias update and the KKT test both use t_i.")


# ---------------------------------------------------------------------------
# Step 2 (ACCEPT): only support vectors are non-zero, and the margin agrees
# ---------------------------------------------------------------------------

def check_support_vectors_and_margin() -> None:
    from svm import decision_function, linear_kernel, margin, smo, support_vectors

    xs = [-1.0, 0.0, 1.0, 2.0]
    ts = [-1, 1, 1, 1]
    C = 10.0
    kernel = linear_kernel()
    alphas, b = smo(xs, ts, C, kernel)

    sv = support_vectors(alphas)
    true_sv = [i for i, a in enumerate(alphas) if a > 1e-5]
    assert sv == true_sv, (
        "support_vectors must return exactly the indices with a_i > tol: the KKT "
        f"conditions force a_i = 0 for every other point. Got {sv}, expected "
        f"{true_sv} from alphas = {[round(a, 6) for a in alphas]}.")
    assert sv, (
        "there must be at least one support vector here; an empty list means the "
        "alpha > tol test is wrong")
    for i in range(len(alphas)):
        if i not in sv:
            assert alphas[i] <= 1e-5, (
                f"only the support vectors may carry weight: a_{i} = {alphas[i]!r} "
                "is non-zero but the point is not a support vector")

    model = {"Xs": xs, "ts": ts, "kernel": kernel, "alphas": alphas, "b": b}
    for i in sv:
        f = decision_function(model, xs[i])
        assert _close(ts[i] * f, 1.0, 1e-4), (
            "every support vector must sit exactly on the margin, "
            f"t_i f(x_i) = 1: at x = {xs[i]} with t = {ts[i]:+d} the margin is "
            f"{ts[i] * f!r}. If it is off by a constant, the bias must be the "
            "AVERAGE of the candidates t_i - sum_j a_j t_j k(x_j, x_i) over the "
            "free support vectors, not one of them and not their sum.")

    m_model = margin(model, xs, ts)
    w = sum(alphas[i] * ts[i] * xs[i] for i in range(len(xs)))
    assert abs(w) > 1e-9, (
        "the check's own primal weight collapsed; the chosen data should give w != 0")
    m_primal = 2.0 / abs(w)
    assert _close(m_model, m_primal, 1e-6), (
        "the margin read off the support vectors must equal the primal "
        f"2 / ||w||: margin(...) = {m_model!r}, 2 / |w| = {m_primal!r}. Here "
        f"w = sum_i a_i t_i x_i = {w!r}. Note 2 / ||w||, not ||w||.")


# ---------------------------------------------------------------------------
# Step 3 (ACCEPT): SMO matches the checker's independent QP reference
# ---------------------------------------------------------------------------

def check_matches_reference_qp() -> None:
    from svm import linear_kernel, rbf_kernel, smo

    problems = [
        ("linear, separable", [-1.5, -0.5, 0.5, 1.5], [-1, -1, 1, 1],
         _ref_linear(), 5.0),
        ("rbf, non-separable soft margin", [-1.0, 0.0, 1.0], [-1, 1, -1],
         _ref_rbf(0.7, 1.0), 1.0),
    ]
    for name, xs, ts, ref_kernel, C in problems:
        kernel = (linear_kernel() if name.startswith("linear")
                  else rbf_kernel(0.7, 1.0))
        alphas, _ = smo(xs, ts, C, kernel)
        assert _feasible(alphas, ts, C), (
            f"[{name}] the SMO solution is not feasible: alphas = "
            f"{[round(a, 6) for a in alphas]}, sum a_i t_i = "
            f"{sum(alphas[i] * ts[i] for i in range(len(xs))):.3e}")

        Q = _Q_ref(ref_kernel, xs, ts)
        ref = _reference_qp(ref_kernel, xs, ts, C)
        got = _dual(Q, alphas)
        want = _dual(Q, ref)
        assert _close(got, want, 1e-4), (
            f"[{name}] SMO and the checker's independent QP solver must reach the "
            f"same dual optimum: SMO gives {got:.8f}, the reference gives "
            f"{want:.8f}. A KKT test that drops t_i, or a bias/box error, stops "
            "short of the optimum.")


# ---------------------------------------------------------------------------
# Step 4: the soft margin tolerates an outlier with a finite margin
# ---------------------------------------------------------------------------

def check_soft_margin_outlier() -> None:
    from svm import margin, rbf_kernel, smo

    xs = [-1.5, -0.5, 0.5, 1.5, 2.5]
    ts = [-1, -1, 1, 1, -1]
    C = 1.0
    kernel = rbf_kernel(1.0, 1.0)
    alphas, b = smo(xs, ts, C, kernel)

    assert _feasible(alphas, ts, C), (
        "the soft-margin solution must be feasible")
    model = {"Xs": xs, "ts": ts, "kernel": kernel, "alphas": alphas, "b": b}
    m = margin(model, xs, ts)
    assert math.isfinite(m) and m > 0.0, (
        f"the soft margin must keep a finite positive margin, got {m!r}")
    assert max(alphas) <= C + 1e-9, "no dual variable may exceed C"
    assert _close(max(alphas), C, 1e-6), (
        "the mislabelled outlier at x = 2.5 must saturate at the box bound "
        f"a = C = {C}: got max(alpha) = {max(alphas)!r}. When a point cannot be "
        "inside the margin, the box constraint is what caps its influence.")


# ---------------------------------------------------------------------------
# Step 5 (LIMIT CASES): hard margin is infeasible on non-separable data
# ---------------------------------------------------------------------------

def check_limit_hard_vs_soft() -> None:
    from svm import linear_kernel, smo

    xs = [0.0, 1.0, 2.0]
    ts = [1, -1, 1]
    kernel = linear_kernel()

    # The checker's own proof that no threshold separates the data: the classes
    # interleave along the line, so the convex hulls overlap.
    pos = [xs[i] for i in range(len(xs)) if ts[i] > 0]
    neg = [xs[i] for i in range(len(xs)) if ts[i] < 0]
    separable = max(pos) < min(neg) or max(neg) < min(pos)
    assert not separable, (
        "the check's own non-separability test must agree: with labels +1, -1, +1 "
        "in this order, the classes interleave and no hyperplane separates them")

    raised = False
    try:
        smo(xs, ts, math.inf, kernel)
    except ValueError:
        raised = True
    assert raised, (
        "a hard margin (C = infinity) leaves the dual unbounded below on "
        "non-separable data, so SMO cannot reach a KKT point. smo must raise "
        "ValueError instead of returning a model that silently misclassifies. "
        "Reporting success here is the bug this step exists to catch.")

    alphas, _ = smo(xs, ts, 1.0, kernel)
    assert _feasible(alphas, ts, 1.0), (
        "the soft margin must still return a feasible solution")
    assert max(alphas) <= 1.0 + 1e-9, "no dual variable may exceed C = 1"
    assert max(alphas) > 0.0, (
        "the soft margin must put weight on the violating points; a solution with "
        "all a_i = 0 means the solver gave up on the data")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("svm.py", "SMO finds a feasible, correct solution", check_smo_feasible),
    ("svm.py", "only support vectors carry weight; margin matches the primal", check_support_vectors_and_margin),
    ("svm.py", "SMO matches the checker's independent QP reference", check_matches_reference_qp),
    ("svm.py", "soft margin absorbs an outlier with a finite margin", check_soft_margin_outlier),
    ("svm.py", "limit: hard margin infeasible on non-separable data", check_limit_hard_vs_soft),
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
    print(f"\n{BOLD}PRML Support Vector Machines From Scratch — progress check{RESET}")
    print(f"{GREY}implement the template, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<9} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<9} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<9} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built SVMs from scratch.{RESET}")
        print(f"  {GREY}Run solutions/svm.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
