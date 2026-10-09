"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism. Each must be CAUGHT by the step named; a MISSED
mutation means the check is too weak, not that the bug is acceptable.
"""
MUTATIONS = [
    # Forget that the induced inner product needs A, and use the ordinary dot product.
    ("inner product ignores A", "geometry.py",
     "    return _dot(u, Av)\n",
     "    return _dot(u, v)\n", "2"),
    # Accept a non-SPD matrix as an inner product.
    ("inner product accepts a non-SPD matrix", "geometry.py",
     "    if not is_spd(A):\n"
     "        raise NotPositiveDefinite(\"A is not symmetric positive definite\")\n",
     "    if False:\n"
     "        raise NotPositiveDefinite(\"A is not symmetric positive definite\")\n", "1"),
    # Projection without the (BᵀB)⁻¹ factor: B Bᵀ instead of B (BᵀB)⁻¹ Bᵀ.
    ("projection forgets the inverse", "geometry.py",
     "    return [[sum(B[t][i] * Y[j][t] for t in range(k)) for j in range(m)]\n"
     "            for i in range(m)]\n",
     "    return [[sum(B[t][i] * B[t][j] for t in range(k)) for j in range(m)]\n"
     "            for i in range(m)]\n", "3"),
    # Affine projection that forgets the offset x0.
    ("affine projection ignores the offset", "geometry.py",
     "    return [x0[i] + sum(P[i][j] * d[j] for j in range(len(d))) for i in range(len(x0))]\n",
     "    return [sum(P[i][j] * x[j] for j in range(len(x))) for i in range(len(x0))]\n", "5"),
    # Gram-Schmidt that orthogonalises but never normalises.
    ("Gram-Schmidt does not normalise", "geometry.py",
     "            basis.append([x / nrm for x in w])\n",
     "            basis.append(list(w))\n", "6"),
    # "Modified" Gram-Schmidt that is really classical (uses the original vector).
    ("modified Gram-Schmidt is classical", "geometry.py",
     "            r = _dot(w if modified else v, q)\n",
     "            r = _dot(v, q)\n", "10"),
    # 2-D rotation with the wrong sign, so its determinant is not +1.
    ("2-D rotation is not proper", "geometry.py",
     "    return [[c, -s], [s, c]]\n",
     "    return [[c, s], [s, c]]\n", "8"),
    # 3-D Rodrigues without the sin term: symmetric, determinant cos²θ, not a rotation.
    ("3-D rotation is not a rotation", "geometry.py",
     "    return [[(1.0 if i == j else 0.0) + s * K[i][j] + (1 - c) * K2[i][j]\n",
     "    return [[(1.0 if i == j else 0.0) + 0.0 * K[i][j] + (1 - c) * K2[i][j]\n", "9"),
]
