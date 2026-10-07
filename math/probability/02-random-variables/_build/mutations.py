"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism. Each must be CAUGHT by the step named; a MISSED
mutation means the check is too weak, not that the bug is acceptable.

The first four are the bugs the skill-tree node names: the misplaced square in the
moment formula, the Geometric support starting at 0 instead of 1, the Poisson
approximation compared at the wrong n (lambda = p instead of n p), and the indicator
variance computed as if the fixed-point indicators were independent.
"""
MUTATIONS = [
    # E[X^2] - (E[X])^2 with the square moved outside the difference.
    ("variance formula squares the wrong term", "random_variables.py",
     "    return second_moment - mean ** 2\n",
     "    return (second_moment - mean) ** 2\n", "1"),
    # Geometric pmf with the support shifted to 0: the mass is (1-p)^k p.
    ("geometric pmf support starts at 0", "random_variables.py",
     "    return (1 - p) ** (k - 1) * p\n",
     "    return (1 - p) ** k * p\n", "3"),
    # Geometric mean under the shifted support: one less than 1/p.
    ("geometric mean one too small (support shifted by one)", "random_variables.py",
     "    return Fraction(1, 1) / Fraction(p)\n",
     "    return Fraction(1, 1) / Fraction(p) - 1\n", "3"),
    # Negative Binomial off by one: C(k, r) instead of C(k-1, r-1).
    ("negative binomial pmf off by one in the binomial coefficient", "random_variables.py",
     "    return Fraction(math.comb(k - 1, r - 1)) * p ** r * q ** (k - r)\n",
     "    return Fraction(math.comb(k, r)) * p ** r * q ** (k - r)\n", "4"),
    # The Poisson mean is left at p, not n p: the approximation is compared at the
    # wrong n, so the error no longer shrinks like p.
    ("Poisson approximation uses p for the mean instead of n p", "random_variables.py",
     "    lam = n * p\n",
     "    lam = p\n", "8"),
    # The fixed-point indicators are treated as independent: the covariance terms
    # are dropped, giving (n-1)/n instead of 1.
    ("fixed-point variance assumes the dependent indicators are independent",
     "random_variables.py",
     "    covariance = n * (n - 1) * (\n"
     "        Fraction(1, n * (n - 1)) - Fraction(1, n) * Fraction(1, n))\n"
     "    return independent_part + covariance\n",
     "    return independent_part\n", "7"),
]
