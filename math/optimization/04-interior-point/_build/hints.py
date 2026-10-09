"""Hints for ``math/optimization/04-interior-point``.

Only the five functions a learner writes are listed; ``solve``, the matrix helpers
and ``_find_interior`` are given in the template. Regenerate the template with

    python3 .claude/skills/graded-module/scripts/make_templates.py \
        math/optimization/04-interior-point \
        math/optimization/04-interior-point/_build/hints.py
"""

HINTS = {
    "interior.py": {
        "equality_constrained_newton":
            "Build the KKT matrix [[Q, A^T], [A, 0]], solve it for (dx, dlambda), "
            "update and stop when ||Qx + c + A^T lambda|| + ||Ax - b|| < tol.",
        "log_barrier_lp":
            "Newton on c^T x - (1/t) sum log(b_i - a_i x): gradient "
            "c + (1/t) sum a_i/s_i, Hessian (1/t) sum a_i a_i^T/s_i^2, backtracking to "
            "keep every slack positive; stop on the Newton decrement.",
        "barrier_method":
            "Solve the barrier at t, record c^T x and the gap m/t, then t <- mu*t; "
            "stop when m/t < tol and return the last point plus the history.",
        "simplex_lp":
            "A 2-D optimum is a vertex: intersect each pair of constraint boundaries, "
            "keep the intersections satisfying every row, and return the cheapest.",
        "phase_one":
            "Phase-I LP: minimise sum s_i subject to a_i x - s_i <= b_i and s_i >= 0; "
            "the original system is feasible exactly when the minimum is 0.",
    },
}
