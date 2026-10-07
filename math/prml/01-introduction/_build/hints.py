"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every graded function from Bishop's chapter 1 (and Murphy's matching material) is
listed, so make_templates stubs it and replaces its body with `raise
NotImplementedError`. The constant `TRUE_F` (the target ``sin(2 pi x)``) and the demo
are left implemented: reference data and demonstration scaffolding, not the
deliverable.
"""

HINTS = {
 "intro.py": {
  "poly_features":
      "The feature vector [1, x, x**2, ..., x**degree].",
  "solve_linear":
      "Gaussian elimination with PARTIAL PIVOTING: at each column swap in the row with "
      "the largest |entry|, eliminate below it, then back-substitute. Raise ValueError "
      "when the pivot is ~0 (singular).",
  "poly_fit":
      "Normal equations: A[i][j] = sum_x phi_i(x) phi_j(x), b[i] = sum_x phi_i(x) t. Add "
      "lam to every diagonal entry EXCEPT i == 0 (the bias is not penalised), then "
      "solve_linear(A, b).",
  "poly_predict":
      "sum_k weights[k] * x**k.",
  "squared_error":
      "The mean of (poly_predict(weights, x) - t)**2 over the points.",
  "bias_variance":
      "Simulate n_sets training sets of sin(2 pi x) + N(0, sigma); average the "
      "predictions at fixed test inputs. bias^2 = mean over test of (mean_pred - f)^2; "
      "variance = mean over test of the per-set squared deviation from mean_pred; noise "
      "= sigma^2; the returned error is the average (pred - (f + FRESH test noise))^2, "
      "so the identity error == bias^2 + variance + noise is a real measurement.",
  "min_risk_decision":
      "The action a minimising loss[a][0]*(1-p) + loss[a][1]*p (ties to action 0). Do "
      "NOT fall back to a fixed 0.5 threshold: an asymmetric loss moves the boundary.",
  "entropy":
      "-sum(pi * log(pi) for pi > 0) in nats; skip zero-probability terms.",
  "kl_divergence":
      "sum(pi * log(pi / qi) for pi > 0). Not symmetric; non-negative and zero only for "
      "equal distributions. Do not flip the ratio.",
  "mutual_information":
      "From a 2-D joint: px, py are the marginals; return sum over p_ij > 0 of "
      "p_ij * log(p_ij / (px_i * py_j)). Zero when independent, positive otherwise.",
 },
}
