"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism, each an exact edit to a copy of the solutions
(or of the checker). Every mutation must be CAUGHT by the step named; a MISSED
mutation means the check is too weak, never that the bug is acceptable.

The five the node names: the q(tau) update drops the Gamma prior parameters; the
ELBO omits the entropy term; the ELBO sequence is overwritten instead of tracked
(so a decrease is hidden); the checker's evidence bound uses >= instead of <=;
and the correlated limit case claims mean-field matches the true marginal
variances. The fourth row mutates check.py: it fires the guard that protects the
checker's own bound direction.
"""
MUTATIONS = [
    # q(tau) forgets the prior Gamma(a0, b0): the updated a and b no longer
    # maximise the same ELBO, so coordinate ascent is no longer monotone.
    ("q(tau) update drops the Gamma prior parameters", "variational.py",
     "        a = a0 + (n + 1.0) / 2.0\n"
     "        b = b0 + 0.5 * exp_sumsq + 0.5 * lambda0 * exp_mu_dev\n",
     "        a = (n + 1.0) / 2.0\n"
     "        b = 0.5 * exp_sumsq + 0.5 * lambda0 * exp_mu_dev\n", "2"),
    # Dropping the entropies breaks the bound: E[ln p] - E[ln q] without the
    # entropy is no longer <= the log evidence.
    ("ELBO omits the entropy term", "variational.py",
     "    return term_lik + term_prior_mu + term_prior_tau + entropy_mu + entropy_tau\n",
     "    return term_lik + term_prior_mu + term_prior_tau\n", "3"),
    # Overwriting instead of appending hides any decrease and leaves a
    # one-element sequence, so the monotonicity accept check can no longer fire.
    ("ELBO sequence is overwritten instead of tracked", "variational.py",
     "        elbos.append(value)\n",
     "        elbos = [value]\n", "2"),
    # The checker's own evidence bound sign is flipped: the correct solution
    # (ELBO below the evidence) must then trip the guard.
    ("the evidence bound uses >= instead of <=", "check.py",
     "    assert bound <= evidence + 1e-9, (\n",
     "    assert bound >= evidence + 1e-9, (\n", "3"),
    # Mean-field cannot match the true marginals of a correlated Gaussian: the
    # fit returns the true variances, so the understatement test must fail.
    ("correlated limit case claims mean-field matches the true marginal variances",
     "variational.py",
     "    return variances\n",
     "    return [1.0, 1.0]\n", "5"),
]
