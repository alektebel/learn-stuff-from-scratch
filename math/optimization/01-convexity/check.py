"""
Progress checker for the convexity templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The checker keeps its own arithmetic: it builds its own chords and measures the Jensen
gap itself (``_ref_gap``), so the preserving-operation and catalogue checks do not
depend on the learner's Jensen routine, and it hard-codes the reference eigenvalues of
the matrices it feeds to the learner's eigensolver.
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

JENSEN_TOL = 1e-6


# ---------------------------------------------------------------------------
# The checker's own Jensen gap (never the learner's)
# ---------------------------------------------------------------------------

def _ref_gap(f, box, seed, n=500):
    """Largest f(mid) - (lam f(x) + (1-lam) f(y)) over n chords, from scratch."""
    rng = random.Random(seed)
    worst = 0.0
    weights = [i / 10.0 for i in range(1, 10)]
    for _ in range(n):
        x = [rng.uniform(lo, hi) for lo, hi in box]
        y = [rng.uniform(lo, hi) for lo, hi in box]
        fx, fy = f(x), f(y)
        for lam in weights:
            mid = [lam * x[k] + (1.0 - lam) * y[k] for k in range(len(box))]
            worst = max(worst, f(mid) - (lam * fx + (1.0 - lam) * fy))
    return worst


# References for the matrices the learner's is_psd must judge.
PSD_MATRICES = [
    ([[2.0]], True),
    ([[0.0]], True),                       # semidefinite is allowed
    ([[2.0, 0.0], [0.0, 0.5]], True),
    ([[-2.0]], False),
    ([[0.0, 1.0], [1.0, 0.0]], False),     # eigenvalues +1, -1: the trace alone would lie
    ([[2.0, 1.0], [1.0, 2.0]], True),      # eigenvalues 1, 3
]


# ---------------------------------------------------------------------------
# Step 1: the Hessian and the PSD test
# ---------------------------------------------------------------------------

def check_hessian_and_psd() -> None:
    from convexity import hessian, jacobi_eigenvalues, is_psd

    H = hessian(lambda x: x[0] ** 2, [1.3])
    assert abs(H[0][0] - 2.0) < 1e-3, f"Hessian of x^2 should be 2, got {H[0][0]}"

    H = hessian(lambda x: x[0] * x[1], [0.3, 0.7])
    assert abs(H[0][1] - 1.0) < 1e-3, f"off-diagonal of Hessian(x*y) should be 1, got {H[0][1]}"

    H = hessian(lambda x: x[0] ** 4, [0.0])
    assert is_psd(H), "the Hessian of x^4 at 0 is the zero matrix: semidefinite counts"

    for matrix, expected in PSD_MATRICES:
        got = is_psd(matrix)
        assert got == expected, f"is_psd({matrix}) = {got}, expected {expected}"

    ev = jacobi_eigenvalues([[2.0, 1.0], [1.0, 2.0]])
    assert len(ev) == 2
    assert abs(ev[0] - 1.0) < 1e-8 and abs(ev[1] - 3.0) < 1e-8, f"eigenvalues should be 1 and 3, got {ev}"

    ev = jacobi_eigenvalues([[0.0, 1.0], [1.0, 0.0]])
    assert abs(ev[0] + 1.0) < 1e-8 and abs(ev[1] - 1.0) < 1e-8, f"eigenvalues should be -1 and 1, got {ev}"


# ---------------------------------------------------------------------------
# Step 2: the Jensen gap
# ---------------------------------------------------------------------------

def check_jensen_gap() -> None:
    from convexity import jensen_gap

    rng = random.Random(0)
    g = jensen_gap(lambda x: x[0] ** 2, [(-2.0, 2.0)], 300, rng)
    assert g <= JENSEN_TOL, f"x^2 is convex, gap should be ~0, got {g}"

    g = jensen_gap(lambda x: -(x[0] ** 2), [(-2.0, 2.0)], 300, rng)
    assert g > JENSEN_TOL, f"-x^2 is concave, the gap is a positive witness, got {g}"

    g = jensen_gap(lambda x: x[0] * x[1], [(-2.0, 2.0), (-2.0, 2.0)], 300, rng)
    assert g > JENSEN_TOL, f"x*y is indefinite, the gap must be positive, got {g}"

    # The gap must be the MAXIMUM over weights, not the minimum: a solver that kept
    # the smallest gap would report ~0 for -x^2 and x*y, so the two asserts above
    # already fail on it. (Sweeping every weight is robustness, not a necessity for
    # -x^2 specifically: a general non-convexity's largest witness can sit at any
    # weight, so the full sweep is the definition applied faithfully.)


# ---------------------------------------------------------------------------
# Step 3: operations that preserve convexity
# ---------------------------------------------------------------------------

def check_preserving() -> None:
    from convexity import nonneg_sum, pointwise_max, affine_compose

    f = nonneg_sum([lambda x: x[0] ** 2, lambda x: x[0] ** 4], [3.0, 0.5])
    assert _ref_gap(f, [(-2.0, 2.0)], 1) <= JENSEN_TOL, "a nonnegative sum of convex functions is convex"

    f = pointwise_max([lambda x: x[0] ** 2, lambda x: (x[0] - 1.0) ** 2])
    assert _ref_gap(f, [(-2.0, 2.0)], 2) <= JENSEN_TOL, "the pointwise maximum of convex functions is convex"

    f = affine_compose(lambda x: x[0] ** 2, [[2.0]], [1.0])
    assert _ref_gap(f, [(-2.0, 2.0)], 3) <= JENSEN_TOL, "an affine composition of a convex function is convex"

    f = nonneg_sum([lambda x: x[0] ** 2], [-1.0])
    assert _ref_gap(f, [(-2.0, 2.0)], 4) > JENSEN_TOL, "a negative weight must break convexity"


# ---------------------------------------------------------------------------
# Step 4: the catalogue, classified correctly
# ---------------------------------------------------------------------------

def _catalogue():
    return [
        ("x^2", lambda x: x[0] ** 2, [(-2.0, 2.0)], True),
        ("abs(x)", lambda x: abs(x[0]), [(-2.0, 2.0)], True),
        ("x^4", lambda x: x[0] ** 4, [(-2.0, 2.0)], True),
        ("exp(x)", lambda x: math.exp(x[0]), [(-2.0, 2.0)], True),
        ("log-sum-exp", lambda x: math.log(math.exp(x[0]) + math.exp(x[1])),
         [(-2.0, 2.0), (-2.0, 2.0)], True),
        ("geometric-mean", lambda x: math.sqrt(x[0] * x[1]), [(0.5, 3.0), (0.5, 3.0)], False),
        ("-x^2", lambda x: -(x[0] ** 2), [(-2.0, 2.0)], False),
        ("x*y", lambda x: x[0] * x[1], [(-2.0, 2.0), (-2.0, 2.0)], False),
        ("sqrt(abs(x))", lambda x: math.sqrt(abs(x[0])), [(-2.0, 2.0)], False),
    ]


def check_catalogue() -> None:
    from convexity import classify

    for i, (name, f, box, expected) in enumerate(_catalogue()):
        # Independent witness: a non-convex function must show a positive gap.
        gap = _ref_gap(f, box, 100 + i)
        if not expected:
            assert gap > JENSEN_TOL, f"sanity: {name} should show a positive reference gap, got {gap}"
        got = classify(f, box, random.Random(7))
        assert got == expected, f"classify({name}) = {got}, expected {expected}"


# ---------------------------------------------------------------------------
# Step 5: the naive sublevel test is fooled by a quasiconvex function
# ---------------------------------------------------------------------------

def check_sublevel() -> None:
    from convexity import sublevel_grid_test, classify

    sqrt_abs = lambda x: math.sqrt(abs(x[0]))  # noqa: E731
    fooled = sublevel_grid_test(sqrt_abs, -4.0, 4.0, [0.25, 0.5, 0.75, 1.0])
    assert fooled is True, "the sublevel sets of sqrt(abs(x)) are intervals: the naive test is fooled"

    caught = sublevel_grid_test(lambda x: -(x[0] ** 2), -4.0, 4.0, [-4.0, -2.0, -1.0, -0.5])
    assert caught is False, "-x^2 has a non-convex sublevel set; the naive test must reject it"

    assert classify(sqrt_abs, [(-2.0, 2.0)], random.Random(0)) is False, \
        "sqrt(abs(x)) is quasiconvex but not convex; classify must say so"


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("convexity.py", "the Hessian and the PSD test", check_hessian_and_psd),
    ("convexity.py", "the Jensen gap", check_jensen_gap),
    ("convexity.py", "operations that preserve convexity", check_preserving),
    ("convexity.py", "the catalogue, classified correctly", check_catalogue),
    ("convexity.py", "the naive sublevel test is fooled", check_sublevel),
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
    print(f"\n{BOLD}Convex Sets and Convex Functions From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built convexity from scratch.{RESET}")
        print(f"  {GREY}Run solutions/convexity.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
