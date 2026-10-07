"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every graded function from the duality chapter (Boyd & Vandenberghe, Ch. 5) is
listed, so make_templates stubs it and replaces its body with `raise
NotImplementedError`. The dense linear-algebra helpers, the teaching constants
and the demo are left implemented: they are scaffolding and reference data, not
part of the node's deliverable.
"""

HINTS = {
 "duality.py": {
  "solve_qp_dual":
      "g(lam) = -(1/2)(c + A^T lam)^T Q^{-1} (c + A^T lam) - b^T lam is concave. "
      "Expand it to -1/2 lam^T H lam - d^T lam + const with H = A Q^{-1} A^T, "
      "d = b + A Q^{-1} c, const = -1/2 c^T Q^{-1} c, then MAXIMISE by cyclic "
      "coordinate ascent: fixing the other lam_j, the best lam_i is "
      "-((d_i + sum_{j!=i} H_ij lam_j)) / H_ii, clipped at 0 (lam >= 0). The sign "
      "of d matters: d is b PLUS A Q^{-1} c, and the value is const - d^T lam - "
      "1/2 lam^T H lam.",
  "solve_lp_dual":
      "The dual of {min c^T x : A x <= b} is {max -b^T y : A^T y = -c, y >= 0}. "
      "It has one variable per constraint; with m primal variables an optimum is "
      "basic, so enumerate every choice of m rows of A, solve the square system "
      "A_S^T y = -c, keep the solutions with y >= 0, and return the LARGEST "
      "-b^T y. A singular basis is skipped. Never take the minimum.",
  "kkt_residuals":
      "Four nonnegative numbers: primal feasibility max(0, max_i (A x - b)_i); "
      "dual feasibility max(0, max_i -lam_i); stationarity max_i |(Q x + c)_i + "
      "(A^T lam)_i|, including the A^T lam pull; complementary slackness "
      "max_i |lam_i (A x - b)_i|. Report all four, plus their maximum.",
  "weak_duality_gap":
      "Return primal - dual, never dual - primal. Weak duality guarantees it is "
      ">= 0 for a feasible pair; a negative value is the sign error that lets a "
      "dual overshoot its primal.",
  "dual_value":
      "The optimal dual value of the QP: g(lam) maximised over lam >= 0. Delegate "
      "to solve_qp_dual so the two cannot disagree.",
  "strong_duality_holds":
      "True iff |primal_value - dual_value| <= tol. Equality is an EXTRA "
      "hypothesis (Slater, or LP feasibility plus boundedness), so a positive "
      "gap must return False: never return True unconditionally.",
 },
}
