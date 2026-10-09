"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism, each an exact edit to a copy of the
solutions (or of the checker). Every mutation must be CAUGHT by the step named;
a MISSED mutation means the check is too weak, never that the bug is acceptable.

The five the node names: the change-of-variables formula drops the 1/|g'|
Jacobian factor; the convolution returns the elementwise product of the pmfs
instead of the convolution sum; the Markov bound is replaced by the exact tail
(so it is no longer a bound above it and no longer looser than Chernoff); the
central-limit standardisation divides by the variance instead of the standard
deviation; and the checker's own Cauchy limit case assumes the sample mean
converges. The last two rows mutate check.py: they fire the guards that protect
the checker's own logic.
"""
MUTATIONS = [
    # Change of variables forgets the Jacobian 1/|g'| factor.
    ("change of variables forgets the |g'| Jacobian factor", "limits.py",
     "    return fy(g_inv(y)) / abs(g_prime_inv(y))\n",
     "    return fy(g_inv(y))\n", "1"),
    # Convolution returns the elementwise product instead of the sum.
    ("convolution returns the elementwise product of the pmfs", "limits.py",
     "    out = [0] * (len(p) + len(q) - 1)\n"
     "    for i, pi in enumerate(p):\n"
     "        if pi == 0:\n"
     "            continue\n"
     "        for j, qj in enumerate(q):\n"
     "            out[i + j] += pi * qj\n"
     "    return out\n",
     "    return [p[i] * q[i] for i in range(min(len(p), len(q)))]\n", "2"),
    # Markov omitted: the checker substitutes the exact tail for the bound, so
    # it is not above the tail and Chernoff is not below it.
    ("Markov bound omitted (returns the exact tail, not a bound above it)",
     "check.py",
     "        markov = markov_bound(mean, float(k))\n",
     "        markov = float(exact)  # Markov omitted: not a bound above the tail\n",
     "3"),
    # CLT standardisation divides by the variance instead of the standard
    # deviation: the standard error becomes sigma^2/sqrt(n) instead of
    # sigma/sqrt(n), and the distance to the standard normal blows up.
    ("CLT standardisation divides by the variance, not the standard deviation",
     "limits.py",
     "    se = sigma / math.sqrt(n)\n",
     "    se = sigma * sigma / math.sqrt(n)\n", "4"),
    # The limit-case checker assumes the Cauchy mean converges: the guard that
    # measures the spread instead must fail.
    ("the Cauchy limit-case check assumes the mean converges", "check.py",
     "    converged = spread_large <= 0.75 * spread_small\n",
     "    converged = True  # assumes the Cauchy mean converges\n", "5"),
]
