"""
Variational inference from scratch, stdlib only.

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
    monotonicity, but keeping the constants makes ``elbo`` a true lower bound on the
    exact log evidence, so the checker can assert ``ELBO <= log evidence`` rather than
    merely watching it rise. The cost is a few ``lgamma``/``digamma`` calls per sweep.

DESIGN DECISION - the mean-field updates are the closed-form coordinate maxima, with
    the shape ``a = a0 + (N + 1) / 2`` fixed by the Normal--Gamma conjugacy.
    A generic gradient or black-box optimiser would work on any model, but the
    conjugate pair gives an exact update, so the ELBO is monotone by construction. The
    cost is that the update does not transfer unchanged to a non-conjugate model.

DESIGN DECISION - the variational Gaussian mixture keeps one Normal--Gamma factor per
    component and the ``E[ln pi_j]`` coupling in the responsibilities.
    Dropping the coupling term makes the responsibilities a plain softmax and breaks
    the monotonicity of the ELBO; carrying it is what makes coordinate ascent valid.
    The cost is a Dirichlet term and its entropy in every ELBO evaluation.

DESIGN DECISION - the correlated-Gaussian limit uses the closed-form reverse-KL
    optimum rather than an iterative fit.
    For a factorised ``q`` the optimal marginal precision is the diagonal of the
    target precision, so each marginal variance is exactly ``1 - rho^2``; the closed
    form makes the mode-seeking shrinkage unambiguous. The cost is that it is a
    two-dimensional special case, not a general structured-VI routine.

Run `python3 variational.py` for the demo. No third-party imports: `math` and
`random` only. Reference implementation, not a template.
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
    if var <= 0.0:
        raise ValueError("gaussian_logpdf: variance must be positive")
    return -0.5 * (math.log(2.0 * math.pi * var) + (x - mu) ** 2 / var)


def _digamma(x):
    """Digamma psi(x) for x > 0: recurrence up to 6, then an asymptotic series.

    `math` has no digamma. The mean-field expectations E[ln tau] = psi(a) -
    log(b) and E[ln pi] need it, so it is worth the ten lines.
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


# ---------------------------------------------------------------------------
# Mean-field VI for a univariate Gaussian with unknown mean and precision
# ---------------------------------------------------------------------------
#
# p(mu, tau) = N(mu | mu0, 1/(lambda0 tau)) * Gamma(tau | a0, b0)   (shape/rate)
# q(mu, tau) = N(mu | m, 1/lambda) * Gamma(tau | a, b)
#
# The a-update is independent of the rest, a = a0 + (N+1)/2; the paper's algebra
# is restated in the README, never copied.

def _elbo_gaussian(xs, mu0, lambda0, a0, b0, mu, lam, a, b):
    """ELBO of the factorised q for the Normal--Gamma model.

    E[ln p(D, mu, tau)] - E[ln q(mu)] - E[ln q(tau)], every constant kept so the
    value can be compared with the exact log evidence.
    """
    n = len(xs)
    s = 1.0 / lam
    Eln_tau = _digamma(a) - math.log(b)
    E_tau = a / b

    # E[ln p(D | mu, tau)] -- the N Gaussian log densities under q.
    exp_sumsq = sum((x - mu) ** 2 for x in xs) + n * s
    term_lik = (
        0.5 * n * Eln_tau - 0.5 * n * math.log(2.0 * math.pi) - 0.5 * E_tau * exp_sumsq
    )

    # E[ln p(mu | tau)]
    exp_mu_dev = (mu - mu0) ** 2 + s
    term_prior_mu = (
        0.5 * math.log(lambda0)
        + 0.5 * Eln_tau
        - 0.5 * math.log(2.0 * math.pi)
        - 0.5 * lambda0 * E_tau * exp_mu_dev
    )

    # E[ln p(tau)]
    term_prior_tau = (
        a0 * math.log(b0)
        - math.lgamma(a0)
        + (a0 - 1.0) * Eln_tau
        - b0 * E_tau
    )

    # Differential entropies.
    entropy_mu = 0.5 * math.log(2.0 * math.pi * math.e * s)
    entropy_tau = a - math.log(b) + math.lgamma(a) + (1.0 - a) * _digamma(a)

    return term_lik + term_prior_mu + term_prior_tau + entropy_mu + entropy_tau


def elbo(xs, params, mu0=0.0, lambda0=1.0, a0=1.0, b0=1.0):
    """ELBO at the given factorised `params` (dict with mu, lambda, a, b)."""
    return _elbo_gaussian(
        list(xs),
        mu0,
        lambda0,
        a0,
        b0,
        params["mu"],
        params["lambda"],
        params["a"],
        params["b"],
    )


def mean_field_gaussian(xs, mu0=0.0, lambda0=1.0, a0=1.0, b0=1.0,
                        maxit=200, tol=1e-10):
    """Mean-field VI for N(x | mu, tau^-1) with a Normal--Gamma prior.

    Alternates the two exact coordinate updates until the ELBO stops moving (and
    for at least three sweeps, so the returned sequence always shows the trend).
    Returns `(params, elbos, bound)` where `params` carries `mu`, `lambda`
    (the precision of q(mu)), `a`, `b`, `tau` (= E[tau]) and `variance`.
    """
    xs = list(xs)
    n = len(xs)
    if n == 0:
        raise ValueError("mean_field_gaussian: need at least one observation")
    xbar = sum(xs) / n

    # q(tau) shape does not depend on the other factor.
    a = a0 + (n + 1.0) / 2.0
    b = b0 + 0.5
    mu = (lambda0 * mu0 + n * xbar) / (lambda0 + n)
    lam = lambda0 + n

    elbos = []
    prev = None
    for it in range(max(3, maxit)):
        # q(mu) given q(tau): the precision is scaled by E[tau].
        E_tau = a / b
        lam = (lambda0 + n) * E_tau
        mu = (lambda0 * mu0 + n * xbar) / (lambda0 + n)
        s = 1.0 / lam

        # q(tau) given q(mu): collect the quadratic terms under q(mu).
        exp_sumsq = sum((x - mu) ** 2 for x in xs) + n * s
        exp_mu_dev = (mu - mu0) ** 2 + s
        a = a0 + (n + 1.0) / 2.0
        b = b0 + 0.5 * exp_sumsq + 0.5 * lambda0 * exp_mu_dev

        value = _elbo_gaussian(xs, mu0, lambda0, a0, b0, mu, lam, a, b)
        elbos.append(value)
        if (
            prev is not None
            and it >= 2
            and abs(value - prev) <= tol * max(1.0, abs(value))
        ):
            break
        prev = value

    params = {"mu": mu, "lambda": lam, "a": a, "b": b,
              "tau": a / b, "variance": 1.0 / lam}
    return params, elbos, elbos[-1]


def log_evidence_known(xs, mu0=0.0, lambda0=1.0, a0=1.0, b0=1.0):
    """Exact log marginal likelihood of the Normal--Gamma model.

    Closing the integral over mu and then over tau gives

        p(D) = (2 pi)^{-N/2} sqrt(lambda0/(lambda0+N))
               * b0^{a0}/Gamma(a0) * Gamma(aN)/bN^{aN}

    with aN = a0 + N/2 and bN = b0 + (S + lambda0 N/(lambda0+N)
    (xbar - mu0)^2)/2. The ELBO must sit at or below this value.
    """
    xs = list(xs)
    n = len(xs)
    if n == 0:
        raise ValueError("log_evidence_known: need at least one observation")
    xbar = sum(xs) / n
    scatter = sum((x - xbar) ** 2 for x in xs)
    lambda_n = lambda0 + n
    a_n = a0 + n / 2.0
    b_n = b0 + 0.5 * (scatter + (lambda0 * n / lambda_n) * (xbar - mu0) ** 2)
    return (
        -0.5 * n * math.log(2.0 * math.pi)
        + 0.5 * math.log(lambda0 / lambda_n)
        + a0 * math.log(b0)
        - math.lgamma(a0)
        + math.lgamma(a_n)
        - a_n * math.log(b_n)
    )


# ---------------------------------------------------------------------------
# Variational Gaussian mixture (mean-field over Z and the parameters)
# ---------------------------------------------------------------------------
#
# q(pi) = Dirichlet(alpha);  q(mu_j, tau_j) = Normal--Gamma(m_j, beta_j, a_j, b_j);
# q(Z) = product_n Categorical(r_n). The coordinate updates are the standard
# variational E/M pair; the ELBO below is assembled term by term from the
# expected log joint and the three entropies.

def _gmm_elbo(xs, r, alpha, beta, m, a, b, alpha0, m0, beta0, a0, b0):
    n = len(xs)
    k = len(alpha)
    alpha_hat = sum(alpha)
    psi_hat = _digamma(alpha_hat)
    Eln_pi = [_digamma(al) - psi_hat for al in alpha]
    Eln_tau = [_digamma(aj) - math.log(bj) for aj, bj in zip(a, b)]
    E_tau = [aj / bj for aj, bj in zip(a, b)]

    # E[ln p(pi)] under Dirichlet(alpha).
    term_pi = (
        math.lgamma(k * alpha0)
        - k * math.lgamma(alpha0)
        + (alpha0 - 1.0) * sum(Eln_pi)
    )

    # E[ln p(mu_j | tau_j)] and E[ln p(tau_j)].
    term_mu = 0.0
    term_tau = 0.0
    for j in range(k):
        term_mu += (
            0.5 * math.log(beta0 / (2.0 * math.pi))
            + 0.5 * Eln_tau[j]
            - 0.5 * beta0 * (E_tau[j] * (m[j] - m0) ** 2 + 1.0 / beta[j])
        )
        term_tau += (
            a0 * math.log(b0)
            - math.lgamma(a0)
            + (a0 - 1.0) * Eln_tau[j]
            - b0 * E_tau[j]
        )

    # E[ln p(X | Z, mu, tau)] and E[ln p(Z | pi)] -- the latter carries the
    # E[ln pi_j] coupling that the responsibilities maximise.
    term_z = 0.0
    for i in range(n):
        for j in range(k):
            exp_quad = E_tau[j] * (xs[i] - m[j]) ** 2 + 1.0 / beta[j]
            term_z += r[i][j] * (
                Eln_pi[j]
                + 0.5 * Eln_tau[j]
                - 0.5 * math.log(2.0 * math.pi)
                - 0.5 * exp_quad
            )

    # Entropies: q(Z), Dirichlet q(pi), Normal--Gamma q(mu_j, tau_j).
    entropy_z = -sum(
        r[i][j] * math.log(r[i][j])
        for i in range(n)
        for j in range(k)
        if r[i][j] > 1e-300
    )
    ln_b = sum(math.lgamma(al) for al in alpha) - math.lgamma(alpha_hat)
    entropy_pi = (
        ln_b + (alpha_hat - k) * psi_hat - sum((al - 1.0) * _digamma(al) for al in alpha)
    )
    entropy_theta = 0.0
    for j in range(k):
        entropy_theta += (
            0.5
            + 0.5 * math.log(2.0 * math.pi)
            - 0.5 * math.log(beta[j])
            - a[j] * math.log(b[j])
            + math.lgamma(a[j])
            + (0.5 - a[j]) * Eln_tau[j]
            + b[j] * E_tau[j]
        )

    return (
        term_pi
        + term_mu
        + term_tau
        + term_z
        + entropy_z
        + entropy_pi
        + entropy_theta
    )


def variational_gmm(xs, k, maxit=200, rng=None, alpha0=1.0, m0=None,
                    beta0=1.0, a0=1.0, b0=1.0, tol=1e-10):
    """Mean-field variational Gaussian mixture; returns `(elbos, resp)`.

    Responsibilities `resp[n][j]` are the variational posterior over assignments.
    The ELBO sequence has one entry per sweep and, by construction of coordinate
    ascent, never decreases.
    """
    xs = list(xs)
    n = len(xs)
    if n == 0:
        raise ValueError("variational_gmm: need at least one observation")
    if k < 1:
        raise ValueError("variational_gmm: need at least one component")
    if rng is None:
        rng = random.Random(0)
    if m0 is None:
        m0 = sum(xs) / n

    # Random soft responsibilities, normalised across components.
    resp = []
    for _ in range(n):
        row = [rng.random() + 1e-3 for _ in range(k)]
        total = sum(row)
        resp.append([v / total for v in row])

    elbos = []
    prev = None
    for it in range(max(3, maxit)):
        n_j = [sum(resp[i][j] for i in range(n)) for j in range(k)]
        xbar = []
        for j in range(k):
            if n_j[j] > 1e-12:
                xbar.append(sum(resp[i][j] * xs[i] for i in range(n)) / n_j[j])
            else:
                xbar.append(0.0)
        s_j = []
        for j in range(k):
            if n_j[j] > 1e-12:
                s_j.append(
                    sum(resp[i][j] * (xs[i] - xbar[j]) ** 2 for i in range(n))
                    / n_j[j]
                )
            else:
                s_j.append(0.0)

        alpha = [alpha0 + n_j[j] for j in range(k)]
        beta = [beta0 + n_j[j] for j in range(k)]
        m = [(beta0 * m0 + n_j[j] * xbar[j]) / beta[j] for j in range(k)]
        a = [a0 + n_j[j] / 2.0 for j in range(k)]
        b = [
            b0
            + 0.5 * n_j[j] * s_j[j]
            + 0.5 * (beta0 * n_j[j] / beta[j]) * (xbar[j] - m0) ** 2
            for j in range(k)
        ]

        # Variational E-step: rho_nj = exp(E[ln pi_j] + 0.5 E[ln tau_j]
        #   - 0.5 log 2pi - 0.5 E[tau_j (x_n - mu_j)^2]).
        alpha_hat = sum(alpha)
        log_pi = [_digamma(al) - _digamma(alpha_hat) for al in alpha]
        log_tau = [_digamma(aj) - math.log(bj) for aj, bj in zip(a, b)]
        E_tau = [aj / bj for aj, bj in zip(a, b)]
        new_resp = []
        for i in range(n):
            logs = []
            for j in range(k):
                exp_quad = E_tau[j] * (xs[i] - m[j]) ** 2 + 1.0 / beta[j]
                logs.append(
                    log_pi[j] + 0.5 * log_tau[j] - 0.5 * math.log(2.0 * math.pi)
                    - 0.5 * exp_quad
                )
            hi = max(logs)
            weights = [math.exp(v - hi) for v in logs]
            total = sum(weights)
            new_resp.append([v / total for v in weights])
        resp = new_resp

        value = _gmm_elbo(xs, resp, alpha, beta, m, a, b, alpha0, m0, beta0, a0, b0)
        elbos.append(value)
        if (
            prev is not None
            and it >= 2
            and abs(value - prev) <= tol * max(1.0, abs(value))
        ):
            break
        prev = value

    return elbos, resp


# ---------------------------------------------------------------------------
# The reverse-KL limit case: mean-field on a correlated Gaussian
# ---------------------------------------------------------------------------

def correlated_gaussian_vb(rho, maxit=200, tol=1e-13):
    """Mean-field fit of a 2-D Gaussian with correlation `rho`.

    The target has unit marginal variances and covariance `rho`; its precision
    matrix is `[[1, -rho], [-rho, 1]] / (1 - rho^2)`. Under a factorised
    `q(x) = q(x1) q(x2)` the reverse-KL optimal marginal precision is the
    diagonal of the target precision, so each fitted marginal variance is
    `1 - rho^2` -- strictly smaller than the true marginal variance of 1. That
    shrinkage toward the modes is the mode-seeking face of the reverse KL.
    Returns `[v1, v2]`.
    """
    if not -1.0 < rho < 1.0:
        raise ValueError("correlated_gaussian_vb: need |rho| < 1")
    denom = 1.0 - rho * rho
    precision = [[1.0 / denom, -rho / denom], [-rho / denom, 1.0 / denom]]
    # Coordinate ascent on the factorised Gaussian: one factor at a time, the
    # optimal precision is the matching diagonal entry. The means of the target
    # are zero, so the optimal factor means sit at zero immediately; the
    # variances are what the fit changes.
    means = [0.0, 0.0]
    variances = [1.0, 1.0]
    for _ in range(max(1, maxit)):
        new_variances = list(variances)
        for j in range(2):
            # E[x_j] given the other factor, then the conditional precision.
            shift = 0.0
            for i in range(2):
                if i != j:
                    shift += precision[j][i] * means[i]
            means[j] = -shift / precision[j][j]
            new_variances[j] = 1.0 / precision[j][j]
        if max(abs(new_variances[j] - variances[j]) for j in range(2)) <= tol:
            variances = new_variances
            break
        variances = new_variances
    return variances


# ---------------------------------------------------------------------------
# Demo
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
    print(
        "variational GMM means: [%s]"
        % ", ".join("%.2f" % means[j] for j in order)
    )
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
