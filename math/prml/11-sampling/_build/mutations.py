"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism, each an exact edit to a copy of the
solutions -- or, for the infinite-variance limit case, to the checker itself.
Every mutation must be CAUGHT by the step named; a MISSED mutation means the
check is too weak, never that the bug is acceptable.

The five the node names: rejection sampling that always accepts (the
``u * M * q <= p`` test dropped); importance weights that are not normalised;
HMC with a forward Euler step instead of leapfrog (no momentum half-kick, so the
energy is wrong); an effective sample size that counts every sample; and the
infinite-variance limit case silently using a heavier-tailed proposal where the
weight variance is actually finite.
"""
MUTATIONS = [
    # The acceptance test is removed: every candidate drawn from the proposal is
    # kept, so the output is Uniform(0, 1), not Beta(2, 3), and the acceptance
    # rate is 1 instead of 1/M.
    ("rejection_sample always accepts (drops the u*M*q <= p test)", "sampling.py",
     "        if rng.random() * M * proposal_pdf(x) <= target_pdf(x):\n"
     "            samples.append(x)\n",
     "        samples.append(x)\n", "1"),
    # The self-normalised estimator forgets to divide by the weight sum, so its
    # value scales with n instead of cancelling the unknown normaliser.
    ("importance_sample does not normalise the self-normalised weights",
     "sampling.py",
     "    self_normalised = sum(w * f(x) for w, x in zip(shifted, xs)) / total\n",
     "    self_normalised = sum(w * f(x) for w, x in zip(shifted, xs))\n", "2"),
    # Leapfrog becomes an explicit forward Euler step: the momentum is updated
    # from the OLD position and there is no half kick, so the discrete energy
    # drifts and the proposal is no longer a faithful Hamiltonian move. The
    # gradient count stays L + 1, so only the energy/covariance/ESS checks catch
    # it.
    ("hmc uses a forward Euler step with no momentum half-kick", "sampling.py",
     "        grad = grad_log_target(x)\n"
     "        gradients += 1\n"
     "        p = _add(p, _scale(0.5 * eps, grad))\n"
     "        for i in range(L):\n"
     "            x = _add(x, _scale(eps, p))\n"
     "            if i != L - 1:\n"
     "                grad = grad_log_target(x)\n"
     "                gradients += 1\n"
     "                p = _add(p, _scale(eps, grad))\n"
     "        grad = grad_log_target(x)\n"
     "        gradients += 1\n"
     "        p = _add(p, _scale(0.5 * eps, grad))\n",
     "        grad = grad_log_target(x)\n"
     "        gradients += 1\n"
     "        for i in range(L):\n"
     "            x = _add(x, _scale(eps, p))\n"
     "            p = _add(p, _scale(eps, grad))\n"
     "            grad = grad_log_target(x)\n"
     "            gradients += 1\n", "3"),
    # The ESS returns the chain length regardless of autocorrelation: the slow
    # random walk looks perfectly efficient and the HMC comparison collapses.
    ("effective_sample_size returns the chain length regardless of autocorrelation",
     "sampling.py",
     "    return _ess_scalar(list(chain))\n",
     "    return float(len(chain))\n", "3"),
    # The limit case quietly swaps the light Gaussian proposal for the valid
    # heavy-tailed one, so the weights have finite variance and the assertions
    # that demand divergence must fire.
    ("infinite-variance limit case uses a valid heavier-tailed proposal",
     "check.py",
     "    gauss = (lambda x: _normal_logpdf(x, 1.0), lambda g: g.gauss(0.0, 1.0))\n",
     "    gauss = (_heavy_logpdf, _heavy_sample)\n", "5"),
]
