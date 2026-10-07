"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism, plus the four the node names. Each must be CAUGHT by
the step named; a MISSED mutation means the check is too weak, not that the bug is
acceptable.

The four the node names for this module:
  * diagonalisability decided by counting distinct eigenvalues instead of independent
    eigenvectors                                                              -> step 4
  * the characteristic polynomial with a wrong sign on a coefficient          -> step 1
  * the defective (Jordan) case reported diagonalisable                       -> step 4
  * Wilkinson's polynomial root-finding claimed accurate when the QR path is
    the stable one                                                            -> step 9
plus an eigenspace shifted by +lambda, a root-finder that drops negative candidates, a
QR that skips its last reflector, an eigensolver that tests the wrong subdiagonal, a
diagonalisation that does not refuse a defective matrix, and a Wilkinson product that
stops one factor early.
"""
MUTATIONS = [
    # 1. Characteristic polynomial: the Faddeev-LeVerrier coefficient loses its sign.
    ("characteristic polynomial coefficient sign flipped", "eigenvalues.py",
     "        coeffs.append(-trace / k)                      # a_k = -(1/k) tr(A M_k)\n",
     "        coeffs.append(trace / k)                       # a_k = (1/k) tr(A M_k)\n", "1"),
    # 2. Diagonalisability decided by counting DISTINCT eigenvalues (the identity fails).
    ("diagonalisability counts distinct eigenvalues", "eigenvalues.py",
     "        total += len(eigenspace_basis(A, lam))\n",
     "        total += 1\n", "4"),
    # 3. The defective Jordan case reported diagonalisable (algebraic multiplicities).
    ("Jordan block reported diagonalisable", "eigenvalues.py",
     "    return total == n\n",
     "    return len(spectrum) == n\n", "4"),
    # 4. Wilkinson experiment claims the polynomial route is the accurate one.
    ("Wilkinson errors report the polynomial route as stable", "eigenvalues.py",
     "    return float(poly_error), float(qr_error)\n",
     "    return float(qr_error), float(poly_error)\n", "9"),
    # 5. Eigenspace built from A + lambda I instead of A - lambda I.
    ("eigenspace uses A + lambda I", "eigenvalues.py",
     "    shifted = [[_F(A[i][j]) - (lam if i == j else Fraction(0)) for j in range(n)]\n",
     "    shifted = [[_F(A[i][j]) + (lam if i == j else Fraction(0)) for j in range(n)]\n", "3"),
    # 6. Rational root candidates: only the positive ones are tried.
    ("rational roots drop the negative candidates", "eigenvalues.py",
     "                             for s in (1, -1)})\n",
     "                             for s in (1,)})\n", "2"),
    # 7. QR decomposition skips its last Householder reflector (R stays non-triangular).
    ("QR skips the last reflector", "eigenvalues.py",
     "    for k in range(n - 1):\n        x = [R[i][k] for i in range(k, n)]\n",
     "    for k in range(n - 2):\n        x = [R[i][k] for i in range(k, n)]\n", "6"),
    # 8. Eigensolver returns the diagonal of A instead of running the iteration.
    ("eigensolver reads the diagonal instead of iterating", "eigenvalues.py",
     "    return sorted(eigs, key=lambda z: (z.real, z.imag))\n",
     "    return [A[i][i] for i in range(len(A))]\n", "7"),
    # 9. Diagonalisation does not refuse when the eigenvectors fall short.
    ("diagonalize does not check independence", "eigenvalues.py",
     "    if len(columns) != n:\n        return None\n",
     "    if len(columns) == 0:\n        return None\n", "5"),
    # 10. Wilkinson product stops at n-1, missing the last factor.
    ("Wilkinson product stops one factor early", "eigenvalues.py",
     "    for k in range(1, n + 1):\n        expanded = [Fraction(0)] * (len(coeffs) + 1)\n",
     "    for k in range(1, n):\n        expanded = [Fraction(0)] * (len(coeffs) + 1)\n", "8"),
]
