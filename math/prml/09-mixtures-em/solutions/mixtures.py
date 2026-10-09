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
    return -0.5 * (_LOG_2PI + math.log(var) + (x - mu) ** 2 / var)


def kmeans(xs, k, rng, maxit=100):
    """Lloyd's algorithm on 1-D data.

    Returns ``(centroids, assignments)``. Centroids start at ``k`` distinct data
    points chosen by ``rng``; every iteration assigns each point to its nearest
    centroid and recomputes each centroid as the mean of its members. An empty
    cluster is reseeded on the point currently farthest from its own centroid, which
    is what keeps Lloyd's from silently dropping a cluster.
    """
    n = len(xs)
    if k <= 0:
        raise ValueError("k must be positive")
    if n < k:
        raise ValueError("need at least k data points")

    order = list(range(n))
    rng.shuffle(order)
    centroids = [float(xs[i]) for i in order[:k]]
    assignments = [-1] * n

    for _ in range(maxit):
        changed = False
        for i, x in enumerate(xs):
            best, best_d = 0, abs(x - centroids[0])
            for j in range(1, k):
                d = abs(x - centroids[j])
                if d < best_d:
                    best, best_d = j, d
            if assignments[i] != best:
                assignments[i] = best
                changed = True

        for j in range(k):
            members = [xs[i] for i in range(n) if assignments[i] == j]
            if members:
                centroids[j] = sum(members) / len(members)
            else:
                far = max(
                    range(n),
                    key=lambda i: abs(xs[i] - centroids[assignments[i]]),
                )
                centroids[j] = float(xs[far])
                assignments[far] = j
                changed = True

        if not changed:
            break

    return centroids, assignments


def gmm_e_step(xs, weights, mus, vars):
    """Responsibilities ``resp[i][j]`` = P(component j | x_i).

    The posterior is the prior times the likelihood, normalised across components;
    it is computed in log space so underflow cannot produce 0/0.
    """
    k = len(weights)
    resp = []
    for x in xs:
        logs = [
            math.log(max(weights[j], 1e-300)) + gaussian_logpdf(x, mus[j], vars[j])
            for j in range(k)
        ]
        top = max(logs)
        scaled = [math.exp(l - top) for l in logs]
        total = sum(scaled)
        resp.append([s / total for s in scaled])
    return resp


def gmm_m_step(xs, resp, var_floor=1e-6):
    """One M-step: weights, means and variances from responsibilities.

    ``weights[j] = N_j / N`` with ``N_j = sum_i r_ij``; means and variances are the
    responsibility-weighted moments of component ``j``. The variance is clamped up to
    ``var_floor`` so a component cannot collapse onto a single point.
    """
    n = len(xs)
    k = len(resp[0])
    weights, mus, vars = [], [], []
    for j in range(k):
        nk = sum(resp[i][j] for i in range(n))
        if nk < 1e-12:
            weights.append(0.0)
            mus.append(0.0)
            vars.append(max(var_floor, _MIN_VAR))
            continue
        weights.append(nk / n)
        mu = sum(resp[i][j] * xs[i] for i in range(n)) / nk
        v = sum(resp[i][j] * (xs[i] - mu) ** 2 for i in range(n)) / nk
        v = max(v, var_floor, _MIN_VAR)
        mus.append(mu)
        vars.append(v)
    return weights, mus, vars


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
    n = len(xs)
    if n == 0:
        raise ValueError("no data")
    mean = sum(xs) / n
    global_var = max(
        sum((x - mean) ** 2 for x in xs) / n, var_floor, _MIN_VAR
    )

    if init is not None:
        if len(init) != k:
            raise ValueError("init must name k means")
        mus = [float(c) for c in init]
        weights = [1.0 / k] * k
        vars = [global_var] * k
    else:
        centroids, assignments = kmeans(xs, k, rng, maxit=maxit)
        mus = [float(c) for c in centroids]
        counts = [0] * k
        for a in assignments:
            counts[a] += 1
        weights = [c / n for c in counts]
        vars = [global_var] * k

    logliks = [_gmm_loglikelihood(xs, weights, mus, vars)]
    for _ in range(maxit):
        resp = gmm_e_step(xs, weights, mus, vars)
        weights, mus, vars = gmm_m_step(xs, resp, var_floor)
        logliks.append(_gmm_loglikelihood(xs, weights, mus, vars))
        if abs(logliks[-1] - logliks[-2]) < 1e-12:
            break
    return weights, mus, vars, logliks


def gmm_em_best(xs, k, rng, restarts=5, maxit=100, var_floor=1e-6):
    """Run ``gmm_em`` ``restarts`` times and return the fit with the best final
    log-likelihood. EM only finds a local optimum, so restarting from different
    K-means initialisations is the cheap defence against a bad one. Returns the same
    tuple as ``gmm_em``."""
    best = None
    best_ll = -math.inf
    for _ in range(restarts):
        weights, mus, vars, logliks = gmm_em(
            xs, k, rng, maxit=maxit, var_floor=var_floor
        )
        final = logliks[-1]
        if final > best_ll:
            best_ll = final
            best = (weights, mus, vars, logliks)
    return best


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
    n = len(xs)
    d = len(xs[0])

    resp = []
    for _ in range(n):
        row = [rng.random() + 1e-9 for _ in range(k)]
        s = sum(row)
        resp.append([r / s for r in row])

    pis = [1.0 / k] * k
    thetas = [[0.5] * d for _ in range(k)]
    logliks = []

    for _ in range(maxit):
        pis = [sum(resp[i][j] for i in range(n)) / n for j in range(k)]
        new_thetas = []
        for j in range(k):
            nj = sum(resp[i][j] for i in range(n))
            if nj < 1e-12:
                new_thetas.append([0.5] * d)
                continue
            new_thetas.append(
                [
                    sum(resp[i][j] * xs[i][t] for i in range(n)) / nj
                    for t in range(d)
                ]
            )
        thetas = new_thetas

        total = 0.0
        for i in range(n):
            terms = [_log_bernoulli_mixture(xs[i], pis, thetas, j) for j in range(k)]
            top = max(terms)
            total += top + math.log(sum(math.exp(t - top) for t in terms))
        logliks.append(total)

        new_resp = []
        for i in range(n):
            terms = [_log_bernoulli_mixture(xs[i], pis, thetas, j) for j in range(k)]
            top = max(terms)
            scaled = [math.exp(t - top) for t in terms]
            s = sum(scaled)
            new_resp.append([v / s for v in scaled])
        resp = new_resp

    return pis, thetas, logliks


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
