"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every function that carries part of the chapter is listed, so make_templates stubs it and
raises NotImplementedError. The small arithmetic helpers (`_dot`, `_matvec`, `_matmul`,
`_transpose`, `_norm`, `_normalize`, `_start_vector`) and the two exceptions are left
implemented: they are boilerplate, not the lesson.
"""
HINTS = {
 "decompositions.py": {
  "cholesky": "One pass over i >= j: s = A[i][j] − Σ_{k<j} L[i][k]L[j][k]. On the diagonal s is the squared pivot — raise NotPositiveDefinite if s <= 0, else L[i][i] = sqrt(s). Off-diagonal, L[i][j] = s / L[j][j]. Check squareness and symmetry first, so a non-SPD matrix raises instead of reaching math.sqrt with a negative.",
  "power_iteration": "Normalise the start vector, then repeat: w = A·v, v = w/‖w‖, λ = vᵀAv. AFTER the loop, test the true residual ‖Av − λv‖ ≤ 1e-7·max(1,|λ|); if it is too large raise NoConvergence — a convergence test on λ alone accepts the +1/−1 oscillation where λ is constant but v flips.",
  "eigenpairs_symmetric": "Loop exactly k times: find (λ, v) with power_iteration on the working matrix M, append it, then deflate M ← M − λ v vᵀ. The subtracted matrix has the same eigenvectors with this λ replaced by 0, so the next dominant pair is the next eigenpair. Return list length k.",
  "svd_via_ata": "gram = AᵀA; its eigenvalues are σ² and its eigenvectors are the right singular vectors V. Use eigenpairs_symmetric(gram, n), sort by eigenvalue descending, σ = sqrt(max(λ,0)), and u = A·v/σ (zero column if σ is 0). Return (U, S, V) as lists of COLUMNS; A = Σ σ_i u_i v_iᵀ.",
  "low_rank_approx": "Compute the SVD, then sum the first k outer products: A_k = Σ_{t<k} S[t]·U[t]⊗V[t]. The number of terms is exactly k; the residual spectral norm is then σ_{k+1} (Eckart-Young).",
 },
}
