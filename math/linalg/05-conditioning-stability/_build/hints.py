"""Graded hints for the conditioning / stability templates (one line per function).

`make_templates.py` replaces each listed function's body with its hint and a
`raise NotImplementedError`, so the template keeps every signature and docstring
but none of the solution.
"""

HINTS = {
    "stability.py": {
        "norm_inf":
            "Return the largest absolute row sum: max over rows of sum(abs(entry)).",
        "norm_1":
            "Return the largest absolute column sum: max over columns j of "
            "sum_i abs(A[i][j]).",
        "norm_frobenius":
            "Square-root of the sum of squares of all entries.",
        "lu_nopivot":
            "Doolittle elimination with no row swaps: copy A into U, keep L as the "
            "identity, and for each k store the multiplier f = U[i][k]/U[k][k] in "
            "L[i][k] and subtract f times row k from every row below. Return "
            "(L, U, identity).",
        "lu_partial_pivot":
            "At each k find the row p >= k of largest |U[i][k]|, swap rows k and p in "
            "U and P (and the already-computed L columns), then eliminate below as in "
            "lu_nopivot; return (L, U, P) with P A = L U.",
        "lu_solve":
            "Factor with the requested pivoting, apply P to b, forward-solve L y = P b, "
            "then back-solve U x = y.",
        "_inverse":
            "Augment A with the identity and run Gauss-Jordan with partial pivoting: "
            "scale each pivot row, clear the column above and below, return the right "
            "half.",
        "condition_number":
            "||A||_inf times ||A^-1||_inf, with both factors in the same infinity norm "
            "and A^-1 from _inverse.",
        "growth_factor":
            "Eliminate (with or without pivoting) to U, then return max|U_ij| divided "
            "by max|A_ij| of the input -- not by max|U|.",
        "backward_error":
            "Form r = A x - b and return ||r||_inf / (||A||_inf ||x||_inf).",
        "forward_error":
            "Return ||x - x_true||_inf / ||x_true||_inf.",
        "perturbation_experiment":
            "For each trial draw A and x_true, set b = A x_true, solve with partial "
            "pivoting, and track the max of forward_error / (condition_number * "
            "(backward_error + n*eps)).",
        "wilkinson_growth":
            "Return the n x n gfpp matrix: 1 on the diagonal, 1 in every entry of the "
            "last column, -1 in the strict lower triangle, 0 above the diagonal.",
    }
}
