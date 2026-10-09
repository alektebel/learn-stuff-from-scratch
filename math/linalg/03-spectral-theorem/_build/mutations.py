"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism, each an exact edit to a copy of the
solutions. Every mutation must be CAUGHT by the step named; a MISSED mutation
means the check is too weak, never that the bug is acceptable.
"""
MUTATIONS = [
    # A rotation applied to Q with the wrong sign leaves the columns not
    # orthonormal, so the reconstructed A = Q diag Q^T is wrong too.
    ("jacobi_eigh accumulates the rotation into Q with the wrong sign", "spectral.py",
     "                    Q[k][q] = s * qkp + c * qkq\n",
     "                    Q[k][q] = -s * qkp + c * qkq\n", "1"),
    # An orthogonality test that always agrees is no test at all.
    ("is_orthogonal never rejects a non-orthonormal matrix", "spectral.py",
     "            if abs(got - want) > tol:\n                return False\n",
     "            if False:\n                return False\n", "2"),
    # Absolutising a negative eigenvalue hides a non-PSD matrix; it must raise.
    ("positive_sqrt never rejects a negative eigenvalue", "spectral.py",
     "        if evals[0] < -tol * scale:\n",
     "        if False:\n", "4"),
    # Q = U is orthogonal but drops V^T, so Q P no longer equals A.
    ("polar_decomposition uses Q = U instead of Q = U V^T", "spectral.py",
     "    Q = _matmul(U, Vt)\n",
     "    Q = U\n", "5"),
    # Singular values must be returned in descending order.
    ("svd returns the singular values in ascending order", "spectral.py",
     "    order = sorted(range(n), key=lambda i: -evals[i])       # descending\n",
     "    order = sorted(range(n), key=lambda i: evals[i])       # descending\n", "6"),
    # Dividing by a zero singular value, or leaving a zero column, breaks U.
    ("svd does not complete the basis for a zero singular value", "spectral.py",
     "            col = _complement_vector(used, m)\n",
     "            col = [0.0] * m\n", "6"),
]
