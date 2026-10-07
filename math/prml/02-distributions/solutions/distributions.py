"""Probability distributions, conjugacy and density estimation, from scratch.

Implements the material of Bishop, *Pattern Recognition and Machine Learning*,
chapter 2, and Murphy, *Probabilistic Machine Learning: An Introduction*, chapter 3
(`bishop:2`, `murphy1:3`). The argument is restated here, never copied:

* the Beta-Bernoulli and Dirichlet-multinomial conjugate updates, which turn a
  sequence of observations into a posterior by adding counts;
* the maximum-likelihood Gaussian: the sample mean and the sample variance with the
  ``1/N`` normaliser, and the sequential (online) conjugate update of a Gaussian mean
  with the observation variance known;
* the exponential-family form: sufficient statistics, natural parameters, the
  log-partition function and the fact that its gradient is the mean;
* nonparametric density estimation: the histogram, the Gaussian kernel density
  estimator and the k-nearest-neighbour estimator.

Everything is the standard library (``math``, ``random``), in double precision.

DESIGN DECISION -- Beta-Bernoulli returns the *parameters* ``(alpha, beta)``, not a
probability. The two numbers are the state; every question (mean, mode, predictive
probability, credible interval) is a pure function of them. Returning the mean would
throw away the concentration, and the whole point of the node is that the update is a
count. **Chosen: ``beta_bernoulli_update`` returns ``(alpha', beta')``; the posterior
mean is the separate ``beta_mean``.** The cost is one extra call at the use site.

DESIGN DECISION -- the MLE variance uses ``1/N``, and that is the interesting fact.
The unbiased estimator divides by ``N-1``; the maximum-likelihood one does not. The
module keeps ``gaussian_mle`` at ``1/N`` so the ``(N-1)/N`` bias is a property of the
code rather than a comment, and the checker measures it by simulation. **Chosen:
``gaussian_mle`` returns the biased MLE.** The cost is that anyone who wants the
unbiased variance must divide by ``N-1`` themselves; the limit case shows why.

DESIGN DECISION -- the sequential Gaussian mean uses a *precision* ``tau = 1/sigma^2``
representation with the observation variance fixed. The update ``tau' = tau + 1/sigma^2``
is additive, so batch and sequential routes agree to floating-point round-off instead of
to an accumulated-division error. **Chosen: carry ``(mu, tau, sigma)``.** The cost is
that the caller must supply the (known, constant) observation ``sigma`` with the state;
the alternative -- recomputing a sample average -- would not be a conjugate update at
all, and the plug-in-the-prior bug is exactly what a mutation plants.

DESIGN DECISION -- KDE uses a Gaussian kernel normalised so that it integrates to one,
and divides by ``n h``. The kernel and the normalisation are separate, named pieces so
that dropping either is a visible bug rather than a silent scale error. **Chosen: a
hand-written ``_gaussian_kernel`` and the explicit ``1/(n h)``.** The cost is two extra
lines; the benefit is that the density integrates to approximately one and can be
compared with the histogram.

    python3 distributions.py     # prints the measurements this file promises
"""

import math
import random


# ---------------------------------------------------------------------------
# Conjugate pairs: Beta-Bernoulli and Dirichlet-multinomial
# ---------------------------------------------------------------------------

def beta_bernoulli_update(alpha, beta, heads, tails):
    """Posterior of a Beta prior after ``heads`` ones and ``tails`` zeros.

    The Bernoulli likelihood contributes ``heads`` successes and ``tails`` failures,
    each of which adds one to the matching Beta parameter:
    ``(alpha', beta') = (alpha + heads, beta + tails)``.
    """
    return (alpha + heads, beta + tails)


def beta_mean(alpha, beta):
    """The mean ``alpha / (alpha + beta)`` of a Beta distribution."""
    return alpha / (alpha + beta)


def dirichlet_multinomial_update(alpha, counts):
    """Posterior of a Dirichlet prior after a multinomial batch ``counts``.

    Each category's count is added to the matching concentration parameter. The prior
    is *included*: the result is ``[a_i + counts_i]``, never ``counts`` alone.
    """
    return [a + c for a, c in zip(alpha, counts)]


# ---------------------------------------------------------------------------
# The Gaussian: MLE, sequential and batch posteriors
# ---------------------------------------------------------------------------

def gaussian_mle(xs):
    """Maximum-likelihood ``(mean, variance)`` of a sample.

    The mean is ``sum(x) / N`` and the variance is
    ``sum((x - mean)^2) / N`` -- the ``1/N`` normaliser. This estimator is biased:
    its expectation is ``(N-1)/N * sigma^2``, not ``sigma^2``.
    """
    n = len(xs)
    mean = sum(xs) / n
    variance = sum((x - mean) ** 2 for x in xs) / n
    return (mean, variance)


def gaussian_sequential_update(posterior, x):
    """One online conjugate update of a Gaussian mean, known observation variance.

    ``posterior`` is ``{"mu", "tau", "sigma"}``: posterior mean, posterior precision
    (``1/variance``) of the mean, and the known observation standard deviation. One
    new observation adds its precision and reweights the two means by precision:

        ``tau_new = tau + 1/sigma^2``
        ``mu_new  = (tau * mu + x / sigma^2) / tau_new``

    This is *not* a running average that forgets the prior.
    """
    mu, tau, sigma = posterior["mu"], posterior["tau"], posterior["sigma"]
    obs_precision = 1.0 / (sigma * sigma)
    tau_new = tau + obs_precision
    mu_new = (tau * mu + x * obs_precision) / tau_new
    return {"mu": mu_new, "tau": tau_new, "sigma": sigma}


def gaussian_posterior(mu0, sigma0, sigma, xs):
    """Closed-form posterior ``(mean, precision)`` of a Gaussian mean from a batch.

    Prior ``mean ~ N(mu0, sigma0^2)``, observation variance ``sigma^2`` known. The
    posterior precision is ``1/sigma0^2 + N/sigma^2`` and the posterior mean is the
    precision-weighted average of the prior mean and the sample mean.
    """
    tau0 = 1.0 / (sigma0 * sigma0)
    obs_precision = 1.0 / (sigma * sigma)
    tau = tau0 + len(xs) * obs_precision
    mu = (tau0 * mu0 + sum(xs) * obs_precision) / tau
    return (mu, tau)


# ---------------------------------------------------------------------------
# The exponential family
# ---------------------------------------------------------------------------

def sufficient_stats(xs, family="bernoulli"):
    """Sufficient statistics: ``(n, sum)`` for Bernoulli, ``(n, sum, sum_sq)`` for Gaussian."""
    if family == "bernoulli":
        return (len(xs), sum(xs))
    if family == "gaussian":
        return (len(xs), sum(xs), sum(x * x for x in xs))
    raise ValueError(f"unknown family {family!r}")


def gaussian_from_sufficient_stats(stats):
    """Recover ``(mean, variance_MLE)`` from ``(n, sum, sum_sq)``."""
    n, total, total_sq = stats
    mean = total / n
    variance = total_sq / n - mean * mean
    return (mean, variance)


def natural_parameters(stats, family="bernoulli", sigma=1.0):
    """The natural parameter the sufficient statistics imply.

    Bernoulli: ``eta = logit(sum/n)``. Gaussian with known variance ``sigma^2``:
    ``eta = (sum/n) / sigma^2``.
    """
    if family == "bernoulli":
        n, total = stats
        mu = total / n
        return math.log(mu / (1.0 - mu))
    if family == "gaussian":
        n, total, _ = stats
        return (total / n) / (sigma * sigma)
    raise ValueError(f"unknown family {family!r}")


def log_partition(eta, family="bernoulli", sigma=1.0):
    """The log-partition ``A(eta)`` of the exponential-family form.

    Bernoulli: ``A(eta) = log(1 + e^eta)``, evaluated stably. Gaussian with known
    variance ``sigma^2``: ``A(eta) = sigma^2 eta^2 / 2``.
    """
    if family == "bernoulli":
        return max(eta, 0.0) + math.log1p(math.exp(-abs(eta)))
    if family == "gaussian":
        return 0.5 * sigma * sigma * eta * eta
    raise ValueError(f"unknown family {family!r}")


def log_partition_gradient(eta, family="bernoulli", sigma=1.0):
    """``A'(eta)``: the sigmoid for Bernoulli, ``sigma^2 eta`` for Gaussian.

    The gradient of the log-partition is the mean of the sufficient statistic, so this
    must equal the distribution parameter recovered from the data.
    """
    if family == "bernoulli":
        return 1.0 / (1.0 + math.exp(-eta))
    if family == "gaussian":
        return sigma * sigma * eta
    raise ValueError(f"unknown family {family!r}")


def exponential_family_stats(xs, family="bernoulli", sigma=1.0):
    """Bundle the statistics, natural parameter, mean and log-partition of ``xs``.

    The returned ``mean`` is ``log_partition_gradient(eta)``; it must equal the
    distribution parameter that the sufficient statistics imply.
    """
    stats = sufficient_stats(xs, family)
    eta = natural_parameters(stats, family, sigma)
    return {
        "stats": stats,
        "eta": eta,
        "mean": log_partition_gradient(eta, family, sigma),
        "log_partition": log_partition(eta, family, sigma),
    }


# ---------------------------------------------------------------------------
# Nonparametric density estimation
# ---------------------------------------------------------------------------

def histogram_density(xs, edges):
    """Histogram density: per bin, ``count / (n * width)``.

    Bins are ``[edges[i], edges[i+1])``; the last bin includes its right edge. Because
    each value is divided by the bin width, the histogram integrates to one.
    """
    n = len(xs)
    last = len(edges) - 2
    densities = []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        if i == last:
            count = sum(1 for x in xs if lo <= x <= hi)
        else:
            count = sum(1 for x in xs if lo <= x < hi)
        densities.append(count / (n * (hi - lo)))
    return densities


def _gaussian_kernel(z):
    """Standard normal density, used as the KDE kernel."""
    return math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)


def kde(xs, x, h):
    """Gaussian kernel density estimate at ``x`` with bandwidth ``h``.

    ``(1 / (n h)) * sum_i K((x - x_i) / h)``. The ``1/(n h)`` scale is what makes it a
    density; the kernel is what makes it smooth.
    """
    n = len(xs)
    return sum(_gaussian_kernel((x - xi) / h) for xi in xs) / (n * h)


def knn_density(xs, x, k):
    """k-nearest-neighbour density estimate at ``x``.

    The ball is the interval ``[x - r, x + r]`` around the ``k``-th nearest sample, so
    in one dimension its volume is ``2 r`` and the estimate is ``k / (n * 2 r)``.
    """
    n = len(xs)
    distances = sorted(abs(xi - x) for xi in xs)
    radius = distances[k - 1]
    if radius <= 0.0:
        return float("inf")
    return k / (n * 2.0 * radius)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo():
    """Print one measurement per construction this module promises."""
    print("Distributions, conjugacy and density estimation — measurements")

    a, b = beta_bernoulli_update(1.0, 1.0, 3.0, 1.0)
    print(f"  Beta(1,1) + 3 heads / 1 tail -> Beta({a:g}, {b:g}), mean {beta_mean(a, b):.4f}")
    a, b = beta_bernoulli_update(1.0, 1.0, 3.0, 0.0)
    print(f"  Beta(1,1) + 3 heads / 0 tails -> Beta({a:g}, {b:g}), mean {beta_mean(a, b):.4f}")

    alpha = dirichlet_multinomial_update([1.0, 1.0, 1.0], [2, 1, 1])
    print(f"  Dirichlet(1,1,1) + [2,1,1] -> {[round(v, 4) for v in alpha]}")

    x9 = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
    mean, var = gaussian_mle(x9)
    print(f"  gaussian_mle(0..9): mean {mean:.4f}, variance(1/N) {var:.4f}"
          f"  (unbiased {sum((x - mean) ** 2 for x in x9) / 9:.4f})")

    post = {"mu": 0.0, "tau": 1.0 / 9.0, "sigma": 1.5}
    for x in [0.3, -1.2, 2.1, 0.7]:
        post = gaussian_sequential_update(post, x)
    bmu, btau = gaussian_posterior(0.0, 3.0, 1.5, [0.3, -1.2, 2.1, 0.7])
    print(f"  sequential posterior: mu {post['mu']:.8f}, tau {post['tau']:.8f}")
    print(f"  batch posterior:      mu {bmu:.8f}, tau {btau:.8f}")

    xs = [1.0, 0.0, 1.0, 1.0, 0.0]
    ef = exponential_family_stats(xs, "bernoulli")
    print(f"  Bernoulli sufficient stats {ef['stats']}, eta {ef['eta']:.6f},"
          f" A'(eta) {ef['mean']:.6f}")

    data = [float(i) for i in range(10)]
    spiky = max(kde(data, v, 0.15) for v in data) / kde(data, 4.5, 0.15)
    smooth = max(kde(data, v, 4.0) for v in data) / kde(data, 4.5, 4.0)
    print(f"  KDE peak/mid ratio: h=0.15 -> {spiky:.1f} (spiky),"
          f" h=4.0 -> {smooth:.2f} (oversmooth)")

    rng = random.Random(12345)
    n, trials, sigma = 8, 20000, 2.0
    acc = 0.0
    for _ in range(trials):
        sample = [rng.gauss(0.0, sigma) for _ in range(n)]
        acc += gaussian_mle(sample)[1]
    print(f"  E[MLE variance] over {trials} samples of {n}: {acc / trials:.4f}"
          f"  vs (N-1)/N sigma^2 = {(n - 1) / n * sigma * sigma:.4f}")


if __name__ == "__main__":
    demo()
