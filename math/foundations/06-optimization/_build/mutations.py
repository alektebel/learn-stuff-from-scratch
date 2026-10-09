"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism. Each must be CAUGHT by the step named; a MISSED
mutation means the check is too weak, not that the bug is acceptable.

Step map:
  3  backtracking_line_search      6  max_stable_step
  5  momentum                     10  kkt_residuals
"""
MUTATIONS = [
    # Drop the Armijo loop: the line search accepts alpha0 unconditionally, so an
    # overshooting step that increases the objective is accepted.
    ("backtracking accepts a step that increases the objective", "optimization.py",
     "    while f([x[i] + alpha * direction[i] for i in range(len(x))]) > f(x) + c * alpha * gd:\n"
     "        alpha *= rho\n"
     "        if alpha < 1e-300:\n"
     "            break\n",
     "    alpha = alpha0\n", "3"),
    # Drop the previous-velocity term: momentum collapses to plain gradient descent.
    ("momentum forgets the previous velocity (beta * v)", "optimization.py",
     "        v = [beta * v[i] + g[i] for i in range(n)]\n",
     "        v = [g[i] for i in range(n)]\n", "5"),
    # The fixed-step ceiling off by a factor: 1/L instead of 2/L, so the 2/L boundary
    # test's "just above 2/L must diverge" case wrongly converges.
    ("fixed-step ceiling is 1/L, not 2/L", "optimization.py",
     "    return 2.0 / L\n",
     "    return 1.0 / L\n", "6"),
    # The KKT residual report drops stationarity, so a feasible non-stationary point
    # looks optimal.
    ("KKT residuals omit the stationarity condition", "optimization.py",
     "    residual = [sum(Q[i][j] * x[j] for j in range(n)) + b[i]\n"
     "                + sum(C[k][i] * lam[k] for k in range(m)) for i in range(n)]\n"
     "    stationarity = _norm(residual)\n",
     "    stationarity = 0.0\n", "10"),
]
