"""
Progress checker for the joint-distributions templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

Every reference value is recomputed here, independently of the learner's code: the
marginals and conditionals by summing the joint directly, the covariance and
correlation from the definition, the multinomial pmf from its own factorial ratio, the
bivariate normal density from its own quadratic form, and the sample covariance from
the 1/(n-1) definition. The node's acceptance rule -- sample covariance matrices
converge to the analytic covariance -- is enforced by comparing a seeded sample to the
analytic matrix, and the limit case is checked in the direction that matters:
Cov(X, Y) = 0 with Y = X^2, decided dependent from the conditionals, never from the
covariance.
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

TWO_PI = 2.0 * math.pi


# ---------------------------------------------------------------------------
# The checker's own arithmetic (never the learner's)
# ---------------------------------------------------------------------------

def _reference_bvn_pdf(x, y, mu, cov):
    """Independent bivariate normal density, written from its quadratic form."""
    vx, cxy, vy = cov[0][0], cov[0][1], cov[1][1]
    det = vx * vy - cxy * cxy
    dx, dy = x - mu[0], y - mu[1]
    quad = (vy * dx * dx - 2.0 * cxy * dx * dy + vx * dy * dy) / det
    return math.exp(-0.5 * quad) / (TWO_PI * math.sqrt(det))


# ---------------------------------------------------------------------------
# Step 1: marginals and conditionals agree with the joint and sum to 1
# ---------------------------------------------------------------------------

def check_joint_marginal_conditional() -> None:
    from joint import conditional, marginal

    joint = {(0, 0): 0.1, (0, 1): 0.2, (1, 0): 0.3, (1, 1): 0.4}
    ref_x = {0: 0.3, 1: 0.7}
    ref_y = {0: 0.4, 1: 0.6}

    got_x = marginal(joint, 0)
    got_y = marginal(joint, 1)
    assert set(got_x) == set(ref_x), (
        f"marginal(joint, 0) keys are {sorted(got_x)}, expected the X values "
        f"{sorted(ref_x)}. axis = 0 keeps X and sums out Y; swapping the axes "
        "produces the Y marginal here only because the joint is symmetric")
    assert set(got_y) == set(ref_y), (
        f"marginal(joint, 1) keys are {sorted(got_y)}, expected the Y values "
        f"{sorted(ref_y)}")
    for key, want in ref_x.items():
        assert abs(got_x[key] - want) < 1e-12, (
            f"marginal X at {key} = {got_x[key]}, expected {want}: sum the joint "
            "over the OTHER coordinate, not along the kept one")
    for key, want in ref_y.items():
        assert abs(got_y[key] - want) < 1e-12, (
            f"marginal Y at {key} = {got_y[key]}, expected {want}")
    assert abs(sum(got_x.values()) - 1.0) < 1e-12, "a marginal pmf must sum to 1"
    assert abs(sum(got_y.values()) - 1.0) < 1e-12, "a marginal pmf must sum to 1"

    cond0 = conditional(joint, 0)
    assert abs(cond0[0] - 1.0 / 3.0) < 1e-12 and abs(cond0[1] - 2.0 / 3.0) < 1e-12, (
        f"P(Y | X = 0) = {cond0}, expected {{0: 1/3, 1: 2/3}}. Divide the row "
        "P(X = 0, Y = y) by P(X = 0) = 0.3, not by 1 and not by the number of "
        "outcomes: the wrong denominator is exactly the bug this step catches")
    assert abs(sum(cond0.values()) - 1.0) < 1e-12, (
        "a conditional pmf must sum to 1; if it does not, the denominator was not "
        "the marginal of the conditioning event")

    # The joint must be reconstructible from a marginal and a conditional.
    for (x, y), p in joint.items():
        rebuilt = got_x[x] * conditional(joint, x)[y]
        assert abs(rebuilt - p) < 1e-12, (
            f"P(X={x}) P(Y={y}|X={x}) = {rebuilt}, but the joint says {p}: "
            "marginal x conditional must return the joint")

    # The same three facts for the list-of-lists form.
    matrix = [[0.1, 0.2], [0.3, 0.4]]
    mx = marginal(matrix, 0)
    my = marginal(matrix, 1)
    assert abs(mx[0] - 0.3) < 1e-12 and abs(mx[1] - 0.7) < 1e-12, (
        f"marginal(matrix, 0) = {mx}, expected [0.3, 0.7]: row sums")
    assert abs(my[0] - 0.4) < 1e-12 and abs(my[1] - 0.6) < 1e-12, (
        f"marginal(matrix, 1) = {my}, expected [0.4, 0.6]: column sums")
    c0 = conditional(matrix, 0)
    assert abs(c0[0] - 1.0 / 3.0) < 1e-12 and abs(c0[1] - 2.0 / 3.0) < 1e-12, (
        f"conditional(matrix, 0) = {c0}, expected [1/3, 2/3]: the first row "
        "normalised by its sum")


# ---------------------------------------------------------------------------
# Step 2: covariance and correlation, with the correlation normalised
# ---------------------------------------------------------------------------

def check_covariance_correlation() -> None:
    from joint import correlation, covariance

    xs = [1.0, 2.0, 3.0]
    doubled = [2.0, 4.0, 6.0]
    assert abs(covariance(xs, doubled) - 4.0 / 3.0) < 1e-12, (
        f"covariance = {covariance(xs, doubled)}, expected 4/3. Cov is "
        "(1/n) sum (x - mean_x)(y - mean_y), with the population 1/n here")
    assert abs(covariance(xs, xs) - 2.0 / 3.0) < 1e-12, (
        "Cov(X, X) is the population variance, (1/n) sum (x - mean)^2")
    assert abs(covariance(xs, doubled) - covariance(doubled, xs)) < 1e-15, (
        "covariance is symmetric in its two arguments")

    assert abs(correlation(xs, doubled) - 1.0) < 1e-12, (
        f"correlation = {correlation(xs, doubled)}, expected 1: y = 2x is a "
        "perfect positive line. Dividing the covariance by sd(X) sd(Y) is what "
        "makes it 1; returning the raw covariance does not")
    assert abs(correlation(xs, [6.0, 4.0, 2.0]) + 1.0) < 1e-12, (
        "a perfect negative line has correlation -1")
    assert abs(correlation([3.0 * v + 10.0 for v in xs],
                           [-2.0 * w + 5.0 for w in doubled]) + 1.0) < 1e-12, (
        "correlation is invariant under positive affine changes of either "
        "variable and flips sign under a negative one: corr(3x, -2y) = -1")

    orthogonal = [1.0, -2.0, 1.0]
    assert abs(covariance(xs, orthogonal)) < 1e-12, (
        "this hand case is constructed with zero covariance; if it is not zero, "
        "the means are being computed with the wrong denominator")
    assert abs(correlation(xs, orthogonal)) < 1e-12, (
        "zero covariance with positive variances means zero correlation")

    vx = covariance(xs, xs)
    vy = covariance(doubled, doubled)
    assert abs(correlation(xs, doubled) - covariance(xs, doubled) / math.sqrt(vx * vy)) < 1e-12, (
        "correlation is Cov / sqrt(Var X Var Y); any other normalisation fails "
        "the perfect-line case above")


# ---------------------------------------------------------------------------
# Step 3: the multinomial pmf sums to 1 and its sampler matches it
# ---------------------------------------------------------------------------

def check_multinomial() -> None:
    from collections import Counter

    from joint import multinomial_pmf, multinomial_samples

    counts = [2, 1, 1]
    probs = [0.5, 0.25, 0.25]
    assert abs(multinomial_pmf(counts, probs) - 0.1875) < 1e-12, (
        f"multinomial_pmf({counts}, {probs}) = {multinomial_pmf(counts, probs)}, "
        "expected 0.1875 = 4!/(2!1!1!) * 0.5^2 * 0.25 * 0.25. The coefficient is "
        "n! / prod c_i!, not prod c_i! / n! (and not the binomial coefficient)")

    total = 0.0
    for a in range(5):
        for b in range(5 - a):
            c = 4 - a - b
            total += multinomial_pmf([a, b, c], probs)
    assert abs(total - 1.0) < 1e-12, (
        f"the multinomial pmf over every count vector with n = 4 sums to {total}, "
        "not 1: it must place all the mass of the four draws somewhere")

    rng = random.Random(1101)
    draws = multinomial_samples(2000, 10, [0.2, 0.3, 0.5], rng)
    assert len(draws) == 2000, "multinomial_samples must return exactly n vectors"
    for row in draws:
        assert sum(row) == 10, (
            f"a sampled count vector {row} does not sum to the number of trials: "
            "each of the trials must fall in exactly one category")
    means = [sum(row[k] for row in draws) / len(draws) for k in range(3)]
    for k, expected in enumerate([2.0, 3.0, 5.0]):
        assert abs(means[k] - expected) < 0.2, (
            f"mean count in category {k} is {means[k]:.3f}, expected about "
            f"{expected} = trials * p. The cumulative walk must use the "
            "probabilities in order, not their complement")

    rng = random.Random(1102)
    draws = multinomial_samples(20000, 2, [0.2, 0.3, 0.5], rng)
    empirical = Counter(tuple(row) for row in draws)
    for a in range(3):
        for b in range(3 - a):
            c = 2 - a - b
            expected = multinomial_pmf([a, b, c], [0.2, 0.3, 0.5])
            got = empirical[(a, b, c)] / len(draws)
            assert abs(got - expected) < 0.02, (
                f"P(counts = {(a, b, c)}) is {got:.4f} in the sample but the pmf "
                f"says {expected:.4f}: the sampler and the pmf describe different "
                "multinomial distributions")


# ---------------------------------------------------------------------------
# Step 4: the bivariate normal density, and sample covariance convergence
# ---------------------------------------------------------------------------

def check_bivariate_normal() -> None:
    from joint import (bivariate_normal_pdf, sample_bivariate_normal,
                       sample_covariance)

    mu = (0.5, -0.5)
    cov = [[1.0, 0.5], [0.5, 2.0]]
    det = cov[0][0] * cov[1][1] - cov[0][1] ** 2

    at_mean = bivariate_normal_pdf(mu[0], mu[1], mu, cov)
    assert abs(at_mean - 1.0 / (TWO_PI * math.sqrt(det))) < 1e-12, (
        f"the density at its mean is {at_mean}, expected "
        f"1/(2 pi sqrt(det)) = {1.0 / (TWO_PI * math.sqrt(det))}: the "
        "normalising constant carries sqrt(det), the determinant of the "
        "covariance")

    for x, y in ((0.0, 0.0), (1.0, 1.0), (-1.0, 2.0), (2.0, -2.0), (0.7, 0.1)):
        got = bivariate_normal_pdf(x, y, mu, cov)
        ref = _reference_bvn_pdf(x, y, mu, cov)
        assert abs(got - ref) < 1e-12, (
            f"pdf({x}, {y}) = {got}, the quadratic form gives {ref}. The "
            "off-diagonal is coupled through the cross term -2 cxy dx dy: "
            "dropping it gives a density that is still normal and still "
            "integrates to 1, but its E[XY] is wrong")

    # Integrate the learner's density on a grid: total mass 1 and, crucially,
    # the cross moment E[XY] - mu_x mu_y equals the analytic covariance.
    lo_x, hi_x, lo_y, hi_y, steps = -8.0, 8.0, -10.0, 10.0, 200
    step_x = (hi_x - lo_x) / steps
    step_y = (hi_y - lo_y) / steps
    mass = 0.0
    cross = 0.0
    for i in range(steps):
        x = lo_x + (i + 0.5) * step_x
        for j in range(steps):
            y = lo_y + (j + 0.5) * step_y
            p = bivariate_normal_pdf(x, y, mu, cov)
            mass += p
            cross += x * y * p
    mass *= step_x * step_y
    cross *= step_x * step_y
    assert abs(mass - 1.0) < 1e-3, (
        f"the density integrates to {mass:.5f}, not 1. If it is far from 1 the "
        "normalising constant is wrong; this also catches a covariance whose "
        "determinant is not the one used in the density")
    apparent_cov = cross - mu[0] * mu[1]
    assert abs(apparent_cov - cov[0][1]) < 0.01, (
        f"the grid gives E[XY] - mu_x mu_y = {apparent_cov:.4f}, but the analytic "
        f"covariance is {cov[0][1]}. This is the cross-term test: a density with "
        "no -2 cxy dx dy term integrates to 1 and still fails here")

    # The unbiased sample covariance is pinned exactly at small n, where 1/n and
    # 1/(n-1) differ by a factor n/(n-1) = 3/2.
    points = [(0.0, 0.0), (1.0, 2.0), (2.0, 4.0)]
    sc = sample_covariance(points)
    assert abs(sc[0][0] - 1.0) < 1e-12, (
        f"sample var_x = {sc[0][0]}, expected 1: the denominator is 1/(n-1) = "
        "1/2 here, not 1/n = 1/3 and not 1")
    assert abs(sc[1][1] - 4.0) < 1e-12, (
        f"sample var_y = {sc[1][1]}, expected 4")
    assert abs(sc[0][1] - 2.0) < 1e-12, (
        f"sample cov_xy = {sc[0][1]}, expected 2. The 1/n convention gives 4/3, "
        "which the node's analytic comparison would forgive at large n, so the "
        "checker pins this small case")

    # Acceptance rule: seeded sample covariance converges to the analytic matrix.
    rng = random.Random(4242)
    samples = sample_bivariate_normal(mu, cov, 200000, rng)
    assert len(samples) == 200000, "sample_bivariate_normal must return n pairs"
    assert all(len(pair) == 2 for pair in samples), "each sample is an (x, y) pair"
    estimate = sample_covariance(samples)
    for row in range(2):
        for col in range(2):
            assert abs(estimate[row][col] - cov[row][col]) < 0.05, (
                f"the sample covariance entry [{row}][{col}] = "
                f"{estimate[row][col]:.4f} did not converge to the analytic "
                f"{cov[row][col]}: the Cholesky factor L must satisfy L L^T = "
                "cov, so a wrong factor shows up as a wrong covariance")


# ---------------------------------------------------------------------------
# Step 5: the limit case -- uncorrelated but dependent
# ---------------------------------------------------------------------------

def check_uncorrelated_but_dependent() -> None:
    from joint import conditional, correlation, covariance, marginal

    # Deterministic, not random: X is symmetric on {-2, -1, 1, 2} with equal
    # probability and Y = X^2. E[XY] = E[X^3] = 0 by symmetry, so Cov = 0.
    joint = {(-2.0, 4.0): 0.25, (-1.0, 1.0): 0.25,
             (1.0, 1.0): 0.25, (2.0, 4.0): 0.25}
    xs = [key[0] for key in joint]
    ys = [key[1] for key in joint]

    cov = covariance(xs, ys)
    assert abs(cov) < 1e-12, (
        f"Cov(X, X^2) = {cov}, expected exactly 0: the symmetric X makes E[X^3] "
        "= 0, so the covariance cancels term by term")
    assert abs(correlation(xs, ys)) < 1e-12, (
        "the correlation is the covariance over positive standard deviations, so "
        "it is zero too")

    marginal_y = marginal(joint, 1)
    assert abs(marginal_y[4.0] - 0.5) < 1e-12 and abs(marginal_y[1.0] - 0.5) < 1e-12, (
        f"the marginal of Y = X^2 is {marginal_y}, expected 1/2 on each of 1 and "
        "4: its spread is what makes Y random")

    for x in (-2.0, -1.0, 1.0, 2.0):
        cond = conditional(joint, x)
        assert len(cond) == 1 and abs(max(cond.values()) - 1.0) < 1e-12, (
            f"P(Y | X = {x}) = {cond}, expected a point mass. Given X, Y = X^2 is "
            "determined: that is the dependence")

    # Dependence is a property of the conditional, not of the covariance.
    independent = all(conditional(joint, x) == marginal_y for x in xs)
    assert independent is False, (
        "X and Y = X^2 have Cov(X, Y) = 0, yet P(Y | X = x) is a point mass for "
        "every x while marginal(Y) spreads 1/2-1/2 over {1, 4}. This is the "
        "node's limit case: inferring independence from zero covariance is the "
        "classic error. Correlation measures only LINEAR association; dependence "
        "is read from the conditional. (If this assert fires, the check itself "
        "started inferring independence from the covariance)")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("joint.py", "joint, marginal and conditional pmfs", check_joint_marginal_conditional),
    ("joint.py", "covariance and correlation", check_covariance_correlation),
    ("joint.py", "multinomial pmf and sampler", check_multinomial),
    ("joint.py", "bivariate normal and sample-covariance convergence", check_bivariate_normal),
    ("joint.py", "uncorrelated but dependent (the limit case)", check_uncorrelated_but_dependent),
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
    print(f"\n{BOLD}Joint Distributions From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built joint distributions from scratch.{RESET}")
        print(f"  {GREY}Run solutions/joint.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
