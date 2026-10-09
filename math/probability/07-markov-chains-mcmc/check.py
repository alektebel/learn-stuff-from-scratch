"""
Progress checker for the Markov-chains-and-MCMC templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 3         # run only step 3
    python3 check.py 3 5       # run steps 3 through 5
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

Every reference value is recomputed here, independently of the learner's code: the
stationary distributions by an exact ``fractions.Fraction`` elimination, the
empirical distribution by counting, and the target moments from the closed form.
The node's acceptance criterion is step 2 -- the empirical distribution of a long
chain matches the stationary distribution -- with step 3 the same statement for
Metropolis-Hastings (it recovers a known target's mean and variance) and step 4 for
Gibbs (it recovers two marginal means, two variances and the correlation sign). The
limit cases are step 5: a periodic chain that has a stationary distribution but
never converges to it, and a bimodal target a tiny-step sampler cannot cross.
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


# ---------------------------------------------------------------------------
# The checker's own arithmetic (never the learner's)
# ---------------------------------------------------------------------------

def _ref_stationary(P):
    """Stationary distribution by exact rational elimination, independent of the
    learner's code. ``P`` is a list of rows of ints/Fractions."""
    n = len(P)
    A = []
    for j in range(n):
        row = [Fraction(P[i][j]) for i in range(n)]
        row[j] -= 1
        row.append(Fraction(0))
        A.append(row)
    A[-1] = [Fraction(1)] * n + [Fraction(1)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(A[r][col]))
        A[col], A[pivot] = A[pivot], A[col]
        pv = A[col][col]
        if pv == 0:
            raise ZeroDivisionError("checker self-test: singular chain")
        for c in range(col, n + 1):
            A[col][c] /= pv
        for r in range(n):
            if r != col and A[r][col] != 0:
                factor = A[r][col]
                for c in range(col, n + 1):
                    A[r][c] -= factor * A[col][c]
    return [A[i][n] for i in range(n)]


def _close(got, want, tol=1e-9):
    return all(abs(float(a) - float(b)) < tol for a, b in zip(got, want))


# The hand 2-state chain used in step 1. Stationary pi = (1/3, 2/3); its right
# eigenvector is (1/2, 1/2), so a solve that uses the transpose lands on uniform.
TWO_STATE = [[Fraction(1, 2), Fraction(1, 2)],
             [Fraction(1, 4), Fraction(3, 4)]]
TWO_STATE_PI = [Fraction(1, 3), Fraction(2, 3)]

# The 3-state chain used in steps 1 and 2. Stationary pi = (2/5, 1/5, 2/5);
# aperiodic (states 0 and 2 have self-loops) and irreducible.
THREE_STATE = [[Fraction(1, 2), Fraction(1, 4), Fraction(1, 4)],
               [Fraction(1, 2), Fraction(0), Fraction(1, 2)],
               [Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)]]
THREE_STATE_PI = [Fraction(2, 5), Fraction(1, 5), Fraction(2, 5)]


# ---------------------------------------------------------------------------
# Step 1: stationary distribution solves pi P = pi and sums to 1
# ---------------------------------------------------------------------------

def check_stationary_distribution() -> None:
    from mcmc import stationary_distribution

    chain_2 = [[0.5, 0.5], [0.25, 0.75]]
    got = stationary_distribution(chain_2)
    want = TWO_STATE_PI
    assert len(got) == 2, f"stationary_distribution returned {len(got)} values, expected 2"
    assert abs(sum(got) - 1.0) < 1e-9, (
        f"the stationary distribution sums to {sum(got)}, not 1: the "
        "normalisation sum pi = 1 is missing or the solve is not normalised")
    assert _close(got, want), (
        f"stationary_distribution([[.5,.5],[.25,.75]]) = {got}, expected "
        "pi = (1/3, 2/3). The left eigenvector of P for eigenvalue 1 solves "
        "sum_i pi_i P[i][j] = pi_j; the RIGHT eigenvector solves P v = v and "
        "here is (1/2, 1/2). A solve that uses P[j][i] instead of P[i][j] "
        "returns uniform")

    # The residual of pi P = pi must vanish.
    for j in range(2):
        lhs = sum(got[i] * chain_2[i][j] for i in range(2))
        assert abs(lhs - got[j]) < 1e-9, (
            f"(pi P)_j = {lhs} but pi_j = {got[j]}: pi is not a left "
            "eigenvector of P -- the equations were built from the transpose")

    chain_3 = [[0.5, 0.25, 0.25], [0.5, 0.0, 0.5], [0.25, 0.25, 0.5]]
    got3 = stationary_distribution(chain_3)
    assert _close(got3, THREE_STATE_PI), (
        f"stationary_distribution of the 3-state chain = {got3}, expected "
        "(2/5, 1/5, 2/5) = (0.4, 0.2, 0.4). Solve pi P = pi with sum pi = 1; "
        "the right eigenvector here is uniform (1/3, 1/3, 1/3)")
    for j in range(3):
        lhs = sum(got3[i] * chain_3[i][j] for i in range(3))
        assert abs(lhs - got3[j]) < 1e-9, (
            f"(pi P)_j = {lhs} but pi_j = {got3[j]} on the 3-state chain")

    # The checker's own exact reference must agree with the hand values.
    assert _ref_stationary(TWO_STATE) == TWO_STATE_PI, (
        "checker self-test: the exact reference for the 2-state chain is wrong")
    assert _ref_stationary(THREE_STATE) == THREE_STATE_PI, (
        "checker self-test: the exact reference for the 3-state chain is wrong")


# ---------------------------------------------------------------------------
# Step 2: the acceptance criterion -- empirical distribution matches pi
# ---------------------------------------------------------------------------

def check_empirical_matches_stationary() -> None:
    from mcmc import simulate_chain, empirical_distribution

    chain = [[0.5, 0.25, 0.25], [0.5, 0.0, 0.5], [0.25, 0.25, 0.5]]
    rng = random.Random(20241101)
    states = simulate_chain(chain, 0, 200000, rng)
    assert len(states) == 200001, (
        f"simulate_chain returned {len(states)} states for steps = 200000: the "
        "trajectory must hold the initial state plus one per step, i.e. steps + 1")
    assert all(s in (0, 1, 2) for s in states), (
        "simulate_chain produced a state outside {0, 1, 2}: the cumulative walk "
        "must index the row of the current state")

    empirical = empirical_distribution(states[1000:], 3)
    want = [float(x) for x in THREE_STATE_PI]
    for k in range(3):
        assert abs(empirical[k] - want[k]) < 0.01, (
            f"empirical P(state = {k}) = {empirical[k]:.4f} over a long chain, "
            f"but the stationary distribution is {want[k]:.4f}. The empirical "
            "distribution of an ergodic chain must converge to pi. Walking the "
            "COLUMN P[.][state] instead of the row P[state] simulates the "
            "transposed chain, whose stationary distribution is the RIGHT "
            "eigenvector (uniform here), so all three fractions drift to 1/3")

    # A deliberately non-uniform chain makes the transposed-chain error
    # unmistakable: uniform 1/3 is 0.0667 away from 0.2 and 0.4.
    assert abs(empirical[1] - 1.0 / 3.0) > 0.05, (
        f"the empirical fraction of state 1 is {empirical[1]:.4f}, close to "
        "1/3: this is the signature of simulating the transposed chain, whose "
        "stationary distribution is uniform, not pi = (0.4, 0.2, 0.4)")


# ---------------------------------------------------------------------------
# Step 3: Metropolis-Hastings recovers a known target
# ---------------------------------------------------------------------------

def check_metropolis_hastings() -> None:
    from mcmc import metropolis_hastings, target_mean_var

    rng = random.Random(20241102)
    samples = metropolis_hastings(
        lambda x: -0.5 * x * x,
        lambda x, g: x + g.gauss(0.0, 1.0),
        0.0, 200000, rng)
    assert len(samples) == 200001, (
        f"metropolis_hastings returned {len(samples)} states, expected steps + 1")
    mean, var = target_mean_var(samples[1000:])
    assert abs(mean - 0.0) < 0.05, (
        f"Metropolis-Hastings on a standard normal gives sample mean "
        f"{mean:.4f}, expected near 0. The chain must target exp(-x^2/2). "
        "Accepting EVERY proposal makes the chain a random walk x_{t+1} = "
        "x_t + noise with no stationary distribution, so the mean drifts")
    assert abs(var - 1.0) < 0.10, (
        f"the sample variance is {var:.4f}, expected near 1 for a standard "
        "normal. A variance far above 1 is the random walk that results from "
        "dropping the min(0, .) acceptance floor and accepting every step")

    # A shifted target with a different scale: mean and variance both pinned.
    rng = random.Random(20241103)
    samples = metropolis_hastings(
        lambda x: -0.5 * ((x - 2.0) / 1.5) ** 2,
        lambda x, g: x + g.gauss(0.0, 1.5),
        0.0, 200000, rng)
    mean, var = target_mean_var(samples[1000:])
    assert abs(mean - 2.0) < 0.10, (
        f"on N(2, 1.5^2) the sample mean is {mean:.4f}, expected near 2")
    assert abs(var - 1.5 ** 2) < 0.25, (
        f"on N(2, 1.5^2) the sample variance is {var:.4f}, expected near 2.25")


# ---------------------------------------------------------------------------
# Step 4: Gibbs sampling recovers the marginals and the correlation sign
# ---------------------------------------------------------------------------

def check_gibbs_sampling() -> None:
    from mcmc import gibbs_sampling, target_mean_var

    rho = 0.7
    spread = math.sqrt(1.0 - rho * rho)
    rng = random.Random(20241104)
    samples = gibbs_sampling(
        [lambda x, g: g.gauss(rho * x[1], spread),
         lambda x, g: g.gauss(rho * x[0], spread)],
        [0.0, 0.0], 200000, rng)
    assert len(samples) == 200001, (
        f"gibbs_sampling returned {len(samples)} states, expected steps + 1")
    body = samples[1000:]
    xs = [s[0] for s in body]
    ys = [s[1] for s in body]

    mean_x, var_x = target_mean_var(xs)
    mean_y, var_y = target_mean_var(ys)
    assert abs(mean_x) < 0.05 and abs(mean_y) < 0.05, (
        f"marginal means are ({mean_x:.4f}, {mean_y:.4f}), expected near 0")
    assert abs(var_x - 1.0) < 0.10 and abs(var_y - 1.0) < 0.10, (
        f"marginal variances are ({var_x:.4f}, {var_y:.4f}), expected near 1. "
        "A second variance near 0 means the second coordinate was never "
        "redrawn: Gibbs must sweep EVERY coordinate each step, not only the "
        "first")

    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    assert sxx > 0 and syy > 0, (
        "a marginal has zero sample variance, so the correlation is undefined: "
        "one coordinate of the Gibbs sweep is not being updated")
    corr = sxy / math.sqrt(sxx * syy)
    assert corr > 0.3, (
        f"sample corr(x, y) = {corr:.4f}, expected a positive value near "
        f"rho = {rho}. The conditionals couple x to rho*y and y to rho*x, so a "
        "correct Gibbs sampler reproduces the positive correlation sign; a "
        "sample whose correlation is ~0 means one coordinate never moved")


# ---------------------------------------------------------------------------
# Step 5: the limit cases -- periodicity and a bimodal target
# ---------------------------------------------------------------------------

def _bimodal_log_target(x):
    """log density of 0.5 N(-4, 0.5^2) + 0.5 N(4, 0.5^2), in log space."""
    a = -0.5 * ((x + 4.0) / 0.5) ** 2
    b = -0.5 * ((x - 4.0) / 0.5) ** 2
    m = max(a, b)
    return m + math.log(0.5 * math.exp(a - m) + 0.5 * math.exp(b - m))


def check_limit_cases() -> None:
    from mcmc import (stationary_distribution, matrix_power, simulate_chain,
                      empirical_distribution, metropolis_hastings)

    # (a) Periodic chain: stationary exists, but the distribution never converges.
    periodic = [[0.0, 1.0], [1.0, 0.0]]
    pi = stationary_distribution(periodic)
    assert _close(pi, [0.5, 0.5]), (
        f"the periodic chain [[0,1],[1,0]] has stationary distribution {pi}, "
        "expected (1/2, 1/2) -- each state is visited every other step")
    assert matrix_power(periodic, 2) == [[1.0, 0.0], [0.0, 1.0]], (
        f"P^2 = {matrix_power(periodic, 2)}, expected the identity: the chain "
        "has period 2, so P alternates between P and I")
    assert matrix_power(periodic, 51) == [[0.0, 1.0], [1.0, 0.0]], (
        f"P^51 = {matrix_power(periodic, 51)}, expected P: odd powers are P")
    even_row = matrix_power(periodic, 50)[0]
    odd_row = matrix_power(periodic, 51)[0]
    converged_even = max(abs(even_row[j] - 0.5) for j in range(2)) < 1e-6
    converged_odd = max(abs(odd_row[j] - 0.5) for j in range(2)) < 1e-6
    assert not converged_even and not converged_odd, (
        "the periodic chain must NOT converge: P^50[0] = (1, 0) and "
        "P^51[0] = (0, 1), each 0.5 away from pi = (1/2, 1/2). A convergence "
        "check that reads a single power of P assumes it settles and is wrong")

    rng = random.Random(20241105)
    states = simulate_chain(periodic, 0, 100, rng)
    assert all(states[k] == k % 2 for k in range(len(states))), (
        "the periodic chain from state 0 must visit 0, 1, 0, 1, ...: the "
        "time-n position is deterministic, not a draw from pi. The empirical "
        "distribution of the LAST position never settles, even though pi does")
    last_empirical = empirical_distribution([states[-1]], 2)
    assert last_empirical == [1.0, 0.0], (
        "the distribution at an even time is a point mass at 0, not pi")

    # (b) Bimodal target: a tiny step never crosses between the modes.
    gap = 8.0
    small_sigma = 0.02
    large_sigma = 8.0
    assert small_sigma < gap / 4, (
        "the small-step sampler must genuinely be a small step; using a large "
        "step here assumes it explores both modes and the limit case is lost")

    rng = random.Random(20241106)
    small = metropolis_hastings(
        _bimodal_log_target,
        lambda x, g: x + g.gauss(0.0, small_sigma),
        -4.0, 100000, rng)[1000:]
    small_left = sum(1 for x in small if x < 0.0) / len(small)
    small_right = 1.0 - small_left
    assert small_left > 0.9 and small_right < 0.05, (
        f"a tiny-step random walk (step {small_sigma}) started at the left "
        f"mode ended with fraction left = {small_left:.4f}, right = "
        f"{small_right:.4f}. With a step far smaller than the gap of {gap} the "
        "chain can never cross, so it samples only one mode: the sample mean "
        "and the coverage of the other mode are simply wrong")

    rng = random.Random(20241107)
    large = metropolis_hastings(
        _bimodal_log_target,
        lambda x, g: x + g.gauss(0.0, large_sigma),
        -4.0, 100000, rng)[1000:]
    large_left = sum(1 for x in large if x < 0.0) / len(large)
    large_right = 1.0 - large_left
    assert large_left > 0.2 and large_right > 0.2, (
        f"a large-step random walk (step {large_sigma}) found fraction left = "
        f"{large_left:.4f}, right = {large_right:.4f}; a step comparable to the "
        "gap crosses between the modes and both are visited. A sampler that "
        "cannot find both modes has not sampled the target")


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("mcmc.py", "stationary distribution: solve pi P = pi (step 1)", check_stationary_distribution),
    ("mcmc.py", "empirical distribution of a long chain matches pi (accept)", check_empirical_matches_stationary),
    ("mcmc.py", "Metropolis-Hastings recovers a known target (accept)", check_metropolis_hastings),
    ("mcmc.py", "Gibbs recovers the marginals and their correlation", check_gibbs_sampling),
    ("mcmc.py", "limit cases: periodic chain and bimodal target", check_limit_cases),
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
    print(f"\n{BOLD}Markov Chains and MCMC From Scratch — progress check{RESET}")
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
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built Markov chains and MCMC from scratch.{RESET}")
        print(f"  {GREY}Run solutions/mcmc.py's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
