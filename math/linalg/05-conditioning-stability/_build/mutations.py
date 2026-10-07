"""Planted bugs for the conditioning / stability checker.

Each entry is ``(description, file, exact text in solutions/<file>, replacement,
check step)``.  `mutate.py` copies the solutions, applies one mutation at a time,
and requires the named step to report a failure (a ``✗``).  The mutation table in
the module README is built from this list.
"""

MUTATIONS = [
    (
        "lu_nopivot silently performs partial pivoting, so the unstable limit case "
        "is solved accurately",
        "stability.py",
        "    for k in range(n):\n"
        "        if U[k][k] == 0.0:\n"
        "            raise ZeroDivisionError(\"zero pivot in LU without pivoting\")\n",
        "    for k in range(n):\n"
        "        p = max(range(k, n), key=lambda i: abs(U[i][k]))\n"
        "        if p != k:\n"
        "            U[k], U[p] = U[p], U[k]\n"
        "            L[k], L[p] = L[p], L[k]\n"
        "        if U[k][k] == 0.0:\n"
        "            raise ZeroDivisionError(\"zero pivot in LU without pivoting\")\n",
        "4",
    ),
    (
        "growth_factor normalises by max|U| instead of max|A|, so it is identically 1",
        "stability.py",
        "    return max_u / max_a",
        "    return max_u / max_u",
        "3",
    ),
    (
        "condition_number mixes norms: it uses ||A||_1 with ||A^-1||_inf",
        "stability.py",
        "    return norm_inf(A) * norm_inf(_inverse(A))",
        "    return norm_1(A) * norm_inf(_inverse(A))",
        "2",
    ),
    (
        "backward_error drops the ||A|| ||x|| normalisation and returns a raw residual",
        "stability.py",
        "    return _vec_inf(residual) / (norm_inf(A) * _vec_inf(x))",
        "    return _vec_inf(residual)",
        "2",
    ),
    (
        "wilkinson_growth puts the ones in the wrong column, so the growth stays 1",
        "stability.py",
        "            elif j == n - 1:\n"
        "                A[i][j] = 1.0\n",
        "            elif i == n - 1:\n"
        "                A[i][j] = 1.0\n",
        "3",
    ),
]
