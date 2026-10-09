"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every graded function from Bishop's chapter 10 (and Murphy's matching chapter 10)
is listed, so make_templates stubs it and replaces its body with `raise
NotImplementedError`. The helper `_digamma` and the demo are left implemented:
scaffolding, not the deliverable.
"""

HINTS = {
 "variational.py": {
  "gaussian_logpdf":
      "Univariate Gaussian log density: -0.5 * (log(2*pi*var) + (x - mu)**2 / var). "
      "Raise ValueError if var <= 0.",
  "elbo":
      "Assemble E[ln p(D, mu, tau)] - E[ln q(mu)] - E[ln q(tau)] from the factorised "
      "q(mu) = N(m, 1/lambda) and q(tau) = Gamma(a, b), keeping every constant. The "
      "likelihood term is 0.5*N*E[ln tau] - 0.5*N*log(2*pi) - 0.5*E[tau]*(sum "
      "(x-m)^2 + N/lambda); the Normal--Gamma prior contributes the mu and tau prior "
      "expectations; the entropies are 0.5*log(2*pi*e/lambda) and "
      "a - log(b) + lgamma(a) + (1-a)*psi(a). E[ln tau] = psi(a) - log(b) via _digamma.",
  "mean_field_gaussian":
      "Coordinate ascent. q(mu): lambda = (lambda0 + N) * E[tau] and "
      "m = (lambda0*mu0 + N*xbar)/(lambda0 + N). q(tau): a = a0 + (N+1)/2 and "
      "b = b0 + 0.5*(sum (x-m)^2 + N/lambda) + 0.5*lambda0*((m-mu0)^2 + 1/lambda). "
      "Recompute `elbo` after each full sweep and append it; stop when it stops "
      "moving, but always record at least three sweeps. Return (params, elbos, "
      "elbos[-1]) with params carrying mu, lambda, a, b, tau = a/b, variance = 1/lambda.",
  "log_evidence_known":
      "Integrate mu out first, then tau. log p(D) = -N/2 log(2 pi) + 0.5 "
      "log(lambda0/(lambda0+N)) + a0 log b0 - lgamma(a0) + lgamma(aN) - aN log bN, "
      "with aN = a0 + N/2 and bN = b0 + (S + (lambda0 N/(lambda0+N))(xbar-mu0)^2)/2.",
  "_gmm_elbo":
      "Sum the expected log joint and the entropies. E[ln p(pi)] under Dirichlet(alpha0); "
      "for each component E[ln p(mu_j | tau_j)] and E[ln p(tau_j)] with the Normal--Gamma "
      "prior; E[ln p(X | Z, mu, tau)] = sum_n sum_j r_nj [0.5 E[ln tau_j] - 0.5 log 2 pi "
      "- 0.5 (E[tau_j](x_n - m_j)^2 + 1/beta_j)]; and the coupling E[ln p(Z | pi)] = "
      "sum_n sum_j r_nj E[ln pi_j]. Entropies: H(Z) = -sum r log r, the Dirichlet "
      "entropy ln B(alpha) + (alpha_hat - K) psi(alpha_hat) - sum (alpha_j - 1) psi(alpha_j), "
      "and the Normal--Gamma joint entropy 0.5 + 0.5 log 2 pi - 0.5 log beta_j - a_j log b_j "
      "+ lgamma(a_j) + (0.5 - a_j) E[ln tau_j] + b_j E[tau_j].",
  "variational_gmm":
      "Initialise soft responsibilities at random and normalise. Each sweep: N_j = sum_i "
      "r_ij, xbar_j, S_j; alpha_j = alpha0 + N_j, beta_j = beta0 + N_j, "
      "m_j = (beta0 m0 + N_j xbar_j)/beta_j, a_j = a0 + N_j/2, b_j = b0 + 0.5 N_j S_j + "
      "0.5 (beta0 N_j/beta_j)(xbar_j - m0)^2; then r_nj is the softmax of E[ln pi_j] + "
      "0.5 E[ln tau_j] - 0.5 log 2 pi - 0.5 (E[tau_j](x_n - m_j)^2 + 1/beta_j). Append "
      "_gmm_elbo each sweep. Return (elbos, resp).",
  "correlated_gaussian_vb":
      "The target precision is [[1, -rho], [-rho, 1]]/(1-rho^2). For a factorised Gaussian "
      "the reverse-KL optimum has marginal precision diag(Sigma^-1) and marginal variance "
      "1 - rho^2. Return [1-rho^2, 1-rho^2] (a coordinate loop that sets each factor's "
      "precision to the matching diagonal entry is fine).",
 },
}
