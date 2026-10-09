"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism. Each must be CAUGHT by the step named; a MISSED
mutation means the check is too weak, not that the bug is acceptable.
"""
MUTATIONS = [
    # P(n, k) with one factor too few: the multiplication principle off by one.
    ("falling factorial multiplies one factor too few", "probability.py",
     "    for i in range(k):\n        result *= n - i\n",
     "    for i in range(k - 1):\n        result *= n - i\n", "1"),
    # Return the favourable COUNT instead of dividing by the sample space.
    ("two pair returns the count, not the probability", "probability.py",
     "    return Fraction(pairs * kicker, total)\n",
     "    return Fraction(pairs * kicker)\n", "3"),
    # Keep only the first inclusion-exclusion term: hands with two aces counted twice.
    ("at-least-one-ace double counts overlapping hands", "probability.py",
     "    favourable = (binomial_coefficient(4, 1) * binomial_coefficient(51, 4)\n"
     "                  - binomial_coefficient(4, 2) * binomial_coefficient(50, 3)\n"
     "                  + binomial_coefficient(4, 3) * binomial_coefficient(49, 2)\n"
     "                  - binomial_coefficient(4, 4) * binomial_coefficient(48, 1))\n",
     "    favourable = binomial_coefficient(4, 1) * binomial_coefficient(51, 4)\n", "4"),
    # The law of total probability silently drops the last case.
    ("total probability drops the last case", "probability.py",
     "    for prior, likelihood in zip(priors, likelihoods):\n",
     "    for prior, likelihood in zip(priors[:-1], likelihoods[:-1]):\n", "5"),
    # Bayes denominator is only the numerator's case: no false-positive term.
    ("Bayes denominator drops the false-positive term", "probability.py",
     "    evidence = total_probability(priors, likelihoods)\n",
     "    evidence = Fraction(priors[index]) * Fraction(likelihoods[index])\n", "6"),
    # An unknowing host treated as a knowing one: 1/3 or 2/3 instead of 1/2.
    ("unknowing Monty Hall host treated as knowing", "probability.py",
     "    if host_knows:\n"
     "        return Fraction(2, 3) if switch else Fraction(1, 3)\n"
     "    return Fraction(1, 2)\n",
     "    if host_knows:\n"
     "        return Fraction(2, 3) if switch else Fraction(1, 3)\n"
     "    return Fraction(2, 3) if switch else Fraction(1, 3)\n", "9"),
    # The simulation counts rounds where the host reveals the car, so it never conditions.
    ("unknowing Monty Hall simulation does not discard car reveals", "probability.py",
     "        else:\n"
     "            opened = rng.choice(others)\n"
     "            if opened == car:\n"
     "                continue\n",
     "        else:\n"
     "            opened = rng.choice(others)\n", "9"),
]
