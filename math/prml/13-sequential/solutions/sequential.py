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
    n = len(pi)
    T = len(obs)
    alphas = []
    cs = []

    a = [pi[i] * B[i][obs[0]] for i in range(n)]
    c = sum(a)
    cs.append(c)
    alphas.append([x / c for x in a])

    for t in range(1, T):
        prev = alphas[-1]
        a = []
        for j in range(n):
            s = 0.0
            for i in range(n):
                s += prev[i] * A[i][j]
            a.append(s * B[j][obs[t]])
        c = sum(a)
        cs.append(c)
        alphas.append([x / c for x in a])

    return alphas, cs


def backward(pi, A, B, obs):
    """Scaled backward algorithm.

    Returns ``(betas, cs)`` with the same scaling factors as :func:`forward`.
    The recursion divides by ``c_{t+1}`` so the product ``alphas[t]*betas[t]``
    is already ``P(q_t | o_1..o_T)``.
    """
    n = len(pi)
    T = len(obs)
    _, cs = forward(pi, A, B, obs)

    betas = [None] * T
    betas[T - 1] = [1.0] * n
    for t in range(T - 2, -1, -1):
        nxt = betas[t + 1]
        b = []
        for i in range(n):
            s = 0.0
            for j in range(n):
                s += A[i][j] * B[j][obs[t + 1]] * nxt[j]
            b.append(s / cs[t + 1])
        betas[t] = b

    return betas, cs


def forward_backward(pi, A, B, obs):
    """Per-time posterior state marginals ``gamma[t][i] = P(q_t = i | obs)``."""
    n = len(pi)
    T = len(obs)
    alphas, _ = forward(pi, A, B, obs)
    betas, _ = backward(pi, A, B, obs)

    gamma = []
    for t in range(T):
        g = [alphas[t][i] * betas[t][i] for i in range(n)]
        s = sum(g)
        gamma.append([x / s for x in g])
    return gamma


def viterbi(pi, A, B, obs):
    """Most likely state sequence (the MAP path) by max-product in log space."""
    n = len(pi)
    T = len(obs)
    log = math.log

    delta = [log(pi[i]) + log(B[i][obs[0]]) for i in range(n)]
    psi = [[0] * n for _ in range(T)]
    for t in range(1, T):
        nd = [0.0] * n
        for j in range(n):
            best = -1e18
            arg = 0
            for i in range(n):
                v = delta[i] + log(A[i][j])
                if v > best:
                    best = v
                    arg = i
            nd[j] = best + log(B[j][obs[t]])
            psi[t][j] = arg
        delta = nd

    best = -1e18
    last = 0
    for i in range(n):
        if delta[i] > best:
            best = delta[i]
            last = i

    path = [0] * T
    path[T - 1] = last
    for t in range(T - 1, 0, -1):
        path[t - 1] = psi[t][path[t]]
    return path


def baum_welch(pi, A, B, obs, maxit=50):
    """EM for HMM parameters.

    Returns ``(pi, A, B, logliks)`` where ``logliks[0]`` is the log-likelihood
    under the starting parameters and each later entry is after one M-step.
    """
    n = len(pi)
    T = len(obs)
    M = len(B[0])

    pi = list(pi)
    A = [row[:] for row in A]
    B = [row[:] for row in B]

    def loglik(p, a_, b_):
        alphas, cs = forward(p, a_, b_, obs)
        return sum(math.log(c) for c in cs)

    logliks = [loglik(pi, A, B)]

    for _ in range(maxit):
        alphas, _ = forward(pi, A, B, obs)
        betas, _ = backward(pi, A, B, obs)

        gamma = []
        for t in range(T):
            g = [alphas[t][i] * betas[t][i] for i in range(n)]
            s = sum(g)
            gamma.append([x / s for x in g])

        xi = []
        for t in range(T - 1):
            num = [[alphas[t][i] * A[i][j] * B[j][obs[t + 1]] * betas[t + 1][j]
                    for j in range(n)] for i in range(n)]
            s = sum(sum(row) for row in num)
            xi.append([[x / s for x in row] for row in num])

        new_pi = gamma[0][:]
        new_A = [[0.0] * n for _ in range(n)]
        for i in range(n):
            denom = sum(gamma[t][i] for t in range(T - 1))
            for j in range(n):
                num = sum(xi[t][i][j] for t in range(T - 1))
                new_A[i][j] = num / denom if denom > 1e-300 else A[i][j]

        new_B = [[0.0] * M for _ in range(n)]
        for i in range(n):
            denom = sum(gamma[t][i] for t in range(T))
            for k in range(M):
                num = sum(gamma[t][i] for t in range(T) if obs[t] == k)
                new_B[i][k] = num / denom if denom > 1e-300 else B[i][k]

        pi, A, B = new_pi, new_A, new_B
        logliks.append(loglik(pi, A, B))

    return pi, A, B, logliks


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
    n = len(mu0)
    mu = list(mu0)
    P = [row[:] for row in P0]
    mus = []
    Ps = []

    for t in range(len(obs)):
        if t > 0:
            mu = _matvec(F, mu)
            P = _add(_matmul(_matmul(F, P), _transpose(F)), Q)

        S = _add(_matmul(_matmul(H, P), _transpose(H)), R)  # innovation covariance
        K = _matmul(_matmul(P, _transpose(H)), _inv(S))
        pred = _matvec(H, mu)
        resid = [obs[t][i] - pred[i] for i in range(len(obs[t]))]
        delta = _matvec(K, resid)
        mu = [mu[i] + delta[i] for i in range(n)]
        P = _matmul(_sub(_eye(n), _matmul(K, H)), P)

        mus.append(mu[:])
        Ps.append([row[:] for row in P])

    return mus, Ps


def rts_smoother(mu0, P0, F, H, Q, R, obs):
    """Rauch-Tung-Striebel smoother: ``p(x_t | y_0..y_{T-1})``."""
    n = len(mu0)
    T = len(obs)
    mus, Ps = kalman_filter(mu0, P0, F, H, Q, R, obs)

    sm = [None] * T
    sP = [None] * T
    sm[T - 1] = mus[T - 1][:]
    sP[T - 1] = [row[:] for row in Ps[T - 1]]

    for t in range(T - 2, -1, -1):
        Pf = Ps[t]
        Pp = _add(_matmul(_matmul(F, Pf), _transpose(F)), Q)  # predicted cov
        G = _matmul(_matmul(Pf, _transpose(F)), _inv(Pp))     # smoother gain
        diff = [sm[t + 1][i] - _matvec(F, mus[t])[i] for i in range(n)]
        inc = _matvec(G, diff)
        sm[t] = [mus[t][i] + inc[i] for i in range(n)]
        sP[t] = _add(Pf, _matmul(_matmul(G, _sub(sP[t + 1], Pp)), _transpose(G)))

    return sm, sP


def batch_gaussian_posterior(mu0, P0, F, H, Q, R, obs):
    """Exact joint posterior marginals of the linear-Gaussian model.

    Assembles the full prior-plus-observations Gaussian in information form and
    inverts it. Returns ``(means, covs)`` for the marginal of each ``x_t``.
    This is the reference the filter and smoother must reproduce.
    """
    n = len(mu0)
    d = len(obs)
    D = n * d

    J = [[0.0] * D for _ in range(D)]
    h = [0.0] * D

    P0i = _inv(P0)
    for a in range(n):
        for b in range(n):
            J[a][b] += P0i[a][b]
        h[a] += sum(P0i[a][b] * mu0[b] for b in range(n))

    Qi = _inv(Q)
    Ft = _transpose(F)
    FQiF = _matmul(_matmul(Ft, Qi), F)
    FQi = _matmul(Ft, Qi)
    QiF = _matmul(Qi, F)
    for t in range(1, d):
        o0 = (t - 1) * n
        o1 = t * n
        for a in range(n):
            for b in range(n):
                J[o0 + a][o0 + b] += FQiF[a][b]
                J[o0 + a][o1 + b] += -FQi[a][b]
                J[o1 + a][o0 + b] += -QiF[a][b]
                J[o1 + a][o1 + b] += Qi[a][b]

    Ri = _inv(R)
    Ht = _transpose(H)
    HtRiH = _matmul(_matmul(Ht, Ri), H)
    for t in range(d):
        o = t * n
        for a in range(n):
            for b in range(n):
                J[o + a][o + b] += HtRiH[a][b]
        tmp = _matvec(_matmul(Ht, Ri), obs[t])
        for a in range(n):
            h[o + a] += tmp[a]

    Jinv = _inv(J)
    mean = _matvec(Jinv, h)
    means = [mean[t * n:(t + 1) * n] for t in range(d)]
    covs = []
    for t in range(d):
        o = t * n
        covs.append([[Jinv[o + a][o + b] for b in range(n)] for a in range(n)])
    return means, covs


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
