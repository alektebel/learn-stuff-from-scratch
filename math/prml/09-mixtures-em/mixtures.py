"""Mixture models and the EM algorithm, from scratch.

K-means (Lloyd's algorithm), EM for a univariate Gaussian mixture, and EM for a
mixture of Bernoullis. Follows Bishop, *Pattern Recognition and Machine Learning*,
chapter 9 (mixture models and EM) and Murphy, *Probabilistic Machine Learning: An
Introduction*, chapter 11 (the argument is restated here, never copied).

DESIGN DECISION - K-means returns both centroids and assignments.
    The assignment is the E-step of K-means and the centroid the M-step; returning
    only centroids hides the half of the algorithm the learner is meant to see. The
    cost is one more object to thread through, and the caller must not assume the
    centroids come back sorted.

DESIGN DECISION - the Gaussian mixture is univariate and its parameters are plain
    lists, not arrays.
    The node is the EM recursion, not vectorised linear algebra; a list per
    component keeps the update readable and dependency-free. The cost is that a
    d-dimensional mixture (full covariances) would need a rewrite, which chapter 9
    does later and is out of scope here.

DESIGN DECISION - the M-step takes an explicit ``var_floor`` and a component whose
    variance would go to zero is lifted to the floor.
    The unconstrained maximum-likelihood Gaussian mixture is ill-posed: a component
    that owns a single point drives its variance to zero and the log-likelihood to
    +inf. A floor makes the objective proper. The cost is that the floored EM is no
    longer the exact M-step, so monotonicity is only guaranteed while the floor is
    inactive.

DESIGN DECISION - ``gmm_em`` accepts an optional ``init`` list of starting means.
    Restarts and the deliberately-bad-initialisation limit case both need to control
    where EM starts; deriving that from the RNG alone is not reproducible across
    Python versions. The cost is one extra keyword argument.

DESIGN DECISION - responsibilities and the log-likelihood are computed in log space
    with the max-subtraction trick.
    Gaussian densities underflow to 0.0 quickly; dividing 0/0 would raise or return
    NaN. Log-space is a few lines longer and costs a handful of exp calls. The cost
    is that ``gaussian_logpdf`` may not be called with a non-positive variance.
"""

import math
import random

_LOG_2PI = math.log(2.0 * math.pi)
# Numerical guard only: it keeps a zero variance from turning into a 0/0. It is not
# the statistical floor; that one is passed as ``var_floor``.
_MIN_VAR = 1e-12


def gaussian_logpdf(x, mu, var):
    """Log density of N(x | mu, var) for a strictly positive ``var``."""
    # TODO: Univariate Gaussian log density: -0.5 * (log(2*pi*var) + (x - mu)**2 / var). Assume var > 0; the M-step owns the variance floor.
    raise NotImplementedError("gaussian_logpdf")


def kmeans(xs, k, rng, maxit=100):
    """Lloyd's algorithm on 1-D data.

    Returns ``(centroids, assignments)``. Centroids start at ``k`` distinct data
    points chosen by ``rng``; every iteration assigns each point to its nearest
    centroid and recomputes each centroid as the mean of its members. An empty
    cluster is reseeded on the point currently farthest from its own centroid, which
    is what keeps Lloyd's from silently dropping a cluster.
    """
    # TODO: Lloyd's algorithm. Seed k distinct data points (rng.shuffle then take k), then alternate: assign each x to the nearest centroid by |x - c|, recompute each centroid as the mean of its members. Reseed an empty cluster on the point farthest from its centroid. Return (centroids, assignments).
    raise NotImplementedError("kmeans")


def gmm_e_step(xs, weights, mus, vars):
    """Responsibilities ``resp[i][j]`` = P(component j | x_i).

    The posterior is the prior times the likelihood, normalised across components;
    it is computed in log space so underflow cannot produce 0/0.
    """
    # TODO: Responsibilities P(j | x_i) proportional to prior_j * N(x_i | mu_j, var_j), normalised across j. Work in log space: log(weight) + gaussian_logpdf, subtract the row max, exponentiate, divide by the row sum. This is the posterior, not the prior.
    raise NotImplementedError("gmm_e_step")


def gmm_m_step(xs, resp, var_floor=1e-6):
    """One M-step: weights, means and variances from responsibilities.

    ``weights[j] = N_j / N`` with ``N_j = sum_i r_ij``; means and variances are the
    responsibility-weighted moments of component ``j``. The variance is clamped up to
    ``var_floor`` so a component cannot collapse onto a single point.
    """
    # TODO: N_j = sum_i r_ij; weight_j = N_j / N; mu_j = sum_i r_ij x_i / N_j; var_j = sum_i r_ij (x_i - mu_j)**2 / N_j, then clamped up to var_floor. Do NOT return the raw N_j as the weight: the weights must sum to one.
    raise NotImplementedError("gmm_m_step")


def _gmm_loglikelihood(xs, weights, mus, vars):
    """Total log-likelihood ``sum_i log sum_j pi_j N(x_i | mu_j, var_j)``."""
    k = len(weights)
    total = 0.0
    for x in xs:
        logs = [
            math.log(max(weights[j], 1e-300)) + gaussian_logpdf(x, mus[j], vars[j])
            for j in range(k)
        ]
        top = max(logs)
        total += top + math.log(sum(math.exp(l - top) for l in logs))
    return total


def gmm_em(xs, k, rng, maxit=100, var_floor=1e-6, init=None):
    """EM for a univariate Gaussian mixture.

    Starts from K-means (or ``init`` means) and alternates E and M steps. Returns
    ``(weights, mus, vars, logliks)`` where ``logliks`` is the full log-likelihood
    after every iteration, starting from the initial parameters. The sequence is
    non-decreasing while the variance floor stays inactive: that is the accept
    criterion for EM convergence.
    """
    # TODO: Initialise from K-means (centroids as means, cluster fractions as weights, the global variance for every component) or from the optional init means. Then loop: E-step responsibilities, M-step parameters, append the total log-likelihood, stop when it stops changing. Return (weights, mus, vars, logliks) with the whole likelihood sequence, starting from the initial parameters.
    raise NotImplementedError("gmm_em")


def gmm_em_best(xs, k, rng, restarts=5, maxit=100, var_floor=1e-6):
    """Run ``gmm_em`` ``restarts`` times and return the fit with the best final
    log-likelihood. EM only finds a local optimum, so restarting from different
    K-means initialisations is the cheap defence against a bad one. Returns the same
    tuple as ``gmm_em``."""
    # TODO: Run gmm_em `restarts` times on the same rng and keep the fit with the highest final log-likelihood. Keep the BEST, not the first or the last.
    raise NotImplementedError("gmm_em_best")


def _log_bernoulli_mixture(x, pis, thetas, j):
    """log P(x | component j) + log pi_j, for a 0/1 vector x."""
    lp = math.log(max(pis[j], 1e-300))
    for t, bit in enumerate(x):
        th = min(max(thetas[j][t], 1e-12), 1.0 - 1e-12)
        lp += bit * math.log(th) + (1 - bit) * math.log(1.0 - th)
    return lp


def bernoulli_mixture_em(xs, k, rng, maxit=100):
    """EM for a mixture of Bernoullis. ``xs`` is a list of 0/1 vectors.

    Returns ``(pis, thetas, logliks)``: the mixture weights, each component's vector
    of success probabilities, and the log-likelihood after every M-step. The M-step
    is a responsibility-weighted average of the bits; the E-step is the same log-space
    posterior as the Gaussian case.
    """
    # TODO: xs are 0/1 vectors. Initialise soft responsibilities at random and normalise them. Loop: M-step weight_j = mean_i r_ij and theta_jt = sum_i r_ij x_it / N_j; E-step responsibilities from log pi_j + sum_t [x_it log theta + (1-x_it) log(1-theta)]. Return (pis, thetas, logliks).
    raise NotImplementedError("bernoulli_mixture_em")


def demo():
    """Print measurements a learner can compare against."""
    rng = random.Random(7)
    xs = []
    for mu in (-6.0, 0.0, 6.0):
        xs += [rng.gauss(mu, 0.6) for _ in range(40)]

    centroids, _ = kmeans(xs, 3, rng)
    print("K-means centroids:", [round(c, 3) for c in sorted(centroids)])

    weights, mus, vars, logliks = gmm_em(
        xs, 3, random.Random(1), maxit=200, var_floor=1e-3
    )
    order = sorted(range(3), key=lambda j: mus[j])
    print("GMM means:", [round(mus[j], 3) for j in order])
    print("GMM weights:", [round(weights[j], 3) for j in order])
    monotone = all(logliks[i + 1] >= logliks[i] - 1e-9 for i in range(len(logliks) - 1))
    print(
        "GMM log-likelihood first -> last:",
        round(logliks[0], 3),
        "->",
        round(logliks[-1], 3),
        "monotone:",
        monotone,
    )

    rng = random.Random(3)
    bx = []
    for _ in range(250):
        th = [0.9, 0.1, 0.9] if rng.random() < 0.5 else [0.1, 0.9, 0.1]
        bx.append([1 if rng.random() < p else 0 for p in th])
    pis, thetas, _ = bernoulli_mixture_em(bx, 2, rng, maxit=200)
    order = sorted(range(2), key=lambda j: thetas[j][0])
    print(
        "Bernoulli mixture thetas:",
        [[round(v, 3) for v in thetas[j]] for j in order],
        "weights:",
        [round(pis[j], 3) for j in order],
    )

    shrinking = [gaussian_logpdf(0.0, 0.0, v) for v in (1e-2, 1e-4, 1e-8)]
    print("logpdf(0 | 0, var):", [round(v, 3) for v in shrinking], "(-> +inf)")
    floored = gmm_em([0.0] * 5 + [100.0], 2, random.Random(3), maxit=100, var_floor=0.5)
    unfloored = gmm_em([0.0] * 5 + [100.0], 2, random.Random(3), maxit=100, var_floor=0.0)
    print(
        "min variance floored ->",
        min(floored[2]),
        " unfloored ->",
        min(unfloored[2]),
    )

    data = []
    rng = random.Random(321)
    for mu in (-10.0, 0.0, 10.0):
        data += [rng.gauss(mu, 0.5) for _ in range(30)]
    bad = gmm_em(
        data, 3, random.Random(1), maxit=200, var_floor=1e-3, init=[0.0, 0.0, 0.0]
    )[3][-1]
    best = gmm_em_best(data, 3, random.Random(99), restarts=8, maxit=200, var_floor=1e-3)[3][-1]
    print("bad init log-likelihood:", round(bad, 3), " best of 8 restarts:", round(best, 3))


if __name__ == "__main__":
    demo()
