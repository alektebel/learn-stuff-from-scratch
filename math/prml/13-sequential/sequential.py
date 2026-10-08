"""
Sequential models from scratch: hidden Markov models and linear-Gaussian
state-space models, in pure stdlib.

Everything here is exact arithmetic you can read: scaled forward-backward,
log-space Viterbi, Baum-Welch EM, the Kalman filter, the Rauch-Tung-Striebel
smoother, and a direct block-Gaussian posterior to check the recursions against.

Run `python3 sequential.py` for the demo.
"""

import math

# ---------------------------------------------------------------------------
# Small dense linear algebra (stdlib only)
# ---------------------------------------------------------------------------


def _matvec(M, v):
    return [sum(M[i][j] * v[j] for j in range(len(v))) for i in range(len(M))]


def _matmul(A, B):
    n, k, m = len(A), len(B), len(B[0])
    return [[sum(A[i][t] * B[t][j] for t in range(k)) for j in range(m)]
            for i in range(n)]


def _transpose(A):
    return [list(col) for col in zip(*A)]


def _add(A, B):
    return [[A[i][j] + B[i][j] for j in range(len(A[0]))] for i in range(len(A))]


def _sub(A, B):
    return [[A[i][j] - B[i][j] for j in range(len(A[0]))] for i in range(len(A))]


def _eye(n):
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _inv(M):
    """Gauss-Jordan inverse. The matrices here are tiny and well conditioned."""
    n = len(M)
    aug = [list(M[i]) + [1.0 if i == j else 0.0 for j in range(n)]
           for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-300:
            raise ValueError("singular matrix")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        pv = aug[col][col]
        aug[col] = [x / pv for x in aug[col]]
        for r in range(n):
            if r != col:
                f = aug[r][col]
                if f != 0.0:
                    aug[r] = [aug[r][c] - f * aug[col][c] for c in range(2 * n)]
    return [row[n:] for row in aug]


# ---------------------------------------------------------------------------
# Hidden Markov models
# ---------------------------------------------------------------------------


def forward(pi, A, B, obs):
    """Scaled forward algorithm.

    Returns ``(alphas, cs)`` where ``alphas[t][i]`` is the normalised forward
    probability ``P(q_t = i | o_1..o_t)`` (so each step sums to 1) and ``cs[t]``
    is the scaling factor used at step ``t`` -- the per-step likelihood
    ``P(o_1..o_t) / P(o_1..o_{t-1})``. Their product is ``P(o_1..o_T)``.

    Dividing at every step is what keeps long sequences from underflowing.
    """
    # TODO: Scaled forward recursion. At t=0 set a_i = pi_i B_i[o_0]; at each later step a_j = (sum_i alpha_{t-1,i} A[i][j]) B_j[o_t]. Divide a by its own sum c_t, append the normalised vector to alphas and c_t to cs, and return (alphas, cs). The division at every step is what stops long sequences underflowing; prod(cs) is P(obs).
    raise NotImplementedError("forward")


def backward(pi, A, B, obs):
    """Scaled backward algorithm.

    Returns ``(betas, cs)`` with the same scaling factors as :func:`forward`.
    The recursion divides by ``c_{t+1}`` so the product ``alphas[t]*betas[t]``
    is already ``P(q_t | o_1..o_T)``.
    """
    # TODO: Scaled backward recursion with the same scaling factors as forward. Start beta_{T-1,i} = 1 and recurse beta_t[i] = (sum_j A[i][j] B_j[o_{t+1}] beta_{t+1,j}) / c_{t+1}. Return (betas, cs). The transition index is A[i][j] (i -> j), not its transpose.
    raise NotImplementedError("backward")


def forward_backward(pi, A, B, obs):
    """Per-time posterior state marginals ``gamma[t][i] = P(q_t = i | obs)``."""
    # TODO: Combine the messages: gamma_t is the elementwise product alphas[t] * betas[t], normalised to sum to one. Return the list of per-time marginals.
    raise NotImplementedError("forward_backward")


def viterbi(pi, A, B, obs):
    """Most likely state sequence (the MAP path) by max-product in log space."""
    # TODO: Max-product in log space with backpointers. delta_0[i] = log pi_i + log B_i[o_0]; for each t and j, delta_t[j] = max_i (delta_{t-1}[i] + log A[i][j]) + log B_j[o_t], storing psi_t[j] = argmax_i. Take the best final state, then trace psi backwards to reconstruct the path. Keep the backpointers: a running max alone is not a decode.
    raise NotImplementedError("viterbi")


def baum_welch(pi, A, B, obs, maxit=50):
    """EM for HMM parameters.

    Returns ``(pi, A, B, logliks)`` where ``logliks[0]`` is the log-likelihood
    under the starting parameters and each later entry is after one M-step.
    """
    # TODO: EM. E-step: run forward-backward for gamma (occupancy) and xi_t[i][j] = alphas[t,i] A[i][j] B_j[o_{t+1}] betas[t+1,j], normalised. M-step: pi_i = gamma_0[i]; A[i][j] proportional to sum_t xi_t[i][j]; B[i][k] proportional to sum_{t: o_t=k} gamma_t[i]. Return (pi, A, B, logliks) with logliks[0] from the starting parameters; it must not decrease.
    raise NotImplementedError("baum_welch")


# ---------------------------------------------------------------------------
# Linear-Gaussian state-space models
# ---------------------------------------------------------------------------


def kalman_filter(mu0, P0, F, H, Q, R, obs):
    """Kalman filter.

    Model: ``x_0 ~ N(mu0, P0)``, ``x_t = F x_{t-1} + w``, ``w ~ N(0, Q)``,
    ``y_t = H x_t + v``, ``v ~ N(0, R)``.

    Returns ``(mus, Ps)``: the filtered means and covariances
    ``p(x_t | y_0..y_t)``.
    """
    # TODO: Predict then correct. At t>0 predict mu <- F mu, P <- F P F^T + Q. Then S = H P H^T + R, K = P H^T S^{-1}, mu <- mu + K (y - H mu), P <- (I - K H) P. Return the filtered (mus, Ps). Dropping R from S is wrong.
    raise NotImplementedError("kalman_filter")


def rts_smoother(mu0, P0, F, H, Q, R, obs):
    """Rauch-Tung-Striebel smoother: ``p(x_t | y_0..y_{T-1})``."""
    # TODO: Filter first, then sweep backwards. Predicted covariance Pp = F P_t F^T + Q; smoother gain G = P_t F^T Pp^{-1} (this is NOT the filter gain). Then m_t = mu_t + G (m_{t+1} - F mu_t) and P_t = P_t + G (P_{t+1} - Pp) G^T. Return the smoothed (means, covs).
    raise NotImplementedError("rts_smoother")


def batch_gaussian_posterior(mu0, P0, F, H, Q, R, obs):
    """Exact joint posterior marginals of the linear-Gaussian model.

    Assembles the full prior-plus-observations Gaussian in information form and
    inverts it. Returns ``(means, covs)`` for the marginal of each ``x_t``.
    This is the reference the filter and smoother must reproduce.
    """
    # TODO: Assemble the full linear-Gaussian system over X = (x_0..x_{T-1}) in information form: J = P0^{-1} on the first block, plus for each transition the residual x_t - F x_{t-1} with precision Q^{-1}, plus H^T R^{-1} H on each observation block and H^T R^{-1} y_t into the info vector. Invert J; the mean is J^{-1} h and the per-time blocks of J^{-1} are the exact marginal covariances. This is the reference, not a shipping algorithm.
    raise NotImplementedError("batch_gaussian_posterior")


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


def demo():
    print("Sequential models from scratch\n")

    pi = [0.6, 0.4]
    A = [[0.7, 0.3], [0.4, 0.6]]
    B = [[0.9, 0.1], [0.2, 0.8]]
    obs = [0, 0, 1, 1, 0, 1, 1, 1]
    print("HMM  pi", pi, " A", A, " B", B, " obs", obs)

    gamma = forward_backward(pi, A, B, obs)
    print("  forward-backward marginals:")
    for t, g in enumerate(gamma):
        print(f"    t={t}  {[round(x, 4) for x in g]}")

    path = viterbi(pi, A, B, obs)
    print("  Viterbi path:", path)

    ll0 = sum(math.log(c) for c in forward(pi, A, B, obs)[1])
    p2, A2, B2, lls = baum_welch(pi, A, B, obs, maxit=20)
    print(f"  Baum-Welch log-likelihood {ll0:.4f} -> {lls[-1]:.4f} "
          f"over {len(lls) - 1} iterations")
    print("    new A:", [[round(x, 3) for x in row] for row in A2])
    print("    new B:", [[round(x, 3) for x in row] for row in B2])

    mu0 = [0.0, 0.0]
    P0 = [[1.0, 0.2], [0.2, 0.8]]
    F = [[0.9, 0.1], [0.0, 0.8]]
    H = [[1.0, 0.0], [0.3, 0.7]]
    Q = [[0.2, 0.05], [0.05, 0.3]]
    R = [[0.4, 0.1], [0.1, 0.5]]
    y = [[0.1, 0.2], [0.5, -0.3], [-0.2, 0.4], [0.3, 0.1]]

    mus, Ps = kalman_filter(mu0, P0, F, H, Q, R, y)
    sm, sP = rts_smoother(mu0, P0, F, H, Q, R, y)
    bm, bc = batch_gaussian_posterior(mu0, P0, F, H, Q, R, y)

    print("\nKalman / RTS vs exact batch Gaussian posterior")
    print("  (filtered matches batch only at the last step; smoothed matches at every step)")
    for t in range(len(y)):
        ferr = max(abs(mus[t][i] - bm[t][i]) for i in range(2))
        serr = max(abs(sm[t][i] - bm[t][i]) for i in range(2))
        print(f"  t={t}  filtered mean {[round(x, 4) for x in mus[t]]} "
              f"(err {ferr:.2e})   smoothed mean {[round(x, 4) for x in sm[t]]} "
              f"(err {serr:.2e})")

    # Limit case: a long sequence underflows without scaling.
    obs_long = [i % 2 for i in range(1200)]
    alpha = [0.5 * 0.5, 0.5 * 0.5]
    for t in range(1, 1200):
        alpha = [sum(alpha[i] * 0.5 for i in range(2)) * 0.5 for _ in range(2)]
    scaled, cs = forward([0.5, 0.5], [[0.5, 0.5], [0.5, 0.5]],
                         [[0.5, 0.5], [0.5, 0.5]], obs_long)
    print(f"\nLimit: unscaled forward after 1200 steps = {max(alpha)} "
          f"(underflow), scaled = {[round(x, 4) for x in scaled[-1]]} "
          f"(stays normalised)")


if __name__ == "__main__":
    demo()
