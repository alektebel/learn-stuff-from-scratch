"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every graded function from chapter 5 of Blitzstein & Hwang is listed, so
make_templates stubs it and replaces its body with `raise NotImplementedError`.
The shared helpers (normal_cdf, the survival functions, shifted_exponential_gap)
and the demo are left implemented: they are demonstration scaffolding, not part
of the node's deliverable.
"""

HINTS = {
 "continuous.py": {
  "uniform_ppf":
      "The inverse of F(x) = x on [0, 1] is the identity: return u. Reject u "
      "outside [0, 1].",
  "exponential_ppf":
      "F(x) = 1 - e^(-rate x), so F^-1(u) = -ln(1 - u)/rate. Use math.log1p(-u) "
      "rather than math.log(1 - u) for accuracy at small u; return 0 at u <= 0 "
      "and +inf at u >= 1.",
  "normal_ppf":
      "Bisect x on [-40, 40] for ~40 steps against Phi(x) = 0.5 (1 + "
      "erf(x/sqrt(2))): move lo up when Phi(mid) < u, else hi down; return the "
      "midpoint. Return -inf at u <= 0 and +inf at u >= 1. Do NOT return "
      "Phi(u): that is the CDF, not its inverse.",
  "inverse_cdf_sample":
      "Universality of the uniform: return [ppf(rng.random()) for _ in range(n)].",
  "ks_statistic":
      "Sort the sample; for the i-th order statistic (i from 1) take the max of "
      "i/n - F(x) and F(x) - (i-1)/n. D is the largest over the sample. Using "
      "i/n on both sides is wrong: it forgets the left limit (i-1)/n.",
  "ks_pvalue":
      "The asymptotic form Q(d sqrt(n)) with lam = d sqrt(n): "
      "2 * sum_{k>=1} (-1)^(k-1) e^(-2 k^2 lam^2), summed until a term < 1e-12 "
      "and clipped to [0, 1]. Returning just the first term 2 e^(-2 lam^2) "
      "exceeds 1 for lam <~ 0.6 and is wrong.",
  "memorylessness_gap":
      "For X ~ Exponential(rate), P(X>s+t|X>s) = P(X>s+t)/P(X>s) = e^(-rate t) "
      "and P(X>t) = e^(-rate t), so the gap is 0 (up to floating rounding).",
  "tail_truncation":
      "rng.random() < 1, and the largest double below 1 is U_MAX = "
      "math.nextafter(1.0, 0.0). Clamp u to U_MAX, take x = -log1p(-u_eff)/rate, "
      "report missing_mass = 1 - u_eff (the unreachable tail, 2**-53 at u = 1) "
      "and missing_quantile = +inf: the true quantile at u = 1 is infinite, so "
      "reporting 0 hides the truncation.",
 },
}
