"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism, each an exact edit to a copy of the
solutions -- or, for the acceptance rule, to the checker itself. Every mutation
must be CAUGHT by the step named; a MISSED mutation means the check is too weak,
never that the bug is acceptable.

The five the node names: the conditional divided by the count instead of
P(X = given); Adam's law averaging the conditionals unweighted; Eve's law
dropping Var(E[Y|X]); the best-predictor check weakened to a single constant
(so a bad predictor passes); and the hierarchical limit case ignoring the
between-group variance.
"""
MUTATIONS = [
    # Conditional uses the row count instead of the marginal of the event.
    ("conditional_expectation divides by the count, not P(X = given)", "cond.py",
     "    return sum(y * p for y, p in terms) / total\n",
     "    return sum(y * p for y, p in terms) / len(terms)\n", "1"),
    # Adam's law averages the conditional means unweighted.
    ("adam_law averages conditionals unweighted, not by P(X = x)", "cond.py",
     "    law = sum(_p_x(joint, x) * conditional_expectation(joint, x)\n"
     "              for x in _x_support(joint))\n",
     "    law = sum(conditional_expectation(joint, x) for x in _x_support(joint))"
     " / len(_x_support(joint))\n", "2"),
    # Eve's law drops the between-group variance.
    ("eve_law drops the Var(E[Y | X]) term", "cond.py",
     "        between += px * (cx - mean) ** 2\n",
     "        between += 0\n", "3"),
    # The best-predictor check is weakened to a single constant: with only the
    # constant left, the richness guard must fire.
    ("best-predictor check compares to a single constant only", "check.py",
     "        \"offset linear\": lambda x: Fraction(1, 4) * x + Fraction(1, 2),\n"
     "        \"quadratic fit\": lambda x: Fraction(-1, 2) * x * x + x + Fraction(1, 2),\n"
     "        \"seeded random\": lambda x: random_lookup[x],\n",
     "", "4"),
    # The hierarchical limit case ignores the between-group variance.
    ("hierarchical limit case ignores the between-group variance", "cond.py",
     "    total = within + between\n",
     "    total = within\n", "5"),
]
