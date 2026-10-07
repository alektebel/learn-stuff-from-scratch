"""Joint distributions from scratch: joint, marginal and conditional pmfs,
covariance and correlation, the multinomial distribution, the bivariate normal,
and the split between correlation and dependence.

Implements chapter 7 of Blitzstein & Hwang, *Introduction to Probability*
(2nd ed.): joint, marginal and conditional distributions, covariance and
correlation, and the named joint distributions (multinomial, bivariate normal).
The argument is restated here, never copied.

The node's acceptance criterion is statistical: sample covariance matrices must
converge to the analytic covariance. The limit case is the one that breaks the
common reading of that criterion: **uncorrelated does not mean independent**.
Take X symmetric with Y = X^2; then Cov(X, Y) = 0 by symmetry, but Y is a
deterministic function of X, so the conditional of Y given X is a point mass,
not the marginal of Y. Correlation zero is therefore not evidence of
independence, and the checker decides dependence from the conditionals.

    python3 joint.py      # prints the measurements this file promises
"""

import math
import random

_TWO_PI = 2.0 * math.pi


# ---------------------------------------------------------------------------
# Joint, marginal and conditional pmfs
# ---------------------------------------------------------------------------

def marginal(joint, axis):
    """Marginal pmf of a 2-D joint distribution along ``axis``.

    ``joint`` is either a dict mapping ``(x, y) -> p`` or a sequence of
    sequences with ``joint[i][j] = P(X = i, Y = j)``. ``axis`` names the
    coordinate to KEEP: 0 keeps the first coordinate (sum out the second), 1
    keeps the second (sum out the first).

    The dict form returns a dict keyed by the kept coordinate; the list form
    returns a list indexed by the kept coordinate.

    DESIGN DECISION -- axis means "keep", not "sum out", and the return type
    follows the input type?
    numpy's ``sum(axis=k)`` removes axis k; a marginal is the distribution of
    one coordinate, so this function keeps what it names, which is the reverse
    of numpy and therefore has to be documented. Keeping the input's container
    (dict of pairs in, dict out; matrix in, list out) means the caller never has
    to know the axes' labels, only their positions -- a joint pmf over strings
    has no natural integer index. The cost is two code paths, one per container.
    """
    if axis not in (0, 1):
        raise ValueError("axis must be 0 (keep X) or 1 (keep Y)")
    if isinstance(joint, dict):
        out = {}
        for (x, y), p in joint.items():
            key = x if axis == 0 else y
            out[key] = out.get(key, 0.0) + float(p)
        return out
    rows = len(joint)
    if rows == 0:
        return []
    cols = len(joint[0])
    if axis == 0:
        return [sum(float(joint[i][j]) for j in range(cols)) for i in range(rows)]
    return [sum(float(joint[i][j]) for i in range(rows)) for j in range(cols)]


def conditional(joint, given):
    """Conditional pmf of Y given X = ``given``: P(Y = y | X = given).

    A row of the joint, normalised by the marginal probability of the
    conditioning event. The dict form returns ``{y: P(Y = y | X = given)}``;
    the list form returns the normalised row as a list. Conditioning on a value
    of X is the choice here (the node asks for P(Y | X = x)); conditioning the
    other way is the same code with the axes swapped.

    DESIGN DECISION -- normalise by the marginal P(X = given), not by the row
    count or by 1?
    The denominator is the probability of the conditioning event,
    P(X = x) = sum_y P(X = x, Y = y). Dividing by the number of outcomes makes
    the row's entries average to 1 instead of summing to 1; dividing by 1
    leaves them as the joint, which sums to P(X = x), not 1. Both are the
    classic error and both are caught by the sum-to-one check.
    """
    if isinstance(joint, dict):
        rows = {}
        for (x, y), p in joint.items():
            rows.setdefault(x, {})[y] = float(p)
        if given not in rows:
            raise KeyError(f"no outcomes with X = {given!r}")
        total = sum(rows[given].values())
        if total <= 0.0:
            raise ValueError("the conditioning event has probability zero")
        return {y: p / total for y, p in rows[given].items()}
    row = [float(v) for v in joint[given]]
    total = sum(row)
    if total <= 0.0:
        raise ValueError("the conditioning event has probability zero")
    return [v / total for v in row]


# ---------------------------------------------------------------------------
# Covariance and correlation
# ---------------------------------------------------------------------------

def covariance(xs, ys):
    """Population covariance of paired data: (1/n) sum (x - mean_x)(y - mean_y).

    DESIGN DECISION -- population 1/n here, and a separate ``sample_covariance``
    at 1/(n-1)?
    Covariance of a distribution is defined with expected values, E[(X-EX)(Y-EY)];
    computing it from an equally weighted list of outcomes therefore uses 1/n.
    An i.i.d. sample is different: the unbiased estimator of the population
    covariance divides by n-1. Keeping the two as separate functions makes the
    division explicit at each call site instead of hiding the 1/n vs 1/(n-1)
    choice inside one function. The cost is two names for one idea; the payoff
    is that the convergence check can compare a 1/(n-1) estimate to an analytic
    population value without ambiguity.
    """
    n = len(xs)
    if n == 0 or len(ys) != n:
        raise ValueError("covariance needs two non-empty lists of equal length")
    mx = sum(xs) / n
    my = sum(ys) / n
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n


def correlation(xs, ys):
    """Pearson correlation: covariance divided by the two standard deviations.

    ``corr = Cov(X, Y) / (sd(X) sd(Y))``, with the population (1/n)
    conventions of ``covariance``. A perfect linear relationship gives +1 or
    -1. Zero variance is rejected: the correlation is undefined there, not 0.

    DESIGN DECISION -- normalise by sd(X) sd(Y), i.e. a product of square roots
    of the variances, rather than by the covariance's own scale?
    The whole point of the correlation is to be unit-free, so it must divide the
    covariance by sqrt(Cov(X,X)) sqrt(Cov(Y,Y)). Returning the raw covariance
    keeps the units and the magnitude, and is exactly the mutation the checker
    plants: it only looks like a correlation when the data happen to be
    standardised.
    """
    vx = covariance(xs, xs)
    vy = covariance(ys, ys)
    if vx <= 0.0 or vy <= 0.0:
        raise ValueError("correlation needs both variables to have positive variance")
    return covariance(xs, ys) / math.sqrt(vx * vy)


def sample_covariance(samples):
    """Unbiased 2x2 sample covariance matrix of a list of (x, y) pairs.

    Uses the 1/(n-1) denominator, the unbiased estimator of the population
    covariance for an i.i.d. sample. Returns ``[[var_x, cov_xy], [cov_xy,
    var_y]]``.

    DESIGN DECISION -- 1/(n-1), and say so, or 1/n to match ``covariance``?
    Matching ``covariance`` would make the estimator biased by a factor
    n/(n-1): at n = 3 that understates the variance by a third, and the
    convergence check only forgives it because 1/(n-1) -> 1/n as n grows. The
    node's acceptance rule compares sample covariance matrices to the ANALYTIC
    covariance, which is a population quantity; the honest estimator of it is
    the 1/(n-1) one, and the checker pins an exact small-n value so the 1/n
    slip cannot hide behind a large sample.
    """
    n = len(samples)
    if n < 2:
        raise ValueError("sample covariance needs at least two observations")
    xs = [float(s[0]) for s in samples]
    ys = [float(s[1]) for s in samples]
    mx = sum(xs) / n
    my = sum(ys) / n
    cxx = sum((x - mx) ** 2 for x in xs) / (n - 1)
    cyy = sum((y - my) ** 2 for y in ys) / (n - 1)
    cxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (n - 1)
    return [[cxx, cxy], [cxy, cyy]]


# ---------------------------------------------------------------------------
# Multinomial
# ---------------------------------------------------------------------------

def multinomial_pmf(counts, probs):
    """Multinomial pmf of one count vector: n! / prod c_i! * prod p_i^{c_i}.

    ``counts`` and ``probs`` are equal-length sequences; ``n = sum(counts)``.
    The multinomial coefficient is computed in exact Python integers before the
    final float product, so it does not overflow and stays exact for moderate n.

    DESIGN DECISION -- factorial ratio in exact integers, not lgamma in logs?
    ``math.lgamma`` never overflows, but it introduces rounding into the
    coefficient and needs ``exp`` to come back, so a small count vector would
    not sum to exactly 1. Exact integer factorials cost big-integer arithmetic
    but keep the pmf exact for a single vector, which is what the sum-to-one
    check wants. The cost is memory/time for huge n, which this node does not
    need.
    """
    counts = [int(c) for c in counts]
    probs = [float(p) for p in probs]
    if len(counts) != len(probs) or not counts:
        raise ValueError("counts and probs must have the same nonzero length")
    if any(c < 0 for c in counts):
        raise ValueError("counts must be non-negative")
    if any(p < 0.0 for p in probs):
        raise ValueError("probabilities must be non-negative")
    if abs(sum(probs) - 1.0) > 1e-9:
        raise ValueError("probabilities must sum to 1")
    n = sum(counts)
    coeff = math.factorial(n)
    for c in counts:
        coeff //= math.factorial(c)
    density = 1.0
    for c, p in zip(counts, probs):
        density *= p ** c
    return coeff * density


def multinomial_samples(n, trials, probs, rng):
    """Draw ``n`` count vectors, each from Multinomial(trials, probs).

    Each of the ``trials`` draws picks a category by walking the cumulative
    probabilities with one ``rng.random()``. Returns a list of ``n`` count
    lists, each summing to ``trials``.

    DESIGN DECISION -- walk the cumulative pmf per draw, not a sum of
    conditionally-binomial components?
    The direct construction draws B_1 ~ Binomial(trials, p_1), then B_2 ~
    Binomial(trials - B_1, p_2/p_1'), etc. It is exact and O(k) per trial, but
    it needs a binomial sampler, itself a small project. Walking the cumulative
    vector is O(k) per individual draw, exact when ``rng.random()`` is uniform,
    and reuses only the uniform stream -- consistent with the inverse-CDF
    approach of the previous node. The cost is O(trials * k) work per vector.
    """
    probs = [float(p) for p in probs]
    if any(p < 0.0 for p in probs):
        raise ValueError("probabilities must be non-negative")
    cumulative = []
    running = 0.0
    for p in probs:
        running += p
        cumulative.append(running)
    out = []
    for _ in range(n):
        counts = [0] * len(probs)
        for _ in range(trials):
            u = rng.random()
            for k, edge in enumerate(cumulative):
                if u < edge:
                    counts[k] += 1
                    break
            else:
                counts[-1] += 1
        out.append(counts)
    return out


# ---------------------------------------------------------------------------
# Bivariate normal
# ---------------------------------------------------------------------------

def _standard_normal_pair(rng):
    """Two independent N(0, 1) draws by the Box-Muller transform."""
    u1 = rng.random()
    while u1 <= 0.0:
        u1 = rng.random()
    u2 = rng.random()
    radius = math.sqrt(-2.0 * math.log(u1))
    angle = _TWO_PI * u2
    return radius * math.cos(angle), radius * math.sin(angle)


def bivariate_normal_pdf(x, y, mu, cov):
    """Density of N(mu, cov) at (x, y), with cov a 2x2 matrix.

    For mu = (mu_x, mu_y) and cov = [[vx, cxy], [cxy, vy]], with determinant
    ``det = vx vy - cxy^2``, the quadratic form is

        q = (vy dx^2 - 2 cxy dx dy + vx dy^2) / det,  dx = x - mu_x, ...

    and the density is exp(-q/2) / (2 pi sqrt(det)). The cross term
    ``-2 cxy dx dy`` is what couples the coordinates; dropping it gives the
    density of uncorrelated (and here independent) normals with the same
    marginal variances, which integrates to 1 and only shows up in E[XY].

    DESIGN DECISION -- closed-form 2x2 inverse, not a general linear solve?
    A 2x2 inverse is three arithmetic operations with a determinant that must be
    computed anyway for the normalising constant, so the closed form is both
    fastest and transparent; hard-coding the inverse of a larger matrix is where
    errors creep in, but here there is no larger matrix. The cost is that the
    dimension 2 is baked in -- exactly the node's scope.
    """
    mux, muy = float(mu[0]), float(mu[1])
    vx = float(cov[0][0])
    cxy = float(cov[0][1])
    vy = float(cov[1][1])
    det = vx * vy - cxy * cxy
    if det <= 0.0:
        raise ValueError("covariance matrix must be positive definite")
    dx = x - mux
    dy = y - muy
    quad = (vy * dx * dx - 2.0 * cxy * dx * dy + vx * dy * dy) / det
    return math.exp(-0.5 * quad) / (_TWO_PI * math.sqrt(det))


def sample_bivariate_normal(mu, cov, n, rng):
    """Draw ``n`` (x, y) pairs from N(mu, cov) by the 2x2 Cholesky factor.

    With cov = [[vx, cxy], [cxy, vy]], the Cholesky factor is

        L = [[sqrt(vx), 0], [cxy / sqrt(vx), sqrt(vy - cxy^2 / vx)]]

    so that L L^T = cov. For z = (z1, z2) with independent N(0, 1) entries,
    ``mu + L z`` has covariance ``L L^T = cov``. Returns a list of (x, y)
    tuples.

    DESIGN DECISION -- Cholesky, not the eigen-decomposition or the
    conditional (x, then y | x) route?
    Cholesky is the unique triangular factor, needs no trigonometry beyond
    Box-Muller, and makes the coupling visible: y = mu_y + l21 z1 + l22 z2.
    The eigen route needs an angle and a rotation, and the conditional route
    states the same factorisation less directly. The cost is that Cholesky
    requires positive definiteness, which the checker already needs to demand
    for the density to exist.
    """
    mux, muy = float(mu[0]), float(mu[1])
    vx = float(cov[0][0])
    cxy = float(cov[0][1])
    vy = float(cov[1][1])
    if vx <= 0.0 or vx * vy - cxy * cxy <= 0.0:
        raise ValueError("covariance matrix must be positive definite")
    l11 = math.sqrt(vx)
    l21 = cxy / l11
    l22 = math.sqrt(vy - l21 * l21)
    out = []
    for _ in range(n):
        z1, z2 = _standard_normal_pair(rng)
        out.append((mux + l11 * z1, muy + l21 * z1 + l22 * z2))
    return out


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo():
    print("Joint distributions from scratch")

    joint = {(-2, 4): 0.25, (-1, 1): 0.25, (1, 1): 0.25, (2, 4): 0.25}
    print("  joint over X in {-2,-1,1,2}, Y = X^2")
    print(f"    marginal(Y)  = {marginal(joint, 1)}")
    print(f"    P(Y|X=-2)    = {conditional(joint, -2)}   (degenerate: a point mass)")
    print(f"    P(Y|X= 1)    = {conditional(joint, 1)}")

    xs = [-2.0, -1.0, 1.0, 2.0]
    ys = [4.0, 1.0, 1.0, 4.0]
    print(f"    Cov(X, Y)    = {covariance(xs, ys):+.3e}   "
          f"corr = {correlation(xs, ys):+.3e}")
    print("    ... and yet Y is a function of X: zero correlation, full dependence")

    counts = [2, 1, 1]
    probs = [0.5, 0.25, 0.25]
    print(f"  multinomial_pmf({counts}, {probs}) = "
          f"{multinomial_pmf(counts, probs):.6f}")

    mu = (1.0, -2.0)
    cov = [[1.0, 0.5], [0.5, 2.0]]
    at_mean = bivariate_normal_pdf(mu[0], mu[1], mu, cov)
    det = cov[0][0] * cov[1][1] - cov[0][1] ** 2
    print(f"  bivariate_normal_pdf(mu) = {at_mean:.6f}  "
          f"(1/(2 pi sqrt(det)) = {1.0 / (_TWO_PI * math.sqrt(det)):.6f})")

    print("  sample_covariance convergence to the analytic covariance")
    rng = random.Random(12345)
    samples = sample_bivariate_normal(mu, cov, 200000, rng)
    for n in (100, 1000, 10000, 200000):
        sc = sample_covariance(samples[:n])
        print(f"    n = {n:>6}   var_x = {sc[0][0]:.4f}   cov_xy = {sc[0][1]:.4f}   "
              f"var_y = {sc[1][1]:.4f}")
    print(f"    analytic        var_x = {cov[0][0]:.4f}   cov_xy = {cov[0][1]:.4f}   "
          f"var_y = {cov[1][1]:.4f}")


if __name__ == "__main__":
    demo()
