"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every graded function from Bishop's chapter 4 (linear models for classification) is
listed, so make_templates stubs it and replaces its body with `raise
NotImplementedError`. The small dense-linear-algebra helpers (`_design`, `_dot`,
`_solve`, `_inverse`, `_gram`, `_gradient`), the fixed data builders and the demo are
left implemented: they are infrastructure the exercise stands on, not the classifier
itself.
"""

HINTS = {
 "classification.py": {
  "sigmoid":
      "The logistic sigmoid 1/(1+exp(-z)). Guard the tails: for z < 0 use exp(z)/(1+exp(z)) "
      "to avoid overflow. It is NOT z/(1+|z|) and it is not an off-by-one shift.",
  "least_squares_classifier":
      "Solve the normal equations (Phi^T Phi) w = Phi^T t with the 0/1 targets and the "
      "bias column already in Phi. Return the weight vector [bias, w_1, ...].",
  "fisher_lda":
      "w = S_W^{-1} (m_1 - m_0): invert the WITHIN-class scatter, not the identity, or "
      "the direction collapses to the plain difference of means. Threshold at the midpoint "
      "of the two projected class means. Return (direction, threshold).",
  "perceptron":
      "Map 0/1 to +1/-1, then sweep: for every point with y (w . phi) <= 0, update "
      "w <- w + y phi. One pass with no mistakes stops the loop. Return (w, passes).",
  "logistic_irls":
      "Newton on the negative log posterior. Each step: p = sigmoid(Phi w), "
      "R = diag(p(1-p)), solve (Phi^T R Phi + ridge I) step = Phi^T (t - p) - ridge w, "
      "w <- w + step. Stop when ||gradient|| < tol; count the updates. Dropping the "
      "p(1-p) factor turns Newton into a much slower fixed-metric iteration.",
  "logistic_gradient_descent":
      "The same objective without curvature: w <- w - lr * gradient, with gradient = "
      "-Phi^T (t - p) + ridge w. Stop on the same ||gradient|| < tol and return the update "
      "count, so it can be compared with IRLS at an identical tolerance.",
  "laplace_logistic":
      "MAP weights = IRLS with ridge = 1 / prior_var. Then the Gaussian approximation is "
      "N(w_MAP, S_N) with S_N = (Phi^T R Phi + ridge I)^{-1}, R = diag(p(1-p)) at the MAP. "
      "The mean is the MAP estimate, NOT 0 and NOT the prior mean; return (mean, covariance).",
 },
}
