"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every function that carries a chapter of Axler is listed, so make_templates stubs it and
replaces its body with a `raise NotImplementedError`. The exact rational arithmetic is
left implemented: `_rref` and `_inverse` are the piece of foundations-01 this module
stands on, and the rest (`_matmul`, `_transpose`, `_identity`, `_is_zero`,
`_columns_to_matrix`, `apply`) is boilerplate.
"""

HINTS = {
    "vector_spaces.py": {
        "rank": "Reduce the matrix with _rref and return the number of pivot columns.",
        "null_space_basis": "RREF, then for each free column f build a vector with 1 at f and -R[i][f] at each pivot column pivots[i].",
        "column_space_basis": "RREF for the pivot columns, then return those columns OF THE ORIGINAL matrix (the columns are the rows of _transpose(matrix)).",
        "matrix_of_map": "B = columns of domain_basis, C = columns of codomain_basis; return C^-1 A B (the inverse is first, on the left).",
        "differentiation_matrix": "(n+1)x(n+1) zero matrix; for k = 1..n set row k-1, column k to k.",
        "matrix_power": "Repeated exact multiplication, starting from the identity for k = 0.",
        "nilpotency_index": "Multiply up from the identity; return the first k in 1..max_power with power == 0, else None.",
        "fundamental_theorem": "n = number of columns; dim null = len(null_space_basis(A)); dim range = rank(A); return (n, dim null, dim range).",
    },
}
