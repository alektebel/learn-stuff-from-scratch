"""Planted bugs for the check suite, one classic mistake per mechanism.

Each mutation is an exact edit to `solutions/kernels.py`. Run:

    python3 .claude/skills/graded-module/scripts/mutate.py \\
        math/prml/06-kernels-gps math/prml/06-kernels-gps/_build/mutations.py

Every entry must be CAUGHT by the step it names; a MISSED entry means the check is
too weak, not the mutation is wrong.
"""

MUTATIONS = [
    (
        "rbf_kernel omits the square (uses |x - y|, a Laplace-style kernel)",
        "kernels.py",
        "        return variance * math.exp(-0.5 * d * d / (length_scale * length_scale))",
        "        return variance * math.exp(-0.5 * abs(d) / (length_scale * length_scale))",
        "1",
    ),
    (
        "cholesky returns the upper factor without conjugating (U instead of L)",
        "kernels.py",
        "                L[i][j] = total / L[j][j]\n"
        "    return L",
        "                L[i][j] = total / L[j][j]\n"
        "    return [list(row) for row in zip(*L)]",
        "2",
    ),
    (
        "gp_posterior drops the observation-noise term from the training covariance",
        "kernels.py",
        "    C = [[gram[i][j] + (noise if i == j else 0.0) for j in range(n)]\n"
        "         for i in range(n)]",
        "    C = [[gram[i][j] for j in range(n)] for i in range(n)]",
        "2",
    ),
    (
        "is_psd accepts a matrix with a negative eigenvalue",
        "kernels.py",
        "    return min(values) >= -tol",
        "    return True",
        "5",
    ),
    (
        "cholesky ignores the jitter, so a singular system is claimed solvable",
        "kernels.py",
        "                total += jitter",
        "                total += 0.0",
        "5",
    ),
]
