"""Hints for the latent-continuous-variables templates.

One entry per graded function.  These are nudges, not code; the worked version
is in ``solutions/latent.py``.
"""

HINTS = {
    "latent.py": {
        "mean_center":
            "Compute the D column means first, then subtract. Keep the shape N x D. "
            "Everything downstream assumes the returned matrix has zero column means.",
        "covariance":
            "Mean-centre, then form Xc^T Xc / N element by element. Use 1/N, NOT 1/(N-1): "
            "with 1/N the mean squared reconstruction error equals the sum of the discarded "
            "eigenvalues exactly (step 2). The matrix is symmetric, so fill both triangles.",
        "pca_eig":
            "Write a cyclic Jacobi solver for the symmetric covariance: for each p < q rotate "
            "to zero a[p][q] using theta = (a[q][q]-a[p][p])/(2 a[p][q]), t = sign(theta)/"
            "(|theta|+sqrt(theta^2+1)), c = 1/sqrt(t^2+1), s = t c. Apply the rotation to the "
            "columns, then the rows, and accumulate it into the eigenvector matrix. Sort the "
            "eigenvalues descending. Components are the top-k eigenvectors; scores are "
            "Xc @ V^T; reconstruction is scores @ V + mean.",
        "pca_svd":
            "Eigen-decompose the D x D matrix Xc^T Xc (an SVD of Xc has squared singular values "
            "equal to its eigenvalues) and divide the eigenvalues by N to get the same "
            "covariances as pca_eig. The eigenvectors are the same principal directions. "
            "The two routes must agree to ~1e-7.",
        "ppca_closed_form":
            "sigma^2 = (1/(D-k)) * sum of the discarded covariance eigenvalues. W = U_k "
            "diag(sqrt(lambda_j - sigma^2)); clip at zero for safety. This is the global "
            "maximum-likelihood solution, while EM only reaches it up to a rotation.",
        "ppca_em":
            "E step: with M = W^T W + sigma^2 I, the posterior has E[z_n] = M^{-1} W^T x_n and "
            "E[z_n z_n^T] = sigma^2 M^{-1} + E[z_n]E[z_n]^T. M step: W_new = (sum x_n E[z_n]^T)"
            "(sum E[z_n z_n^T])^{-1} and sigma^2_new = mean_n(||x_n||^2 - 2 E[z_n]^T W_new^T x_n "
            "+ tr(E[z_n z_n^T] W_new^T W_new)) / D. Log-likelihood: -ND/2 ln 2pi - N/2 ln|C| "
            "- N/2 tr(C^{-1} S) with C = W W^T + sigma^2 I and S = Xc^T Xc / N. It must not "
            "decrease.",
        "kernel_pca":
            "Centre in feature space: Kc = K - 1 K / N - K 1 / N + 1 K 1 / N^2 (row means and "
            "the grand mean). Eigen-decompose Kc; the j-th training score is sqrt(lambda_j) v_j. "
            "Keep the top k eigenvalues in descending order.",
        "pca_gram":
            "For D > N the D x D covariance is rank-deficient, so use the N x N Gram matrix "
            "G = Xc Xc^T. Its nonzero eigenvalues are N times the covariance eigenvalues; "
            "recover each direction as v = Xc^T u / sqrt(lambda). The centred data has rank at "
            "most N-1, so the smallest Gram eigenvalue is ~0 and must not be returned.",
        "demo":
            "Generate X = Z A + small noise with a low-rank A, then fit each model and print "
            "the top variances, the reconstruction error versus the discarded-eigenvalue sum, "
            "the PPCA sigma^2 from both routes, and the kernel-PCA spectrum.",
    },
}
