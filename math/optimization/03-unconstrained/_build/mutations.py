"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism, each an exact edit to a copy of the
solutions. Every mutation must be CAUGHT by the step named; a MISSED mutation
means the check is too weak, never that the bug is acceptable.
"""
MUTATIONS = [
    # Sufficient decrease is the safeguard that makes steepest descent converge.
    # Returning the full step every time drops the Armijo test and the iteration
    # overshoots immediately.
    ("backtracking accepts any step (Armijo test dropped)", "minimise.py",
     "    t = 1.0\n"
     "    while f([x[i] + t * d[i] for i in range(len(x))]) > fx + alpha * t * slope:\n"
     "        t *= beta\n"
     "        if t < 1e-16:\n"
     "            break\n"
     "    return t\n",
     "    t = 1.0\n"
     "    while f([x[i] + t * d[i] for i in range(len(x))]) > fx + alpha * t * slope:\n"
     "        break\n"
     "    return t\n", "1"),
    # The line search is the adaptive step. A hard-wired step ignores the local
    # curvature and diverges whenever it exceeds 2/L.
    ("gradient_descent uses a fixed step (ignores line search)", "minimise.py",
     "        d = [-gi for gi in g]\n"
     "        t = backtracking_line_search(f, grad, x, d)\n"
     "        x = [x[i] + t * d[i] for i in range(len(x))]\n",
     "        d = [-gi for gi in g]\n"
     "        t = 1.0\n"
     "        x = [x[i] + t * d[i] for i in range(len(x))]\n", "1"),
    # The Newton direction is -H^{-1} g. Using -g turns the method into gradient
    # descent: it keeps curvature out and the iteration count explodes.
    ("newton uses the gradient step (drops the Hessian)", "minimise.py",
     "        y = _solve_regularized(g, H)\n"
     "        decrement = _dot(g, y)\n",
     "        y = list(g)\n"
     "        decrement = _dot(g, y)\n", "3"),
    # The decrement stopping test must be tight enough to iterate into the
    # near-optimum regime. A loose test stops before the quadratic rate appears.
    ("the stopping test is so loose the quadratic exponent is not observed", "minimise.py",
     "        if decrement / 2.0 <= tol:\n"
     "            break\n",
     "        if decrement / 2.0 <= 1.0:\n"
     "            break\n", "2"),
    # The limit case needs the raw (undamped) Newton step. Damping it too hides
    # the divergence from a far start.
    ("the limit case assumes undamped Newton converges from far away", "minimise.py",
     "        if line_search:\n"
     "            t = backtracking_line_search(f, grad, x, d)\n"
     "        else:\n"
     "            t = 1.0\n",
     "        if True:\n"
     "            t = backtracking_line_search(f, grad, x, d)\n"
     "        else:\n"
     "            t = 1.0\n", "4"),
]
