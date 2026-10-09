"""Graded hints for the QR / least-squares templates (one line per function).

`make_templates.py` replaces each listed function's body with its hint and a
`raise NotImplementedError`, so the template keeps every signature and docstring
but none of the solution.
"""

HINTS = {
    "leastsquares.py": {
        "householder_qr":
            "For column k build the reflector H = I - 2 v v^T from the sub-column, "
            "apply it to R from the left, and accumulate Q <- Q H.",
        "normal_equations":
            "Form C = A^T A and rhs = A^T b, then solve the square system C x = rhs.",
        "qr_least_squares":
            "From A = Q R, solve R x = Q^T b using the first n rows of R and the "
            "first n entries of Q^T b.",
        "svd_least_squares":
            "With A = U diag(S) V^T, x = V diag(1/S) U^T b, taking 1/S = 0 for "
            "singular values at or below tol * S[0].",
        "residual_norm":
            "Return ||A x - b||_2: form the residual vector, then its Euclidean norm.",
        "condition_number":
            "Take the largest over the smallest singular value from the SVD; not the "
            "ratio of the diagonal entries.",
        "exact_least_squares":
            "Convert A and b to Fraction, solve A^T A x = A^T b exactly, and return "
            "Fractions.",
    }
}
