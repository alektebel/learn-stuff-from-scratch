"""
Progress checker for the limits-and-inequalities templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

Every reference value is recomputed here, independently of the learner's code: the
transformed density from its analytic closed form, the dice convolution from the hand
count ``(k-1)/36`` as exact ``Fraction``s, the binomial tail from its own factorial
ratio as exact ``Fraction``s, and the Cauchy and exponential spreads from the checker's
own sampler. The node's acceptance rule -- every bound at or above the exact tail, with
Chernoff strictly tighter than Markov -- is enforced point by point, and the central
limit theorem is checked in the direction that matters: the Kolmogorov-Smirnov distance
at ``4n`` is roughly half the distance at ``n`` (the Berry-Esseen order). The limit case
is the Cauchy distribution, whose sample mean does not concentrate.
"""

import math
import pathlib
import random
import shutil
import sys
import traceback
from fractions import Fraction
from math import comb

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


# ---------------------------------------------------------------------------
# The checker's own arithmetic (never the learner's)
# ---------------------------------------------------------------------------

def _reference_binomial_tail(n, p, k):
    """P(Binomial(n, p) >= k) as an exact Fraction, from its own sum."""
    if k <= 0:
        return Fraction(1)
    if k > n:
        return Fraction(0)
    p = Fraction(p)
    q = 1 - p
    total = Fraction(0)
    for i in range(k, n + 1):
        total += comb(n, i) * p ** i * q ** (n - i)
    return total


def _reference_dice_sum():
    """pmf of the sum of two fair dice, {2: 1/36, ..., 12: 1/36}."""
    return {k: Fraction(k - 1, 36) if k <= 7 else Fraction(13 - k, 36)
            for k in range(2, 13)}


def _interquartile_range(values):
    """IQR by linear interpolation, computed here rather than by any solution."""
    ordered = sorted(values)
    count = len(ordered)

    def quantile(q):
        position = q * (count - 1)
        low = int(math.floor(position))
        high = int(math.ceil(position))
        if low == high:
            return ordered[low]
        return ordered[low] + (position - low) * (ordered[high] - ordered[low])

    return quantile(0.75) - quantile(0.25)


def _checker_sample_means(dist, n, trials, rng):
    """The checker's own sample-mean simulation, used only for comparisons."""
    means = []
    for _ in range(trials):
        total = 0.0
        for _ in range(n):
            total += dist(rng)
        means.append(total / n)
    return means


# ---------------------------------------------------------------------------
# Step 1: change of variables
# ---------------------------------------------------------------------------

def check_change_of_variables() -> None:
    from limits import change_of_variables

    # X ~ Exp(1), Y = X^2 (increasing on the support). Analytic:
    # f_Y(y) = f_X(sqrt y) / (2 sqrt y) = exp(-sqrt y) / (2 sqrt y).
    g_inv = math.sqrt
    g_prime_inv = lambda y: 2.0 * math.sqrt(y)
    fy = lambda x: math.exp(-x) if x >= 0.0 else 0.0
    worst = 0.0
    for i in range(1, 301):
        y = 0.02 * i
        got = change_of_variables(y, g_inv, g_prime_inv, fy)
        ref = math.exp(-math.sqrt(y)) / (2.0 * math.sqrt(y))
        worst = max(worst, abs(got - ref))
    assert worst < 1e-9, (
        f"the largest error against the analytic f_Y is {worst:.3e}. For Y = X^2 "
        "with X ~ Exp(1), f_Y(y) = f_X(sqrt y) / |g'(sqrt y)| = exp(-sqrt y) / "
        "(2 sqrt y): the Jacobian 1/|g'| factor is missing if the values are too "
        "large by 2 sqrt y")

    # A linear map: X ~ N(0, 1), Y = 3X - 2, so f_Y(y) = phi((y + 2)/3) / 3.
    phi = lambda x: math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)
    lin_inv = lambda y: (y + 2.0) / 3.0
    lin_prime = lambda y: 3.0
    worst = 0.0
    for i in range(-100, 101):
        y = 0.1 * i
        got = change_of_variables(y, lin_inv, lin_prime, phi)
        ref = phi((y + 2.0) / 3.0) / 3.0
        worst = max(worst, abs(got - ref))
    assert worst < 1e-12, (
        f"the linear map error is {worst:.3e}. For Y = 3X - 2, the density is "
        "f_X((y + 2)/3) / 3: a constant scale enters through 1/|g'|")

    # A decreasing map so the absolute value of g' matters. X ~ Exp(1),
    # Y = 1/X, so f_Y(y) = f_X(1/y) / y^2 = exp(-1/y) / y^2 for y > 0 and
    # g'(x) = -1/x^2, i.e. g'(1/y) = -y^2.
    recip_inv = lambda y: 1.0 / y
    recip_prime = lambda y: -y * y
    worst = 0.0
    for i in range(1, 301):
        y = 0.01 * i
        got = change_of_variables(y, recip_inv, recip_prime, fy)
        ref = math.exp(-1.0 / y) / (y * y)
        worst = max(worst, abs(got - ref))
    assert worst < 1e-12, (
        f"the decreasing-map error is {worst:.3e}. For Y = 1/X the Jacobian is "
        "1/|g'(1/y)| = 1/y^2 with g' = -1/x^2: dropping the absolute value "
        "returns a NEGATIVE density, which is impossible")


# ---------------------------------------------------------------------------
# Step 2: convolution
# ---------------------------------------------------------------------------

def check_convolution() -> None:
    from limits import convolution

    # Two fair dice: the sum 2..12 has the triangular hand count.
    die = [Fraction(0)] + [Fraction(1, 6)] * 6
    summed = convolution(die, die)
    assert len(summed) == 13, (
        f"the convolution of two length-7 pmfs has length {len(summed)}, "
        "expected 13 = 7 + 7 - 1: the index runs over 0..12, with 0 and 1 "
        "carrying no mass because the dice start at 1")
    reference = _reference_dice_sum()
    for k, want in reference.items():
        assert summed[k] == want, (
            f"P(sum = {k}) = {summed[k]}, expected {want}. The coefficient is "
            "the CONVOLUTION sum_i p[i] q[k - i], not the elementwise product "
            "p[k] q[k]")
    assert sum(summed) == 1, (
        f"the sum of the convolved dice pmf is {sum(summed)}, not 1: "
        "convolution preserves total mass")

    # Two independent Poisson(1) variables give Poisson(2). This exercises the
    # convolution on a non-uniform, unbounded-support pmf.
    pois1 = [math.exp(-1.0) / math.factorial(i) for i in range(16)]
    pois2 = convolution(pois1, pois1)
    assert len(pois2) == 31, (
        f"the convolved Poisson support has length {len(pois2)}, expected 31")
    total = 0.0
    for k in range(31):
        reference_value = math.exp(-2.0) * 2.0 ** k / math.factorial(k)
        assert abs(pois2[k] - reference_value) < 1e-9, (
            f"P(Poisson(2) = {k}) is {pois2[k]:.3e} but the convolution gives "
            f"{reference_value:.3e}. The pmf of a sum of two independent "
            "Poisson variables is the convolution of their pmfs, which is "
            "Poisson with added rates")
        total += pois2[k]
    assert total > 0.999, (
        f"the convolved Poisson pmf sums to {total:.6f}, not near 1: the "
        "unbounded tail may have been truncated away")


# ---------------------------------------------------------------------------
# Step 3: the bounds lie above the exact tail, and Chernoff beats Markov
# ---------------------------------------------------------------------------

def check_bounds() -> None:
    from limits import (chebyshev_bound, chernoff_bound, exact_tail_bernoulli,
                        exact_tail_exponential, markov_bound)

    cases = [
        (100, Fraction(3, 10), 40),
        (100, Fraction(3, 10), 45),
        (100, Fraction(3, 10), 50),
        (200, Fraction(1, 4), 70),
    ]
    for n, p, k in cases:
        exact = _reference_binomial_tail(n, p, k)
        got = exact_tail_bernoulli(n, p, k)
        assert got == exact, (
            f"exact_tail_bernoulli({n}, {p}, {k}) = {got}, expected {exact}: "
            "sum the binomial pmf over i = k..n with exact integer binomial "
            "coefficients")

        mean = n * float(p)
        var = n * float(p) * (1.0 - float(p))
        exact_f = float(exact)
        markov = markov_bound(mean, float(k))
        chebyshev = chebyshev_bound(var, float(k) - mean)
        mgf = lambda s, n=n, p=p: (1.0 - float(p) + float(p) * math.exp(s)) ** n
        chernoff = chernoff_bound(mgf, float(k))

        assert markov + 1e-12 >= exact_f, (
            f"Markov at Binomial({n}, {p}) >= {k} is {markov}, BELOW the exact "
            f"tail {exact_f}. Markov needs E[X]/t = {mean}/{k}; a value at the "
            "exact tail is not a bound above it")
        assert chebyshev + 1e-12 >= exact_f, (
            f"Chebyshev is {chebyshev}, below the exact tail {exact_f}. The "
            "deviation is t = k - E[X] and the bound is Var/t^2")
        assert chernoff + 1e-12 >= exact_f, (
            f"Chernoff is {chernoff}, below the exact tail {exact_f}. It is "
            "inf_{s>0} exp(-s t) M(s) and must be an upper bound")
        assert chernoff < markov, (
            f"Chernoff {chernoff} is not tighter than Markov {markov} at "
            f"Binomial({n}, {p}) >= {k}. If Markov has been replaced by the "
            "exact tail, the two are equal and this fails: Chernoff must be "
            "strictly below the Markov bound on the large deviations tested")

    # Exponential(rate): exact tail exp(-rate t), mgf rate/(rate - s).
    rate, t = 2.0, 3.0
    exact = exact_tail_exponential(rate, t)
    assert abs(exact - math.exp(-6.0)) < 1e-15, (
        f"exact_tail_exponential(2, 3) = {exact}, expected exp(-6) = "
        f"{math.exp(-6.0)}: P(Exp(rate) >= t) = exp(-rate t)")
    markov = markov_bound(1.0 / rate, t)
    exponential_mgf = lambda s: rate / (rate - s) if s < rate else math.inf
    chernoff = chernoff_bound(exponential_mgf, t)
    assert markov + 1e-12 >= exact, (
        f"Markov for the exponential is {markov}, below the exact tail {exact}")
    assert chernoff + 1e-12 >= exact, (
        f"Chernoff for the exponential is {chernoff}, below the exact tail "
        f"{exact}")
    assert chernoff < markov, (
        f"Chernoff {chernoff} must be tighter than Markov {markov} for the "
        "exponential large deviation")


# ---------------------------------------------------------------------------
# Step 4: the law of large numbers and the Berry-Esseen rate of the CLT
# ---------------------------------------------------------------------------

def check_lln_and_clt() -> None:
    from limits import clt_error, lln_sample_means

    # Law of large numbers on U(0, 1): averaging the running means over many
    # replications makes the curve settle on 1/2.
    rng = random.Random(555)
    uniform = lambda r: r.random()
    running = lln_sample_means(uniform, 400, 2000, rng)
    assert len(running) == 400, (
        f"lln_sample_means returned {len(running)} entries, expected n = 400")
    assert abs(running[-1] - 0.5) < 0.01, (
        f"the running mean after 400 draws is {running[-1]:.5f}, expected about "
        "0.5: the law of large numbers says it converges to E[X]")
    assert abs(running[-1] - running[-2]) < 0.01, (
        "the running mean is still jumping between the last two steps; "
        "averaging over the replications should have settled it")

    # Central limit theorem: the KS distance to N(0, 1) at 4n is about half the
    # distance at n (Berry-Esseen, order 1/sqrt(n)). An exponential(2) has
    # skewness 2 and standard deviation 0.5, so a standardisation that divides
    # by the variance instead of the standard deviation changes the scale.
    def exponential_two(r):
        return -math.log(1.0 - r.random()) / 2.0

    rng = random.Random(20240)
    error_n = clt_error(exponential_two, 25, 100000, rng)
    error_4n = clt_error(exponential_two, 100, 100000, rng)
    assert error_n < 0.15, (
        f"the KS distance at n = 25 is {error_n:.4f}, far above the expected "
        "order. Standardise with (mean - mu) / (sigma / sqrt(n)): dividing by "
        "the variance sigma^2 instead of the standard deviation sigma blows the "
        "scale up and inflates this distance toward 0.3")
    assert error_4n < 0.12, (
        f"the KS distance at n = 100 is {error_4n:.4f}, too large for this n")
    ratio = error_n / error_4n
    assert 1.4 < ratio < 3.2, (
        f"the KS distance falls by a factor {ratio:.2f} from n = 25 to n = 100, "
        "expected about 2. The Berry-Esseen rate is 1/sqrt(n), so quadrupling n "
        "should halve the error; a ratio near 1 means the error is not the "
        "distribution distance but the empirical jitter (too few trials)")


# ---------------------------------------------------------------------------
# Step 5: the limit case -- the Cauchy sample mean does not concentrate
# ---------------------------------------------------------------------------

def check_cauchy_limit() -> None:
    from limits import cauchy_sample_means

    rng = random.Random(31337)
    trials = 40000
    small = cauchy_sample_means(4, trials, rng)
    large = cauchy_sample_means(16, trials, rng)
    spread_small = _interquartile_range(small)
    spread_large = _interquartile_range(large)
    assert spread_small > 0.5, (
        f"the Cauchy sample-mean spread at n = 4 is {spread_small:.4f}. The "
        "standard Cauchy has IQR 2, and the mean of n draws is again Cauchy, so "
        "it stays O(1) rather than shrinking")

    # Positive control: a finite-variance distribution's sample means DO
    # concentrate. If this failed too, the spread metric would be blind.
    def exponential_one(r):
        return -math.log(1.0 - r.random())

    expo_small = _checker_sample_means(exponential_one, 4, trials, rng)
    expo_large = _checker_sample_means(exponential_one, 16, trials, rng)
    expo_ratio = _interquartile_range(expo_large) / _interquartile_range(expo_small)
    assert expo_ratio < 0.75, (
        f"the Exp(1) sample-mean spread fell by a factor {expo_ratio:.3f}, "
        "expected about 0.5 from n = 4 to n = 16. The spread metric must "
        "detect concentration for a finite-variance law, or it cannot be "
        "trusted to detect its absence for the Cauchy")

    # The limit-case check must decide non-convergence from the spread, not
    # assume the mean converges. This guard fires if it is weakened to assume
    # convergence.
    converged = spread_large <= 0.75 * spread_small
    assert converged is False, (
        f"the Cauchy spread went from {spread_small:.4f} at n = 4 to "
        f"{spread_large:.4f} at n = 16, a ratio of "
        f"{spread_large / spread_small:.3f}. It does NOT shrink by the "
        "finite-variance 1/sqrt(n) factor: the Cauchy mean is undefined and the "
        "sample mean does not converge. If this assert fires, the check itself "
        "started assuming convergence instead of measuring it")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("limits.py", "change of variables (the Jacobian factor)", check_change_of_variables),
    ("limits.py", "convolution of pmfs", check_convolution),
    ("limits.py", "bounds above the exact tail, Chernoff < Markov", check_bounds),
    ("limits.py", "law of large numbers and the 1/sqrt(n) CLT rate", check_lln_and_clt),
    ("limits.py", "the Cauchy sample mean does not converge", check_cauchy_limit),
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
    print(f"\n{BOLD}Limits and Inequalities From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built the limit theorems from scratch.{RESET}")
        print(f"  {GREY}Run solutions/limits.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
