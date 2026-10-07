"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every graded function from chapter 11 of Bishop is listed, so make_templates
stubs it and replaces its body with ``raise NotImplementedError``. The ``Chain``
container, the small vector helpers, the autocorrelation helpers
(``_autocovariance``, ``_ess_scalar``), the cost reporters (``gradient_count``,
``target_eval_count``) and the demonstration scaffolding are left implemented:
they are not part of the node's deliverable.
"""

HINTS = {
 "sampling.py": {
  "rejection_sample":
      "Return a Chain of exactly n ACCEPTED samples. Loop: x = propose(rng); "
      "proposals += 1; accept x when rng.random() * M * proposal_pdf(x) <= "
      "target_pdf(x). Count the candidates in chain.proposals. Always accepting "
      "returns draws from the proposal, not the target (the planted bug).",
  "importance_sample":
      "Draw n proposals; w_i = exp(target_logpdf(x_i) - proposal_logpdf(x_i)). "
      "Return a dict: estimate = (1/n) sum w_i f(x_i) (unbiased when the target "
      "is normalised); self_normalised = sum w_i f(x_i) / sum w_i (DIVIDE by the "
      "weight sum -- dropping the division is the planted bug and makes the "
      "value scale with n); weights = the raw ratios; ess = (sum w)^2 / sum "
      "w^2, computed on weights divided by their maximum to avoid overflow.",
  "metropolis_hastings":
      "Return a Chain of steps + 1 states starting at x0. For each step draw y = "
      "propose(x, rng) and accept when "
      "log(rng.random()) < min(0.0, log_target(y) - log_target(x)). The min(0, .) "
      "floor makes an uphill move certain and a downhill move occasional; "
      "keeping only 0 accepts every step (the planted bug). Record target_evals.",
  "gibbs_sample":
      "Return a Chain of steps + 1 state tuples starting at x0. Each sweep "
      "redraws EVERY coordinate: x[i] = cond_samplers[i](x, rng), in order, in "
      "place. Sweeping only the first coordinate freezes the rest at x0 and is "
      "the planted bug.",
  "hmc":
      "Return a Chain of steps + 1 states. Each step: p ~ N(0, I); save "
      "H_start = -log_target(x) + |p|^2/2; half momentum kick p += (eps/2) grad; "
      "then for i in range(L): x += eps p, and if i != L - 1 p += eps grad; "
      "then a final half kick p += (eps/2) grad. Accept the endpoint with "
      "log(u) < min(0, H_start - H_end); on rejection restore x. Count L + 1 "
      "gradients per step (two half kicks plus L - 1 full kicks) and one target "
      "evaluation per step beyond the initial. Dropping the half kicks (a "
      "forward Euler step) breaks energy conservation and is the planted bug.",
  "effective_sample_size":
      "Scalar chain: Geyer's initial-positive-sequence estimate n / (1 + 2 sum "
      "of consecutive autocorrelation PAIRS), truncated at the first "
      "non-positive pair, clamped to [1, n] (the _ess_scalar helper does this). "
      "Vector chain: the minimum over coordinates. Returning the chain length "
      "regardless of autocorrelation is the planted bug.",
 },
}
