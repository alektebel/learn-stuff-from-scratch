"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism, each an exact edit to a copy of the
solutions (or of the checker). Every mutation must be CAUGHT by the step named;
a MISSED mutation means the check is too weak, never that the bug is acceptable.

The five the node names: the correlation left unnormalised (so a perfect line
does not read 1), the conditional with the wrong denominator, the bivariate
normal density without its correlation cross term, the sample covariance at 1/n
where the node compares to a population quantity, and the checker itself
inferring independence from zero covariance in the limit case. The last one
mutates check.py: it fires the assertion that guards the checker's own logic.
"""
MUTATIONS = [
    # Correlation returns the raw covariance: a perfect line no longer reads 1.
    ("correlation uses the unnormalised covariance", "joint.py",
     "    return covariance(xs, ys) / math.sqrt(vx * vy)\n",
     "    return covariance(xs, ys)\n", "2"),
    # Conditional divides by 1 instead of the marginal of the conditioning event.
    ("conditional uses the wrong denominator (not P(X = given))", "joint.py",
     "        total = sum(rows[given].values())\n",
     "        total = 1.0\n", "1"),
    # Bivariate normal density drops the -2 cxy dx dy coupling term.
    ("bivariate normal drops the covariance cross term", "joint.py",
     "    quad = (vy * dx * dx - 2.0 * cxy * dx * dy + vx * dy * dy) / det\n",
     "    quad = (vy * dx * dx + vx * dy * dy) / det\n", "4"),
    # Sample covariance uses 1/n where the acceptance rule compares to the
    # analytic (population) covariance.
    ("sample covariance uses 1/n instead of 1/(n-1)", "joint.py",
     "    cxx = sum((x - mx) ** 2 for x in xs) / (n - 1)\n"
     "    cyy = sum((y - my) ** 2 for y in ys) / (n - 1)\n"
     "    cxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (n - 1)\n",
     "    cxx = sum((x - mx) ** 2 for x in xs) / n\n"
     "    cyy = sum((y - my) ** 2 for y in ys) / n\n"
     "    cxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n\n", "4"),
    # The limit-case checker infers independence from zero covariance: the
    # assertion that guards against exactly this must fail.
    ("the limit-case check infers independence from zero covariance", "check.py",
     "    independent = all(conditional(joint, x) == marginal_y for x in xs)\n",
     "    independent = abs(cov) < 1e-12\n", "5"),
]
