"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every function that carries part of the chapter is listed, so make_templates stubs it
and replaces its body with `raise NotImplementedError`. The small arithmetic helpers
(`_dot`, `_matmul`, `_transpose`, `_identity`, `_solve`) are left implemented: `_solve`
is the piece of foundations-01 this module stands on, and the rest are boilerplate.
"""
HINTS = {
 "geometry.py": {
  "is_symmetric": "True when A is square and A[i][j] == A[j][i] within a small relative tolerance.",
  "is_spd": "Cholesky: a symmetric matrix is positive definite exactly when A = L Lᵀ exists with a strictly positive diagonal. Return False on the first non-positive pivot.",
  "inner": "Reject A unless it is SPD (raise NotPositiveDefinite), then return uᵀ A v — compute A·v first, then dot with u.",
  "norm": "The square root of the inner product of u with itself.",
  "angle": "arccos( <u,v> / (||u||·||v||) ), clamped to [-1, 1]; raise if either norm is 0.",
  "projection_matrix": "P = B (BᵀB)⁻¹ Bᵀ with the spanning vectors as the columns of B. Build the Gram matrix G = BᵀB, solve G Y = Bᵀ (one right-hand side per coordinate), then P[i][j] = Σ_t B[t][i]·Y[t][j].",
  "project": "Multiply the projection matrix by x.",
  "affine_project": "Project x − x0 onto span(B), then add x0 back.",
  "gram_schmidt": "For each vector, subtract its component along every basis vector found so far and normalise. Classical uses the ORIGINAL vector in each inner product; modified uses the partially reduced one. Skip a vector whose residual is ~0.",
  "rotation_2d": "[[cos θ, −sin θ], [sin θ, cos θ]].",
  "rotation_3d": "Rodrigues: normalise the axis to k, build the skew matrix K with K v = k × v, then R = I + sin θ·K + (1 − cos θ)·K².",
 },
}
