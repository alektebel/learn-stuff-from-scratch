"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every graded function from Bishop's chapter 13 is listed, so make_templates stubs
it and replaces its body with a `# TODO: <hint>` line plus `raise
NotImplementedError`. The small dense linear-algebra helpers (`_matvec`,
`_matmul`, `_transpose`, `_add`, `_sub`, `_eye`, `_inv`) and the demo are left
implemented: scaffolding, not the deliverable.
"""

HINTS = {
    "sequential.py": {
        "forward":
            "Scaled forward recursion. At t=0 set a_i = pi_i B_i[o_0]; at each "
            "later step a_j = (sum_i alpha_{t-1,i} A[i][j]) B_j[o_t]. Divide a by "
            "its own sum c_t, append the normalised vector to alphas and c_t to "
            "cs, and return (alphas, cs). The division at every step is what stops "
            "long sequences underflowing; prod(cs) is P(obs).",
        "backward":
            "Scaled backward recursion with the same scaling factors as forward. "
            "Start beta_{T-1,i} = 1 and recurse "
            "beta_t[i] = (sum_j A[i][j] B_j[o_{t+1}] beta_{t+1,j}) / c_{t+1}. "
            "Return (betas, cs). The transition index is A[i][j] (i -> j), not its "
            "transpose.",
        "forward_backward":
            "Combine the messages: gamma_t is the elementwise product "
            "alphas[t] * betas[t], normalised to sum to one. Return the list of "
            "per-time marginals.",
        "viterbi":
            "Max-product in log space with backpointers. delta_0[i] = "
            "log pi_i + log B_i[o_0]; for each t and j, delta_t[j] = max_i "
            "(delta_{t-1}[i] + log A[i][j]) + log B_j[o_t], storing psi_t[j] = "
            "argmax_i. Take the best final state, then trace psi backwards to "
            "reconstruct the path. Keep the backpointers: a running max alone is "
            "not a decode.",
        "baum_welch":
            "EM. E-step: run forward-backward for gamma (occupancy) and "
            "xi_t[i][j] = alphas[t,i] A[i][j] B_j[o_{t+1}] betas[t+1,j], "
            "normalised. M-step: pi_i = gamma_0[i]; A[i][j] proportional to "
            "sum_t xi_t[i][j]; B[i][k] proportional to sum_{t: o_t=k} gamma_t[i]. "
            "Return (pi, A, B, logliks) with logliks[0] from the starting "
            "parameters; it must not decrease.",
        "kalman_filter":
            "Predict then correct. At t>0 predict mu <- F mu, "
            "P <- F P F^T + Q. Then S = H P H^T + R, K = P H^T S^{-1}, "
            "mu <- mu + K (y - H mu), P <- (I - K H) P. Return the filtered "
            "(mus, Ps). Dropping R from S is wrong.",
        "rts_smoother":
            "Filter first, then sweep backwards. Predicted covariance "
            "Pp = F P_t F^T + Q; smoother gain G = P_t F^T Pp^{-1} (this is NOT "
            "the filter gain). Then m_t = mu_t + G (m_{t+1} - F mu_t) and "
            "P_t = P_t + G (P_{t+1} - Pp) G^T. Return the smoothed (means, covs).",
        "batch_gaussian_posterior":
            "Assemble the full linear-Gaussian system over X = (x_0..x_{T-1}) in "
            "information form: J = P0^{-1} on the first block, plus for each "
            "transition the residual x_t - F x_{t-1} with precision Q^{-1}, plus "
            "H^T R^{-1} H on each observation block and H^T R^{-1} y_t into the "
            "info vector. Invert J; the mean is J^{-1} h and the per-time blocks of "
            "J^{-1} are the exact marginal covariances. This is the reference, not "
            "a shipping algorithm.",
    },
}
