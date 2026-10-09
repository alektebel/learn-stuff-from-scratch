"""Limits and inequalities from scratch: change of variables, convolutions, the
Markov / Chebyshev / Chernoff bounds against exact tails, and the law of large
numbers and central limit theorem by simulation.

Implements themes from Blitzstein & Hwang, *Introduction to Probability*
(2nd ed.): change of variables and convolutions (chapter 8) and the limit
theorems and inequalities (chapter 10). The arguments are restated here, never
copied.

The node turns on two quantitative facts that simulation can exhibit:

* a bound is only a bound if it sits *above* the tail it estimates, point by
  point -- Markov is simple, Chebyshev sharper, Chernoff sharper still on the
  deviations where its minimum is found; and
* the central limit theorem converges at the Berry-Esseen rate, so the
  Kolmogorov-Smirnov distance between the standardised sample mean and the
  standard normal falls like ``1/sqrt(n)``.

The limit case is the Cauchy distribution: its mean is undefined, the sample
mean does not converge, and the finite-variance ``1/sqrt(n)`` shrinkage of the
sample-mean spread is absent because the mean of ``n`` i.i.d. Cauchy draws is
again Cauchy, with the same scale.

    python3 limits.py      # prints the measurements this file promises
"""

import math
import random
from fractions import Fraction
from math import comb


# ---------------------------------------------------------------------------
# Change of variables and convolution
# ---------------------------------------------------------------------------

def change_of_variables(y, g_inv, g_prime_inv, fy):
    """Density of Y = g(X) at ``y``, for a strictly monotone g.

    ``g_inv(y)`` returns the unique x with g(x) = y, ``g_prime_inv(y)`` returns
    g'(x) at that x, and ``fy`` is the density of X. Then

        f_Y(y) = f_X(g^{-1}(y)) / |g'(g^{-1}(y))|.

    DESIGN DECISION -- take g^{-1} and g' as callables instead of a symbolic g?
    Symbolic differentiation and inversion would need a computer-algebra layer
    to handle even x^2, and a numeric derivative would add its own error to the
    test. Passing the two pieces keeps the formula as the closed form the node
    asks for and lets the caller use the exact inverse. The cost is that the
    caller must supply the inverse and its derivative and is responsible for the
    monotonicity on the support; the function cannot check that. The ``abs`` is
    the point of the exercise: for a decreasing map |g'| enters, and dropping it
    flips the sign of a positive density.
    """
    # TODO: f_Y(y) = f_X(g^{-1}(y)) / |g'(g^{-1}(y))|. Call g_inv(y) once to get x, then divide fy(x) by abs(g_prime_inv(y)). Do NOT drop the 1/|g'| Jacobian factor, and keep the abs: a decreasing map gives a negative density without it.
    raise NotImplementedError("change_of_variables")


def convolution(p, q):
    """pmf of the sum of two independent integer-valued variables.

    ``p`` and ``q`` are sequences with ``p[i] = P(X = i)`` and ``q[j] =
    P(Y = j)``, starting at value 0. The result ``r`` has length
    ``len(p) + len(q) - 1`` and ``r[k] = sum_i p[i] q[k - i]``, the pmf of
    X + Y.

    DESIGN DECISION -- sequences indexed by value from 0, not dicts on arbitrary
    integer support?
    A dict handles negatives and gaps, but every pmf the node needs (dice,
    binomial, Poisson) starts at 0 with no gaps, and a list makes the
    convolution index arithmetic plain. Arithmetic is container-agnostic:
    ``p[i] * q[j]`` works for floats and exact ``Fraction``s alike, and the
    accumulator starts at the integer 0, which promotes to whatever the
    products are, so exactness is preserved when the inputs are exact. The cost
    is a shifted index for the dice case, which the caller handles.
    """
    # TODO: Return a list of length len(p) + len(q) - 1 with out[k] = sum_i p[i] * q[k - i]. This is the pmf of X + Y; it is NOT the elementwise product p[k] * q[k]. Products of Fractions stay exact.
    raise NotImplementedError("convolution")


# ---------------------------------------------------------------------------
# The three bounds
# ---------------------------------------------------------------------------

def markov_bound(mean, t):
    """Markov's inequality: P(X >= t) <= E[X] / t for X >= 0.

    Returns ``min(1, mean / t)``; the cap only makes explicit the trivial bound
    when t is below the mean. A non-positive t returns 1.0, also trivial.

    DESIGN DECISION -- cap at 1, or return the raw ratio?
    ``E[X]/t`` can exceed 1 for t < E[X], and a probability bound above 1 is
    still valid (every probability is <= 1) but useless and confusing. Capping
    costs nothing and keeps the comparison with Chernoff meaningful. The cost is
    that for t below the mean the bound is flat at 1, so a caller cannot see the
    ratio; this node always tests t above the mean.
    """
    # TODO: Return min(1.0, mean / t) for t > 0 (1.0 for t <= 0). Markov says P(X >= t) <= E[X]/t for X >= 0. Do NOT return the exact tail: a bound at the tail is not a bound above it.
    raise NotImplementedError("markov_bound")


def chebyshev_bound(var, t):
    """Chebyshev's inequality: P(|X - E[X]| >= t) <= Var(X) / t^2.

    Returns ``min(1, var / t^2)``. This bounds a *two-sided* deviation, so it
    also upper-bounds the one-sided tail P(X >= E[X] + t) that the node tests;
    it is usually looser than Chernoff because it throws away the shape of the
    distribution and uses only its variance.

    DESIGN DECISION -- no mean argument?
    Chebyshev's right-hand side is translation invariant: shifting X does not
    change Var or the width t, so the mean is irrelevant to the bound. Asking
    for it would invite the classic error of writing Var/(X - t)^2. The cost is
    that the caller must form the deviation t = threshold - mean itself; the
    checker documents that.
    """
    # TODO: Return min(1.0, var / t**2) for t > 0 (1.0 for t <= 0). The deviation t is one-sided already supplied by the caller; the bound depends only on the variance.
    raise NotImplementedError("chebyshev_bound")


def chernoff_bound(mgf_value, t):
    """Chernoff's bound: P(X >= t) <= inf_{s>0} exp(-s t) M(s).

    ``mgf_value`` is a callable returning the moment-generating function
    ``M(s) = E[exp(s X)]`` at ``s``. The infimum is approximated by the minimum
    over a fixed geometric grid of s in (0, 50), which always contains 0 in its
    closure so the trivial value 1.0 is available.

    DESIGN DECISION -- minimise on a grid instead of solving d/ds = 0?
    The optimum s* solves ``M'(s)/M(s) = t``, which for a general mgf is a
    transcendental equation; for the binomial it has a closed form, but coding
    one per distribution defeats the purpose of a *generic* Chernoff bound. A
    geometric grid (ratio 1.05, from 1e-6 to 50) is distribution-free, and its
    minimum is always an upper bound because it is the exponential tilted
    probability at a particular s. The cost is that the grid minimum can exceed
    the true infimum by a small factor; the checker only demands that the result
    is *above* the exact tail and *tighter* than Markov, which the grid
    satisfies with room to spare. An ``OverflowError`` from an mgf at large s is
    swallowed (that s is treated as infinity): the tilted factor ``exp(-s t)``
    can only make large-s candidates worse, so the infimum is not there.
    """
    # TODO: Minimise exp(-s * t) * mgf_value(s) over a geometric grid of s > 0 (start at 1e-6, multiply by 1.05 up to 50) and cap the result at 1.0. mgf_value is a callable M(s); treat an OverflowError from it as an infinite candidate.
    raise NotImplementedError("chernoff_bound")


# ---------------------------------------------------------------------------
# Exact tails
# ---------------------------------------------------------------------------

def exact_tail_bernoulli(n, p, k):
    """P(Binomial(n, p) >= k), exactly, as a ``Fraction``.

    The tail is ``sum_{i=k}^{n} C(n, i) p^i (1 - p)^{n-i}``. ``p`` may be a
    ``Fraction`` or a float; a float is converted exactly to its binary
    rational, so the result is the exact tail of that rational parameter.

    DESIGN DECISION -- exact ``Fraction`` rather than a float sum?
    The node's acceptance rule is that every bound is above the exact tail. If
    the tail itself were rounded to a float, a bound could appear to beat the
    truth because the truth was rounded down, especially in the far tail where
    the terms are tiny. Exact rationals remove that artefact; the comparison is
    then genuinely about the inequalities. The cost is large-denominator
    arithmetic, fine at the n the node uses.
    """
    # TODO: sum_{i=k}^{n} C(n, i) p^i (1-p)^{n-i} as a Fraction: convert p with Fraction(p), q = 1 - p, and accumulate comb(n, i) * p**i * q**(n-i). Handle k <= 0 (return 1) and k > n (return 0).
    raise NotImplementedError("exact_tail_bernoulli")


def exact_tail_exponential(rate, t):
    """P(Exponential(rate) >= t) = exp(-rate t).

    The exponential is the continuous workhorse of the bound checks: its mgf is
    ``rate / (rate - s)`` for s < rate, so Chernoff and Markov can both be
    evaluated against this exact tail. A non-positive t returns 1.0.

    DESIGN DECISION -- a continuous tail beside the discrete one?
    The binomial gives an exact rational tail and needs no floating point; the
    exponential gives a continuous exact tail and lets the same three bounds be
    tested in the continuous setting. Keeping both exercises the bound code on
    two different mgfs without adding distributions the node does not name.
    """
    # TODO: P(Exp(rate) >= t) = exp(-rate * t); return 1.0 for t <= 0.
    raise NotImplementedError("exact_tail_exponential")


# ---------------------------------------------------------------------------
# Simulation: law of large numbers and central limit theorem
# ---------------------------------------------------------------------------

def lln_sample_means(dist, n, trials, rng):
    """Running sample means of ``dist``, averaged over ``trials`` replications.

    ``dist(rng)`` draws one observation. For each of ``trials`` independent
    replications draw n observations and record the running mean after
    m = 1..n draws; average those running means across the replications. The
    returned list has length n and its late entries approach E[X] as m grows,
    which is the law of large numbers.

    DESIGN DECISION -- average the running means across replications instead of
    showing one path?
    A single path's running mean is itself random and, at small m, noisy enough
    that "convergence" is hard to see or check. Averaging R independent paths
    keeps the running-mean curve but divides its variance by R, so the curve
    visibly flattens on E[X] and the checker can use a tight tolerance. The cost
    is ``n * trials`` draws rather than n, and the curve is no longer a single
    realisation -- the point here is the trend, not one path.
    """
    # TODO: For each of trials replications, draw n observations and keep a running total; add the running mean after each draw to a per-m accumulator, then divide each accumulator by trials. Return the n averaged running means; late entries approach E[X].
    raise NotImplementedError("lln_sample_means")


def _standard_normal_cdf(z):
    """Standard normal CDF ``Phi(z)`` via the error function."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def clt_error(dist, n, trials, rng):
    """Kolmogorov-Smirnov distance from the standardised sample mean to N(0, 1).

    Draws ``trials`` sample means, each the mean of n i.i.d. draws from
    ``dist``; estimates the mean and standard deviation from all draws;
    standardises each sample mean with ``(mean - mu) / (sigma / sqrt(n))``; and
    returns ``sup_z |F_emp(z) - Phi(z)|`` over the ordered standardised values.

    DESIGN DECISION -- estimate mu and sigma from the pooled draws instead of
    taking them as arguments?
    Requiring (mu, sigma) would make the function specific to distributions
    whose parameters the caller can name, and would complicate the ``dist``
    protocol (a bare callable). Estimating them from the ``trials * n`` draws is
    the plug-in route; it removes a location and a scale shift and leaves the
    Berry-Esseen decay intact. The cost is a floor of order ``1/sqrt(trials)``
    from the empirical CDF itself, which is why ``trials`` is large and the
    check compares the ratio between n and 4n rather than an absolute constant.
    Dividing by the standard deviation ``sigma`` (the standard error
    ``sigma / sqrt(n)``) is essential: dividing by the variance gives a different
    scale entirely.
    """
    # TODO: Draw trials sample means of n draws each, also collecting all draws. Estimate mu and sigma from the pooled draws, set se = sigma / sqrt(n) (standard error: divide by the standard deviation, NOT the variance), standardise each sample mean as (m - mu)/se, sort, and return the sup of |empirical CDF - Phi(z)| over the ordered values (compare both i/trials and (i+1)/trials at each jump).
    raise NotImplementedError("clt_error")


def cauchy_sample_means(n, trials, rng):
    """Sample means of ``trials`` independent Cauchy samples of size n.

    The standard Cauchy is drawn by the inverse-CDF transform
    ``tan(pi (u - 1/2))`` for uniform u. The returned list holds one mean per
    replication. This is the limit case of the node: the Cauchy mean does not
    exist, and the mean of n i.i.d. Cauchy draws is again Cauchy with the same
    scale, so the spread of these means does not shrink with n.

    DESIGN DECISION -- inverse CDF, not a ratio of normals?
    A standard Cauchy is the ratio of two independent standard normals, which
    would need the Box-Muller pair used in the previous node; the inverse CDF is
    one ``tan`` and one uniform, reuses the same uniform stream as every other
    sampler here, and makes the heavy tails explicit. The cost is that
    ``rng.random()`` can be arbitrarily close to 0 or 1 and ``tan`` then returns
    a very large magnitude -- which is exactly the heavy tail the limit case
    needs, not an error.
    """
    # TODO: For each of trials replications draw n standard Cauchy values by tan(pi * (rng.random() - 0.5)), average them, and return the list of means. The heavy tails are the point: the mean of n Cauchy draws is again Cauchy, so these means do not concentrate.
    raise NotImplementedError("cauchy_sample_means")


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo():
    print("Limits and inequalities from scratch")

    # Change of variables: X ~ Exp(1), Y = X^2.
    g_inv = math.sqrt
    g_prime_inv = lambda y: 2.0 * math.sqrt(y)
    fy = lambda x: math.exp(-x) if x >= 0.0 else 0.0
    print("  change of variables: X ~ Exp(1), Y = X^2")
    for y in (0.25, 1.0, 4.0):
        got = change_of_variables(y, g_inv, g_prime_inv, fy)
        ref = math.exp(-math.sqrt(y)) / (2.0 * math.sqrt(y))
        print(f"    y = {y:>5.2f}   f_Y = {got:.8f}   analytic = {ref:.8f}")

    # Convolution of two fair dice, exactly.
    die = [Fraction(0)] + [Fraction(1, 6)] * 6
    total = convolution(die, die)
    print("  convolution of two dice: P(sum = k)")
    for k in (2, 4, 7, 10, 12):
        print(f"    k = {k:>2}   P = {float(total[k]):.6f}   ({total[k]})")

    # Bounds against the exact binomial tail.
    n, p = 100, Fraction(3, 10)
    mgf = lambda s: (1.0 - float(p) + float(p) * math.exp(s)) ** n
    print(f"  bounds at Binomial({n}, 3/10)")
    for k in (40, 45, 50):
        exact = exact_tail_bernoulli(n, p, k)
        mean = n * float(p)
        var = n * float(p) * (1.0 - float(p))
        m = markov_bound(mean, float(k))
        c = chebyshev_bound(var, float(k) - mean)
        ch = chernoff_bound(mgf, float(k))
        print(f"    k = {k:>2}   exact = {float(exact):.3e}   "
              f"Markov = {m:.4f}   Chebyshev = {c:.4f}   Chernoff = {ch:.4e}")

    print(f"  exact_tail_exponential(2, 3) = {exact_tail_exponential(2.0, 3.0):.6f}"
          f"   (e^-6 = {math.exp(-6.0):.6f})")

    # Law of large numbers: running mean of U(0, 1).
    rng = random.Random(20240607)
    uniform = lambda r: r.random()
    running = lln_sample_means(uniform, 400, 2000, rng)
    print("  law of large numbers: running mean of U(0, 1) -> 0.5")
    for m in (1, 5, 20, 100, 400):
        print(f"    m = {m:>4}   running mean = {running[m - 1]:.5f}")

    # Central limit theorem: the KS error decays like 1/sqrt(n). An
    # exponential(2) has nonzero skewness, so the finite-n distance is large
    # enough to see above the empirical jitter.
    exponential_two = lambda r: -math.log(1.0 - r.random()) / 2.0
    print("  central limit theorem: KS distance of the standardised mean to N(0, 1)")
    previous = None
    for n in (25, 100, 400):
        rng = random.Random(1000 + n)
        err = clt_error(exponential_two, n, 60000, rng)
        ratio = "" if previous is None else f"   x{previous / err:.2f}"
        print(f"    n = {n:>4}   error = {err:.5f}{ratio}")
        previous = err

    # Limit case: the Cauchy sample mean does not concentrate.
    print("  limit case: spread of the sample mean, n -> 4n")
    rng = random.Random(7)
    cauchy_small = cauchy_sample_means(4, 20000, rng)
    cauchy_large = cauchy_sample_means(16, 20000, rng)
    expo = lambda r: -math.log(1.0 - r.random())
    print(f"    Cauchy IQR   n=4  = {_iqr(cauchy_small):.4f}   "
          f"n=16 = {_iqr(cauchy_large):.4f}   (does not shrink)")
    expo_small = _sample_means(expo, 4, 20000, rng)
    expo_large = _sample_means(expo, 16, 20000, rng)
    print(f"    Exp(1) IQR   n=4  = {_iqr(expo_small):.4f}   "
          f"n=16 = {_iqr(expo_large):.4f}   (shrinks by ~2)")


def _iqr(values):
    """Interquartile range of ``values``, by linear interpolation."""
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


def _sample_means(dist, n, trials, rng):
    """Sample means of ``trials`` samples of size n -- demo helper only."""
    means = []
    for _ in range(trials):
        total = 0.0
        for _ in range(n):
            total += dist(rng)
        means.append(total / n)
    return means


if __name__ == "__main__":
    demo()
