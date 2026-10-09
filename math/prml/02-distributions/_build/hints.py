"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every graded function from Bishop's chapter 2 (and Murphy's matching material) is
listed, so make_templates stubs it and replaces its body with `raise
NotImplementedError`. The Gaussian-kernel helper `_gaussian_kernel` and the demo are
left implemented: scaffolding, not the deliverable.
"""

HINTS = {
 "distributions.py": {
  "beta_bernoulli_update":
      "Posterior of a Beta(alpha, beta) prior after `heads` ones and `tails` zeros: "
      "add heads to alpha and tails to beta, returning (alpha + heads, beta + tails). "
      "Do not swap them.",
  "beta_mean":
      "alpha / (alpha + beta).",
  "dirichlet_multinomial_update":
      "Each multinomial count adds to the matching prior concentration: "
      "[a_i + counts_i]. Keep the prior; never return the counts alone.",
  "gaussian_mle":
      "mean = sum(xs) / N; variance = sum((x - mean)**2) / N. The 1/N normaliser is "
      "the maximum-likelihood choice and is biased low.",
  "gaussian_sequential_update":
      "One online conjugate update of a Gaussian mean with known observation variance. "
      "With tau = 1/prior_variance and obs = 1/sigma**2: tau_new = tau + obs; "
      "mu_new = (tau * mu + x * obs) / tau_new. This weights the prior by its precision; "
      "it is NOT a plain running average.",
  "gaussian_posterior":
      "Batch closed form: tau = 1/sigma0**2 + N/sigma**2; "
      "mu = (mu0/sigma0**2 + sum(xs)/sigma**2) / tau. Return (mu, tau).",
  "sufficient_stats":
      "Bernoulli -> (n, sum(xs)); Gaussian -> (n, sum(xs), sum(x*x)).",
  "gaussian_from_sufficient_stats":
      "From (n, total, total_sq): mean = total/n; variance = total_sq/n - mean**2.",
  "natural_parameters":
      "Bernoulli -> logit(sum/n) = log((sum/n) / (1 - sum/n)); "
      "Gaussian with known sigma -> (sum/n) / sigma**2.",
  "log_partition":
      "Bernoulli -> log(1 + exp(eta)), evaluated stably with the max(eta, 0) trick; "
      "Gaussian with known sigma -> sigma**2 * eta**2 / 2.",
  "log_partition_gradient":
      "A'(eta): the sigmoid 1/(1 + exp(-eta)) for the Bernoulli; sigma**2 * eta for "
      "the Gaussian. This must equal the mean.",
  "exponential_family_stats":
      "Bundle sufficient_stats, natural_parameters, log_partition_gradient and "
      "log_partition into a dict with keys stats, eta, mean, log_partition. mean is "
      "A'(eta).",
  "histogram_density":
      "For each bin [edges[i], edges[i+1]) (last edge inclusive) return "
      "count / (n * (hi - lo)), so the histogram integrates to one.",
  "kde":
      "Gaussian kernel density: (1/(n*h)) * sum_i _gaussian_kernel((x - x_i)/h). Both "
      "the kernel and the 1/(n h) normalisation are required.",
  "knn_density":
      "Sort the distances |x_i - x|; r is the k-th smallest. Return k / (n * 2*r); "
      "the 2r is the one-dimensional ball volume.",
 },
}
