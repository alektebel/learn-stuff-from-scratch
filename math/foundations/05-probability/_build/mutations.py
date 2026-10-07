"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism. Each must be CAUGHT by the step named; a MISSED
mutation means the check is too weak, not that the bug is acceptable.
"""
MUTATIONS = [
    # Cholesky accepts a non-positive pivot, so a non-SPD matrix is taken as a covariance.
    ("Cholesky accepts a non-SPD matrix", "gaussians.py",
     "                if s <= 0.0:\n"
     "                    raise NotPositiveDefinite(\n"
     "                        f\"pivot {s:.3e} at ({i},{i}) is not positive: A is not positive definite\")\n",
     "                if s <= -1e300:\n"
     "                    raise NotPositiveDefinite(\n"
     "                        f\"pivot {s:.3e} at ({i},{i}) is not positive: A is not positive definite\")\n",
     "1"),
    # The log density through the inverse and the determinant: on a block covariance
    # whose determinant underflows, det Σ is 0.0 and log det raises/loses everything.
    ("log density via inverse+det", "gaussians.py",
     "    L = cholesky(Sigma)\n"
     "    z = _forward_sub(L, [x[i] - mu[i] for i in range(n)])\n"
     "    quadratic = _dot(z, z)\n"
     "    log_det = 2.0 * sum(math.log(L[i][i]) for i in range(n))\n"
     "    return -0.5 * (n * math.log(_TWO_PI) + log_det + quadratic)\n",
     "    aug = [list(Sigma[i]) + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]\n"
     "    det = 1.0\n"
     "    for col in range(n):\n"
     "        p = max(range(col, n), key=lambda i: abs(aug[i][col]))\n"
     "        aug[col], aug[p] = aug[p], aug[col]\n"
     "        if p != col:\n"
     "            det = -det\n"
     "        det *= aug[col][col]\n"
     "        pv = aug[col][col]\n"
     "        aug[col] = [v / pv for v in aug[col]]\n"
     "        for i in range(n):\n"
     "            if i != col and aug[i][col]:\n"
     "                f = aug[i][col]\n"
     "                aug[i] = [a - f * b for a, b in zip(aug[i], aug[col])]\n"
     "    inv = [row[n:] for row in aug]\n"
     "    dx = [x[i] - mu[i] for i in range(n)]\n"
     "    quadratic = sum(dx[i] * inv[i][j] * dx[j] for i in range(n) for j in range(n))\n"
     "    return -0.5 * (n * math.log(_TWO_PI) + math.log(det) + quadratic)\n",
     "4"),
    # The density without its normalising constant does not integrate to 1.
    ("density missing the normalising constant", "gaussians.py",
     "    return -0.5 * (n * math.log(_TWO_PI) + log_det + quadratic)\n",
     "    return -0.5 * (log_det + quadratic)\n",
     "3"),
    # Sampling forgets the Cholesky factor: the covariance of the draws is the identity.
    ("sampling ignores the covariance", "gaussians.py",
     "    L = cholesky(Sigma)\n"
     "    z = [rng.gauss(0.0, 1.0) for _ in range(n)]\n"
     "    return [mu[i] + sum(L[i][j] * z[j] for j in range(i + 1)) for i in range(n)]\n",
     "    z = [rng.gauss(0.0, 1.0) for _ in range(n)]\n"
     "    return [mu[i] + z[i] for i in range(n)]\n",
     "5"),
    # The transformed covariance loses the transpose: A Σ instead of A Σ Aᵀ.
    ("linear map covariance loses the transpose", "gaussians.py",
     "    Sigma_y = _matmul(_matmul(A, Sigma), _transpose(A))\n",
     "    Sigma_y = _matmul(A, Sigma)\n",
     "6"),
    # The product adds covariances instead of precisions.
    ("product adds covariances", "gaussians.py",
     "    P = [[P1[i][j] + P2[i][j] for j in range(n)] for i in range(n)]\n",
     "    P = [[Sigma1[i][j] + Sigma2[i][j] for j in range(n)] for i in range(n)]\n",
     "7"),
    # The marginal returns the whole covariance instead of the submatrix.
    ("marginal returns the wrong block", "gaussians.py",
     "    return [mu[i] for i in idx], _submatrix(Sigma, idx, idx)\n",
     "    return [mu[i] for i in idx], Sigma\n",
     "8"),
    # The conditional covariance omits the Schur-complement subtraction.
    ("conditional covariance is not a Schur complement", "gaussians.py",
     "    Sigma_a = [[S_aa[r][c] - S_ab_Y[r][c] for c in range(na)] for r in range(na)]\n",
     "    Sigma_a = [[S_aa[r][c] for c in range(na)] for r in range(na)]\n",
     "9"),
    # The change of variables drops the Jacobian factor.
    ("change of variables drops the Jacobian", "gaussians.py",
     "        return pdf_x(g_inv(y)) * abs(g_inv_prime(y))\n",
     "        return pdf_x(g_inv(y))\n",
     "10"),
]
