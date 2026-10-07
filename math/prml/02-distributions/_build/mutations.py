"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism, each an exact edit to a copy of the
solutions. Every mutation must be CAUGHT by the step named; a MISSED mutation
means the check is too weak, never that the bug is acceptable.
"""
MUTATIONS = [
    # Swapping the counts updates the wrong parameter: the prior no longer means
    # what Beta(alpha, beta) says.
    ("beta update adds heads to beta and tails to alpha (swapped)", "distributions.py",
     "    return (alpha + heads, beta + tails)\n",
     "    return (alpha + tails, beta + heads)\n", "1"),
    # Forgetting the prior turns the posterior into the raw counts; the strength of
    # the prior (pseudo-counts) is lost.
    ("dirichlet update forgets the prior (returns counts only)", "distributions.py",
     "    return [a + c for a, c in zip(alpha, counts)]\n",
     "    return list(counts)\n", "1"),
    # A running average with unit pseudo-counts ignores the observation variance and
    # the prior precision, so it cannot reproduce the batch posterior.
    ("gaussian sequential update uses a plain average that ignores the prior precision",
     "distributions.py",
     "    obs_precision = 1.0 / (sigma * sigma)\n"
     "    tau_new = tau + obs_precision\n"
     "    mu_new = (tau * mu + x * obs_precision) / tau_new\n",
     "    tau_new = tau + 1.0\n"
     "    mu_new = (tau * mu + x) / tau_new\n", "2"),
    # The unbiased normaliser: E[sum sq dev / (N-1)] = sigma^2, so the (N-1)/N bias
    # disappears and the accept check must notice.
    ("gaussian_mle divides by N-1 instead of N (no bias)", "distributions.py",
     "    variance = sum((x - mean) ** 2 for x in xs) / n\n",
     "    variance = sum((x - mean) ** 2 for x in xs) / (n - 1)\n", "3"),
    # Dropping the 1/(n h) scale leaves a sum of kernels, which is not a density:
    # it does not integrate to one.
    ("kde drops the 1/(n h) normalisation", "distributions.py",
     "    return sum(_gaussian_kernel((x - xi) / h) for xi in xs) / (n * h)\n",
     "    return sum(_gaussian_kernel((x - xi) / h) for xi in xs)\n", "5"),
    # Dropping the kernel leaves the normalisation alone, a flat (non-smooth) estimate.
    ("kde drops the Gaussian kernel", "distributions.py",
     "    return sum(_gaussian_kernel((x - xi) / h) for xi in xs) / (n * h)\n",
     "    return 1.0 / (n * h)\n", "5"),
]
