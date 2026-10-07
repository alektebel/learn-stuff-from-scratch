"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every graded function from Axler's chapters 6 and 7 is listed, so make_templates
stubs it and replaces its body with `raise NotImplementedError`. The small dense
arithmetic helpers (`_identity`, `_transpose`, `_matmul`, `_matvec`, `_dot`,
`_norm`, `_gram_schmidt`, `_complement_vector`) and the demo are left implemented:
they are plumbing and demonstration scaffolding, not the node's deliverable.
"""

HINTS = {
 "spectral.py": {
  "jacobi_eigh":
      "Cyclic Jacobi on the symmetric A: sweep the pairs p<q, zero A[p][q] with the "
      "rotation tau=(A[q][q]-A[p][p])/(2 A[p][q]), t=sign(tau)/(|tau|+sqrt(1+tau^2)), "
      "c=1/sqrt(1+t^2), s=t c; apply the same rotation to A (M<-MJ then M<-J^T M) and "
      "accumulate it into Q (Q<-QJ). Return (eigenvalues ascending, Q) so that "
      "A = Q diag(evals) Q^T.",
  "orthonormal_eigenbasis":
      "(evals ascending, Q) as jacobi_eigh, but when eigenvalues agree within tol, "
      "re-orthonormalise the span of their columns so the answer is an orthonormal basis "
      "of each eigenspace. Never fix which basis: any orthonormal basis of the eigenspace "
      "is valid.",
  "is_orthogonal":
      "True iff the columns are orthonormal: for every pair (i, j), the dot product of "
      "column i and column j of Q is 1 when i==j and 0 otherwise, within tol. This covers "
      "the rectangular U of an SVD too.",
  "positive_sqrt":
      "Symmetric PSD square root via A = Q diag(evals) Q^T: return Q diag(sqrt(evals)) "
      "Q^T, clamping a round-off eigenvalue to 0 but RAISING ValueError for a genuinely "
      "negative eigenvalue. Returns a symmetric PSD matrix whose square is A.",
  "polar_decomposition":
      "Return (Q, P) with A = Q P, Q orthogonal and P symmetric PSD, from the SVD "
      "A = U diag(S) V^T: Q = U V^T and P = V diag(S) V^T. Do not use Q = U.",
  "svd":
      "Return (U, S, Vt) with A = U diag(S) V^T, S descending. From the spectral theorem "
      "applied to A^T A: its eigenvalues are the squared singular values and its "
      "eigenvectors are V; the left singular vectors are A v / s, and a zero singular "
      "value is COMPLETED to an orthonormal basis instead of dividing by zero.",
 },
}
