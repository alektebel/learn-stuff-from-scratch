"""Planted bugs for the QR / least-squares checker.

Each entry is ``(description, file, exact text in solutions/<file>, replacement,
check step)``. `mutate.py` copies the solutions, applies one mutation at a time,
and requires the named step to report a failure (a ``✗``). The mutation table in
the module README is built from this list.
"""

MUTATIONS = [
    (
        "Householder Q accumulated with the wrong reflector weight (Q^T Q != I)",
        "leastsquares.py",
        "                Q[i][t] -= 2.0 * d * v[t - k]",
        "                Q[i][t] -= d * v[t - k]",
        "1",
    ),
    (
        "normal equations form A A^T and use b instead of A^T A and A^T b",
        "leastsquares.py",
        "    At = _transpose(A)\n"
        "    C = _matmul(At, A)\n"
        "    rhs = _matvec(At, b)\n"
        "    return _solve(C, rhs)",
        "    At = _transpose(A)\n"
        "    C = _matmul(A, At)\n"
        "    rhs = list(b)\n"
        "    return _solve(C, rhs)[:len(A[0])]",
        "2",
    ),
    (
        "QR least squares back-substitutes the wrong R rows (bottom n instead of top n)",
        "leastsquares.py",
        "    R1 = [R[i][:n] for i in range(n)]",
        "    R1 = [R[i][:n] for i in range(m - n, m)]",
        "2",
    ),
    (
        "condition_number uses the ratio of diagonal entries instead of singular values",
        "leastsquares.py",
        "    _, S, _ = _svd(A)",
        "    S = [abs(A[i][i]) for i in range(min(len(A), len(A[0])))]",
        "4",
    ),
    (
        "limit-case check accepts the normal-equations error as equal to QR "
        "(normal_equations aliased to the QR answer)",
        "leastsquares.py",
        "    At = _transpose(A)\n"
        "    C = _matmul(At, A)\n"
        "    rhs = _matvec(At, b)\n"
        "    return _solve(C, rhs)",
        "    return qr_least_squares(A, b)",
        "4",
    ),
]
