"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism. Each must be CAUGHT by the step named; a MISSED
mutation means the check is too weak, not that the bug is acceptable.
"""
MUTATIONS = [
    # Divide by whatever is on the diagonal instead of the largest entry in the column.
    ("no partial pivoting", "elimination.py",
     "    return max(range(r, len(U)), key=lambda i: abs(U[i][c]))\n",
     "    return r\n", "10"),
    # Build the basis from the pivot columns instead of the free columns.
    ("null space uses pivot columns", "elimination.py",
     "    free = [c for c in range(n) if c not in pivots]\n",
     "    free = list(pivots)\n", "5"),
    # Forget the sign the row swaps contribute to the determinant.
    ("determinant ignores row swaps", "elimination.py",
     "    return -det if swaps % 2 else det\n",
     "    return det\n", "9"),
    # Return some vector for an inconsistent system instead of reporting it.
    ("solve accepts inconsistent systems", "elimination.py",
     "    for i in range(len(pivots), m):\n"
     "        if abs(R[i][n]) > tol:               # 0·x = nonzero: no solution\n"
     "            raise InconsistentSystem(\"the augmented system has 0 = nonzero\")\n",
     "    pass  # mutation: no consistency check\n", "4"),
    # Invert a singular matrix instead of refusing.
    ("inverse has no singularity check", "elimination.py",
     "    if len(pivots) < n:\n"
     "        raise SingularMatrix(f\"rank {len(pivots)} < {n}\")\n",
     "    pass  # mutation: no singularity check\n", "8"),
    # Keep the particular solution but throw away the free directions.
    ("general solution drops the null space", "elimination.py",
     "    return particular, null_space(A)\n",
     "    return particular, []\n", "6"),
]
