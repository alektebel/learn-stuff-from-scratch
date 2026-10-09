"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism. Each must be CAUGHT by the step named; a MISSED
mutation means the check is too weak, not that the bug is acceptable.

Step map:
  1  quadratic_gradient        5  trace_quadratic_gradient
  2  least_squares_gradient    6  central_difference / relative_gradient_error
  3  logdet_gradient           7  quadratic_hessian
  4  trace_linear_gradient     8  taylor_second_order
"""
MUTATIONS = [
    # Treat A as symmetric: 2Ax instead of (A + Aᵀ)x. Invisible for symmetric A.
    ("quadratic gradient assumes symmetric A (2Ax)", "vector_calculus.py",
     "    S = [[A[i][j] + A[j][i] for j in range(n)] for i in range(n)]\n"
     "    return [sum(S[i][j] * x[j] for j in range(n)) for i in range(n)]\n",
     "    S = [[2.0 * A[i][j] for j in range(n)] for i in range(n)]\n"
     "    return [sum(S[i][j] * x[j] for j in range(n)) for i in range(n)]\n", "1"),
    # Flip the sign of ∇‖Ax − b‖²: x − t∇f becomes an ascent direction.
    ("least-squares gradient has the wrong sign", "vector_calculus.py",
     "    return [2.0 * sum(A[i][j] * r[i] for i in range(m)) for j in range(n)]\n",
     "    return [-2.0 * sum(A[i][j] * r[i] for i in range(m)) for j in range(n)]\n", "2"),
    # Drop the transpose: return X⁻¹ instead of X⁻ᵀ. Invisible for symmetric X.
    ("log-det gradient forgets the transpose", "vector_calculus.py",
     "    return _transpose(_inverse(X))\n",
     "    return _inverse(X)\n", "3"),
    # Drop the transpose in tr(A X): return A instead of Aᵀ.
    ("trace gradient forgets the transpose", "vector_calculus.py",
     "    return _transpose(A)\n",
     "    return A\n", "4"),
    # Drop the symmetrisation in tr(XᵀA X): return A X instead of (A + Aᵀ)X.
    ("trace-quadratic gradient drops symmetrisation", "vector_calculus.py",
     "    S = [[A[i][j] + A[j][i] for j in range(n)] for i in range(n)]\n"
     "    return [[sum(S[i][k] * X[k][j] for k in range(n))\n",
     "    S = [[A[i][j] for j in range(n)] for i in range(n)]\n"
     "    return [[sum(S[i][k] * X[k][j] for k in range(n))\n", "5"),
    # Forward difference instead of central: error O(h) rather than O(h²).
    ("finite differences are forward, not central", "vector_calculus.py",
     "        grad.append((f(xp) - f(xm)) / (2.0 * h))\n",
     "        grad.append((f(xp) - f(x)) / h)\n", "6"),
    # Drop the symmetrisation in the Hessian: return A instead of A + Aᵀ.
    ("Hessian drops the symmetrisation term", "vector_calculus.py",
     "    return [[A[i][j] + A[j][i] for j in range(n)] for i in range(n)]\n",
     "    return [[A[i][j] for j in range(n)] for i in range(n)]\n", "7"),
    # Drop the quadratic term: remainder becomes O(h²), ratio ~4 not ~8.
    ("second-order Taylor drops the quadratic term", "vector_calculus.py",
     "    quad = 0.5 * sum(p[i] * H[i][j] * p[j] for i in range(n) for j in range(n))\n",
     "    quad = 0.0 * sum(p[i] * H[i][j] * p[j] for i in range(n) for j in range(n))\n", "8"),
]
