"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every graded function from chapter 8 (change of variables, convolution) and
chapter 10 (bounds, limit theorems) of Blitzstein & Hwang is listed, so
make_templates stubs it and replaces its body with `raise NotImplementedError`.
The standard-normal CDF, the IQR helper, the demo-only sample-mean helper and
`demo()` are left implemented: they are scaffolding, not part of the deliverable.
"""

HINTS = {
 "limits.py": {
  "change_of_variables":
      "f_Y(y) = f_X(g^{-1}(y)) / |g'(g^{-1}(y))|. Call g_inv(y) once to get x, "
      "then divide fy(x) by abs(g_prime_inv(y)). Do NOT drop the 1/|g'| "
      "Jacobian factor, and keep the abs: a decreasing map gives a negative "
      "density without it.",
  "convolution":
      "Return a list of length len(p) + len(q) - 1 with out[k] = sum_i "
      "p[i] * q[k - i]. This is the pmf of X + Y; it is NOT the elementwise "
      "product p[k] * q[k]. Products of Fractions stay exact.",
  "markov_bound":
      "Return min(1.0, mean / t) for t > 0 (1.0 for t <= 0). Markov says "
      "P(X >= t) <= E[X]/t for X >= 0. Do NOT return the exact tail: a bound "
      "at the tail is not a bound above it.",
  "chebyshev_bound":
      "Return min(1.0, var / t**2) for t > 0 (1.0 for t <= 0). The deviation "
      "t is one-sided already supplied by the caller; the bound depends only on "
      "the variance.",
  "chernoff_bound":
      "Minimise exp(-s * t) * mgf_value(s) over a geometric grid of s > 0 "
      "(start at 1e-6, multiply by 1.05 up to 50) and cap the result at 1.0. "
      "mgf_value is a callable M(s); treat an OverflowError from it as an "
      "infinite candidate.",
  "exact_tail_bernoulli":
      "sum_{i=k}^{n} C(n, i) p^i (1-p)^{n-i} as a Fraction: convert p with "
      "Fraction(p), q = 1 - p, and accumulate comb(n, i) * p**i * q**(n-i). "
      "Handle k <= 0 (return 1) and k > n (return 0).",
  "exact_tail_exponential":
      "P(Exp(rate) >= t) = exp(-rate * t); return 1.0 for t <= 0.",
  "lln_sample_means":
      "For each of trials replications, draw n observations and keep a running "
      "total; add the running mean after each draw to a per-m accumulator, then "
      "divide each accumulator by trials. Return the n averaged running means; "
      "late entries approach E[X].",
  "clt_error":
      "Draw trials sample means of n draws each, also collecting all draws. "
      "Estimate mu and sigma from the pooled draws, set se = sigma / sqrt(n) "
      "(standard error: divide by the standard deviation, NOT the variance), "
      "standardise each sample mean as (m - mu)/se, sort, and return the sup of "
      "|empirical CDF - Phi(z)| over the ordered values (compare both i/trials "
      "and (i+1)/trials at each jump).",
  "cauchy_sample_means":
      "For each of trials replications draw n standard Cauchy values by "
      "tan(pi * (rng.random() - 0.5)), average them, and return the list of "
      "means. The heavy tails are the point: the mean of n Cauchy draws is "
      "again Cauchy, so these means do not concentrate.",
 },
}
