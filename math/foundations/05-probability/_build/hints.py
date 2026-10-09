"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every function that carries part of the chapter is listed, so make_templates stubs it and
replaces its body with `raise NotImplementedError`. The arithmetic helpers (`_dot`,
`_matvec`, `_matmul`, `_transpose`, `_identity`, `_submatrix`, `_forward_sub`,
`_back_sub`, `solve_spd`) are left implemented: a triangular solve is the support this
module stands on (foundations-03's Cholesky), not part of the lesson.
"""

HINTS = {
 "gaussians.py": {
  "cholesky": "One pass, lower triangular: for i, j ≤ i compute s = A[i][j] − Σ_k L[i][k]L[j][k], raise NotPositiveDefinite if A is not square/symmetric or if a diagonal s ≤ 0, else L[i][i] = √s and L[i][j] = s/L[j][j].",
  "log_gaussian_density": "Factor Σ = L Lᵀ, forward-solve L z = x − μ, then return −½( n·log 2π + 2·Σ log Lᵢᵢ + ‖z‖² ). Never form Σ⁻¹ or det Σ — that is the whole point on a nearly singular Σ.",
  "gaussian_density": "exp(log_gaussian_density(x, μ, Σ)).",
  "sample_gaussian": "Factor Σ = L Lᵀ, draw z with rng.gauss(0,1) once per dimension, return μ + L z.",
  "linear_transform": "mean = A μ + b (b defaults to zeros); covariance = A Σ Aᵀ, i.e. matmul(matmul(A, Σ), transpose(A)).",
  "product_of_gaussians": "Precision form: P₁ = Σ₁⁻¹, P₂ = Σ₂⁻¹ (solve against I), P = P₁+P₂, mean = P⁻¹(P₁μ₁ + P₂μ₂), covariance = P⁻¹.",
  "marginal": "Return the matching entries of μ and the principal submatrix Σ[idx][:, idx].",
  "conditional": "Blocks Σ_aa, Σ_ab, Σ_bb. Solve Σ_bb Y = Σ_ba. Mean = μ_a + Yᵀ(x_b − μ_b); covariance = Σ_aa − Σ_ab Y (the Schur complement — subtract the part explained by x_b).",
  "change_of_variables_1d": "Return a function of y equal to pdf_x(g_inv(y)) · |g_inv_prime(y)|. The second factor is the Jacobian; without it the function does not integrate to 1.",
 },
}
