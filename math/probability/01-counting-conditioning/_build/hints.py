"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every function that carries part of chapters 1-2 of Blitzstein & Hwang is listed, so
make_templates stubs it and replaces its body with `raise NotImplementedError`. Nothing
is left implemented: even the counting helpers are the lesson here.
"""

HINTS = {
 "probability.py": {
  "falling_factorial":
      "The multiplication principle: multiply exactly k descending factors n·(n−1)···(n−k+1). "
      "Return 0 when k > n or k < 0, and 1 when k == 0.",
  "binomial_coefficient":
      "C(n, k) = P(n, k)/k!. Fold the division into the product (multiply, then integer-divide "
      "by i+1) so every partial result stays exact. Return 0 outside 0 <= k <= n; use C(n, n−k) "
      "to keep the loop short.",
  "poker_two_pair_probability":
      "Favourable hands: C(13,2) ways to pick the two paired ranks, C(4,2)² suit choices, and "
      "44 kickers (11 unused ranks × 4 suits). Divide by C(52,5) — a count is not a probability.",
  "poker_at_least_one_ace_probability":
      "Inclusion-exclusion over the four aces: C(4,1)C(51,4) − C(4,2)C(50,3) + C(4,3)C(49,2) − "
      "C(4,4)C(48,1), divided by C(52,5). The naive first term counts hands with two aces twice. "
      "The complement 1 − C(48,5)/C(52,5) is equivalent.",
  "total_probability":
      "Σ_i P(H_i)·P(E | H_i) over the whole partition. Convert every input with Fraction first "
      "so float prefixes do not creep in. Drop no term.",
  "bayes_posterior":
      "P(H_index)·P(E | H_index) divided by the law of total probability over EVERY case (call "
      "total_probability). Using only the numerator's case makes the posterior 1.",
  "diagnostic_posterior":
      "Two cases: [prevalence, 1 − prevalence] with likelihoods [sensitivity, 1 − specificity]. "
      "Defer to bayes_posterior on index 0; the false-positive term is 1 − specificity.",
  "monty_hall_probability":
      "Knowing host: 2/3 for switching, 1/3 for staying. Unknowing host: condition on the reveal "
      "showing a goat — the two closed doors are symmetric, so 1/2 either way.",
  "simulate_two_pair":
      "Deal with rng.sample(range(52), 5); card c has rank c // 4. Count hands whose rank "
      "multiplicities are exactly [2, 2, 1]. Return Fraction(wins, trials).",
  "simulate_at_least_one_ace":
      "Deal 5 cards and count the hands containing any rank-0 (ace) card. Return Fraction.",
  "simulate_diagnostic":
      "Per person draw disease with probability prevalence, then the test result with "
      "sensitivity or 1 − specificity. Return true positives / positives (the posterior).",
  "simulate_monty_hall":
      "Place car and pick; the knowing host opens a goat among the other doors, the unknowing "
      "host opens one at random and the round is DISCARDED if it shows the car. Condition the "
      "win rate on completed rounds only.",
 },
}
