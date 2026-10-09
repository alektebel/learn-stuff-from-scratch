"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every function that carries part of chapters 3-4 of Blitzstein & Hwang is listed, so
make_templates stubs it and replaces its body with `raise NotImplementedError`. Nothing
is left implemented: the shared helpers are part of the lesson too.
"""

HINTS = {
 "random_variables.py": {
  "variance_from_moments":
      "Return second_moment - mean ** 2. The square belongs on the mean alone: "
      "(second_moment - mean) ** 2 is the classic misplacement and collapses to 0 "
      "whenever the mean equals the second moment.",
  "summarize":
      "Sample mean and variance of the draws as Fractions: mean = sum/n, second = "
      "sum(x^2)/n, variance via variance_from_moments. Return (mean, variance).",
  "cdf_from_pmf":
      "Sum pmf(j) for j = 0..k, starting from Fraction(0). Return 0 for k < 0. The "
      "Geometric and Negative Binomial pmf return 0 below their support, so this is safe.",
  "bernoulli_pmf":
      "1 - p at k = 0, p at k = 1, 0 elsewhere. Convert p with Fraction first.",
  "bernoulli_cdf":
      "0 for k < 0, 1 - p for 0 <= k < 1, 1 for k >= 1.",
  "bernoulli_mean":
      "E[X] = p, as a Fraction.",
  "bernoulli_variance":
      "Var(X) = p(1-p), via variance_from_moments(mean, E[X^2]) and note X^2 = X for an "
      "indicator, so the second moment is p.",
  "binomial_pmf":
      "C(n,k) p^k (1-p)^(n-k) with math.comb, converted to Fraction; 0 outside 0 <= k <= n.",
  "binomial_cdf":
      "Sum the PMF over 0..k via cdf_from_pmf.",
  "binomial_mean":
      "E[X] = n p.",
  "binomial_variance":
      "Var(X) = n p (1-p).",
  "geometric_pmf":
      "(1-p)^(k-1) p for k >= 1, else 0. Support starts at 1: the first trial is the "
      "success, so there are k-1 failures before it.",
  "geometric_cdf":
      "1 - (1-p)^k for k >= 1, else 0.",
  "geometric_mean":
      "E[X] = 1/p. Counting trials, not failures: the failures convention gives "
      "(1-p)/p, smaller by one.",
  "geometric_variance":
      "Var(X) = (1-p)/p^2.",
  "negative_binomial_pmf":
      "C(k-1, r-1) p^r (1-p)^(k-r) for k >= r, else 0: the last trial is the r-th "
      "success and the first k-1 trials hold r-1 successes.",
  "negative_binomial_cdf":
      "Sum the PMF from k = r upward via cdf_from_pmf.",
  "negative_binomial_mean":
      "E[X] = r/p.",
  "negative_binomial_variance":
      "Var(X) = r(1-p)/p^2.",
  "poisson_pmf":
      "e^-lambda lambda^k / k!, evaluated in float by recurrence (start at e^-lambda and "
      "multiply by lambda/i for i = 1..k) so a large k cannot overflow the factorial. "
      "0 for k < 0.",
  "poisson_cdf":
      "Sum the PMF over 0..k; 0 for k < 0.",
  "poisson_mean":
      "E[X] = lambda, as a float.",
  "poisson_variance":
      "Var(X) = lambda, as a float.",
  "binomial_poisson_tv_distance":
      "0.5 * sum over k >= 0 of |Binomial(n,p)(k) - Poisson(np)(k)|. The Poisson mean is "
      "n p, not p, and the Poisson tail past n must be added because the Binomial is 0 "
      "there.",
  "expected_fixed_points":
      "By linearity, sum over the n positions of P(position i is fixed) = n * (1/n) = 1 "
      "for n >= 1 (0 for n = 0). Independence is NOT required and is false here.",
  "fixed_points_variance":
      "Add the covariances, do not drop them. Sum of the n independent variances "
      "(each (1/n)(1-1/n)) plus n(n-1) times the covariance 1/(n(n-1)) - 1/n^2. The "
      "result is exactly 1 for n >= 2; the independence-only value (n-1)/n is wrong.",
  "simulate_bernoulli":
      "rng = random.Random(seed); return a list of 1 when rng.random() < p else 0, "
      "trials long.",
  "simulate_binomial":
      "Each of the trials draws counts successes in n independent Bernoulli(p) flips; "
      "return the list of counts.",
  "simulate_geometric":
      "Count trials until the first rng.random() < p; return the list of counts (each "
      ">= 1).",
  "simulate_negative_binomial":
      "Count trials until r successes, incrementing the success count on rng.random() < p; "
      "return the list.",
  "simulate_poisson":
      "Knuth's method: target = exp(-lambda); multiply rng.random() into a running product "
      "until it is <= target; the number of factors is the draw. Return the list.",
  "simulate_fixed_points":
      "For each trial build perm = list(range(n)), rng.shuffle(perm), and append the count "
      "of i with perm[i] == i. Return the list.",
 },
}
