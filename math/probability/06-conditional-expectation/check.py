"""
Progress checker for the conditional-expectation templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

Every reference value is recomputed here, independently of the learner's code: the
conditional means and variances by normalising the joint row directly, E[Y] and Var(Y)
by summing the joint, and E[Var(Y|X)] / Var(E[Y|X]) by walking the conditioning values.
The node's acceptance rule -- E[Y|X] has mean squared error no larger than any other
predictor g(X) -- is enforced against a best constant, a linear predictor, a quadratic
predictor and a seeded random predictor, with a strict win over the best constant. The
limit case is a two-stage model whose total variance must be reconstructed from
E[Var(Y|X)] + Var(E[Y|X]), never from the within-group term alone.
"""

import pathlib
import random
import shutil
import sys
import traceback
from fractions import Fraction

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


# ---------------------------------------------------------------------------
# The checker's own arithmetic (never the learner's)
# ---------------------------------------------------------------------------

def _outcomes(joint):
    """((x, y), p) pairs for a dict joint or a matrix joint[i][j]."""
    if isinstance(joint, dict):
        return list(joint.items())
    return [((i, j), p) for i, row in enumerate(joint) for j, p in enumerate(row)]


def _mean_y(joint):
    return sum(y * p for (_x, y), p in _outcomes(joint))


def _second_y(joint):
    return sum(y * y * p for (_x, y), p in _outcomes(joint))


def _var_y(joint):
    mean = _mean_y(joint)
    return _second_y(joint) - mean * mean


def _ref_cond_mean(joint, given):
    num = sum(y * p for (x, y), p in _outcomes(joint) if x == given)
    den = sum(p for (x, y), p in _outcomes(joint) if x == given)
    return num / den


def _ref_cond_var(joint, given):
    num = sum(y * y * p for (x, y), p in _outcomes(joint) if x == given)
    den = sum(p for (x, y), p in _outcomes(joint) if x == given)
    mean = num / den
    return num / den - mean * mean


def _sample_joint(joint, trials, rng):
    """The checker's own sampler, a cumulative walk over the joint."""
    outcomes = _outcomes(joint)
    cumulative = []
    acc = 0
    for xy, p in outcomes:
        acc = acc + p
        cumulative.append((acc, xy))
    draws = []
    for _ in range(trials):
        u = rng.random()
        for acc, xy in cumulative:
            if u <= acc:
                draws.append(xy)
                break
        else:
            draws.append(outcomes[-1][0])
    return draws


def _sample_binomial(n, q, rng):
    return sum(1 for _ in range(n) if rng.random() < q)


def _sample_hierarchical(p, n, q0, q1, trials, rng):
    draws = []
    for _ in range(trials):
        if rng.random() < p:
            draws.append(_sample_binomial(n, q1, rng))
        else:
            draws.append(_sample_binomial(n, q0, rng))
    return draws


def _variance(values):
    n = len(values)
    mean = sum(values) / n
    return sum((v - mean) ** 2 for v in values) / n


# The hand joint used across steps 1-3: X in {0, 1}, Y in {0, 1}.
#   P(0, 0) = 1/2, P(0, 1) = 1/4, P(1, 0) = 1/4.
# Marginals: P(X = 0) = 3/4, P(X = 1) = 1/4, E[Y] = 1/4, Var(Y) = 3/16.
HAND = {(0, 0): Fraction(1, 2), (0, 1): Fraction(1, 4),
        (1, 0): Fraction(1, 4)}

# The nonlinear joint used in step 4: X in {0, 1, 2}, Y in {0, 1}.
# Conditional means are 1/2, 1, 1/2 -- an inverted V, so no straight line fits.
NONLINEAR = {(0, 0): Fraction(1, 6), (0, 1): Fraction(1, 6),
             (1, 0): Fraction(0), (1, 1): Fraction(1, 3),
             (2, 0): Fraction(1, 6), (2, 1): Fraction(1, 6)}


# ---------------------------------------------------------------------------
# Step 1: conditional expectation and variance against exact hand values
# ---------------------------------------------------------------------------

def check_conditional_moments() -> None:
    from cond import conditional_expectation, conditional_variance

    joint = HAND
    got = conditional_expectation(joint, 0)
    assert got == Fraction(1, 3), (
        f"E[Y | X = 0] = {got}, expected 1/3. The row is P(X=0,Y=0)=1/2 and "
        "P(X=0,Y=1)=1/4, and P(X = 0) = 3/4, so the conditional mean is "
        "(0*1/2 + 1*1/4) / (3/4) = 1/3. Dividing by the number of outcomes (2) "
        "gives 1/8 and dividing by 1 gives 1/4 -- both are the classic bug this "
        "step catches")
    got = conditional_expectation(joint, 1)
    assert got == Fraction(0), (
        f"E[Y | X = 1] = {got}, expected 0: the only outcome with X = 1 has Y = 0")

    got = conditional_variance(joint, 0)
    assert got == Fraction(2, 9), (
        f"Var(Y | X = 0) = {got}, expected 2/9 = E[Y^2|X=0] - (1/3)^2 = "
        "1/3 - 1/9. The second moment is (0^2*1/2 + 1^2*1/4)/(3/4) = 1/3; using "
        "an unnormalised sum, or the wrong denominator, changes it")
    got = conditional_variance(joint, 1)
    assert got == Fraction(0), (
        f"Var(Y | X = 1) = {got}, expected 0: given X = 1, Y is a point mass at 0")

    # The same identities for the matrix (list-of-lists) form.
    matrix = [[Fraction(1, 2), Fraction(1, 4)],
              [Fraction(1, 4), Fraction(0)]]
    got = conditional_expectation(matrix, 0)
    assert got == Fraction(1, 3), (
        f"the matrix form gives E[Y | X = 0] = {got}, expected 1/3: "
        "matrix[i][j] = P(X = i, Y = j), so row 0 is [1/2, 1/4] and its "
        "conditional mean is (1/4)/(3/4)")
    got = conditional_variance(matrix, 0)
    assert got == Fraction(2, 9), (
        f"the matrix form gives Var(Y | X = 0) = {got}, expected 2/9")


# ---------------------------------------------------------------------------
# Step 2: Adam's law, exactly and by simulation
# ---------------------------------------------------------------------------

def check_adams_law() -> None:
    from cond import adam_law

    joint = HAND
    direct, law = adam_law(joint)
    ref = _mean_y(joint)
    assert direct == ref == Fraction(1, 4), (
        f"the direct E[Y] is {direct}, expected 1/4 (= 1 * P(0, 1)). Sum y * p "
        "over every outcome of the joint")
    assert law == ref, (
        f"sum_x P(X = x) E[Y | X = x] = {law}, expected 1/4. The conditional "
        "means are E[Y|X=0] = 1/3 and E[Y|X=1] = 0; weighting them by the "
        "marginals P(X=0)=3/4 and P(X=1)=1/4 gives (3/4)(1/3) = 1/4. Averaging "
        "the two conditionals UNWEIGHTED gives 1/6, which is the bug step 2 "
        "plants")
    assert direct == law, (
        "Adam's law must hold exactly: the joint mean equals the marginal-"
        "weighted average of the conditional means")

    # A second, symmetric joint in matrix form: the two sides agree there too.
    matrix = [[Fraction(1, 4), Fraction(0)],
              [Fraction(1, 4), Fraction(1, 2)]]
    direct_m, law_m = adam_law(matrix)
    assert direct_m == law_m == _mean_y(matrix), (
        f"Adam's law for the matrix joint gives direct = {direct_m} and law = "
        f"{law_m}; they must both equal the joint mean {_mean_y(matrix)}")

    # Simulation: the conditional means must reproduce the sample.
    rng = random.Random(20260601)
    draws = _sample_joint(joint, 120000, rng)
    empirical = sum(y for _x, y in draws) / len(draws)
    assert abs(float(ref) - empirical) < 0.02, (
        f"the sample mean of Y is {empirical:.4f}, not close to the analytic "
        "E[Y] = 0.25: the independent sampler and the joint disagree")
    for x in (0, 1):
        group = [y for gx, y in draws if gx == x]
        assert group, f"no sampled outcome had X = {x}"
        emp_cond = sum(group) / len(group)
        want = float(_ref_cond_mean(joint, x))
        assert abs(emp_cond - want) < 0.03, (
            f"sample E[Y | X = {x}] = {emp_cond:.4f}, not close to the analytic "
            f"{want}: Adam's law is a statement about these conditional means")


# ---------------------------------------------------------------------------
# Step 3: Eve's law, exactly and by simulation
# ---------------------------------------------------------------------------

def check_eves_law() -> None:
    from cond import eve_law

    joint = HAND
    direct, within, between = eve_law(joint)
    ref = _var_y(joint)
    assert direct == ref == Fraction(3, 16), (
        f"Var(Y) from the joint is {direct}, expected 3/16 = E[Y^2] - (E[Y])^2 "
        "= 1/4 - 1/16")
    assert within == Fraction(1, 6), (
        f"E[Var(Y | X)] = {within}, expected 1/6 = (3/4)(2/9) + (1/4)(0): weight "
        "each conditional variance by the marginal P(X = x)")
    assert between == Fraction(1, 48), (
        f"Var(E[Y | X]) = {between}, expected 1/48 = (3/4)(1/3 - 1/4)^2 + "
        "(1/4)(0 - 1/4)^2: the spread of the conditional means about E[Y]")
    assert direct == within + between, (
        f"Eve's law fails: Var(Y) = {direct} but E[Var(Y|X)] + Var(E[Y|X]) = "
        f"{within + between}. Dropping Var(E[Y | X]) leaves {within}, which is "
        "the naive within-group variance and is exactly the bug step 3 plants")

    # Simulation: the identity must hold on the sample too.
    rng = random.Random(20260602)
    draws = _sample_joint(joint, 120000, rng)
    empirical_var = _variance([y for _x, y in draws])
    assert abs(float(ref) - empirical_var) < 0.02, (
        f"sample Var(Y) = {empirical_var:.4f}, not close to the analytic "
        f"{float(ref):.4f}")
    overall = sum(y for _x, y in draws) / len(draws)
    within_emp = 0.0
    between_emp = 0.0
    for x in (0, 1):
        group = [y for gx, y in draws if gx == x]
        assert group, f"no sampled outcome had X = {x}"
        w = len(group) / len(draws)
        mean_x = sum(group) / len(group)
        within_emp += w * _variance(group)
        between_emp += w * (mean_x - overall) ** 2
    assert abs(within_emp + between_emp - empirical_var) < 1e-9, (
        "Eve's law must hold identically on any sample: within + between must "
        "reconstruct the sample variance")
    assert abs(within_emp - float(Fraction(1, 6))) < 0.03, (
        f"sample E[Var(Y|X)] = {within_emp:.4f}, not close to 1/6")
    assert abs(between_emp - float(Fraction(1, 48))) < 0.02, (
        f"sample Var(E[Y|X]) = {between_emp:.4f}, not close to 1/48. If this is "
        "far off while within is fine, the between-group spread was dropped")


# ---------------------------------------------------------------------------
# Step 4: E[Y|X] is the best predictor in squared error (the acceptance rule)
# ---------------------------------------------------------------------------

def check_best_predictor() -> None:
    from cond import best_predictor_mse, conditional_expectation

    joint = NONLINEAR
    mean_ref = _mean_y(joint)
    assert mean_ref == Fraction(2, 3), (
        "checker self-test: the nonlinear joint must have mean 2/3; rebuild the "
        "hand joint if this fires")

    mse_eyx = best_predictor_mse(joint, lambda x: conditional_expectation(joint, x))
    assert mse_eyx == Fraction(1, 6), (
        f"MSE of E[Y | X] is {mse_eyx}, expected 1/6 = E[Var(Y | X)] = "
        "(1/3)(1/4) + (1/3)(0) + (1/3)(1/4). E[Y | X] is 1/2, 1, 1/2 and the "
        "residual variance is what is left")

    mse_const = best_predictor_mse(joint, lambda x: mean_ref)
    assert mse_const == Fraction(2, 9), (
        f"the best constant predictor has MSE {mse_const}, expected Var(Y) = "
        "2/9. The best constant is the mean")
    assert mse_eyx < mse_const, (
        f"E[Y | X] scores {mse_eyx} and the best constant scores {mse_const}: "
        "on a joint where Y depends on X, conditioning must be STRICTLY better "
        "than any constant. This is the acceptance criterion")

    rng = random.Random(20260603)
    random_lookup = {x: Fraction(rng.randint(-6, 6), rng.randint(1, 4))
                     for x in (0, 1, 2)}
    challengers = {
        "best constant": lambda x: mean_ref,
        "offset linear": lambda x: Fraction(1, 4) * x + Fraction(1, 2),
        "quadratic fit": lambda x: Fraction(-1, 2) * x * x + x + Fraction(1, 2),
        "seeded random": lambda x: random_lookup[x],
    }
    for name, predictor in challengers.items():
        mse = best_predictor_mse(joint, predictor)
        assert mse_eyx <= mse, (
            f"the {name} predictor scores {mse}, BELOW E[Y | X]'s {mse_eyx}: "
            "E[Y | X] must minimise E[(Y - g(X))^2] over every function g of X. "
            "If a predictor beats it, conditional_expectation is not returning "
            "the conditional mean")
    assert len(challengers) >= 4, (
        "this check must compare E[Y | X] against more than a single constant: "
        f"only {len(challengers)} challenger(s) are tested. A check against one "
        "constant lets a bad predictor pass. The classic weak step names only "
        "the constant, which is the bug planted for this step")


# ---------------------------------------------------------------------------
# Step 5: the limit case -- the naive spread ignores Var(E[Y | X])
# ---------------------------------------------------------------------------

def check_hierarchical_limit_case() -> None:
    from cond import hierarchical_moments

    p, n, q0, q1 = Fraction(1, 3), 6, Fraction(1, 5), Fraction(3, 5)
    total, within, between = hierarchical_moments(p, n, q0, q1)

    exp_within = p * n * q1 * (1 - q1) + (1 - p) * n * q0 * (1 - q0)
    exp_between = p * (1 - p) * (n * (q1 - q0)) ** 2
    assert within == exp_within, (
        f"E[Var(Y | X)] = {within}, expected {exp_within}: for Binomial(n, q) "
        "the conditional variance is n q (1 - q), mixed over the two groups")
    assert between == exp_between, (
        f"Var(E[Y | X]) = {between}, expected {exp_between} = p(1-p)(n q1 - "
        "n q0)^2. Setting this to zero is exactly the bug this step plants")
    assert total == within + between, (
        f"the total variance is {total} but E[Var(Y|X)] + Var(E[Y|X]) = "
        f"{within + between}. The naive reading uses only the within-group term "
        f"{within} and understates the spread")
    assert between > 0 and total > within, (
        f"the hierarchy must actually spread the group means: between = "
        f"{between}, total = {total}, within-only = {within}. With q1 != q0 the "
        "between-group variance is positive, so the naive within-only variance "
        "must be too small")

    # Simulation: the observed variance matches the FULL total, not the within term.
    rng = random.Random(20260604)
    draws = _sample_hierarchical(float(p), n, float(q0), float(q1), 120000, rng)
    empirical_var = _variance(draws)
    assert abs(empirical_var - float(total)) < 0.05, (
        f"sample Var(Y) = {empirical_var:.4f}, not close to the closed-form "
        f"total {float(total):.4f}: the between-group variance is part of the "
        "truth, not an artefact")
    assert empirical_var > float(within) + 0.5, (
        f"sample Var(Y) = {empirical_var:.4f} is barely above the within-group "
        f"term {float(within):.4f}: if the two nearly coincide the hierarchy does "
        "not exercise the limit case")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("cond.py", "conditional expectation and variance (exact)", check_conditional_moments),
    ("cond.py", "Adam's law: E[Y] = sum_x P(X=x) E[Y|X=x]", check_adams_law),
    ("cond.py", "Eve's law: Var(Y) = E[Var(Y|X)] + Var(E[Y|X])", check_eves_law),
    ("cond.py", "E[Y|X] beats every tested predictor (accept)", check_best_predictor),
    ("cond.py", "hierarchical limit case (naive spread is too small)", check_hierarchical_limit_case),
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
    print(f"\n{BOLD}Conditional Expectation From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<8} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<8} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<8} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built conditional expectation from scratch.{RESET}")
        print(f"  {GREY}Run solutions/cond.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
