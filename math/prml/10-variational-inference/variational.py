"""
Variational inference from scratch, stdlib only. TEMPLATE: fill in the stubs.

Three objects, all fitted by coordinate ascent on the same evidence lower bound
(ELBO):

* the mean-field variational approximation to a univariate Gaussian with unknown
  mean and precision (a Normal--Gamma model);
* the exact log evidence of the same Normal--Gamma model, which the ELBO sits
  below;
* a variational Gaussian mixture, mean-field over the assignments and the
  component parameters.

The reverse-KL limit case -- a correlated Gaussian whose marginal variances the
mean-field fit shrinks toward the modes -- closes the module.

DESIGN DECISION - the Normal--Gamma ELBO keeps every constant, including both
    entropies.
    Tracking only the terms that move under coordinate ascent is enough to see
    monotonicity, but keeping the constants makes the ELBO a true lower bound on the
    exact log evidence, so the checker can assert ``ELBO <= log evidence``. The cost is
    a few ``lgamma``/``digamma`` calls per sweep.

DESIGN DECISION - the mean-field updates are the closed-form coordinate maxima, with
    the shape ``a = a0 + (N + 1) / 2`` fixed by the Normal--Gamma conjugacy.
    The conjugate pair gives an exact update, so the ELBO is monotone by construction;
    a generic gradient optimiser would transfer to other models but lose that
    guarantee.

DESIGN DECISION - the variational Gaussian mixture keeps one Normal--Gamma factor per
    component and the ``E[ln pi_j]`` coupling in the responsibilities.
    Dropping the coupling term makes the responsibilities a plain softmax and breaks
    monotonicity; carrying it is what makes coordinate ascent valid.

DESIGN DECISION - the correlated-Gaussian limit uses the closed-form reverse-KL
    optimum rather than an iterative fit.
    For a factorised ``q`` the optimal marginal precision is the diagonal of the target
    precision, so each marginal variance is exactly ``1 - rho^2``; the cost is that it
    is a two-dimensional special case, not a general structured-VI routine.

Run `python3 check.py` to see the steps. `_digamma` and `demo` are scaffolding,
not graded; everything else raises NotImplementedError until you write it.
"""

import math
import random

__all__ = [
    "gaussian_logpdf",
    "mean_field_gaussian",
    "log_evidence_known",
    "elbo",
    "variational_gmm",
    "correlated_gaussian_vb",
]


def gaussian_logpdf(x, mu, var):
    """Log density of N(x | mu, var). Requires var > 0."""
    raise NotImplementedError("gaussian_logpdf")


def _digamma(x):
    """Digamma psi(x) for x > 0: recurrence up to 6, then an asymptotic series.

    Scaffolding: `math` has no digamma, and the mean-field expectations
    E[ln tau] = psi(a) - log(b) and E[ln pi] need it.
    """
    if x <= 0.0:
        raise ValueError("digamma: argument must be positive")
    result = 0.0
    while x < 6.0:
        result -= 1.0 / x
        x += 1.0
    inv = 1.0 / x
    inv2 = inv * inv
    result += (
        math.log(x)
        - 0.5 * inv
        - inv2
        * (
            1.0 / 12.0
            - inv2
            * (
                1.0 / 120.0
                - inv2
                * (1.0 / 252.0 - inv2 * (1.0 / 240.0 - inv2 / 132.0))
            )
        )
    )
    return result


def elbo(xs, params, mu0=0.0, lambda0=1.0, a0=1.0, b0=1.0):
    """ELBO at the given factorised `params` (dict with mu, lambda, a, b).

    Assemble E[ln p(D, mu, tau)] - E[ln q(mu)] - E[ln q(tau)], keeping every
    normalising constant so the value can be compared with the exact log
    evidence. The expectations E[ln tau] use `_digamma`, and q(mu)'s entropy is
    the Gaussian entropy 0.5 log(2 pi e / lambda).
    """
    raise NotImplementedError("elbo")


def mean_field_gaussian(xs, mu0=0.0, lambda0=1.0, a0=1.0, b0=1.0,
                        maxit=200, tol=1e-10):
    """Mean-field VI for N(x | mu, tau^-1) with a Normal--Gamma prior.

    q(mu, tau) = N(mu | m, 1/lambda) * Gamma(tau | a, b). Alternating the two
    exact coordinate updates is hill-climbing on `elbo`: update q(mu) with
    lambda = (lambda0 + N) E[tau], then q(tau) with a = a0 + (N+1)/2 and b from
    the quadratic terms under the new q(mu). Iterate until the ELBO stops moving
    (and for at least three sweeps). Returns `(params, elbos, bound)` where
    `params` carries `mu`, `lambda`, `a`, `b`, `tau` (= E[tau]) and `variance`.
    """
    raise NotImplementedError("mean_field_gaussian")


def log_evidence_known(xs, mu0=0.0, lambda0=1.0, a0=1.0, b0=1.0):
    """Exact log marginal likelihood of the Normal--Gamma model.

    Integrate mu out first (a Gaussian convolution), then tau (a Gamma
    integral): p(D) = (2 pi)^{-N/2} sqrt(lambda0/(lambda0+N))
    b0^{a0}/Gamma(a0) Gamma(aN)/bN^{aN}, with aN = a0 + N/2 and
    bN = b0 + (S + lambda0 N/(lambda0+N)(xbar - mu0)^2)/2. The ELBO must sit at
    or below this value.
    """
    raise NotImplementedError("log_evidence_known")


def _gmm_elbo(xs, r, alpha, beta, m, a, b, alpha0, m0, beta0, a0, b0):
    """ELBO of the variational Gaussian mixture at the given factors.

    Sum the expected log joint -- q(pi) Dirichlet, q(mu_j, tau_j) Normal--Gamma,
    q(Z) responsibilities -- over the three entropies H(Z), H(pi) and the
    Normal--Gamma joint entropy. The E[ln pi_j] coupling must appear inside the
    term that the responsibilities maximise.
    """
    raise NotImplementedError("_gmm_elbo")


def variational_gmm(xs, k, maxit=200, rng=None, alpha0=1.0, m0=None,
                    beta0=1.0, a0=1.0, b0=1.0, tol=1e-10):
    """Mean-field variational Gaussian mixture; returns `(elbos, resp)`.

    Initialise soft responsibilities at random, then alternate: compute the
    posterior parameters N_j, xbar_j, S_j, update alpha/beta/m/a/b, and set the
    responsibilities to the softmax of
    E[ln pi_j] + 0.5 E[ln tau_j] - 0.5 log 2 pi - 0.5 E[tau_j (x_n - mu_j)^2].
    Append `_gmm_elbo` each sweep; it must not decrease. `resp[n][j]` is the
    posterior over assignments.
    """
    raise NotImplementedError("variational_gmm")


def correlated_gaussian_vb(rho, maxit=200, tol=1e-13):
    """Mean-field fit of a 2-D Gaussian with correlation `rho`.

    Target precision [[1, -rho], [-rho, 1]]/(1-rho^2). Under a factorised
    q(x) = q(x1) q(x2) the reverse-KL optimal marginal precision is the matching
    diagonal entry, so each fitted marginal variance is 1 - rho^2, strictly
    below the true marginal variance of 1. Returns `[v1, v2]`.
    """
    raise NotImplementedError("correlated_gaussian_vb")


# ---------------------------------------------------------------------------
# Demo -- scaffolding, left implemented. It calls the functions above.
# ---------------------------------------------------------------------------

def _demo_gaussian():
    rng = random.Random(7)
    true_mu, true_var = 1.5, 2.0
    xs = [rng.gauss(true_mu, math.sqrt(true_var)) for _ in range(400)]
    params, elbos, _ = mean_field_gaussian(xs)
    evidence = log_evidence_known(xs)
    print(
        "mean-field q(mu): mu = %.3f (true %.3f), E[tau] = %.3f (true %.3f)"
        % (params["mu"], true_mu, params["tau"], 1.0 / true_var)
    )
    print(
        "ELBO %.3f -> %.3f over %d sweeps, monotone: %s, <= log evidence %.3f: %s"
        % (
            elbos[0],
            elbos[-1],
            len(elbos),
            all(elbos[i + 1] >= elbos[i] - 1e-9 for i in range(len(elbos) - 1)),
            evidence,
            elbos[-1] <= evidence + 1e-9,
        )
    )


def _demo_gmm():
    rng = random.Random(21)
    xs = []
    for mu in (-6.0, 0.0, 6.0):
        xs.extend(rng.gauss(mu, 0.6) for _ in range(40))
    elbos, resp = variational_gmm(xs, 3, rng=random.Random(21))
    masses = [sum(row[j] for row in resp) for j in range(3)]
    means = [
        sum(resp[i][j] * xs[i] for i in range(len(xs))) / masses[j] for j in range(3)
    ]
    order = sorted(range(3), key=lambda j: means[j])
    print("variational GMM means: [%s]" % ", ".join("%.2f" % means[j] for j in order))
    print(
        "ELBO %.3f -> %.3f, monotone: %s"
        % (
            elbos[0],
            elbos[-1],
            all(elbos[i + 1] >= elbos[i] - 1e-9 for i in range(len(elbos) - 1)),
        )
    )


def _demo_correlated():
    for rho in (0.5, 0.9, 0.99):
        v = correlated_gaussian_vb(rho)
        print(
            "rho = %.2f: fitted marginal variances %.4f, true 1.0 (understated by "
            "%.1f%%)" % (rho, v[0], 100.0 * (1.0 - v[0]))
        )


def demo():
    _demo_gaussian()
    _demo_gmm()
    _demo_correlated()


if __name__ == "__main__":
    demo()
