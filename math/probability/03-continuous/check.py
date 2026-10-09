"""
Progress checker for the continuous-random-variables templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

Every reference value is recomputed here from math.erf / math.exp, independently of the
learner's code: the normal CDF from erf, the exponential survival from exp, the KS
statistic by brute force over a grid that includes both sides of each order statistic,
and the KS p-value from its own alternating series. The node's acceptance rule is enforced
literally: inverse-CDF samples must pass a KS test against the target CDF, and a
deliberately mis-scaled sampler must fail the same test.
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

SQRT2 = math.sqrt(2.0)
N_SAMPLE = 5000
# 1% two-sided Kolmogorov critical value for the asymptotic distribution.
CRITICAL_1PC = 1.63


# ---------------------------------------------------------------------------
# The checker's own arithmetic (never the learner's)
# ---------------------------------------------------------------------------

def _normal_cdf(x):
    """Independent reference: Phi(x) = (1 + erf(x/sqrt(2))) / 2."""
    return 0.5 * (1.0 + math.erf(x / SQRT2))


def _ks_reference(samples, cdf):
    """Brute-force D = sup |F_n - F|, probing both sides of each jump.

    This never looks at the (i-1)/n formula the solution uses: it counts the
    empirical CDF at a point just left of and just right of every order
    statistic, which is where the continuous F and the step F_n can be farthest
    apart.
    """
    xs = sorted(samples)
    n = len(xs)
    if n == 0:
        return 0.0
    best = 0.0
    for x in xs:
        eps = 1e-9 * (1.0 + abs(x))
        for probe in (x - eps, x + eps):
            empirical = sum(1 for v in xs if v <= probe) / n
            best = max(best, abs(empirical - cdf(probe)))
    return best


def _q_reference(lam):
    """Independent reference for the Kolmogorov Q, summed to the double limit."""
    total, sign = 0.0, 1.0
    for k in range(1, 100000):
        term = math.exp(-2.0 * (k * lam) ** 2)
        total += sign * term
        if term < 1e-16:
            break
        sign = -sign
    return min(1.0, max(0.0, 2.0 * total))


# ---------------------------------------------------------------------------
# Step 1: the quantile functions invert their CDFs
# ---------------------------------------------------------------------------

def check_ppf_inverse() -> None:
    from continuous import uniform_ppf, exponential_ppf

    for u in (0.0, 0.1, 0.25, 0.5, 0.75, 0.95, 1.0):
        assert abs(uniform_ppf(u) - u) < 1e-15, (
            f"uniform_ppf({u}) = {uniform_ppf(u)}, expected {u}: Uniform(0,1) has "
            "F(x) = x on [0, 1], so its inverse is the identity")

    rate = 2.0
    for u in (0.05, 0.25, 0.5, 0.75, 0.95, 0.999):
        x = exponential_ppf(u, rate)
        back = 1 - math.exp(-rate * x)
        assert abs(back - u) < 1e-12, (
            f"exponential_ppf({u}, {rate}) = {x}, but F(x) = {back}, not {u}. The "
            "inverse of F(x) = 1 - e^(-rate x) is -ln(1 - u)/rate, not -ln(u)/rate")
    assert exponential_ppf(0.0, rate) == 0.0, "F^-1(0) = 0"
    assert exponential_ppf(1.0, rate) == math.inf, "F^-1(1) = +inf"
    assert abs(exponential_ppf(0.5, rate) - math.log(2) / rate) < 1e-12, (
        "the median of Exponential(rate) is ln(2)/rate")
    previous = -1.0
    for u in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        value = exponential_ppf(u, rate)
        assert value >= previous, "the quantile function must be non-decreasing"
        previous = value


# ---------------------------------------------------------------------------
# Step 2: the Normal quantile -- bisection, and it is the inverse
# ---------------------------------------------------------------------------

def check_normal_ppf() -> None:
    from continuous import normal_ppf

    known = {
        0.5: 0.0,
        0.975: 1.959963984540054,
        0.95: 1.6448536269514722,
        0.75: 0.6744897501960817,
        0.25: -0.6744897501960817,
        0.025: -1.959963984540054,
    }
    for u, expected in known.items():
        got = normal_ppf(u)
        assert abs(got - expected) < 1e-6, (
            f"normal_ppf({u}) = {got}, expected {expected}. If you got {u} back, you "
            "returned the CDF Phi(x) instead of its inverse: the quantile at 0.975 "
            "must be 1.96, not 0.975")

    for u in (0.01, 0.2, 0.5, 0.8, 0.99):
        x = normal_ppf(u)
        back = _normal_cdf(x)
        assert abs(back - u) < 1e-9, (
            f"normal_ppf({u}) = {x}, but Phi(x) = {back}, not {u}. Bisect on "
            "Phi(x) = 0.5 (1 + erf(x/sqrt(2))) until it crosses u")

    for u in (0.1, 0.3, 0.45):
        assert abs(normal_ppf(u) + normal_ppf(1 - u)) < 1e-9, (
            "the standard normal is symmetric, so F^-1(u) = -F^-1(1 - u)")

    assert normal_ppf(0.0) == -math.inf and normal_ppf(1.0) == math.inf, (
        "the tails of the normal map to -inf and +inf")
    assert normal_ppf(0.6) > normal_ppf(0.4), "the quantile must increase with u"


# ---------------------------------------------------------------------------
# Step 3: inverse-CDF sampling passes a KS test (the node's acceptance rule)
# ---------------------------------------------------------------------------

def check_inverse_cdf_sample() -> None:
    from continuous import (inverse_cdf_sample, uniform_ppf, exponential_ppf,
                            normal_ppf, ks_statistic, ks_pvalue)

    n = N_SAMPLE
    crit = CRITICAL_1PC / math.sqrt(n)

    cases = [
        ("uniform", uniform_ppf, lambda v: min(1.0, max(0.0, v)), 3001),
        ("exponential", lambda q: exponential_ppf(q, 1.7),
         lambda v: 0.0 if v <= 0 else 1 - math.exp(-1.7 * v), 3002),
        ("normal", normal_ppf, _normal_cdf, 3003),
    ]
    for label, ppf, cdf, seed in cases:
        rng = random.Random(seed)
        xs = inverse_cdf_sample(ppf, n, rng)
        assert len(xs) == n, f"inverse_cdf_sample must return n = {n} draws"
        d = ks_statistic(xs, cdf)
        p = ks_pvalue(d, n)
        assert d < crit, (
            f"{label}: inverse-CDF sample fails its own KS test, D = {d:.5f} > "
            f"{crit:.5f}. ppf(U) with U = rng.random() must have the target CDF; a "
            "wrong parameter or the wrong inverse shows up here.")
        assert p > 0.01, (
            f"{label}: KS p-value {p:.4f} is too small at D = {d:.5f}; the sample "
            "does not look like it came from the target CDF")

    # A deliberately mis-scaled sampler must FAIL the same test. This is the
    # independent direction: passing is not enough, the test must discriminate.
    rng = random.Random(3004)
    bad = inverse_cdf_sample(lambda q: exponential_ppf(q, 1.7 * 3.0), n, rng)
    d_bad = ks_statistic(bad, lambda v: 0.0 if v <= 0 else 1 - math.exp(-1.7 * v))
    assert d_bad > crit, (
        f"the KS test must reject a sampler with three times the rate; D = {d_bad:.5f} "
        f"<= {crit:.5f}. If this passes, the test is not measuring the CDF.")
    assert ks_pvalue(d_bad, n) < 1e-3, (
        "the mis-scaled sampler must get a tiny KS p-value, not just a large D")


# ---------------------------------------------------------------------------
# Step 4: the KS statistic -- two-sided, with the (i-1)/n left limit
# ---------------------------------------------------------------------------

def check_ks_statistic() -> None:
    from continuous import ks_statistic

    # A deterministic sample whose true D is dominated by the LEFT limit:
    # F(x_(i)) is far above (i-1)/n, so a checker that uses i/n on both sides
    # reports the wrong (smaller) number.
    xs = [1.0, 2.0, 3.0, 4.0]
    cdf = lambda v: 1 - math.exp(-2.0 * v)
    got = ks_statistic(xs, cdf)
    expected = _ks_reference(xs, cdf)
    assert abs(got - expected) < 1e-6, (
        f"ks_statistic = {got}, brute force gives {expected}. D = sup|F_n - F| uses "
        "max(i/n - F(x_i), F(x_i) - (i-1)/n): the (i-1)/n left limit is the term "
        "that catches a CDF hiding above the empirical step.")

    # The left-limit term really is the maximum here, so the mutation that drops
    # it is visible.
    left = max(cdf(x) - (i - 1) / len(xs) for i, x in enumerate(xs, start=1))
    assert abs(expected - left) < 1e-6, (
        "the checker expects the left-limit term to determine D for this sample; "
        "if it did not, this step would not probe the (i-1)/n convention")

    # A few random samples against the independent brute force.
    for seed in (41, 42, 43):
        rng = random.Random(seed)
        draws = [exponential_draw(rng) for _ in range(37)]
        ref = _ks_reference(draws, cdf)
        assert abs(ks_statistic(draws, cdf) - ref) < 1e-6, (
            f"ks_statistic disagrees with brute force on a random sample "
            f"({ks_statistic(draws, cdf)} vs {ref})")

    assert ks_statistic([], cdf) == 0.0, "an empty sample has D = 0"


def exponential_draw(rng):
    """An exponential(2) draw, built here so check.py never calls the learner's."""
    return -math.log1p(-rng.random()) / 2.0


# ---------------------------------------------------------------------------
# Step 5: the KS p-value is the whole alternating series
# ---------------------------------------------------------------------------

def check_ks_pvalue() -> None:
    from continuous import ks_pvalue

    assert abs(ks_pvalue(0.0, 100) - 1.0) < 1e-12, (
        "a zero statistic has p-value 1, not 0")

    for d, n in ((0.5, 100), (0.03, 1000), (1.36 / math.sqrt(100), 100),
                 (2.0, 25), (1.0, 50)):
        lam = d * math.sqrt(n)
        expected = _q_reference(lam)
        got = ks_pvalue(d, n)
        assert abs(got - expected) < 1e-9, (
            f"ks_pvalue({d}, {n}) = {got}, expected Q({lam:.4f}) = {expected}. "
            "Q(lam) = 2 sum_k (-1)^(k-1) e^(-2 k^2 lam^2); stopping after the "
            "first term is only the large-lam approximation")

    # The regime that exposes the truncation: lam = 0.5, where the first term
    # alone exceeds 1 while Q is about 0.96.
    d = 0.5 / math.sqrt(100)
    first_term = 2.0 * math.exp(-2.0 * 0.5 ** 2)
    got = ks_pvalue(d, 100)
    assert first_term > 1.0, "the checker needs a lam where one term > 1"
    assert got < 1.0, (
        f"ks_pvalue = {got} > 1 at lam = 0.5: the alternating series was truncated "
        "to its first term, which is not a probability")
    assert abs(got - 0.9643) < 5e-3, (
        f"at lam = 0.5 the asymptotic p-value is about 0.964, got {got}")

    previous = 1.0
    for d in (0.2, 0.5, 1.0, 2.0, 4.0):
        value = ks_pvalue(d, 400)
        assert 0.0 <= value <= 1.0, "a p-value must lie in [0, 1]"
        assert value <= previous + 1e-12, (
            "the p-value must fall as the statistic grows")
        previous = value


# ---------------------------------------------------------------------------
# Step 6: memorylessness -- exact for the exponential, false when shifted
# ---------------------------------------------------------------------------

def check_memorylessness() -> None:
    from continuous import memorylessness_gap, shifted_exponential_gap

    rate = 1.3
    for s, t in ((0.5, 0.7), (2.0, 3.0), (0.1, 5.0), (10.0, 0.2)):
        gap = memorylessness_gap(rate, s, t)
        assert abs(gap) < 1e-12, (
            f"Exponential({rate}) is memoryless: P(X>s+t|X>s) - P(X>t) = {gap} at "
            f"s={s}, t={t}, not 0. Both survivals must be e^(-rate x).")

    # A shifted exponential is NOT memoryless under the same identity.
    shift = 0.75
    s, t = 2.0, 1.0
    gap = shifted_exponential_gap(rate, shift, s, t)
    expected = math.exp(-rate * t) - math.exp(-rate * (t - shift))
    assert abs(gap - expected) < 1e-12, (
        f"shifted_exponential_gap = {gap}, expected {expected}")
    assert abs(gap) > 1e-6, (
        "the checker requires the shifted exponential to have a nonzero gap; a "
        "shifted variable is not memoryless, and a checker that only looks at the "
        "excess would wrongly call it so")


# ---------------------------------------------------------------------------
# Step 7: the limit case -- float rounding near u = 1 truncates the tail
# ---------------------------------------------------------------------------

def check_tail_truncation() -> None:
    from continuous import tail_truncation, exponential_ppf, inverse_cdf_sample

    rate = 1.0
    info = tail_truncation(rate, 1.0)
    assert info["missing_mass"] > 0.0, (
        "the requested u = 1 maps to a finite point; the mass above it is strictly "
        "positive, so reporting missing_mass = 0 hides the truncation")
    assert abs(info["missing_mass"] - 2.0 ** -53) < 1e-30, (
        f"the unreachable tail mass is 2**-53, got {info['missing_mass']}")
    assert info["missing_quantile"] == math.inf, (
        "the quantile still missing above the largest reachable point is +inf: the "
        "true quantile at u = 1 is +inf, so claiming a finite missing quantile "
        "hides the tail")

    x_max = info["x"]
    assert math.isfinite(x_max) and x_max > 0, (
        "the largest reachable exponential quantile must be finite and positive")

    rng = random.Random(7001)
    xs = inverse_cdf_sample(lambda u: exponential_ppf(u, rate), 200000, rng)
    assert max(xs) <= x_max + 1e-12, (
        f"a sample reached {max(xs)}, above the largest reachable quantile {x_max}: "
        "rng.random() < 1, so no draw can exceed -log1p(-U_MAX)/rate")
    assert math.isinf(exponential_ppf(1.0, rate)), (
        "the quantile at u = 1 is +inf; the sampler simply cannot ask for it")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("continuous.py", "Uniform / Exponential quantiles invert their CDFs", check_ppf_inverse),
    ("continuous.py", "Normal quantile by bisection on erf", check_normal_ppf),
    ("continuous.py", "inverse-CDF samples pass a KS test", check_inverse_cdf_sample),
    ("continuous.py", "KS statistic uses both ECDF limits", check_ks_statistic),
    ("continuous.py", "KS p-value is the full asymptotic series", check_ks_pvalue),
    ("continuous.py", "memorylessness, and the shifted counterexample", check_memorylessness),
    ("continuous.py", "tail truncation near u = 1 (the limit case)", check_tail_truncation),
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
    print(f"\n{BOLD}Continuous Random Variables From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built continuous random variables from scratch.{RESET}")
        print(f"  {GREY}Run solutions/continuous.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
