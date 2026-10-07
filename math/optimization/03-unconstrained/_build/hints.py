"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every graded function from the unconstrained-minimisation chapter (Boyd &
Vandenberghe, Ch. 9) is listed, so make_templates stubs it and replaces its body
with `raise NotImplementedError`. The Gaussian-elimination helper `solve`, the
small vector helpers and the demo are left implemented: they are scaffolding,
not the node's deliverable.
"""

HINTS = {
 "minimise.py": {
  "backtracking_line_search":
      "Armijo sufficient decrease along d from x. Compute g = grad(x), slope = "
      "g . d and fx = f(x); start t = 1 and while f(x + t d) > fx + alpha * t * "
      "slope, shrink t by beta. Stop shrinking near 1e-16 so the loop cannot hang "
      "on a non-descent direction. Return t. Dropping the Armijo test (always "
      "returning 1) makes the caller diverge: the test is the whole point.",
  "gradient_descent":
      "Steepest descent: at each iteration record f(x); g = grad(x); stop when "
      "||g|| < tol; set d = -g and step x <- x + backtracking_line_search(f, grad, "
      "x, d) * d. Return (x, f(x), history). Do NOT hard-wire a fixed step: the "
      "backtracking search is what adapts to the curvature and to the current "
      "scale, and a fixed step above 2/L diverges.",
  "newton_decrement":
      "The squared Newton decrement g^T H^{-1} g. Solve H y = g and return g^T y. "
      "H may be singular: try the plain solve first and, only on ValueError, add "
      "a ridge lam*I with lam starting at 1e-8 and multiplied by 10 until the "
      "solve succeeds. For positive-definite H the value is positive and measures "
      "the gap to the optimum through the quadratic model; the stopping rule is "
      "decrement / 2 <= tol.",
  "newton":
      "At each iteration form g = grad(x), H = hess(x) and y = the regularised "
      "solve of H y = g; decrement = g . y; append it and stop as soon as "
      "decrement / 2 <= tol. Otherwise the Newton direction is d = -y; when "
      "line_search is true damp the step with backtracking_line_search, else take "
      "the raw step t = 1. Update x and count the iteration. Return "
      "(x, decrement_history, iterations). The raw step is only safe near the "
      "optimum; from a far start it overshoots and diverges, which is exactly the "
      "limit case.",
 },
}
