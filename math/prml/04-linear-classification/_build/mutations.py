"""Planted bugs for the check suite, one classic mistake per mechanism.

Each mutation is an exact edit to `solutions/classification.py`. Run:

    python3 .claude/skills/graded-module/scripts/mutate.py \\
        math/prml/04-linear-classification math/prml/04-linear-classification/_build/mutations.py

Every entry must be CAUGHT by the step it names; a MISSED entry means the check is too
weak, not the mutation is wrong.
"""

MUTATIONS = [
    (
        "sigmoid is the rational z/(1+|z|) instead of 1/(1+exp(-z))",
        "classification.py",
        "    if z >= 0.0:\n"
        "        return 1.0 / (1.0 + math.exp(-z))\n"
        "    e = math.exp(z)\n"
        "    return e / (1.0 + e)",
        "    return z / (1.0 + abs(z))",
        "2",
    ),
    (
        "Fisher's direction drops the within-class scatter (plain difference of means)",
        "classification.py",
        "    direction = _solve(scatter, [m1[j] - m0[j] for j in range(d)])",
        "    direction = [m1[j] - m0[j] for j in range(d)]",
        "1",
    ),
    (
        "IRLS uses the unweighted Phi^T Phi (drops the p(1-p) factor of the Hessian)",
        "classification.py",
        "        weights = [pi * (1.0 - pi) for pi in p]",
        "        weights = [1.0 for _ in p]",
        "3",
    ),
    (
        "the Laplace mean is set to zero instead of the MAP weights",
        "classification.py",
        "    mean, _ = logistic_irls(Xs, ts, maxit=200, tol=1e-13, ridge=ridge)",
        "    mean = [0.0] * len(_design(Xs)[0])",
        "4",
    ),
    (
        "the unregularised logistic run silently carries an L2 prior (default ridge = 1)",
        "classification.py",
        "def logistic_irls(Xs, ts, maxit=100, tol=1e-8, ridge=0.0):",
        "def logistic_irls(Xs, ts, maxit=100, tol=1e-8, ridge=1.0):",
        "5",
    ),
]
