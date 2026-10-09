"""Planted bugs for ``math/optimization/04-interior-point``.

    python3 .claude/skills/graded-module/scripts/mutate.py \
        math/optimization/04-interior-point \
        math/optimization/04-interior-point/_build/mutations.py

Each tuple is (description, file, exact text in solutions/<file>, replacement, step).
Every mutation must be CAUGHT by the named check step.
"""

MUTATIONS = [
    (
        "equality_constrained_newton solves the unconstrained system "
        "(drops the A^T lambda / A blocks)",
        "interior.py",
        "        d = solve(K, rhs)\n",
        "        d = solve([row[:n] for row in K[:n]], "
        "[-r_dual[i] for i in range(n)]) + [0.0] * m\n",
        "1",
    ),
    (
        "log_barrier_lp flips the sign of the linear cost term",
        "interior.py",
        "        g = list(c)\n",
        "        g = [-v for v in c]\n",
        "2",
    ),
    (
        "barrier_method never grows t, so the gap stays at m/t0",
        "interior.py",
        "        t *= mu\n",
        "        t = t  # planted: t never grows\n",
        "3",
    ),
    (
        "the enumeration reference accepts infeasible vertices",
        "interior.py",
        "            if all(_dot(A_ub[k], x) <= b_ub[k] + 1e-9 for k in range(m)):\n",
        "            if True:  # planted: accepts infeasible vertices\n",
        "4",
    ),
    (
        "phase_one declares every LP feasible",
        "interior.py",
        "    return sum(z[n:]) <= tol\n",
        "    return True  # planted: every LP is declared feasible\n",
        "5",
    ),
]
