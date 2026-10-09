"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism. Each must be CAUGHT by the step named; a MISSED
mutation means the check is too weak, not that the bug is acceptable.

The four the node names for this module:
  * change of basis applied as S A S^{-1} (or A S S^{-1}) instead of S^{-1} A S  -> step 4
  * differentiation matrix off by one (missing factor)                           -> step 6
  * rank-nullity asserting equality with the wrong count                         -> step 7
  * nilpotency tested at power n instead of n+1                                  -> step 8
plus a null-space sign error and a range basis taken from the reduced frame.
"""
MUTATIONS = [
    # Change of basis multiplied in the wrong order: S A S^-1 instead of S^-1 A S.
    ("change of basis uses S A S^-1", "vector_spaces.py",
     "    return _matmul(_matmul(_inverse(C), A), B)\n",
     "    return _matmul(_matmul(B, A), _inverse(C))\n", "4"),
    # Change of basis that cancels itself: A B C^-1 = A when B = C.
    ("change of basis collapses to A", "vector_spaces.py",
     "    return _matmul(_matmul(_inverse(C), A), B)\n",
     "    return _matmul(A, _matmul(B, _inverse(C)))\n", "4"),
    # Differentiation off by one: the output power k-1 instead of the input power k.
    ("differentiation drops the power factor", "vector_spaces.py",
     "        D[k - 1][k] = Fraction(k)\n",
     "        D[k - 1][k] = Fraction(k - 1)\n", "6"),
    # Rank-nullity reports the number of rows as dim range instead of the rank.
    ("rank-nullity counts rows as dim range", "vector_spaces.py",
     "    range_dim = rank(A)\n",
     "    range_dim = len(A)\n", "7"),
    # Nilpotency searched only up to power n, missing D^{n+1} = 0.
    ("nilpotency tested at power n", "vector_spaces.py",
     "    for k in range(1, max_power + 1):\n",
     "    for k in range(1, max_power):\n", "8"),
    # Null-space free variable given the wrong sign.
    ("null-space sign is wrong", "vector_spaces.py",
     "            v[p] = -R[i][f]\n",
     "            v[p] = R[i][f]\n", "2"),
    # Range basis taken from the reduced frame (rows of the RREF) instead of the columns.
    ("range basis comes from the reduced frame", "vector_spaces.py",
     "    columns = _transpose(matrix)\n",
     "    columns = _rref(matrix)[0]\n", "3"),
]
