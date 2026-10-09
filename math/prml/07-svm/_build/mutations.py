"""Planted bugs for the check suite, one classic mistake per mechanism.

Each mutation is an exact edit to `solutions/svm.py`. Run:

    python3 .claude/skills/graded-module/scripts/mutate.py \\
        math/prml/07-svm math/prml/07-svm/_build/mutations.py

Every entry must be CAUGHT by the step it names; a MISSED entry means the check is
too weak, not that the mutation is wrong.
"""

MUTATIONS = [
    (
        "the SMO KKT test drops t_i from the error",
        "svm.py",
        "    return ((ts[i] * E_i < -tol and alphas[i] < C)\n"
        "            or (ts[i] * E_i > tol and alphas[i] > 0.0))",
        "    return ((E_i < -tol and alphas[i] < C)\n"
        "            or (E_i > tol and alphas[i] > 0.0))",
        "1",
    ),
    (
        "the bias update drops the averaging over the support vectors",
        "svm.py",
        "    return total / len(free)",
        "    return total",
        "2",
    ),
    (
        "support_vectors keeps the wrong side of the threshold (a_i < 0)",
        "svm.py",
        "    return [i for i, a in enumerate(alphas) if a > tol]",
        "    return [i for i, a in enumerate(alphas) if a < 0.0]",
        "2",
    ),
    (
        "margin returns ||w|| instead of 2 / ||w||",
        "svm.py",
        "    return 2.0 / math.sqrt(w2)",
        "    return math.sqrt(w2)",
        "2",
    ),
    (
        "the hard-margin limit case claims it succeeds on non-separable data",
        "svm.py",
        "    if C == math.inf and passes < max_passes:",
        "    if False:  # mutation: claim the hard margin succeeds",
        "5",
    ),
]
