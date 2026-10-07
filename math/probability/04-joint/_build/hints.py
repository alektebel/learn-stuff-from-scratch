"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every graded function from chapter 7 of Blitzstein & Hwang is listed, so
make_templates stubs it and replaces its body with `raise NotImplementedError`.
The Box-Muller helper (``_standard_normal_pair``) and ``demo`` are left
implemented: they are demonstration scaffolding, not part of the node's
deliverable.
"""

HINTS = {
 "joint.py": {
  "marginal":
      "axis names the coordinate to KEEP: 0 keeps X (sum the joint over Y), 1 "
      "keeps Y. Dict of (x, y) -> p returns a dict keyed by the kept coordinate; "
      "a matrix joint[i][j] returns a list. Sum along the OTHER axis.",
  "conditional":
      "Divide the row P(X = given, Y = y) by the marginal P(X = given) = "
      "sum_y P(X = given, Y = y). A dict joint returns {y: prob}; a matrix "
      "returns the normalised row as a list. Do NOT divide by 1 or by the number "
      "of outcomes: the conditional must sum to 1.",
  "covariance":
      "(1/n) sum (x - mean_x)(y - mean_y), the population convention, because "
      "the lists are equally weighted outcomes of a joint distribution. Use the "
      "population 1/n here; sample_covariance is the 1/(n-1) estimator.",
  "correlation":
      "Cov(X, Y) / sqrt(Cov(X, X) * Cov(Y, Y)): normalise by the two standard "
      "deviations so a perfect line gives +1 or -1. Reject zero variance. Do NOT "
      "return the raw covariance: it only equals the correlation for already "
      "standardised data.",
  "sample_covariance":
      "From a list of (x, y) pairs, return [[var_x, cov_xy], [cov_xy, var_y]] "
      "with the unbiased 1/(n-1) denominator (n = number of pairs). Reject n < 2. "
      "Using 1/n makes the small-n result wrong by the factor n/(n-1).",
  "multinomial_pmf":
      "n! / prod(c_i!) * prod(p_i^{c_i}) with n = sum(c). Build n! // prod(c_i!) "
      "in exact integers first, then multiply by the float product p_i^{c_i} "
      "(0**0 = 1). Return a float.",
  "multinomial_samples":
      "Return n count lists. Per trial, draw u = rng.random() and walk the "
      "cumulative probs, incrementing the first category whose cumulative "
      "probability exceeds u. Each vector must sum to trials.",
  "bivariate_normal_pdf":
      "With det = vx*vy - cxy^2 and dx, dy the offsets from mu, the quadratic "
      "form is (vy dx^2 - 2 cxy dx dy + vx dy^2)/det and the density is "
      "exp(-q/2) / (2 pi sqrt(det)). Keep the -2 cxy dx dy cross term: without it "
      "the density still integrates to 1 but E[XY] is wrong.",
  "sample_bivariate_normal":
      "2x2 Cholesky: l11 = sqrt(vx), l21 = cxy/l11, l22 = sqrt(vy - l21^2). Draw "
      "independent standard normals z1, z2 (Box-Muller is provided), return "
      "(mu_x + l11 z1, mu_y + l21 z1 + l22 z2). The factor must satisfy L L^T = "
      "cov, so the sample covariance converges to cov.",
 },
}
