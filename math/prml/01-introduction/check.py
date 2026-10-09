"""
Progress checker for the PRML-introduction templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The checker carries its own arithmetic: its own polynomial evaluator and mean squared
error (`_f`, `_mse`), and it measures the expected test error against fresh noise. The
identity it enforces -- ``error == bias^2 + variance + noise`` -- is checked by comparing
two independently measured sides, never by reading one side off the other.
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
# The checker's own references (never the learner's)
# ---------------------------------------------------------------------------

def _f(x):
    """The target function: sin(2 pi x)."""
    return math.sin(2.0 * math.pi * x)


def _eval(w, x):
    """Evaluate a polynomial by Horner's rule, from scratch."""
    acc = 0.0
    for coefficient in reversed(w):
        acc = acc * x + coefficient
    return acc


def _mse(w, xs, ts):
    """Mean squared error, from scratch."""
    return sum((_eval(w, x) - t) ** 2 for x, t in zip(xs, ts)) / len(xs)


# ---------------------------------------------------------------------------
# Step 1: least squares and the polynomial primitives
# ---------------------------------------------------------------------------

def check_least_squares() -> None:
    from intro import poly_features, poly_fit, poly_predict, squared_error

    assert poly_features(2.0, 3) == [1.0, 2.0, 4.0, 8.0], \
        f"poly_features(2, 3) must be [1, 2, 4, 8], got {poly_features(2.0, 3)}"

    xs = [i / 19.0 for i in range(20)]
    ts = [1.0 - 2.0 * x + 0.5 * x * x for x in xs]
    w = poly_fit(xs, ts, 2)
    want = [1.0, -2.0, 0.5]
    assert all(abs(w[k] - want[k]) < 1e-8 for k in range(3)), \
        f"a quadratic must be recovered exactly, got {w}"

    assert abs(poly_predict(w, 0.5) - _eval(want, 0.5)) < 1e-9, \
        "poly_predict must evaluate the fitted polynomial"
    assert abs(squared_error(w, xs, ts) - _mse(want, xs, ts)) < 1e-12, \
        "squared_error must be the mean squared error"


# ---------------------------------------------------------------------------
# Step 2: the degree-9 limit (overfitting, and ridge fixing it)
# ---------------------------------------------------------------------------

def check_degree_nine_limit() -> None:
    from intro import poly_fit

    rng = random.Random(2)
    x9 = [i / 9.0 for i in range(10)]
    t9 = [_f(x) + rng.gauss(0.0, 0.3) for x in x9]
    xt = [0.005 + 0.99 * i / 399.0 for i in range(400)]
    tt = [_f(x) for x in xt]

    w = poly_fit(x9, t9, 9)
    train = _mse(w, x9, t9)
    test = _mse(w, xt, tt)
    assert train < 1e-6, f"degree 9 interpolates 10 points, train error should be ~0, got {train}"
    assert test > 0.2, f"the interpolation of the noise must not generalise, test error got {test}"

    wr = poly_fit(x9, t9, 9, lam=1e-5)
    test_ridge = _mse(wr, xt, tt)
    assert test_ridge < 0.25 * test, \
        f"ridge (lam=1e-5) must cut the test error; unregularised {test:.3e}, ridge {test_ridge:.3e}"


# ---------------------------------------------------------------------------
# Step 3: the bias-variance decomposition by simulation
# ---------------------------------------------------------------------------

def check_bias_variance() -> None:
    from intro import bias_variance

    bias_sq, variance, noise, error = bias_variance(degree=1, n_train=20, sigma=0.2, seed=1)
    assert bias_sq > 0.0 and variance > 0.0 and noise > 0.0, \
        f"all three terms must be positive, got {(bias_sq, variance, noise)}"
    assert abs((bias_sq + variance + noise) - error) < 0.02, (
        "the simulated expected test error must equal bias^2 + variance + noise: "
        f"{error:.4f} vs {bias_sq + variance + noise:.4f}")

    # A more flexible model trades bias for variance.
    b0, v0, _, _ = bias_variance(degree=0, n_train=20, sigma=0.2, seed=1, n_sets=150)
    b6, v6, _, _ = bias_variance(degree=6, n_train=20, sigma=0.2, seed=1, n_sets=150)
    assert b0 > b6, f"bias^2 should fall as the model grows: degree 0 {b0:.4f} vs degree 6 {b6:.4f}"
    assert v6 > v0, f"variance should rise as the model grows: degree 0 {v0:.4f} vs degree 6 {v6:.4f}"


# ---------------------------------------------------------------------------
# Step 4: minimum-risk decisions
# ---------------------------------------------------------------------------

def check_min_risk() -> None:
    from intro import min_risk_decision

    symmetric = [[0.0, 1.0], [1.0, 0.0]]
    assert min_risk_decision(0.4, symmetric) == 0, "below 0.5 with a symmetric loss, take action 0"
    assert min_risk_decision(0.6, symmetric) == 1, "above 0.5 with a symmetric loss, take action 1"

    # Asymmetric loss: action 0 costs 10 when the class is 1, action 1 costs 1 when it
    # is 0. The boundary moves to p = 1 / 11, well below 0.5.
    asymmetric = [[0.0, 10.0], [1.0, 0.0]]
    assert min_risk_decision(0.4, asymmetric) == 1, \
        "an asymmetric loss must move the boundary away from p = 0.5"
    assert min_risk_decision(0.05, asymmetric) == 0, \
        "below the asymmetric boundary the cheap action is still action 0"


# ---------------------------------------------------------------------------
# Step 5: entropy, KL divergence and mutual information
# ---------------------------------------------------------------------------

def check_information_theory() -> None:
    from intro import entropy, kl_divergence, mutual_information

    assert abs(entropy([1.0])) < 1e-12, "a point mass has zero entropy"
    assert abs(entropy([0.5, 0.5]) - math.log(2.0)) < 1e-12, \
        f"entropy([0.5, 0.5]) must be ln 2, got {entropy([0.5, 0.5])}"
    assert entropy([0.5, 0.5]) > entropy([0.9, 0.1]), "entropy is largest at the uniform"

    assert abs(kl_divergence([0.2, 0.3, 0.5], [0.2, 0.3, 0.5])) < 1e-12, \
        "KL(p || p) must be zero"
    assert kl_divergence([0.7, 0.3], [0.5, 0.5]) > 0.0, \
        "KL(p || q) must be positive for different distributions"
    for p, q in (([0.9, 0.1], [0.5, 0.5]), ([0.3, 0.3, 0.4], [0.2, 0.5, 0.3])):
        assert kl_divergence(p, q) >= 0.0, "KL divergence is non-negative"

    independent = [[0.25, 0.25], [0.25, 0.25]]
    assert abs(mutual_information(independent)) < 1e-12, \
        "mutual information of an independent joint is zero"
    assert abs(mutual_information([[0.5, 0.0], [0.0, 0.5]]) - math.log(2.0)) < 1e-12, \
        "perfectly correlated fair bits carry ln 2 of mutual information"


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("intro.py", "least squares reproduces a polynomial", check_least_squares),
    ("intro.py", "degree-9 on 10 points: overfitting and ridge", check_degree_nine_limit),
    ("intro.py", "the bias-variance decomposition", check_bias_variance),
    ("intro.py", "minimum-risk decisions and a loss matrix", check_min_risk),
    ("intro.py", "entropy, KL divergence and mutual information", check_information_theory),
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
    print(f"\n{BOLD}PRML Introduction From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<10} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<10} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<10} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built the PRML introduction from scratch.{RESET}")
        print(f"  {GREY}Run solutions/intro.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
