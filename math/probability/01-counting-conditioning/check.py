"""
Progress checker for the counting-and-conditioning templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 4         # run only step 4
    python3 check.py 4 6       # run steps 4 through 6
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

Every reference probability is computed here, independently, from math.comb and
fractions.Fraction, so the checker never asks your own code what the right answer is.
The acceptance rule from the skill tree is enforced literally: the exact Fraction must
sit within four standard errors of a 10**5-trial simulation.
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

def _within_4se(exact, simulated, trials=TRIALS):
    """(agrees, gap, bound): |exact - sim| <= 4 sqrt(p(1-p)/N), on floats."""
    p = float(exact)
    bound = 4.0 * math.sqrt(p * (1.0 - p) / trials)
    gap = abs(p - float(simulated))
    return gap <= bound, gap, bound


def _se_message(what, exact, simulated, gap, bound):
    return (f"{what}: exact {float(exact):.6f} vs simulated {float(simulated):.6f} "
            f"differ by {gap:.6f}, more than the 4-standard-error bound {bound:.6f} at "
            f"{TRIALS} trials. The two computations disagree about the sample space or "
            "about the conditioning, not just about noise.")


# ---------------------------------------------------------------------------
# Step 1: the multiplication principle, P(n, k)
# ---------------------------------------------------------------------------

def check_falling_factorial() -> None:
    from probability import falling_factorial

    assert falling_factorial(5, 0) == 1, (
        "falling_factorial(5, 0) must be 1: there is exactly one empty selection")
    assert falling_factorial(5, 2) == 20, (
        f"falling_factorial(5, 2) = {falling_factorial(5, 2)}, expected 20 = 5·4: P(n, k) "
        "multiplies exactly k descending factors, so a loop over the wrong range is off by one")
    assert falling_factorial(5, 5) == 120, (
        f"falling_factorial(5, 5) = {falling_factorial(5, 5)}, expected 120 = 5!")
    assert falling_factorial(5, 6) == 0, (
        "falling_factorial(5, 6) must be 0: you cannot pick 6 distinct items from 5")

    rng = random.Random(11)
    for _ in range(200):
        n = rng.randint(0, 60)
        k = rng.randint(-3, n + 3)
        expected = math.factorial(n) // math.factorial(n - k) if 0 <= k <= n else 0
        got = falling_factorial(n, k)
        assert got == expected, (
            f"falling_factorial({n}, {k}) = {got}, expected {expected}. P(n, k) = "
            "n·(n−1)···(n−k+1) for 0 <= k <= n, 0 for k > n, 1 for k = 0.")


# ---------------------------------------------------------------------------
# Step 2: subsets, C(n, k)
# ---------------------------------------------------------------------------

def check_binomial_coefficient() -> None:
    from probability import binomial_coefficient

    assert binomial_coefficient(52, 5) == 2_598_960, (
        f"C(52, 5) = {binomial_coefficient(52, 5)}, expected 2598960: this is the poker "
        "sample space, and a wrong value poisons every hand probability")
    assert binomial_coefficient(5, 0) == 1 and binomial_coefficient(5, 5) == 1, (
        "C(n, 0) = C(n, n) = 1: the empty set and the whole set are the only such subsets")
    assert binomial_coefficient(5, 6) == 0 and binomial_coefficient(5, -1) == 0, (
        "C(n, k) is 0 outside 0 <= k <= n, not an error")

    rng = random.Random(13)
    for _ in range(300):
        n = rng.randint(0, 60)
        k = rng.randint(-2, n + 2)
        expected = math.comb(n, k) if 0 <= k <= n else 0
        got = binomial_coefficient(n, k)
        assert got == expected, (
            f"binomial_coefficient({n}, {k}) = {got}, expected {expected}. C(n, k) is "
            "P(n, k)/k!; folding the division into the product keeps it exact, but the "
            "first and last factors are where an off-by-one hides (check C(n, n−k)).")


# ---------------------------------------------------------------------------
# Step 3: counting with the sample space (two pair)
# ---------------------------------------------------------------------------

def check_poker_two_pair() -> None:
    from probability import poker_two_pair_probability, simulate_two_pair

    expected = Fraction(math.comb(13, 2) * math.comb(4, 2) ** 2 * 44, math.comb(52, 5))
    got = poker_two_pair_probability()
    assert got == expected, (
        f"P(two pair) = {got}, expected {expected}. Count the favourable hands "
        "C(13,2)·C(4,2)²·44 AND divide by the C(52,5) sample space; a returned count "
        "(or a ratio with the wrong denominator) is not a probability.")

    simulated = simulate_two_pair(TRIALS, seed=101)
    ok, gap, bound = _within_4se(expected, simulated)
    assert ok, _se_message("two-pair simulation", expected, simulated, gap, bound)

    again = simulate_two_pair(TRIALS, seed=101)
    assert again == simulated, (
        "simulate_two_pair is not reproducible for a fixed seed: seed the generator "
        "you use, not a module-level one")


# ---------------------------------------------------------------------------
# Step 4: unions without double counting (at least one ace)
# ---------------------------------------------------------------------------

def check_poker_at_least_one_ace() -> None:
    from probability import poker_at_least_one_ace_probability, simulate_at_least_one_ace

    expected = Fraction(math.comb(52, 5) - math.comb(48, 5), math.comb(52, 5))
    got = poker_at_least_one_ace_probability()
    assert got == expected, (
        f"P(at least one ace) = {got}, expected {expected}. Counting C(4,1)·C(51,4) "
        "counts a hand with two aces twice and with three aces three times; the overlaps "
        "must be subtracted (inclusion-exclusion), or use the complement C(48,5)/C(52,5).")
    assert got < Fraction(1, 3) + Fraction(1, 100), (
        "the correct overlap correction pulls the answer below the naive 4·C(51,4)/C(52,5)")

    simulated = simulate_at_least_one_ace(TRIALS, seed=102)
    ok, gap, bound = _within_4se(expected, simulated)
    assert ok, _se_message("at-least-one-ace simulation", expected, simulated, gap, bound)


# ---------------------------------------------------------------------------
# Step 5: the law of total probability
# ---------------------------------------------------------------------------

def check_total_probability() -> None:
    from probability import total_probability

    priors = [Fraction(1, 2), Fraction(1, 3), Fraction(1, 6)]
    likelihoods = [Fraction(1, 4), Fraction(1, 2), Fraction(3, 4)]
    expected = sum(p * l for p, l in zip(priors, likelihoods))
    got = total_probability(priors, likelihoods)
    assert got == expected, (
        f"total_probability = {got}, expected {expected}. Every case in the partition "
        f"contributes: {[str(p * l) for p, l in zip(priors, likelihoods)]} should sum; "
        "dropping a term drops a way for E to happen.")

    assert total_probability([Fraction(1)], [Fraction(3, 7)]) == Fraction(3, 7), (
        "with a one-case partition the law must return that case's contribution unchanged")

    # The diagnostic decomposition: P(+) = P(+|D)P(D) + P(+|H)P(H).
    prevalence, sensitivity, specificity = Fraction(1, 100), Fraction(95, 100), Fraction(90, 100)
    evidence = total_probability([prevalence, 1 - prevalence],
                                 [sensitivity, 1 - specificity])
    assert evidence == sensitivity * prevalence + (1 - specificity) * (1 - prevalence), (
        "the evidence must include the false-positive term (1 − specificity)(1 − prevalence), "
        "not only the true-positive term")


# ---------------------------------------------------------------------------
# Step 6: Bayes' rule
# ---------------------------------------------------------------------------

def check_bayes_posterior() -> None:
    from probability import bayes_posterior

    priors = [Fraction(1, 2), Fraction(1, 2)]
    likelihoods = [Fraction(9, 10), Fraction(1, 10)]
    assert bayes_posterior(priors, likelihoods, 0) == Fraction(9, 10), (
        "with a 50/50 prior and likelihoods 9/10 vs 1/10 the posterior is 9/10")
    assert bayes_posterior(priors, likelihoods, 1) == Fraction(1, 10)
    total = bayes_posterior(priors, likelihoods, 0) + bayes_posterior(priors, likelihoods, 1)
    assert total == 1, "the posteriors over a partition must sum to 1"

    # A three-case case where dropping any term changes the denominator.
    priors3 = [Fraction(1, 2), Fraction(1, 3), Fraction(1, 6)]
    likelihoods3 = [Fraction(1, 5), Fraction(1, 2), Fraction(9, 10)]
    evidence = sum(p * l for p, l in zip(priors3, likelihoods3))
    assert bayes_posterior(priors3, likelihoods3, 2) == Fraction(1, 6) * Fraction(9, 10) / evidence, (
        "the Bayes denominator is the law of total probability over ALL cases; using only "
        "the numerator's case makes the posterior 1 and is the classic missing-false-positive bug")


# ---------------------------------------------------------------------------
# Step 7: the base rate (limit case: intuitive answer off by an order of magnitude)
# ---------------------------------------------------------------------------

def check_base_rate() -> None:
    from probability import diagnostic_posterior, simulate_diagnostic

    prevalence, sensitivity, specificity = Fraction(1, 100), Fraction(95, 100), Fraction(90, 100)
    expected = Fraction(sensitivity * prevalence,
                        sensitivity * prevalence + (1 - specificity) * (1 - prevalence))
    got = diagnostic_posterior(prevalence, sensitivity, specificity)
    assert got == expected, (
        f"P(disease | +) = {got}, expected {expected}. The denominator needs the "
        "false-positive term (1 − specificity)·(1 − prevalence) = 99/1000; without it the "
        "posterior collapses to 1.")

    assert got < Fraction(1, 10), (
        f"P(disease | +) = {float(got):.4f} should be under 0.10: a 1% base rate drags a "
        "95%-sensitive test below 10% even though the test itself is good")
    assert sensitivity / got > 10, (
        f"the test's sensitivity {float(sensitivity):.2f} overstates P(disease | +) = "
        f"{float(got):.4f} by only {float(sensitivity / got):.2f}×; the whole point of the "
        "base-rate case is that the gap is more than an order of magnitude")

    simulated = simulate_diagnostic(prevalence, sensitivity, specificity, TRIALS, seed=707)
    ok, gap, bound = _within_4se(expected, simulated)
    assert ok, _se_message("diagnostic simulation", expected, simulated, gap, bound)


# ---------------------------------------------------------------------------
# Step 8: Monty Hall with a host who knows
# ---------------------------------------------------------------------------

def check_monty_hall_knowing() -> None:
    from probability import monty_hall_probability, simulate_monty_hall

    assert monty_hall_probability(True, True) == Fraction(2, 3), (
        f"switching against a knowing host wins 2/3 (got "
        f"{monty_hall_probability(True, True)}): the host's forced reveal transfers the "
        "2/3 probability of your first pick being a goat onto the one other closed door")
    assert monty_hall_probability(False, True) == Fraction(1, 3), (
        "staying against a knowing host wins 1/3: your first pick is right one time in three")
    assert (monty_hall_probability(True, True)
            - monty_hall_probability(False, True)) == Fraction(1, 3), (
        "switching must beat staying by exactly 1/3 against a knowing host")

    for switch in (False, True):
        exact = monty_hall_probability(switch, True)
        simulated = simulate_monty_hall(switch, True, TRIALS, seed=808)
        ok, gap, bound = _within_4se(exact, simulated)
        assert ok, _se_message(
            f"Monty Hall (knowing host, {'switch' if switch else 'stay'}) simulation",
            exact, simulated, gap, bound)
    assert simulate_monty_hall(True, True, 5_000, seed=9) == \
        simulate_monty_hall(True, True, 5_000, seed=9), (
        "simulate_monty_hall is not reproducible for a fixed seed")


# ---------------------------------------------------------------------------
# Step 9: Monty Hall with a host who does NOT know (the limit case)
# ---------------------------------------------------------------------------

def check_monty_hall_unknowing() -> None:
    from probability import monty_hall_probability, simulate_monty_hall

    assert monty_hall_probability(True, False) == Fraction(1, 2), (
        f"switching against an unknowing host wins 1/2, got "
        f"{monty_hall_probability(True, False)}. If you got 2/3 you gave the host knowledge "
        "he does not have: a random reveal that happens to show a goat leaves the two closed "
        "doors symmetric.")
    assert monty_hall_probability(False, False) == Fraction(1, 2), (
        "staying against an unknowing host also wins 1/2: conditioned on a goat being "
        "revealed, the two remaining doors are exchangeable")
    assert monty_hall_probability(True, False) != monty_hall_probability(True, True), (
        "the host's knowledge must change the answer (1/2 vs 2/3); that contrast is the "
        "limit case this step exists to test")

    for switch in (False, True):
        exact = monty_hall_probability(switch, False)
        simulated = simulate_monty_hall(switch, False, TRIALS, seed=909)
        ok, gap, bound = _within_4se(exact, simulated)
        assert ok, _se_message(
            f"Monty Hall (unknowing host, {'switch' if switch else 'stay'}) simulation",
            exact, simulated, gap, bound)

    # The simulation must condition on the game continuing, not count the rounds
    # where the host reveals the car.
    one = simulate_monty_hall(True, False, 50_000, seed=5)
    assert Fraction(4, 10) < one < Fraction(6, 10), (
        f"the unknowing-host simulation returned {float(one):.4f}; a value near 2/3 means "
        "rounds where the host reveals the car were not discarded")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("probability.py", "multiplication principle P(n, k)", check_falling_factorial),
    ("probability.py", "subsets C(n, k)", check_binomial_coefficient),
    ("probability.py", "counting with the sample space (two pair)", check_poker_two_pair),
    ("probability.py", "unions without double counting (an ace)", check_poker_at_least_one_ace),
    ("probability.py", "law of total probability", check_total_probability),
    ("probability.py", "Bayes' rule", check_bayes_posterior),
    ("probability.py", "base rate off by an order of magnitude", check_base_rate),
    ("probability.py", "Monty Hall, knowing host", check_monty_hall_knowing),
    ("probability.py", "Monty Hall, unknowing host", check_monty_hall_unknowing),
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
    print(f"\n{BOLD}Probability From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built counting and conditioning from scratch.{RESET}")
        print(f"  {GREY}Run solutions/probability.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
