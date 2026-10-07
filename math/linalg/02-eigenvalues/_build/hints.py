"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every function that carries a step of the build is listed, so make_templates stubs it and
replaces its body with a `raise NotImplementedError`. The exact arithmetic and numerical
helpers (`_rref`, `_null_space_basis`, `_integer_divisors`, `_clear_denominators`,
`_synthetic_divide`, `_poly_eval_complex`, `hessenberg`, ...) are left implemented: they
are the linalg-01 prerequisite or boilerplate, and the lesson starts once a matrix can be
reduced and a polynomial can be evaluated.
"""

HINTS = {
    "eigenvalues.py": {
        "characteristic_polynomial": "Faddeev-LeVerrier: M_k = A M_{k-1} + a_{k-1} I and a_k = -(1/k) tr(A M_k); return [1, a_1, ..., a_n].",
        "evaluate_polynomial": "Horner over the coefficients high to low: result = result * x + a.",
        "rational_roots": "Rational root theorem: candidates p/q with p | constant and q | leading coefficient; synthetic-divide each hit to keep multiplicity.",
        "eigenvalues_exact": "rational_roots(characteristic_polynomial(A)).",
        "eigenspace_basis": "The null space of A - lambda I (build the shift, then _null_space_basis).",
        "is_diagonalizable": "Sum len(eigenspace_basis(A, lam)) over distinct eigenvalues and compare to n: geometric multiplicities, not distinct eigenvalues, not algebraic multiplicities.",
        "diagonalize": "Stack eigenvectors as the columns of P and put the matching eigenvalues on D's diagonal; return None when they number fewer than n.",
        "qr_decompose": "Householder: for each column build v = x - alpha e1 with alpha = -sign(x_0)||x||, apply H = I - 2 v v^T to R, and accumulate H into Q.",
        "qr_eigenvalues": "hessenberg(A), then shifted QR with the Wilkinson shift, deflating the last row; solve a trailing 2x2 in closed form for a complex pair.",
        "wilkinson_polynomial": "Multiply out (x - 1)(x - 2)...(x - n) exactly; return the coefficients high to low.",
        "companion_matrix": "1s on the subdiagonal; last column holds -c[n-i]/c[0] for i = 0..n-1.",
        "roots_newton_deflation": "Newton from index n down to 1; after each root, synthetic-divide it out of the polynomial.",
        "wilkinson_experiment": "Run roots_newton_deflation and qr_eigenvalues(companion_matrix(coeffs)); return (max poly root error, max QR error), each nearest-matched to 1..n.",
    },
}
