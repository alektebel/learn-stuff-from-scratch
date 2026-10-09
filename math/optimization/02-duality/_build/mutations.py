"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism, each an exact edit to a copy of the
solutions. Every mutation must be CAUGHT by the step named; a MISSED mutation
means the check is too weak, never that the bug is acceptable.
"""
MUTATIONS = [
    # The dual value's linear term is -b^T lam. Flipping its sign reports a
    # value that no longer matches the primal (and can even look "safe" under
    # weak duality because it drops instead of rising).
    ("the QP dual value flips the sign of the lambda offset", "duality.py",
     "    return const - _dot(d, lam) - 0.5 * _quad(lam, H)\n",
     "    return const + _dot(d, lam) - 0.5 * _quad(lam, H)\n", "1"),
    # Stationarity is Q x + c + A^T lam = 0. Dropping A^T lam leaves the primal
    # gradient, which is nonzero wherever a constraint is active.
    ("KKT stationarity drops the A^T lam term", "duality.py",
     "    stationarity = max(abs(qx[i] + c[i] + at_lam[i]) for i in range(m))\n",
     "    stationarity = max(abs(qx[i] + c[i]) for i in range(m))\n", "3"),
    # The gap is primal - dual. Reversing it turns a witness of slackness
    # (a positive gap) into a negative number, i.e. a claimed violation.
    ("weak duality gap returns dual - primal", "duality.py",
     "    return primal - dual\n",
     "    return dual - primal\n", "4"),
    # The LP dual is a MAXIMUM over -b^T y; taking the smallest basic value
    # picks an interior-ish feasible point, not the optimum.
    ("the LP dual objective minimises instead of maximises", "duality.py",
     "        if best is None or value > best:\n            best = value\n",
     "        if best is None or value < best:\n            best = value\n", "2"),
    # Strong duality is an extra hypothesis. Returning True unconditionally
    # hides the positive gap of the no-Slater limit case.
    ("strong_duality_holds assumes strong duality always holds", "duality.py",
     "    return abs(primal_value - dual_value) <= tol\n",
     "    return True\n", "5"),
]
