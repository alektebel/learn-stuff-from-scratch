"""Discrete random variables and expectation, from scratch.

Implements chapters 3 and 4 of Blitzstein & Hwang, *Introduction to
Probability* (2nd ed.): the PMF and CDF of the named discrete distributions
(ch. 3) and expectation, variance and linearity with indicator random
variables (ch. 4). The argument is restated here, never copied.

Every distribution is written twice: as an exact PMF (``Fraction`` wherever the
mass is rational) with closed-form mean and variance, and as a seeded
Monte-Carlo sampler. The skill-tree acceptance criterion is that the exact mean
and variance sit within four standard errors of a 10**5-trial simulation, and
that the Poisson approximation to the Binomial improves at the predicted rate.

DESIGN DECISION -- exact fractions, or floats, for the PMF?
Floating point would hide an off-by-one in a support behind rounding, which is
exactly the bug this node plants (a Geometric support starting at 0 instead of
1 shifts the mean by a whole unit). **Chosen: ``Fraction`` for every
distribution whose mass is rational** -- Bernoulli, Binomial, Geometric,
Negative Binomial. **Poisson is the exception**: its mass carries ``e^-lambda``,
which is irrational, so it is computed in float and compared with a small
absolute tolerance. The cost is slow ``p**k`` arithmetic for large support; the
payoff is that "wrong support" and "rounding" cannot be mistaken for each other.

DESIGN DECISION -- does Geometric count trials or failures before success?
Both conventions are common, and they differ by exactly one: ``1/p`` for the
number of trials to the first success versus ``(1-p)/p`` for the number of
failures before it. **Chosen: count trials, support {1, 2, 3, ...}.**
Consequence: ``pmf(1) = p`` and ``cdf(k) = 1 - (1-p)**k``. The cost is that the
same name means a different number in another textbook; the checker pins the
choice by asserting ``pmf(1) == p`` and ``mean == 1/p``.

DESIGN DECISION -- Negative Binomial as trials or as failures?
The same fork one level up. **Chosen: the number of trials needed to collect r
successes**, support {r, r+1, ...}, so ``mean = r/p`` and the Geometric is the
case ``r = 1``. Cost: ``pmf`` is ``C(k-1, r-1) p**r (1-p)**(k-r)``, and ``k-1``
is an easy place to lose an off-by-one.

DESIGN DECISION -- variance from the definition, or from the moments?
The definition is ``E[(X - E X)**2]``; the computational form is
``E[X**2] - (E[X])**2``. **Chosen: a ``variance_from_moments(mean, second)``
helper**, because it forces the second moment to be supplied explicitly and
makes the classic error -- squaring the wrong term, ``(E[X**2] - E[X])**2`` --
a one-line mutation the checker must catch. Cost: an extra function and the
risk of catastrophic cancellation, which is why the caller keeps exact
``Fraction`` moments and only converts at the end.

DESIGN DECISION -- must linearity of expectation use independence?
No: ``E[X + Y] = E[X] + E[Y]`` for *any* two random variables, dependent or
not, because expectation is a sum over the joint sample space. **Chosen: the
fixed points of a uniformly random permutation** as the limit case. The
indicators ``I_i`` ("position i is fixed") are strongly dependent -- a
permutation cannot have exactly one fixed point when n >= 2 -- yet the
expectation of their sum is ``n * (1/n) = 1``. The dependence shows up in the
*variance*, where the covariance terms must not be dropped: the
independence-only value ``(n-1)/n`` is wrong. This is the module's limit case.

DESIGN DECISION -- what does a simulation return?
The sibling module returned a probability ``Fraction(wins, trials)``. Here the
quantity is a mean and a variance, so the checker needs more than one summary.
**Chosen: each simulation returns its list of raw integer draws.** From one
list the checker computes the sample mean, the sample variance, and the
standard error of the variance itself (via the sample fourth central moment).
Cost: 10**5 small ints per run, which is nothing next to the clarity.

DESIGN DECISION -- how to measure the Poisson approximation to the Binomial?
Pointwise comparison at one k would be a weak test. **Chosen: the total
variation distance** ``0.5 * sum_k |Bin(n,p)(k) - Pois(np)(k)|``, which is the
right global error and, by Le Cam's bound, is ``O(np**2) = O(lambda p)``. The
checker holds ``lambda = n p`` fixed and requires the distance to fall sharply
as ``p`` shrinks -- the "shrinks as predicted" clause of the node.

    python3 random_variables.py      # prints the measurements this file promises
"""

from collections import Counter
from fractions import Fraction
import math
import random


# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------

def variance_from_moments(mean, second_moment):
    """The computational variance: ``E[X**2] - (E[X])**2``.

    ``second_moment`` is ``E[X**2]``. The square belongs on the mean alone:
    ``(second_moment - mean) ** 2`` is a different, wrong expression that
    collapses to 0 whenever the mean equals the second moment (e.g. Bernoulli).
    """
    return second_moment - mean ** 2


def summarize(draws):
    """Sample mean and sample variance of a list of draws, as exact Fractions.

    Returns ``(mean, variance)`` with ``variance = E[X**2] - (E[X])**2``
    computed from the same ``variance_from_moments`` helper, so a misplaced
    square is caught on simulated data too.
    """
    n = len(draws)
    if n == 0:
        raise ValueError("no draws to summarize")
    mean = Fraction(sum(draws), n)
    second = Fraction(sum(x * x for x in draws), n)
    return mean, variance_from_moments(mean, second)


def cdf_from_pmf(pmf, k):
    """CDF of a distribution whose support begins at 0 or later: add ``pmf(j)``.

    Safe for the Geometric and Negative Binomial because their ``pmf`` returns
    ``0`` below the support. Only ``j`` in ``0..k`` are visited; a negative
    ``k`` returns ``0``.
    """
    if k < 0:
        return Fraction(0)
    return sum((pmf(j) for j in range(k + 1)), Fraction(0))


# ---------------------------------------------------------------------------
# Bernoulli (chapter 3)
# ---------------------------------------------------------------------------

def bernoulli_pmf(p, k):
    """P(X = k) for X ~ Bernoulli(p): ``1 - p`` at 0, ``p`` at 1, else 0."""
    p = Fraction(p)
    if k == 0:
        return 1 - p
    if k == 1:
        return p
    return Fraction(0)


def bernoulli_cdf(p, k):
    """P(X <= k) for X ~ Bernoulli(p)."""
    p = Fraction(p)
    if k < 0:
        return Fraction(0)
    if k < 1:
        return 1 - p
    return Fraction(1)


def bernoulli_mean(p):
    """E[X] = p."""
    return Fraction(p)


def bernoulli_variance(p):
    """Var(X) = p(1-p), from the moments (X**2 = X for an indicator)."""
    p = Fraction(p)
    return variance_from_moments(bernoulli_mean(p), p)


# ---------------------------------------------------------------------------
# Binomial (chapter 3)
# ---------------------------------------------------------------------------

def binomial_pmf(n, p, k):
    """P(X = k) for X ~ Binomial(n, p): ``C(n,k) p**k (1-p)**(n-k)``.

    Counting is the prerequisite node, so ``math.comb`` supplies C(n, k); the
    support is ``0 <= k <= n``.
    """
    if not 0 <= k <= n:
        return Fraction(0)
    p = Fraction(p)
    q = 1 - p
    return Fraction(math.comb(n, k)) * p ** k * q ** (n - k)


def binomial_cdf(n, p, k):
    """P(X <= k) = sum_{j=0..k} PMF(j)."""
    return cdf_from_pmf(lambda j: binomial_pmf(n, p, j), k)


def binomial_mean(n, p):
    """E[X] = n p."""
    return n * Fraction(p)


def binomial_variance(n, p):
    """Var(X) = n p (1-p)."""
    p = Fraction(p)
    return n * p * (1 - p)


# ---------------------------------------------------------------------------
# Geometric (chapter 3) -- number of trials to the first success
# ---------------------------------------------------------------------------

def geometric_pmf(p, k):
    """P(X = k) = ``(1-p)**(k-1) p`` for k >= 1 (trials until first success).

    Support starts at 1: ``pmf(1) = p``. A support starting at 0 (the number of
    failures before the first success) is the classic off-by-one and gives
    ``(1-p)**k p``.
    """
    p = Fraction(p)
    if k < 1:
        return Fraction(0)
    return (1 - p) ** (k - 1) * p


def geometric_cdf(p, k):
    """P(X <= k) = ``1 - (1-p)**k`` for k >= 1, else 0."""
    p = Fraction(p)
    if k < 1:
        return Fraction(0)
    return 1 - (1 - p) ** k


def geometric_mean(p):
    """E[X] = 1/p."""
    return Fraction(1, 1) / Fraction(p)


def geometric_variance(p):
    """Var(X) = (1-p)/p**2."""
    p = Fraction(p)
    return (1 - p) / p ** 2


# ---------------------------------------------------------------------------
# Negative Binomial (chapter 3) -- trials to collect r successes
# ---------------------------------------------------------------------------

def negative_binomial_pmf(r, p, k):
    """P(X = k) = ``C(k-1, r-1) p**r (1-p)**(k-r)`` for k >= r.

    ``X`` is the number of trials needed to collect ``r`` successes, so the
    last trial is a success and the first ``k-1`` hold ``r-1`` successes.
    Returns 0 for k < r. The Geometric is ``r = 1``.
    """
    if k < r:
        return Fraction(0)
    p = Fraction(p)
    q = 1 - p
    return Fraction(math.comb(k - 1, r - 1)) * p ** r * q ** (k - r)


def negative_binomial_cdf(r, p, k):
    """P(X <= k) = sum_{j=r..k} PMF(j)."""
    return cdf_from_pmf(lambda j: negative_binomial_pmf(r, p, j), k)


def negative_binomial_mean(r, p):
    """E[X] = r/p."""
    return Fraction(r, 1) / Fraction(p)


def negative_binomial_variance(r, p):
    """Var(X) = r(1-p)/p**2."""
    p = Fraction(p)
    return Fraction(r, 1) * (1 - p) / p ** 2


# ---------------------------------------------------------------------------
# Poisson (chapter 3) -- irrational mass, computed in float
# ---------------------------------------------------------------------------

def poisson_pmf(lam, k):
    """P(X = k) = ``e**(-lam) lam**k / k!`` for k >= 0, else 0.

    ``lambda`` may be a Fraction; the mass is evaluated in float because
    ``e**(-lambda)`` is irrational.
    """
    if k < 0:
        return 0.0
    lam = float(lam)
    # Build the term by recurrence instead of lam**k / k! so that a large k
    # (the Poisson tail past n) cannot overflow the factorial conversion.
    term = math.exp(-lam)
    for i in range(1, k + 1):
        term *= lam / i
    return term


def poisson_cdf(lam, k):
    """P(X <= k) = sum_{j=0..k} PMF(j)."""
    if k < 0:
        return 0.0
    return sum(poisson_pmf(lam, j) for j in range(k + 1))


def poisson_mean(lam):
    """E[X] = lambda."""
    return float(lam)


def poisson_variance(lam):
    """Var(X) = lambda."""
    return float(lam)


# ---------------------------------------------------------------------------
# The Poisson approximation to the Binomial (chapter 4 reach; limit case)
# ---------------------------------------------------------------------------

def binomial_poisson_tv_distance(n, p):
    """Total variation distance between Binomial(n, p) and Poisson(n p).

    ``0.5 * sum_{k>=0} |Bin(n,p)(k) - Pois(np)(k)|``. Both masses are summed
    over the whole line: the Binomial vanishes past ``n``, so the Poisson tail
    past ``n`` is added explicitly. By Le Cam's bound this is O(n p**2), i.e.
    O(lambda p) for fixed ``lambda = n p``, so it must shrink like ``p``.
    """
    p = float(p)
    lam = n * p
    total = 0.0
    for k in range(0, n + 1):
        total += abs(float(binomial_pmf(n, p, k)) - poisson_pmf(lam, k))
    k = n + 1
    while True:
        term = poisson_pmf(lam, k)
        total += term
        if term < 1e-18 or k > n + 1000:
            break
        k += 1
    return 0.5 * total


# ---------------------------------------------------------------------------
# Linearity of expectation with dependent indicators (chapter 4, limit case)
# ---------------------------------------------------------------------------

def expected_fixed_points(n):
    """E[# fixed points of a uniformly random permutation of n elements].

    By linearity, ``sum_i E[I_i]`` where ``I_i`` marks position i fixed. Each
    ``E[I_i] = 1/n`` because position i holds one of the n values uniformly and
    exactly one of them is i. The indicators are dependent (a permutation with
    n >= 2 cannot have exactly n-1 fixed points), but linearity never cared:
    the answer is 1 for every n >= 1, and 0 for n = 0.
    """
    if n <= 0:
        return Fraction(0)
    return sum((Fraction(1, n) for _ in range(n)), Fraction(0))


def fixed_points_variance(n):
    """Var(# fixed points) = 1 for n >= 2, 0 otherwise.

    The dependence is the whole point. ``Var(sum I_i)`` is not the sum of the
    variances; it adds ``2 sum_{i<j} Cov(I_i, I_j)``. Here
    ``P(I_i) = 1/n``, ``P(I_i I_j) = 1/(n(n-1))``, so each covariance is
    ``1/(n(n-1)) - 1/n**2`` and the two terms collapse to exactly 1. Dropping
    the covariance sum -- computing the variance *as if* the indicators were
    independent -- gives ``(n-1)/n``, which the checker rejects.
    """
    if n <= 1:
        return Fraction(0)
    independent_part = sum(
        (Fraction(1, n) * (1 - Fraction(1, n)) for _ in range(n)), Fraction(0))
    covariance = n * (n - 1) * (
        Fraction(1, n * (n - 1)) - Fraction(1, n) * Fraction(1, n))
    return independent_part + covariance


# ---------------------------------------------------------------------------
# Simulations: one seeded generator per call, raw draws returned
# ---------------------------------------------------------------------------

def simulate_bernoulli(p, trials, seed=0):
    """Return ``trials`` draws of Bernoulli(p) as a list of 0/1."""
    rng = random.Random(seed)
    p = float(p)
    return [1 if rng.random() < p else 0 for _ in range(trials)]


def simulate_binomial(n, p, trials, seed=0):
    """Return ``trials`` draws of Binomial(n, p) as a list of counts.

    Each draw counts successes in n independent Bernoulli(p) flips.
    """
    rng = random.Random(seed)
    p = float(p)
    return [sum(1 for _ in range(n) if rng.random() < p) for _ in range(trials)]


def simulate_geometric(p, trials, seed=0):
    """Return ``trials`` draws of Geometric(p) counting trials to first success."""
    rng = random.Random(seed)
    p = float(p)
    draws = []
    for _ in range(trials):
        trials_used = 1
        while rng.random() >= p:
            trials_used += 1
        draws.append(trials_used)
    return draws


def simulate_negative_binomial(r, p, trials, seed=0):
    """Return ``trials`` draws of the trials needed to collect ``r`` successes."""
    rng = random.Random(seed)
    p = float(p)
    draws = []
    for _ in range(trials):
        successes = 0
        trials_used = 0
        while successes < r:
            trials_used += 1
            if rng.random() < p:
                successes += 1
        draws.append(trials_used)
    return draws


def simulate_poisson(lam, trials, seed=0):
    """Return ``trials`` draws of Poisson(lambda).

    Uses Knuth's product method: multiply ``Uniform(0,1)`` factors until the
    running product drops below ``e**(-lambda)``; the number of factors is the
    draw. Fine for the modest ``lambda`` used here.
    """
    rng = random.Random(seed)
    lam = float(lam)
    target = math.exp(-lam)
    draws = []
    for _ in range(trials):
        product = 1.0
        count = 0
        while True:
            product *= rng.random()
            if product <= target:
                break
            count += 1
        draws.append(count)
    return draws


def simulate_fixed_points(n, trials, seed=0):
    """Return ``trials`` counts of fixed points of random permutations of n.

    ``rng.shuffle`` gives a uniform permutation; count positions ``i`` with
    ``perm[i] == i``. The draws are the sums of the dependent indicators whose
    expectation ``expected_fixed_points`` computes by linearity.
    """
    rng = random.Random(seed)
    draws = []
    for _ in range(trials):
        perm = list(range(n))
        rng.shuffle(perm)
        draws.append(sum(1 for i in range(n) if perm[i] == i))
    return draws


if __name__ == "__main__":
    import math as _math

    TRIALS = 100_000

    def report(name, exact_mean, exact_var, draws):
        mean, var = summarize(draws)
        n = len(draws)
        mean_se = _math.sqrt(float(exact_var) / n)
        centre = sum(draws) / n
        m4 = sum((x - centre) ** 4 for x in draws) / n
        var_se = _math.sqrt(max(m4 - (sum((x - centre) ** 2 for x in draws) / n) ** 2, 0.0) / n)
        flag = ""
        if abs(float(exact_mean) - float(mean)) > 4 * mean_se:
            flag += "  MEAN OUTSIDE 4SE"
        if abs(float(exact_var) - float(var)) > 4 * var_se + 1e-9:
            flag += "  VAR OUTSIDE 4SE"
        print(f"  {name:<22} mean {float(exact_mean):8.4f} sim {float(mean):8.4f}"
              f"   var {float(exact_var):8.4f} sim {float(var):8.4f}{flag}")

    print("Random variables from scratch — exact vs 10^5-trial simulation")
    p = Fraction(1, 2)
    report("Bernoulli(1/2)", bernoulli_mean(p), bernoulli_variance(p),
           simulate_bernoulli(p, TRIALS, seed=1))
    report("Binomial(20,1/2)", binomial_mean(20, p), binomial_variance(20, p),
           simulate_binomial(20, p, TRIALS, seed=2))
    p3 = Fraction(1, 3)
    report("Geometric(1/3)", geometric_mean(p3), geometric_variance(p3),
           simulate_geometric(p3, TRIALS, seed=3))
    report("NegBinom(4,1/3)", negative_binomial_mean(4, p3),
           negative_binomial_variance(4, p3),
           simulate_negative_binomial(4, p3, TRIALS, seed=4))
    report("Poisson(3)", poisson_mean(3), poisson_variance(3),
           simulate_poisson(3, TRIALS, seed=5))

    print("  line-up: fixed points of a random permutation (dependent indicators)")
    for n in (2, 5, 50):
        exact_mean, exact_var = expected_fixed_points(n), fixed_points_variance(n)
        draws = simulate_fixed_points(n, TRIALS, seed=6)
        report(f"n = {n}", exact_mean, exact_var, draws)
    p5 = Fraction(1, 5)
    print(f"  the independence-only variance would be (n-1)/n = "
          f"{float((1 - Fraction(1, 5))):.4f}; the truth is "
          f"{float(fixed_points_variance(5)):.4f}")

    print("  Poisson approximation to Binomial, total variation distance (n p = 1)")
    for n in (10, 100, 1000):
        print(f"    n = {n:>4}, p = {1 / n:.4f}   TV = "
              f"{binomial_poisson_tv_distance(n, Fraction(1, n)):.6f}")
