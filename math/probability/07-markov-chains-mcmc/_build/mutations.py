"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism, each an exact edit to a copy of the
solutions -- or, for the bimodal limit case, to the checker itself. Every
mutation must be CAUGHT by the step named; a MISSED mutation means the check is
too weak, never that the bug is acceptable.

The five the node names: the stationary distribution taken as the right
eigenvector instead of the left; the simulated chain walking the transpose;
Metropolis-Hastings accepting every step; Gibbs sweeping only the first
coordinate; and the bimodal limit case assuming a small step explores both
modes.
"""
MUTATIONS = [
    # The stationary distribution solves P v = v (right eigenvector) instead of
    # pi P = pi (left eigenvector). The right eigenvector for eigenvalue 1 of a
    # row-stochastic P is uniform, so the non-uniform hand chains catch it.
    ("stationary_distribution uses the right eigenvector (P[j][i])", "mcmc.py",
     "        row = [P[i][j] for i in range(n)]\n",
     "        row = [P[j][i] for i in range(n)]\n", "1"),
    # The chain walks the column P[.][current] instead of the row P[current]:
    # the transposed chain, whose stationary distribution is uniform (the right
    # eigenvector of P), not pi = (0.4, 0.2, 0.4).
    ("simulate_chain applies P^T (walks the column, not the row)", "mcmc.py",
     "        for j, p in enumerate(P[current]):\n",
     "        for j, p in enumerate([row[current] for row in P]):\n", "2"),
    # The acceptance floor is dropped: log(U) < 0 is always true, so every
    # proposal is accepted and the chain is an unconstrained random walk.
    ("metropolis_hastings drops the min(0, .) floor (accepts every step)", "mcmc.py",
     "        if math.log(rng.random()) < min(0.0, log_y - log_x):\n",
     "        if math.log(rng.random()) < 0.0:\n", "3"),
    # Gibbs redraws only the first coordinate; the second stays frozen at x0, so
    # its variance is zero and the correlation is undefined.
    ("gibbs_sampling sweeps only the first coordinate", "mcmc.py",
     "        for i, sampler in enumerate(cond_samplers):\n",
     "        for i, sampler in enumerate(cond_samplers[:1]):\n", "4"),
    # The limit case uses a large "small" step, assuming it explores both modes:
    # with a step comparable to the gap it does, so the trapped assertion fires.
    ("bimodal limit case assumes the small step explores both modes", "check.py",
     "    small_sigma = 0.02\n",
     "    small_sigma = 5.0\n", "5"),
]
