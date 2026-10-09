"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every function that carries part of chapter 7 is listed, so make_templates stubs it and
replaces its body with `raise NotImplementedError`. The arithmetic helpers (`_dot`,
`_norm`, `_matvec`, `_transpose`, `_identity`, `_solve`, `jacobi_eigenvalues`,
`condition_number`, `quadratic_value`, `quadratic`) are left implemented: they are
boilerplate, not the lesson.

One file only: `optimization.py` (the name does not shadow any stdlib module).
"""
HINTS = {
 "optimization.py": {
  "quadratic_gradient": "∇(½xᵀAx − bᵀx) = A x − b: multiply A by x, then subtract b componentwise. The ½ cancels, so there is no factor of 2.",
  "gradient_descent": "Loop: g = grad_f(x); stop when ‖g‖ ≤ tol; update x ← x − step·g. Return (x, iterations, history), history[0] = a copy of x0 and len(history) = iterations + 1.",
  "backtracking_line_search": "Armijo: alpha = alpha0; while f(x + alpha·direction) > f(x) + c·alpha·(∇f(x)·direction): alpha *= rho. Return alpha. Reject a non-descent direction (∇f·direction ≥ 0) with ValueError.",
  "gradient_descent_backtracking": "Like gradient_descent but take direction = −∇f(x) and the step from backtracking_line_search(f, grad_f, x, direction, alpha0, rho, c). Return (x, iterations, history).",
  "momentum": "Heavy ball: v ← beta·v + ∇f(x); x ← x − step·v. The previous velocity term beta·v is the method — dropping it gives plain gradient descent. Return (x, iterations, history).",
  "max_stable_step": "The fixed-step ceiling for a quadratic with largest Hessian eigenvalue L is 2/L (not 1/L): |1 − tλ| < 1 for every λ requires t < 2/λ_max.",
  "lagrange_quadratic": "Solve the KKT block system [[Q, Cᵀ], [C, 0]]·[x; λ] = [−b; d] with _solve. Return (x, λ) — do not drop the multipliers.",
  "kkt_residuals": "Return (‖Qx + b + Cᵀλ‖, ‖Cx − d‖): the stationarity residual AND the primal-feasibility residual. Both must be computed.",
 },
}
