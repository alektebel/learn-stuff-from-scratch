"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every graded function of Bishop chapter 7 (sparse kernel machines, here SVMs) is
listed, so make_templates stubs it and replaces its body with `raise
NotImplementedError`. The given infrastructure (`_clip`, `dual_objective`,
`_project` and the demo) is copied unchanged: it is scaffolding, not the SVM
itself.
"""

HINTS = {
    "svm.py": {
        "linear_kernel":
            "k(x, y) = variance * (x y + offset). Return a closure `kernel(x, y)` "
            "capturing variance and offset.",
        "rbf_kernel":
            "k(x, y) = variance * exp(-(x - y)^2 / (2 length_scale^2)). The exponent "
            "is the SQUARED distance; return a closure `kernel(x, y)`.",
        "gram":
            "Return an n x n list of lists with K[i][j] = kernel(xs[i], xs[j]). Fill "
            "both K[i][j] and K[j][i] from the same value so symmetry is exact.",
        "_violates_kkt":
            "With E_i = f(x_i) - t_i, the soft-margin KKT conditions are: at a_i = 0, "
            "t_i E_i >= 0; at a_i = C, t_i E_i <= 0; for 0 < a_i < C, t_i E_i = 0. "
            "Report a violation when |t_i E_i| exceeds tol on the admissible side. "
            "The label t_i multiplies E_i, it is not optional.",
        "_bias_from_support_vectors":
            "For every free support vector (0 < a_i < C), t_i (sum_j a_j t_j "
            "k(x_j, x_i) + b) = 1, so b = t_i - sum_j a_j t_j k(x_i, x_j). Collect "
            "the candidates over all free support vectors and return their AVERAGE. "
            "If none is free, average over every support vector as a fallback.",
        "smo":
            "Platt's simplified SMO. Keep alphas and b; repeat full passes until no "
            "pair changes for `max_passes` in a row. For a violating i, pick a random "
            "j != i, compute E_i, E_j, the bounds L = max(0, a_j - a_i), "
            "H = min(C, C + a_j - a_i) (same label: L = max(0, a_i + a_j - C), "
            "H = min(C, a_i + a_j)), eta = 2K_ij - K_ii - K_jj, then "
            "a_j <- clip(a_j - t_j (E_i - E_j) / eta, L, H) and "
            "a_i <- clip(a_i + t_i t_j (a_j^old - a_j), 0, C). Update b from the "
            "bound-free variable(s). On C = math.inf the dual is unbounded below "
            "unless the data are separable: if the passes never settle, raise "
            "ValueError.",
        "support_vectors":
            "Return the indices i with a_i > tol. The KKT conditions make a_i = 0 "
            "for every other point.",
        "decision_function":
            "Return b + sum_i a_i t_i k(x_i, x) over the non-zero alphas. The model "
            "is a dict with keys 'alphas', 'b', 'Xs', 'ts', 'kernel'.",
        "margin":
            "The geometric margin is 2 / ||w||. In feature space "
            "||w||^2 = sum_ij a_i a_j t_i t_j k(x_i, x_j); return 2 / sqrt of that "
            "(for a linear kernel this equals |sum_i a_i t_i x_i|). It is 2 / ||w||, "
            "not ||w||.",
        "reference_qp":
            "An independent solver for the same dual, to cross-check SMO. Projected "
            "gradient: a <- proj(a - (Q a - 1) / L) with Q_ij = t_i t_j K_ij and L the "
            "largest eigenvalue of Q (power iteration). `_project` is given: it "
            "returns the closest point with 0 <= a <= C and sum_i t_i a_i = 0.",
    },
}
