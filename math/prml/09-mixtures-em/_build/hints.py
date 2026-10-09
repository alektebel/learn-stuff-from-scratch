"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every graded function from Bishop's chapter 9 (and Murphy's matching chapter 11) is
listed, so make_templates stubs it and replaces its body with `raise
NotImplementedError`. The helpers `_gmm_loglikelihood` and `_log_bernoulli_mixture`
and the demo are left implemented: scaffolding, not the deliverable.
"""

HINTS = {
 "mixtures.py": {
  "gaussian_logpdf":
      "Univariate Gaussian log density: -0.5 * (log(2*pi*var) + (x - mu)**2 / var). "
      "Assume var > 0; the M-step owns the variance floor.",
  "kmeans":
      "Lloyd's algorithm. Seed k distinct data points (rng.shuffle then take k), "
      "then alternate: assign each x to the nearest centroid by |x - c|, recompute "
      "each centroid as the mean of its members. Reseed an empty cluster on the point "
      "farthest from its centroid. Return (centroids, assignments).",
  "gmm_e_step":
      "Responsibilities P(j | x_i) proportional to prior_j * N(x_i | mu_j, var_j), "
      "normalised across j. Work in log space: log(weight) + gaussian_logpdf, subtract "
      "the row max, exponentiate, divide by the row sum. This is the posterior, not "
      "the prior.",
  "gmm_m_step":
      "N_j = sum_i r_ij; weight_j = N_j / N; mu_j = sum_i r_ij x_i / N_j; "
      "var_j = sum_i r_ij (x_i - mu_j)**2 / N_j, then clamped up to var_floor. "
      "Do NOT return the raw N_j as the weight: the weights must sum to one.",
  "gmm_em":
      "Initialise from K-means (centroids as means, cluster fractions as weights, the "
      "global variance for every component) or from the optional init means. Then loop: "
      "E-step responsibilities, M-step parameters, append the total log-likelihood, "
      "stop when it stops changing. Return (weights, mus, vars, logliks) with the whole "
      "likelihood sequence, starting from the initial parameters.",
  "gmm_em_best":
      "Run gmm_em `restarts` times on the same rng and keep the fit with the highest "
      "final log-likelihood. Keep the BEST, not the first or the last.",
  "bernoulli_mixture_em":
      "xs are 0/1 vectors. Initialise soft responsibilities at random and normalise "
      "them. Loop: M-step weight_j = mean_i r_ij and theta_jt = sum_i r_ij x_it / N_j; "
      "E-step responsibilities from log pi_j + sum_t [x_it log theta + (1-x_it) "
      "log(1-theta)]. Return (pis, thetas, logliks).",
 },
}
