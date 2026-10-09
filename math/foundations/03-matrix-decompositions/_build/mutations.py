"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism. Each must be CAUGHT by the step named; a MISSED
mutation means the check is too weak, not that the bug is acceptable.
"""
MUTATIONS = [
    # Treat A as SPD without testing the pivot: the first negative pivot reaches math.sqrt.
    ("Cholesky skips the positive-pivot test", "decompositions.py",
     "                if s <= 0.0:\n",
     "                if False:\n", "2"),
    # Power iteration reports the oscillating +1/-1 case as if it had converged.
    ("power iteration ignores non-convergence", "decompositions.py",
     "    if resid > tol * max(1.0, abs(lam)):\n"
     "        raise NoConvergence(\n"
     "            f\"no dominant eigenvector after {iters} iterations (residual {resid:.2e}): \"\n"
     "            \"the two largest eigenvalues have equal magnitude, so the iterates alternate\")\n",
     "    if resid > tol * max(1.0, abs(lam)):\n"
     "        pass\n", "4"),
    # Deflation loop runs one time too many: k+1 pairs instead of k.
    ("deflation loop is off by one", "decompositions.py",
     "    for _ in range(k):\n        lam, v = power_iteration(M)\n",
     "    for _ in range(k + 1):\n        lam, v = power_iteration(M)\n", "5"),
    # Rank-k approximation keeps k+1 terms (off-by-one in k).
    ("low-rank approximation is off by one", "decompositions.py",
     "    for t in range(min(k, len(S))):\n",
     "    for t in range(min(k + 1, len(S))):\n", "7"),
    # Singular values are the eigenvalues of AᵀA, not their square roots.
    ("SVD forgets the square root", "decompositions.py",
     "        sigma = math.sqrt(lam) if lam > 0.0 else 0.0\n",
     "        sigma = lam if lam > 0.0 else 0.0\n", "6"),
    # Clamp away the small eigenvalue so the squared-condition loss disappears.
    ("hiding the AᵀA precision loss", "decompositions.py",
     "        sigma = math.sqrt(lam) if lam > 0.0 else 0.0\n",
     "        sigma = math.sqrt(lam) if lam > 1e-12 else 0.0\n", "8"),
]
