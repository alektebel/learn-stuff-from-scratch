"""
Progress checker for the random-variables templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

Every reference mean, variance, PMF and CDF is computed here, independently, from
math.comb and fractions.Fraction (Poisson from math.exp, since e^-lambda is irrational).
The acceptance rule from the skill tree is enforced literally: the exact mean must sit
within four standard errors of a 10**5-trial simulation, and the variance within four
standard errors of the sample variance, whose standard error is estimated from the
sample fourth central moment.
"""

import math
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

TRIALS = 100_000


# ---------------------------------------------------------------------------
# The checker's own arithmetic (never the learner's)
# ---------------------------------------------------------------------------

def _binom_pmf(n, p, k):
    if not 0 <= k <= n:
        return Fraction(0)
    p = Fraction(p)
    return Fraction(math.comb(n, k)) * p ** k * (1 - p) ** (n - k)


def _pois_pmf(lam, k):
    if k < 0:
        return 0.0
    lam = float(lam)
    term = math.exp(-lam)
    for i in range(1, k + 1):
        term *= lam / i
    return term


def _tv_distance(n, p):
    """Independent total-variation distance between Binomial(n,p) and Poisson(np)."""
    p = float(p)
    lam = n * p
    total = 0.0
    for k in range(n + 1):
        total += abs(float(_binom_pmf(n, p, k)) - _pois_pmf(lam, k))
    k = n + 1
    while True:
        term = _pois_pmf(lam, k)
        total += term
        if term < 1e-18 or k > n + 1000:
            break
        k += 1
    return 0.5 * total


def _sample_mean_var(draws):
    n = len(draws)
    mean = Fraction(sum(draws), n)
    second = Fraction(sum(x * x for x in draws), n)
    return mean, second - mean ** 2


def _check_mean(label, exact_mean, exact_var, draws):
    mean, _ = _sample_mean_var(draws)
    bound = 4.0 * math.sqrt(float(exact_var) / len(draws))
    gap = abs(float(exact_mean) - float(mean))
    assert gap <= bound + 1e-9, (
        f"{label}: exact mean {float(exact_mean):.6f} vs simulated {float(mean):.6f} "
        f"(gap {gap:.6f} > 4-SE {bound:.6f}). The sampler and the PMF disagree about "
        "the support or the parameter, not just about noise.")


def _check_variance(label, exact_var, draws):
    n = len(draws)
    mean = sum(draws) / n
    s2 = sum((x - mean) ** 2 for x in draws) / n
    m4 = sum((x - mean) ** 4 for x in draws) / n
    # Asymptotic standard error of the sample variance: Var((X-mean)^2)/n.
    var_se = math.sqrt(max(m4 - s2 * s2, 0.0) / n)
    bound = 4.0 * var_se + 1e-6
    gap = abs(float(exact_var) - s2)
    assert gap <= bound, (
        f"{label}: exact variance {float(exact_var):.6f} vs simulated {s2:.6f} "
        f"(gap {gap:.6f} > bound {bound:.6f}). Check the variance formula E[X^2] - "
        "(E[X])^2 and the support the sampler draws from.")


# ---------------------------------------------------------------------------
# Step 1: Bernoulli
# ---------------------------------------------------------------------------

def check_bernoulli() -> None:
    from random_variables import (bernoulli_pmf, bernoulli_cdf, bernoulli_mean,
                                  bernoulli_variance, simulate_bernoulli)

    half, quarter = Fraction(1, 2), Fraction(1, 4)
    assert bernoulli_pmf(half, 0) == Fraction(1, 2), (
        f"bernoulli_pmf(1/2, 0) = {bernoulli_pmf(half, 0)}, expected 1/2: the mass at "
        "0 is 1 - p")
    assert bernoulli_pmf(half, 1) == Fraction(1, 2), (
        f"bernoulli_pmf(1/2, 1) = {bernoulli_pmf(half, 1)}, expected 1/2: the mass at 1 is p")
    assert bernoulli_pmf(half, 2) == 0, "Bernoulli support is {{0, 1}}; pmf(2) must be 0"
    assert bernoulli_pmf(quarter, 0) == Fraction(3, 4)
    assert bernoulli_cdf(half, -1) == 0 and bernoulli_cdf(half, 0) == Fraction(1, 2), (
        "bernoulli_cdf must be 0 below the support and 1 - p at k = 0")
    assert bernoulli_cdf(half, 1) == 1, "the CDF reaches 1 at k = 1"

    assert bernoulli_mean(quarter) == Fraction(1, 4), "E[X] = p"
    assert bernoulli_variance(half) == Fraction(1, 4) and \
        bernoulli_variance(quarter) == Fraction(3, 16), (
            f"Var(X) must be p(1-p) (got {bernoulli_variance(half)} for p = 1/2); "
            "E[X^2] - (E[X])^2 with the square misplaced collapses to 0")

    draws = simulate_bernoulli(half, TRIALS, seed=11)
    _check_mean("Bernoulli(1/2)", bernoulli_mean(half), bernoulli_variance(half), draws)
    _check_variance("Bernoulli(1/2)", bernoulli_variance(half), draws)


# ---------------------------------------------------------------------------
# Step 2: Binomial
# ---------------------------------------------------------------------------

def check_binomial() -> None:
    from random_variables import (binomial_pmf, binomial_cdf, binomial_mean,
                                  binomial_variance, simulate_binomial)

    rng = random.Random(21)
    for _ in range(120):
        n = rng.randint(0, 30)
        p = Fraction(rng.randint(1, 9), 10)
        for k in range(-1, n + 2):
            got = binomial_pmf(n, p, k)
            expected = _binom_pmf(n, p, k)
            assert got == expected, (
                f"binomial_pmf({n}, {p}, {k}) = {got}, expected {expected}. The PMF is "
                "C(n,k) p^k (1-p)^(n-k), zero outside 0 <= k <= n.")
        probe = rng.randint(-1, n + 1)
        expected_cdf = sum((_binom_pmf(n, p, j) for j in range(0, max(probe, -1) + 1)),
                           Fraction(0))
        assert binomial_cdf(n, p, probe) == expected_cdf, (
            f"binomial_cdf({n}, {p}, {probe}) must sum the PMF over 0..k, got "
            f"{binomial_cdf(n, p, probe)}, expected {expected_cdf}")

    p = Fraction(1, 2)
    assert binomial_mean(20, p) == 10, "E[X] = n p"
    assert binomial_variance(20, p) == 5, (
        f"Var(X) must be n p (1-p) = 5, got {binomial_variance(20, p)}")

    draws = simulate_binomial(20, p, TRIALS, seed=22)
    _check_mean("Binomial(20,1/2)", binomial_mean(20, p), binomial_variance(20, p), draws)
    _check_variance("Binomial(20,1/2)", binomial_variance(20, p), draws)


# ---------------------------------------------------------------------------
# Step 3: Geometric -- the support starts at 1
# ---------------------------------------------------------------------------

def check_geometric() -> None:
    from random_variables import (geometric_pmf, geometric_cdf, geometric_mean,
                                  geometric_variance, simulate_geometric)

    p = Fraction(1, 4)
    q = 1 - p
    assert geometric_pmf(p, 0) == 0, (
        "geometric_pmf(p, 0) must be 0: X counts trials to the first success, so its "
        "support starts at 1, not 0")
    assert geometric_pmf(p, 1) == p, (
        f"geometric_pmf(1/4, 1) = {geometric_pmf(p, 1)}, expected 1/4 = p. This is the "
        "support off-by-one: the failures-before-success convention uses (1-p)^k p and "
        "starts at 0")
    assert geometric_pmf(p, 2) == q * p and geometric_pmf(p, 3) == q ** 2 * p, (
        "geometric_pmf(p, k) = (1-p)^(k-1) p for k >= 1")
    assert geometric_cdf(p, 0) == 0, "the CDF is 0 at k = 0 under the trials convention"
    assert geometric_cdf(p, 2) == 1 - q ** 2, "geometric_cdf(p, k) = 1 - (1-p)^k"
    tail = sum((geometric_pmf(p, k) for k in range(1, 2001)), Fraction(0))
    assert abs(tail - 1) < Fraction(1, 10 ** 9), (
        "the Geometric PMF must sum to 1 over its support: a shifted support leaves the "
        "total at 1 - p or multiplies it by (1-p)")

    assert geometric_mean(p) == 4, (
        f"geometric_mean(1/4) = {geometric_mean(p)}, expected 4 = 1/p. A support starting "
        "at 0 would give (1-p)/p = 3, wrong by one.")
    assert geometric_variance(p) == Fraction(3, 4) / Fraction(1, 16), (
        f"geometric_variance(1/4) = {geometric_variance(p)}, expected (1-p)/p^2 = 12")

    draws = simulate_geometric(p, TRIALS, seed=33)
    _check_mean("Geometric(1/4)", geometric_mean(p), geometric_variance(p), draws)
    _check_variance("Geometric(1/4)", geometric_variance(p), draws)


# ---------------------------------------------------------------------------
# Step 4: Negative Binomial -- trials to collect r successes
# ---------------------------------------------------------------------------

def check_negative_binomial() -> None:
    from random_variables import (negative_binomial_pmf, negative_binomial_cdf,
                                  negative_binomial_mean, negative_binomial_variance,
                                  simulate_negative_binomial)

    p = Fraction(1, 3)
    q = 1 - p
    assert negative_binomial_pmf(3, p, 2) == 0, "support is k >= r"
    assert negative_binomial_pmf(3, p, 3) == p ** 3, (
        f"negative_binomial_pmf(3, 1/3, 3) = {negative_binomial_pmf(3, p, 3)}, expected "
        "p^3: the first k = r trials must all be successes")
    assert negative_binomial_pmf(3, p, 4) == Fraction(3, 1) * p ** 3 * q, (
        "negative_binomial_pmf(r,p,k) = C(k-1, r-1) p^r (1-p)^(k-r): the last trial is a "
        "success and the previous k-1 trials hold r-1 successes")
    expected_cdf = sum((negative_binomial_pmf(3, p, k) for k in range(3, 8)), Fraction(0))
    assert negative_binomial_cdf(3, p, 7) == expected_cdf, (
        "negative_binomial_cdf must sum the PMF from k = r, not from 0")

    assert negative_binomial_mean(4, p) == 12, "E[X] = r/p"
    assert negative_binomial_variance(4, p) == Fraction(24), (
        f"Var(X) must be r(1-p)/p^2 = 24, got {negative_binomial_variance(4, p)}")

    draws = simulate_negative_binomial(4, p, TRIALS, seed=44)
    _check_mean("NegBinom(4,1/3)", negative_binomial_mean(4, p),
                negative_binomial_variance(4, p), draws)
    _check_variance("NegBinom(4,1/3)", negative_binomial_variance(4, p), draws)


# ---------------------------------------------------------------------------
# Step 5: Poisson
# ---------------------------------------------------------------------------

def check_poisson() -> None:
    from random_variables import (poisson_pmf, poisson_cdf, poisson_mean,
                                  poisson_variance, simulate_poisson)

    assert abs(poisson_pmf(2, 0) - math.exp(-2)) < 1e-15, (
        "poisson_pmf(lambda, 0) = e^-lambda")
    for lam in (Fraction(1, 2), Fraction(3), Fraction(7)):
        for k in range(0, 12):
            got = poisson_pmf(lam, k)
            expected = _pois_pmf(lam, k)
            assert abs(got - expected) < 1e-12, (
                f"poisson_pmf({lam}, {k}) = {got}, expected {expected}: "
                "e^-lambda lambda^k / k!")
        probe = 5
        expected_cdf = sum((_pois_pmf(lam, j) for j in range(probe + 1)), 0.0)
        assert abs(poisson_cdf(lam, probe) - expected_cdf) < 1e-12, (
            "poisson_cdf must sum the PMF over 0..k")
    assert poisson_pmf(3, -1) == 0, "the Poisson support is k >= 0"
    assert poisson_mean(3) == 3 and poisson_variance(3) == 3, (
        "for a Poisson both the mean and the variance equal lambda")

    draws = simulate_poisson(3, TRIALS, seed=55)
    _check_mean("Poisson(3)", poisson_mean(3), poisson_variance(3), draws)
    _check_variance("Poisson(3)", poisson_variance(3), draws)


# ---------------------------------------------------------------------------
# Step 6: linearity of expectation with dependent indicators
# ---------------------------------------------------------------------------

def _enumerate_fixed_points(n):
    """Exact mean and variance of # fixed points, by listing all n! permutations."""
    from itertools import permutations
    counts = [sum(1 for i in range(n) if perm[i] == i)
              for perm in permutations(range(n))]
    total = len(counts)
    mean = Fraction(sum(counts), total)
    second = Fraction(sum(c * c for c in counts), total)
    return mean, second - mean ** 2


def check_linearity_of_expectation() -> None:
    from random_variables import expected_fixed_points, simulate_fixed_points

    assert expected_fixed_points(0) == 0, "a permutation of nothing has no fixed points"
    for n in (1, 2, 5, 10, 100):
        assert expected_fixed_points(n) == 1, (
            f"expected_fixed_points({n}) = {expected_fixed_points(n)}, expected 1. By "
            "linearity E[#fixed] = sum_i P(position i fixed) = n * (1/n). Independence "
            "is not required and must not be assumed -- it is not true here.")

    # The indicators really are dependent: two positions cannot both be fixed
    # with the product probability, and n-1 fixed points is impossible.
    n = 5
    joint = Fraction(1, n * (n - 1))
    product = Fraction(1, n) * Fraction(1, n)
    assert joint != product, (
        "the checker expects P(I_1 I_2) != P(I_1)P(I_2); if these matched, this is not "
        "the dependent-indicator limit case")

    for n in (2, 5, 6):
        exact_mean, exact_var = _enumerate_fixed_points(n)
        assert expected_fixed_points(n) == exact_mean, (
            f"expected_fixed_points({n}) disagrees with brute-force enumeration over all "
            f"{math.factorial(n)} permutations ({exact_mean})")
        assert exact_var > 0

    for n in (2, 5):
        draws = simulate_fixed_points(n, TRIALS, seed=66)
        _check_mean(f"fixed points, n={n}", expected_fixed_points(n),
                    Fraction(1), draws)


# ---------------------------------------------------------------------------
# Step 7: the variance grows the covariance terms (the limit case)
# ---------------------------------------------------------------------------

def check_dependent_variance() -> None:
    from random_variables import fixed_points_variance, simulate_fixed_points

    assert fixed_points_variance(0) == 0 and fixed_points_variance(1) == 0, (
        "0 or 1 positions have no fixed-point variance")
    for n in (2, 3, 5, 50):
        assert fixed_points_variance(n) == 1, (
            f"fixed_points_variance({n}) = {fixed_points_variance(n)}, expected 1. "
            "Var(sum I_i) is not sum Var(I_i): the covariances contribute. The "
            "independence-only value is (n-1)/n, e.g. 4/5 at n = 5.")
    assert fixed_points_variance(5) != Fraction(4, 5), (
        "the checker requires the dependent answer 1, distinct from the "
        "independence-only (n-1)/n = 4/5")

    for n in (2, 5, 6):
        exact_mean, exact_var = _enumerate_fixed_points(n)
        assert fixed_points_variance(n) == exact_var, (
            f"fixed_points_variance({n}) = {fixed_points_variance(n)} disagrees with "
            f"brute-force enumeration ({exact_var})")

    for n in (2, 5, 50):
        draws = simulate_fixed_points(n, TRIALS, seed=77)
        _check_variance(f"fixed-point variance, n={n}",
                        fixed_points_variance(n), draws)


# ---------------------------------------------------------------------------
# Step 8: the Poisson approximation error shrinks like p
# ---------------------------------------------------------------------------

def check_poisson_approximation() -> None:
    from random_variables import binomial_poisson_tv_distance

    for n, p in ((10, Fraction(1, 10)), (20, Fraction(1, 4)),
                 (100, Fraction(1, 100))):
        got = binomial_poisson_tv_distance(n, p)
        expected = _tv_distance(n, p)
        assert abs(got - expected) < 1e-9, (
            f"binomial_poisson_tv_distance({n}, {p}) = {got}, expected {expected}. It is "
            "0.5 sum_k |Binomial(n,p)(k) - Poisson(np)(k)| over the WHOLE line, with "
            "lambda = n p in the Poisson.")

    # Hold lambda = n p = 1 fixed and let n grow: by Le Cam the distance is
    # O(lambda p), so it must fall by roughly a factor of 10 per factor of 10 in n.
    errors = [binomial_poisson_tv_distance(n, Fraction(1, n))
              for n in (10, 100, 1000)]
    assert errors[0] > errors[1] > errors[2] > 0, (
        f"the Poisson approximation must improve as n grows with n p = 1 fixed; got "
        f"{errors}. Comparing at the wrong n, or forgetting lambda = n p, breaks this.")
    assert errors[0] > 3 * errors[1] and errors[1] > 3 * errors[2], (
        f"the error must fall by roughly a factor of 10 per factor of 10 in n (Le Cam: "
        f"O(n p^2)); got ratios {errors[0] / errors[1]:.2f}, {errors[1] / errors[2]:.2f}")

    scaled = [error / (1.0 / n) for error, n in zip(errors, (10, 100, 1000))]
    assert max(scaled) / min(scaled) < Fraction(6, 5), (
        f"error / p should be roughly constant (the error is proportional to p); got "
        f"{[round(s, 5) for s in scaled]}")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("random_variables.py", "Bernoulli PMF/CDF, mean, variance", check_bernoulli),
    ("random_variables.py", "Binomial PMF/CDF, mean, variance", check_binomial),
    ("random_variables.py", "Geometric support starts at 1", check_geometric),
    ("random_variables.py", "Negative Binomial PMF/CDF", check_negative_binomial),
    ("random_variables.py", "Poisson PMF/CDF, mean, variance", check_poisson),
    ("random_variables.py", "linearity with dependent indicators", check_linearity_of_expectation),
    ("random_variables.py", "variance under dependence (the limit case)", check_dependent_variance),
    ("random_variables.py", "Poisson approximation error shrinks", check_poisson_approximation),
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
    print(f"\n{BOLD}Random Variables From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<19} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<19} {title}")
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
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<19} {title}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built random variables from scratch.{RESET}")
        print(f"  {GREY}Run solutions/random_variables.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
