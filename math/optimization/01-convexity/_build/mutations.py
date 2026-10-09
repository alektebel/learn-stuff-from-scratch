"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism, each an exact edit to a copy of the
solutions. Every mutation must be CAUGHT by the step named; a MISSED mutation
means the check is too weak, never that the bug is acceptable.
"""
MUTATIONS = [
    # The trace is not the whole spectrum: a matrix with eigenvalues +1 and -1
    # has trace 0 and would pass.
    ("is_psd tests the trace instead of every eigenvalue", "convexity.py",
     "    return all(lam >= -tol for lam in jacobi_eigenvalues(A))\n",
     "    return sum(jacobi_eigenvalues(A)) >= -tol\n", "1"),
    # The off-diagonal central difference already contains the factor 1/4.
    ("Hessian off-diagonal divides by h^2 instead of 4 h^2", "convexity.py",
     "            value = (f(pp) - f(pm) - f(mp) + f(mm)) / (4.0 * h * h)\n",
     "            value = (f(pp) - f(pm) - f(mp) + f(mm)) / (h * h)\n", "1"),
    # The minimum over the weight sweep only ever anchors the convex case; a
    # violation is positive and would be discarded.
    ("jensen_gap keeps the minimum over the sweep instead of the maximum",
     "convexity.py",
     "            if gap > best:\n                best = gap\n",
     "            best = min(best, gap)\n", "2"),
    # The minimum of convex functions is not convex.
    ("pointwise_max takes the minimum", "convexity.py",
     "    return lambda x: max(f(x) for f in fs)\n",
     "    return lambda x: min(f(x) for f in fs)\n", "3"),
    # Dropping the Jensen test leaves the classifier leaning on one local
    # certificate, which is positive at the cusp of sqrt(abs(x)).
    ("classify drops the Jensen test (Hessian at the centre only)", "convexity.py",
     "    if jensen_gap(f, box, n, rng) > tol:\n        return False\n",
     "    if False:\n        return False\n", "4"),
    # The naive test must keep the f <= level inequality; the superlevel sets of
    # a quasiconvex function are not convex.
    ("sublevel grid test uses the superlevel sets", "convexity.py",
     "        inside = [v <= level for v in vals]\n",
     "        inside = [v >= level for v in vals]\n", "5"),
]
