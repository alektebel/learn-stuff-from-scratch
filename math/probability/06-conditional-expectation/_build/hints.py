"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every graded function from chapter 9 of Blitzstein & Hwang is listed, so
make_templates stubs it and replaces its body with `raise NotImplementedError`.
The joint-handling helpers, the samplers and ``demo`` are left implemented: they
are demonstration scaffolding, not part of the node's deliverable.
"""

HINTS = {
 "cond.py": {
  "conditional_expectation":
      "E[Y | X = given] = sum_y y P(Y = y | X = given). Normalise the row "
      "P(X = given, Y = y) by the marginal P(X = given) = sum_y P(X = given, Y = y). "
      "Never divide by the number of outcomes or by 1: the conditional pmf must sum "
      "to 1. Works for a dict {(x, y): p} and a matrix joint[i][j].",
  "conditional_variance":
      "Var(Y | X = given) = E[Y^2 | X = given] - (E[Y | X = given])^2, with the "
      "same row normalised by P(X = given). The second moment is "
      "sum_y y^2 P(X = given, Y = y) / P(X = given).",
  "adam_law":
      "Return (direct, law): direct = sum over outcomes of y * p; "
      "law = sum_x P(X = x) * E[Y | X = x]. Weight each conditional by the "
      "marginal P(X = x) -- averaging the conditionals unweighted is the planted bug.",
  "eve_law":
      "Return (Var(Y), E[Var(Y | X)], Var(E[Y | X])). Var(Y) directly from the "
      "joint; E[Var(Y|X)] = sum_x P(X=x) Var(Y|X=x); "
      "Var(E[Y|X]) = sum_x P(X=x) (E[Y|X=x] - E[Y])^2. The total equals the sum of "
      "the two components.",
  "best_predictor_mse":
      "E[(Y - g(X))^2] = sum over outcomes of p * (y - predictor(x))^2. The "
      "predictor is any callable x -> number; E[Y | X] is the minimiser.",
  "hierarchical_moments":
      "X ~ Bernoulli(p), Y | X = 1 ~ Binomial(n, q1), Y | X = 0 ~ Binomial(n, q0). "
      "with = p n q1 (1-q1) + (1-p) n q0 (1-q0); "
      "between = p (1-p) (n q1 - n q0)^2; total = with + between. Return "
      "(total, with, between). Dropping 'between' is the planted bug.",
 },
}
