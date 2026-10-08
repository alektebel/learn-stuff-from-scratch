"""Planted bugs for the latent-continuous-variables checker.

Each entry is ``(description, file, exact text, replacement, check step)``.
``mutate.py`` copies ``solutions/`` into a temp dir, applies the replacement to
``solutions/latent.py``, and requires that the named step reports a failure.

Run from the repository root:

    python3 .claude/skills/graded-module/scripts/mutate.py \
        math/prml/12-latent-continuous math/prml/12-latent-continuous/_build/mutations.py
"""

MUTATIONS = [
    # Step 2: forgetting to mean-centre leaves the scores with a nonzero mean and
    # breaks the reconstruction-error identity.
    (
        "pca_eig does not mean-centre the data",
        "latent.py",
        "    mu = _mean(X)\n    Xc = mean_center(X)\n    vals, vecs = _eig_sorted(covariance(Xc))",
        "    mu = _mean(X)\n    Xc = [row[:] for row in X]\n    vals, vecs = _eig_sorted(covariance(Xc))",
        "2",
    ),
    # Step 2: using one extra component reconstructs too well and breaks the
    # discarded-eigenvalue identity.
    (
        "pca_eig reconstruction uses k + 1 components",
        "latent.py",
        "    n_used = k\n",
        "    n_used = k + 1\n",
        "2",
    ),
    # Step 4: the closed-form noise variance must be the discarded-eigenvalue
    # average, not a retained eigenvalue.
    (
        "ppca_closed_form drops the noise-term average",
        "latent.py",
        "    sigma2 = sum(vals[k:]) / (d - k)\n",
        "    sigma2 = vals[k - 1]\n",
        "4",
    ),
    # Step 4: if sigma^2 is frozen at its initialization EM cannot reach the MLE.
    (
        "ppca_em never updates sigma^2",
        "latent.py",
        "        sigma2 = max(sigma2_new, 1e-12)\n        W = Wnew",
        "        sigma2 = sigma2\n        W = Wnew",
        "4",
    ),
    # Step 5: kernel PCA must centre the kernel in feature space before the
    # eigen-decomposition, otherwise the top eigenvalue is the constant direction
    # and the whole spectrum is wrong.
    (
        "kernel_pca skips the feature-space centring of K",
        "latent.py",
        "    Kc = [[K[i][j] - row[i] - row[j] + total for j in range(n)] for i in range(n)]\n",
        "    Kc = [[K[i][j] for j in range(n)] for i in range(n)]\n",
        "5",
    ),
    # Step 5: the score columns must be the centred kernel's eigenvectors; a
    # transposed index gives orthonormal-looking columns that are not eigenvectors
    # of Kc, which the Gram test alone cannot see.
    (
        "kernel_pca transposes the eigenvector indexing",
        "latent.py",
        "    projection = [[vecs[j][i] * math.sqrt(max(vals[j], 0.0)) for j in range(k)]"
        " for i in range(n)]\n",
        "    projection = [[vecs[i][j] * math.sqrt(max(vals[j], 0.0)) for j in range(k)]"
        " for i in range(n)]\n",
        "5",
    ),
    # Step 6: the limit case must use the N x N Gram matrix, not the D x D
    # covariance; the eigenvalues then differ by the factor N.
    (
        "Gram limit uses the D x D covariance matrix",
        "latent.py",
        "    G = _gram_XXt(Xc)\n",
        "    G = covariance(X)\n",
        "6",
    ),
]
