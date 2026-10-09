"""Continuous random variables from scratch: the Uniform, Normal and
Exponential distributions, inverse-CDF sampling, memorylessness, and the
Kolmogorov-Smirnov goodness-of-fit test.

Implements chapter 5 of Blitzstein & Hwang, *Introduction to Probability*
(2nd ed.): continuous random variables and their densities, the named
continuous distributions, and universality of the uniform. The argument is
restated here, never copied.

Every distribution is reachable through its inverse CDF (the quantile
function): a single Uniform(0, 1) stream feeds all three. The node's acceptance
criterion is that inverse-CDF samples pass a Kolmogorov-Smirnov test against
the target CDF; the node's limit case is a heavy tail whose quantile grows fast
enough that float rounding near u = 1 truncates the support.

    python3 continuous.py      # prints the measurements this file promises
"""

import math
import random

_SQRT2 = math.sqrt(2.0)
# The largest double strictly below 1: rng.random() never returns 1, so this is
# the closest the inverse-CDF sampler can get to the heavy-tail limit.
U_MAX = math.nextafter(1.0, 0.0)


# ---------------------------------------------------------------------------
# Quantile functions (inverse CDFs)
# ---------------------------------------------------------------------------

def uniform_ppf(u):
    """Inverse CDF of Uniform(0, 1): the identity on [0, 1].

    Uniform(0, 1) has F(x) = x on [0, 1], so F^{-1}(u) = u. Its role is to be
    the input stream: U ~ Uniform(0, 1) and X = F^{-1}(U) has CDF F, for ANY F
    (universality of the uniform).
    """
    if not 0.0 <= u <= 1.0:
        raise ValueError("uniform_ppf takes u in [0, 1]")
    return u


def exponential_ppf(u, rate):
    """Inverse CDF of Exponential(rate): F(x) = 1 - exp(-rate x).

    F^{-1}(u) = -log(1 - u) / rate. ``log1p(-u)`` is used instead of
    ``log(1 - u)`` so accuracy is kept when u is small; the endpoints map to
    0 and +inf.
    """
    if rate <= 0.0:
        raise ValueError("rate must be positive")
    if u <= 0.0:
        return 0.0
    if u >= 1.0:
        return math.inf
    return -math.log1p(-u) / rate


def normal_cdf(x):
    """Standard normal CDF: Phi(x) = (1 + erf(x / sqrt(2))) / 2."""
    return 0.5 * (1.0 + math.erf(x / _SQRT2))


def normal_ppf(u):
    """Inverse CDF of the standard normal, by BISECTION on ``math.erf``.

    DESIGN DECISION -- bisection on erf, not a rational approximation?
    The usual quantile approximations (Beasley-Springer-Moro, Acklam) are fast
    but their constants are opaque: a wrong constant looks exactly like a
    wrong method, which is the bug this node plants (returning the CDF). A
    bisection makes every iteration an honest evaluation of Phi and returns
    the quantile to about 1e-11 in 40 steps, because the bracket [-40, 40] has
    width 80 and 80 / 2**40 ~ 7e-11. The cost is speed, which a learning
    module can pay.

    DESIGN DECISION -- why [-40, 40]?
    Any u in (0, 1) reachable as a double has a quantile inside [-38, 38], so
    the bracket never needs to be wider; narrower would need more steps to
    resolve the tails.
    """
    if u <= 0.0:
        return -math.inf
    if u >= 1.0:
        return math.inf
    lo, hi = -40.0, 40.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if normal_cdf(mid) < u:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ---------------------------------------------------------------------------
# Universality of the uniform: inverse-CDF sampling
# ---------------------------------------------------------------------------

def inverse_cdf_sample(ppf, n, rng):
    """Draw n samples as X = ppf(U) with U = rng.random().

    DESIGN DECISION -- sample by inverting the CDF, or by a per-distribution
    algorithm (Box-Muller for the Normal, sum of exponentials for the Gamma)?
    Inversion is one line per distribution, reuses the uniform stream, is
    exactly monotone (preserves order statistics), and is the statement of the
    node. The cost is that it needs the quantile in closed form, which the
    Normal does not have -- hence the bisection. For a tail-heavy target it is
    also exactly where float precision bites (see ``tail_truncation``).
    """
    return [ppf(rng.random()) for _ in range(n)]


# ---------------------------------------------------------------------------
# Kolmogorov-Smirnov
# ---------------------------------------------------------------------------

def ks_statistic(samples, cdf):
    """Two-sided Kolmogorov-Smirnov statistic D of a sample against ``cdf``.

    Sort the sample. At the i-th order statistic x_(i) (i from 1) the empirical
    CDF jumps from (i-1)/n just below x_(i) to i/n at it, so the vertical gap
    to the true F(x_(i)) is bounded by ``max(i/n - F, F - (i-1)/n)``. D is the
    largest gap over the sample. Using ``i/n`` on both sides is the classic
    error: it forgets the left limit and shrinks D.

    DESIGN DECISION -- why this two-sided form?
    D = sup_x |F_n(x) - F(x)|. The sup is attained at an order statistic, and
    the ECDF there has a vertical jump, so both one-sided gaps must be checked.
    The cost is one extra max term; the payoff is that the (i-1)/n side is the
    only place a sample can hide a mis-specified CDF.
    """
    n = len(samples)
    if n == 0:
        return 0.0
    xs = sorted(samples)
    d = 0.0
    for i, x in enumerate(xs, start=1):
        f = cdf(x)
        d = max(d, i / n - f, f - (i - 1) / n)
    return d


def ks_pvalue(d, n):
    """Asymptotic p-value of D: Q(d sqrt(n)), the Kolmogorov distribution.

    Q(lam) = 2 * sum_{k=1}^{inf} (-1)^(k-1) exp(-2 k^2 lam^2), the asymptotic
    (n -> inf) form. The alternating series is summed until a term is below
    1e-12, and the result is clipped to [0, 1].

    DESIGN DECISION -- keep the whole alternating series, not its first term?
    ``2 exp(-2 lam^2)`` is the large-lam approximation; for lam <~ 0.6 it
    exceeds 1 (e.g. 1.213 at lam = 0.5), where Q is actually 0.96. Truncating
    after one term is the classic error and reports impossible p-values, so the
    checker pins both the value and the <= 1 bound. The cost is a few hundred
    exp calls per p-value, which is nothing.
    """
    if d <= 0.0:
        return 1.0
    lam = d * math.sqrt(n)
    # Q -> 1 as lam -> 0; below this the series is accurate but slow, so use
    # the limit (error O(lam)).
    if lam < 1e-3:
        return 1.0
    total = 0.0
    sign = 1.0
    for k in range(1, 10001):
        term = math.exp(-2.0 * (k * lam) ** 2)
        total += sign * term
        if term < 1e-12:
            break
        sign = -sign
    return min(1.0, max(0.0, 2.0 * total))


# ---------------------------------------------------------------------------
# Memorylessness
# ---------------------------------------------------------------------------

def _exponential_survival(rate, x):
    """P(X > x) for X ~ Exponential(rate), zero rate checks at the call site."""
    if x <= 0.0:
        return 1.0
    return math.exp(-rate * x)


def _shifted_survival(rate, shift, x):
    """P(X > x) for X = shift + Exponential(rate), support (shift, inf)."""
    if x <= shift:
        return 1.0
    return math.exp(-rate * (x - shift))


def memorylessness_gap(rate, s, t):
    """P(X > s+t | X > s) - P(X > t) for X ~ Exponential(rate).

    For the exponential the conditional survival equals the unconditional one,
    exp(-rate t), so the gap is exactly 0: the variable is memoryless. The
    checker also builds a SHIFTED exponential, where the same subtraction is
    nonzero -- that is the variable that is *not* memoryless.
    """
    if rate <= 0.0:
        raise ValueError("rate must be positive")
    if s <= 0.0:
        raise ValueError("condition on s > 0")
    conditional = _exponential_survival(rate, s + t) / _exponential_survival(rate, s)
    return conditional - _exponential_survival(rate, t)


def shifted_exponential_gap(rate, shift, s, t):
    """Same gap for X = shift + Exponential(rate), which is not memoryless.

    With s, t > shift the conditional excess is still exp(-rate t), but the
    unconditional P(X > t) = exp(-rate (t - shift)); the gap is
    exp(-rate t) - exp(-rate (t - shift)) = exp(-rate t) (1 - exp(rate shift)),
    which is nonzero for shift > 0. The memorylessness identity
    P(X > s+t | X > s) = P(X > t) holds for the exponential alone.
    """
    if rate <= 0.0:
        raise ValueError("rate must be positive")
    if s <= shift:
        raise ValueError("need s > shift to condition on the excess")
    conditional = (
        _shifted_survival(rate, shift, s + t) / _shifted_survival(rate, shift, s)
    )
    return conditional - _shifted_survival(rate, shift, t)


# ---------------------------------------------------------------------------
# The limit case: the tail float rounding truncates
# ---------------------------------------------------------------------------

def tail_truncation(rate, u):
    """Tail mass and tail quantile the inverse-CDF sampler can never reach.

    ``rng.random()`` lies in [0, 1), so the closest it comes to 1 is
    U_MAX = 1 - 2**-53. The largest exponential quantile any sample can reach
    is therefore x_max = -log1p(-U_MAX)/rate, and the support (x_max, inf) --
    mass 1 - U_MAX = 2**-53 -- is silently dropped. For a requested ``u``
    (clamped to U_MAX) this returns a dict:

    * ``x``               -- the quantile actually reached;
    * ``missing_mass``    -- probability above that point;
    * ``missing_quantile``-- quantile still missing above ``x``: +inf, because
      the true quantile at u = 1 is +inf.

    DESIGN DECISION -- report the missing quantile, or call the sampler exact?
    It is tempting to say "2**-53 is negligible, so sampling is exact". For an
    unbounded right tail the missing piece is not a rounding error in x, it is
    an entire infinite interval of the support, so ``missing_quantile`` is
    +inf. Hiding that (returning 0, or pretending u can reach 1) is the bug the
    checker plants. The cost is that the honest answer is not a single number.
    """
    if rate <= 0.0:
        raise ValueError("rate must be positive")
    u_eff = min(u, U_MAX)
    x = exponential_ppf(u_eff, rate)
    return {
        "u": u,
        "u_max": U_MAX,
        "x": x,
        "missing_mass": 1.0 - u_eff,
        "missing_quantile": math.inf if math.isfinite(x) else 0.0,
    }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo():
    rate = 1.3
    print("Continuous random variables from scratch")
    print(f"  uniform_ppf(0.3)                = {uniform_ppf(0.3):.6f}")
    x = exponential_ppf(0.5, rate)
    print(f"  exponential_ppf(0.5, rate=1.3)  = {x:.6f}  "
          f"(F = {1 - math.exp(-rate * x):.6f})")
    z = normal_ppf(0.975)
    print(f"  normal_ppf(0.975)               = {z:.6f}  "
          f"(Phi = {normal_cdf(z):.6f})")

    n = 50000
    print(f"  inverse-CDF sample, n = {n}, against the target CDF (KS test)")
    for label, ppf, cdf, seed in (
        ("uniform    ", uniform_ppf, lambda v: min(1.0, max(0.0, v)), 2001),
        ("exponential", lambda q: exponential_ppf(q, rate),
         lambda v: 0.0 if v <= 0 else 1 - math.exp(-rate * v), 2002),
        ("normal     ", normal_ppf, normal_cdf, 2003),
    ):
        rng = random.Random(seed)
        xs = inverse_cdf_sample(ppf, n, rng)
        d = ks_statistic(xs, cdf)
        print(f"    {label}  D = {d:.5f}   p = {ks_pvalue(d, n):.4f}")

    s, t = 2.0, 3.0
    print(f"  memorylessness gap Exp(1.3), s={s}, t={t}   = "
          f"{memorylessness_gap(rate, s, t):+.3e}")
    print(f"  same gap, shifted by 0.75 (not memoryless) = "
          f"{shifted_exponential_gap(rate, 0.75, s, t):+.3e}")

    info = tail_truncation(1.0, 1.0)
    print(f"  tail truncation Exp(1), u -> 1: largest reachable x = "
          f"{info['x']:.6f}")
    print(f"    missing mass = {info['missing_mass']:.3e}, "
          f"missing quantile = {info['missing_quantile']}")


if __name__ == "__main__":
    demo()
