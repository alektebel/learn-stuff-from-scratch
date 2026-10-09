"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every graded function from Bishop's chapter 3 (and Murphy's matching material) is
listed, so make_templates stubs it and replaces its body with `raise
NotImplementedError`. The small dense-linear-algebra helpers (`solve_linear`,
`inverse`, `log_det`, `_gram`, `_rhs`) and the demo are left implemented: they are
infrastructure the exercise stands on, not the regression itself.
"""

HINTS = {
 "regression.py": {
  "design_matrix":
      "One row per input x, one column per basis callable: Phi[i][j] = basis[j](xs[i]). "
      "Return a list of lists of floats.",
  "mle_weights":
      "Normal equations: solve (Phi^T Phi) w = Phi^T t. Return None when the system is "
      "singular (rank(Phi) < M, e.g. fewer points than basis functions): the MLE is then "
      "not unique, so do not invent a vector. Catch the ValueError from solve_linear.",
  "ridge_weights":
      "Solve (alpha I + Phi^T Phi) w = Phi^T t: add alpha to EVERY diagonal entry "
      "(there is no unpenalised intercept column). alpha > 0 makes it non-singular even "
      "when Phi^T Phi is not. Do not subtract alpha.",
  "bayesian_posterior":
      "S_N^{-1} = alpha I + beta Phi^T Phi and m_N = beta S_N Phi^T t. Multiply EVERY "
      "entry of Phi^T Phi and of Phi^T t by beta (a common bug drops beta from the "
      "Phi^T Phi side). Return (mean, covariance) with covariance = inverse(S_N^{-1}).",
  "predictive_distribution":
      "For each row phi: mean = phi . m_N, variance = 1/beta + phi^T S_N phi. The 1/beta "
      "observation-noise term is the floor and must not be dropped.",
  "log_evidence":
      "ln p(t|alpha,beta) = M/2 ln alpha + N/2 ln beta - E(m_N) - N/2 ln(2 pi) + "
      "1/2 ln|S_N|, with E(m_N) = beta/2 ||t - Phi m_N||^2 + alpha/2 m_N^T m_N and "
      "S_N^{-1} = alpha I + beta Phi^T Phi. Note ln|S_N| = -ln|S_N^{-1}|; omitting the "
      "Occam term lets the grid run to the smallest alpha.",
  "maximise_evidence":
      "Grid-search alphas x betas and return the (alpha, beta) with the largest "
      "log_evidence. Skip non-positive values; ties go to the first pair so the result "
      "is deterministic. Return the pair, not just its value.",
 },
}
