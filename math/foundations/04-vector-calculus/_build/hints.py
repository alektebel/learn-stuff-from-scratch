"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every function that carries part of the chapter is listed, so make_templates stubs it
and replaces its body with `raise NotImplementedError`. The arithmetic helpers (`_dot`,
`_norm`, `_matvec`, `_matmul`, `_transpose`, `_identity`, `_det`, `_inverse`) are left
implemented: they are boilerplate, not the lesson.

One file only: `vector_calculus.py` (the name does not shadow any stdlib module).
"""
HINTS = {
 "vector_calculus.py": {
  "quadratic_gradient": "∇(xᵀAx) = (A + Aᵀ)x for any square A. Build S = A + Aᵀ, then return S x. Do NOT return 2Ax: that is only correct when A is symmetric.",
  "least_squares_gradient": "∇‖Ax − b‖² = 2Aᵀ(Ax − b). Compute the residual r = A x − b (not b − A x), then the j-th component is 2 Σᵢ A[i][j]·r[i].",
  "logdet_gradient": "∇ log det X = X⁻ᵀ, the TRANSPOSE of the inverse (Jacobi's formula: d det = det·tr(X⁻¹ dX)). Return _transpose(_inverse(X)).",
  "trace_linear_gradient": "∇_X tr(A X) = Aᵀ. Return the transpose of A.",
  "trace_quadratic_gradient": "∇_X tr(XᵀA X) = (A + Aᵀ)X. Build S = A + Aᵀ, then return S X (matrix–matrix product).",
  "quadratic_hessian": "∇²(xᵀAx) = A + Aᵀ. Return the symmetric part doubled; it must be symmetric.",
  "central_difference": "For each coordinate j: (f(x + h eⱼ) − f(x − h eⱼ)) / (2h). Use h in the SECOND evaluation too; two points, not one.",
  "relative_gradient_error": "Compare grad_f(x) with central_difference(f, x, h); return max|difference| divided by a scale (the larger of the two norms, floored at 1e-12).",
  "taylor_second_order": "f(x) + ∇f(x)ᵀp + ½ pᵀ∇²f(x)p. The ½ must be there; dropping the quadratic term leaves an O(h²) remainder.",
  "error_curve": "Return [(h, relative_gradient_error(f, grad_f, x, h)) for h in hs] — one pair per requested step size, in order.",
 },
}
