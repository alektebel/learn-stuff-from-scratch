"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every graded function from chapters 11 and 12 of Blitzstein & Hwang is listed, so
make_templates stubs it and replaces its body with `raise NotImplementedError`.
The small matrix helper ``_matmul`` and the demonstration scaffolding
(``_correlation``, ``_bimodal_log_target``) are left implemented: they are not
part of the node's deliverable.
"""

HINTS = {
 "mcmc.py": {
  "stationary_distribution":
      "Solve pi P = pi with sum pi = 1. Build the linear system: equation j is "
      "sum_i pi_i (P[i][j] - delta_ij) = 0; replace the last (redundant) "
      "equation by sum_i pi_i = 1; solve by Gaussian elimination and normalise. "
      "This is the LEFT eigenvector of P for eigenvalue 1. Using P[j][i] gives "
      "the right eigenvector (uniform here) and is the planted bug.",
  "matrix_power":
      "Return P**n by repeated multiplication (n = 0 is the identity). Used to "
      "expose periodicity: for [[0,1],[1,0]], even powers are I and odd powers "
      "are P, so it never converges.",
  "simulate_chain":
      "Return steps + 1 states starting at `state`. Each step draws U uniform "
      "and walks the cumulative sum of the CURRENT ROW P[current], choosing the "
      "first j with U < cumulative. Walking the column P[.][current] simulates "
      "the transposed chain and is the planted bug.",
  "empirical_distribution":
      "Count how many of `states` fall in each of 0 .. n_states - 1 and divide "
      "by len(states); return the list of fractions.",
  "metropolis_hastings":
      "Return steps + 1 states starting at x0. For each step draw y = "
      "proposal(x, rng) and accept it when "
      "log(rng.random()) < min(0.0, log_target(y) - log_target(x)); the min(0, .) "
      "floor is what makes an uphill move always accepted and a downhill move "
      "only sometimes. Keeping only the 0 accepts every step (the planted bug).",
  "gibbs_sampling":
      "Return steps + 1 state vectors starting at x0. Each sweep redraws EVERY "
      "coordinate: x[i] = cond_samplers[i](x, rng), in order, in place. Sweeping "
      "only the first coordinate freezes the rest at x0 and is the planted bug.",
  "target_mean_var":
      "Return (mean, population variance) of a list of scalars: mean = sum/n; "
      "variance = sum((s - mean)^2) / n.",
 },
}
