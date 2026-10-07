"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every graded function from chapters 2 and 3 of Boyd & Vandenberghe is listed,
so make_templates stubs it and replaces its body with `raise NotImplementedError`.
The catalogue, the expected table and the demo are left implemented: they are
reference data and demonstration scaffolding, not part of the node's deliverable.
"""

HINTS = {
 "convexity.py": {
  "hessian":
      "Central differences, h = 1e-4: diagonal (f(x+h e_i) - 2 f(x) + f(x-h e_i))/h^2; "
      "off-diagonal (pp - pm - mp + mm)/(4 h^2). Return a symmetric list of lists. "
      "Forward differences with the same h carry an O(h) bias; central ones are O(h^2).",
  "jacobi_eigenvalues":
      "Cyclic Jacobi on a symmetric matrix: sweep p<q, zero a[p][q] with a rotation "
      "t = sign(theta)/(|theta|+sqrt(theta^2+1)), theta = (a[q][q]-a[p][p])/(2 a[p][q]); "
      "apply the rotation to the columns and then to the rows; return the sorted diagonal. "
      "Use this, not Cholesky: a convex Hessian may be only semidefinite.",
  "is_psd":
      "Every eigenvalue of the symmetric A is >= -tol (a NEGATIVE tolerance: a zero "
      "eigenvalue is allowed, as at x = 0 for x^4). Using the trace, or requiring strictly "
      "positive eigenvalues, is wrong.",
  "jensen_gap":
      "Max over n random chords and every lambda in LAMBDAS of f(lam x + (1-lam) y) - "
      "[lam f(x) + (1-lam) f(y)]. Return the MAXIMUM (a single witness suffices), never the "
      "minimum, and sweep lambda rather than only the midpoint.",
  "nonneg_sum":
      "Return a function of x that sums weights[i] * fs[i](x). Convex only when every "
      "weight is >= 0; do not take abs(weights), that would hide a negative one.",
  "pointwise_max":
      "Return a function of x that is the MAXIMUM of fs[i](x): convex when every fs[i] is. "
      "A minimum of convex functions need not be convex.",
  "affine_compose":
      "Return x -> f([sum_j A[i][j] x[j] + b[i] for i]). Convex when f is convex, for any A and b.",
  "sublevel_grid_test":
      "On a grid over [lo, hi] sample f; for each level the set f <= level is convex in 1-D "
      "iff the points where f <= level are ONE contiguous run. Count runs; more than one "
      "means not convex. Keep the inequality as f <= level (a quasiconvex function is still "
      "fooling this test).",
  "classify":
      "Convex iff jensen_gap(f, box, n, rng) <= tol AND is_psd(hessian(f, centre), tol) at "
      "the box centre. Both tests are needed: Jensen finds the global violations, the "
      "Hessian certifies the smooth case.",
 },
}
