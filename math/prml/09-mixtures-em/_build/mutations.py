"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism, each an exact edit to a copy of the
solutions. Every mutation must be CAUGHT by the step named; a MISSED mutation
means the check is too weak, never that the bug is acceptable.
"""
MUTATIONS = [
    # The responsibilities must be normalised into mixture weights; returning the
    # raw component masses makes the weights sum to N and the recovery check fails.
    ("M-step does not normalise responsibilities into weights", "mixtures.py",
     "        weights.append(nk / n)\n",
     "        weights.append(nk)\n", "3"),
    # Using the prior as the responsibility throws away the data: every component
    # gets the same mean and variance and the parameters are never recovered.
    ("E-step uses the prior instead of the posterior", "mixtures.py",
     "        resp.append([s / total for s in scaled])\n",
     "        resp.append([weights[j] for j in range(k)])\n", "3"),
    # Without the floor a component that owns one point drives its variance to zero,
    # the degenerate maximum-likelihood solution the floor exists to prevent.
    ("variance floor is not applied (collapse)", "mixtures.py",
     "        v = max(v, var_floor, _MIN_VAR)\n",
     "        v = max(v, _MIN_VAR)\n", "5"),
    # Overwriting instead of appending hides any decrease and leaves a one-element
    # sequence, so the monotonicity accept check can no longer fire.
    ("log-likelihood sequence is overwritten instead of tracked", "mixtures.py",
     "        logliks.append(_gmm_loglikelihood(xs, weights, mus, vars))\n",
     "        logliks = [_gmm_loglikelihood(xs, weights, mus, vars)]\n", "2"),
    # Keeping the first restart reports a poor local optimum as if it were the
    # best available fit; the comparison against the reference restarts must fail.
    ("restart comparison keeps the first result instead of the best", "mixtures.py",
     "        if final > best_ll:\n"
     "            best_ll = final\n"
     "            best = (weights, mus, vars, logliks)\n",
     "        if best is None:\n"
     "            best_ll = final\n"
     "            best = (weights, mus, vars, logliks)\n", "5"),
]
