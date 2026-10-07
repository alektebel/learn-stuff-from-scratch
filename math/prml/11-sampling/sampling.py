"""Sampling methods from scratch: rejection sampling, importance sampling, the
Markov-chain workhorses Metropolis-Hastings and Gibbs, and Hamiltonian Monte
Carlo.

Implements chapter 11 of Bishop, *Pattern Recognition and Machine Learning*
("Sampling Methods"): rejection sampling, importance sampling, Markov chain
Monte Carlo, the Metropolis-Hastings algorithm, Gibbs sampling and the hybrid
(Hamiltonian) Monte Carlo method. The argument is restated here, never copied.

The acceptance criterion of this node is a measurement, not an identity.
Importance-sampling estimates of a mean must be unbiased across repeated runs,
and on a correlated Gaussian HMC must return a higher effective sample size per
gradient than a random-walk Metropolis-Hastings run given the same evaluation
budget. The limit case is the classical trap of importance sampling: a proposal
whose tails are lighter than the target's makes the importance weights have
infinite variance, so the estimate has heavy spread and does not converge. A
proposal at least as heavy-tailed as the target does converge.

    python3 sampling.py    # prints the measurements this file promises
"""

import math
import random

__all__ = [
    "Chain",
    "rejection_sample",
    "importance_sample",
    "metropolis_hastings",
    "gibbs_sample",
    "hmc",
    "effective_sample_size",
    "gradient_count",
    "target_eval_count",
]


class Chain(list):
    """A list of samples tagged with the evaluation cost of the run.

    A plain ``list`` would throw away the number of proposal draws, target
    evaluations and gradients a sampler spent, which is exactly what the
    acceptance criterion compares. The class is a ``list`` subclass so every
    list operation still works; the counters are extra attributes.

    DESIGN DECISION -- carry the cost on the returned chain, not in a global
    counter?
    A global counter is shared between runs, so two samplers compared in the same
    process would contaminate each other's budgets, and a threaded or nested run
    would be impossible to attribute. Attaching the counters to the object the
    function already returns keeps every measurement local to its run; the cost
    is a tiny custom container instead of a bare list.
    """

    def __init__(self, samples=(), proposals=0, target_evals=0, gradients=0):
        super().__init__(samples)
        self.proposals = proposals
        self.target_evals = target_evals
        self.gradients = gradients


def _is_vector(x):
    """True for a state that is a vector (list or tuple) rather than a scalar."""
    return isinstance(x, (list, tuple))


def _copy(x):
    """A fresh list for a vector state, the value itself for a scalar."""
    if _is_vector(x):
        return list(x)
    return x


def _add(a, b):
    """Elementwise ``a + b`` for vector states, scalar addition otherwise."""
    if _is_vector(a):
        return [ai + bi for ai, bi in zip(a, b)]
    return a + b


def _scale(s, v):
    """``s * v`` elementwise for vector states, scalar multiplication otherwise."""
    if _is_vector(v):
        return [s * vi for vi in v]
    return s * v


def _norm2(v):
    """Squared Euclidean norm (the scalar square for a scalar state)."""
    if _is_vector(v):
        return sum(vi * vi for vi in v)
    return v * v


# ---------------------------------------------------------------------------
# Rejection sampling
# ---------------------------------------------------------------------------

def rejection_sample(target_pdf, proposal_pdf, propose, M, n, rng):
    """``n`` exact samples from ``target_pdf`` by rejection sampling.

    ``propose(rng)`` draws one candidate ``x`` from the proposal density
    ``proposal_pdf``; the candidate is accepted when ``u * M * proposal_pdf(x)
    <= target_pdf(x)`` for a fresh uniform ``u``, and rejected otherwise. ``M``
    must satisfy ``M >= sup_x target_pdf(x) / proposal_pdf(x)``, so the expected
    acceptance probability is ``1 / M``. Returns a ``Chain`` of exactly ``n``
    accepted samples; ``chain.proposals`` is the number of candidates drawn.

    DESIGN DECISION -- accept on ``u * M q <= p`` rather than
    ``u <= p / (M q)``?
    The two are algebraically identical but the first evaluates the densities at
    most once each and never divides, so it cannot divide by zero on a proposal
    with a zero. It is also the form in which the invariant is easiest to see:
    the number ``u * M * q`` is itself a uniform draw on ``[0, M q]``, and the
    test keeps it under the target at ``x``. Dropping the comparison and always
    accepting turns the output into ``n`` draws from the proposal, which is the
    planted bug. The cost is one surplus multiplication per candidate.
    """
    # TODO: Return a Chain of exactly n ACCEPTED samples. Loop: x = propose(rng); proposals += 1; accept x when rng.random() * M * proposal_pdf(x) <= target_pdf(x). Count the candidates in chain.proposals. Always accepting returns draws from the proposal, not the target (the planted bug).
    raise NotImplementedError("rejection_sample")


# ---------------------------------------------------------------------------
# Importance sampling
# ---------------------------------------------------------------------------

def importance_sample(target_logpdf, proposal_logpdf, propose, f, n, rng):
    """Draw ``n`` proposals and estimate ``E_p[f(X)]`` by importance weighting.

    Returns a dict with

    ``estimate``        ``(1/n) sum_i w_i f(x_i)`` with ``w_i =
                        p(x_i) / q(x_i)``. This is unbiased for a *normalised*
                        target density ``p``.
    ``self_normalised`` ``sum_i w_i f(x_i) / sum_i w_i``. This is consistent --
                        not unbiased at finite ``n`` -- when only an
                        unnormalised ``p`` is known, because the unknown
                        normalising constant cancels.
    ``weights``         the ``n`` raw ratios ``w_i``.
    ``ess``             the importance-sampling effective sample size
                        ``(sum_i w_i)^2 / sum_i w_i^2``.

    All ``w_i`` are shifted by their maximum before exponentiation for the
    self-normalised estimate and the ESS, so a large common factor cannot
    overflow; the plain ``estimate`` deliberately keeps the unshifted ratios so
    that it remains the unbiased estimator of the normalised target only.

    DESIGN DECISION -- both the plain and the self-normalised estimator?
    A single function cannot be both unbiased and usable with an unnormalised
    target. The plain weighted mean is unbiased when ``p`` integrates to one;
    the self-normalised ratio trades that for consistency under an unknown
    normaliser. Returning both makes the trade explicit instead of hiding it,
    and the checker grades each on the case where it holds. The cost is that a
    caller must know which one it needs.
    """
    # TODO: Draw n proposals; w_i = exp(target_logpdf(x_i) - proposal_logpdf(x_i)). Return a dict: estimate = (1/n) sum w_i f(x_i) (unbiased when the target is normalised); self_normalised = sum w_i f(x_i) / sum w_i (DIVIDE by the weight sum -- dropping the division is the planted bug and makes the value scale with n); weights = the raw ratios; ess = (sum w)^2 / sum w^2, computed on weights divided by their maximum to avoid overflow.
    raise NotImplementedError("importance_sample")


# ---------------------------------------------------------------------------
# Metropolis-Hastings and Gibbs
# ---------------------------------------------------------------------------

def metropolis_hastings(log_target, propose, x0, steps, rng):
    """Metropolis-Hastings with a symmetric proposal; ``steps + 1`` states.

    ``log_target(x)`` is the log unnormalised target and ``propose(x, rng)``
    returns a candidate ``y`` with ``q(y | x) = q(x | y)`` (a symmetric
    random-walk proposal, e.g. ``x + noise``). A candidate is accepted with
    probability ``min(1, exp(log_target(y) - log_target(x)))``. The returned
    ``Chain`` includes the initial state and counts ``steps + 1`` target
    evaluations.

    DESIGN DECISION -- accept on ``log(u) < min(0, log_target(y) -
    log_target(x))``?
    Taking logs keeps the ratio from underflowing when the target is tiny, and
    the ``min(0, .)`` floor is what makes an uphill move certain and a downhill
    move only sometimes. Without the floor ``log(u) < 0`` is always true and
    every step is accepted, so the chain becomes an unconstrained random walk
    with no stationary distribution -- the planted bug. The cost is one ``log``
    per step.
    """
    # TODO: Return a Chain of steps + 1 states starting at x0. For each step draw y = propose(x, rng) and accept when log(rng.random()) < min(0.0, log_target(y) - log_target(x)). The min(0, .) floor makes an uphill move certain and a downhill move occasional; keeping only 0 accepts every step (the planted bug). Record target_evals.
    raise NotImplementedError("metropolis_hastings")


def gibbs_sample(cond_samplers, x0, steps, rng):
    """Gibbs sampling: every sweep redraws every coordinate from its conditional.

    ``cond_samplers[i](x, rng)`` draws ``x[i]`` from its distribution given all
    the other coordinates as they currently stand. One sweep updates every
    coordinate in order (a systematic scan); the returned ``Chain`` holds
    ``steps + 1`` state tuples, starting at ``x0``.

    DESIGN DECISION -- update every coordinate in place, in order?
    A Gibbs sweep must redraw *every* coordinate from the conditional given the
    rest; redrawing only the first freezes the others at ``x0`` and the sample
    describes a line, not the target -- the planted bug. Updating in place is
    the standard systematic scan: later coordinates condition on the already
    updated earlier ones, which is still a valid transition kernel. The cost is
    a sequential sweep that cannot be vectorised.
    """
    # TODO: Return a Chain of steps + 1 state tuples starting at x0. Each sweep redraws EVERY coordinate: x[i] = cond_samplers[i](x, rng), in order, in place. Sweeping only the first coordinate freezes the rest at x0 and is the planted bug.
    raise NotImplementedError("gibbs_sample")


# ---------------------------------------------------------------------------
# Hamiltonian Monte Carlo
# ---------------------------------------------------------------------------

def hmc(log_target, grad_log_target, eps, L, x0, steps, rng):
    """Hamiltonian Monte Carlo with the leapfrog integrator.

    ``log_target(x)`` is the log unnormalised target and ``grad_log_target(x)``
    its gradient. Each step draws a fresh standard-normal momentum, integrates
    Hamilton's equations for ``L`` leapfrog moves of size ``eps``, and accepts
    the endpoint with the Metropolis rule on the Hamiltonian
    ``H(x, p) = -log_target(x) + 0.5 * |p|^2``. Returns ``steps + 1`` states and
    records ``L + 1`` gradient evaluations per step in ``chain.gradients``: the
    two half kicks plus the ``L - 1`` full kicks of the loop.

    DESIGN DECISION -- leapfrog (a symplectic, reversible integrator) rather
    than explicit Euler?
    The Metropolis acceptance compares the true Hamiltonian at the two ends. For
    that ratio to be a valid acceptance probability the proposal map must be
    volume-preserving and reversible; leapfrog is both, so it targets the
    correct distribution exactly while conserving ``H`` to ``O(eps^2)``.
    Explicit Euler (``x += eps p`` then ``p += eps grad`` with no half kick) is
    neither: the energy of the discrete trajectory drifts, the acceptance
    collapses or the chain samples the wrong covariance -- the planted bug. The
    cost is a half sized first and last kick, and so ``L + 1`` gradients rather
    than ``L`` per step.
    """
    # TODO: Return a Chain of steps + 1 states. Each step: p ~ N(0, I); save H_start = -log_target(x) + |p|^2/2; half momentum kick p += (eps/2) grad; then for i in range(L): x += eps p, and if i != L - 1 p += eps grad; then a final half kick p += (eps/2) grad. Accept the endpoint with log(u) < min(0, H_start - H_end); on rejection restore x. Count L + 1 gradients per step (two half kicks plus L - 1 full kicks) and one target evaluation per step beyond the initial. Dropping the half kicks (a forward Euler step) breaks energy conservation and is the planted bug.
    raise NotImplementedError("hmc")


# ---------------------------------------------------------------------------
# Effective sample size and cost reporting
# ---------------------------------------------------------------------------

def _autocovariance(xs, lag):
    """Sample autocovariance of ``xs`` at ``lag`` (divide by ``n``)."""
    n = len(xs)
    mean = sum(xs) / n
    total = 0.0
    for i in range(n - lag):
        total += (xs[i] - mean) * (xs[i + lag] - mean)
    return total / n


def _ess_scalar(xs):
    """ESS of one scalar chain by Geyer's initial-positive-sequence estimator.

    ``n / (1 + 2 sum_k rho_k)`` with the sum over consecutive lag *pairs*
    ``rho_{k} + rho_{k+1}``, truncated at the first non-positive pair. Pairing
    the lags and stopping at the first negative pair keeps the estimate from
    turning negative on a noisy autocorrelation function, which a single-lag
    truncation does not. The autocorrelation is truncated at 1000 lags for cost.
    """
    n = len(xs)
    if n < 2:
        return float(n)
    mean = sum(xs) / n
    variance = sum((x - mean) ** 2 for x in xs) / n
    if variance == 0.0:
        return float(n)
    max_lag = min(n - 2, 1000)
    gamma = [_autocovariance(xs, k) for k in range(max_lag + 1)]
    g0 = gamma[0]
    total = 0.0
    k = 1
    while k + 1 <= max_lag:
        pair = (gamma[k] + gamma[k + 1]) / g0
        if pair <= 0.0:
            break
        total += pair
        k += 2
    ess = n / (1.0 + 2.0 * total)
    if ess < 1.0:
        return 1.0
    if ess > n:
        return float(n)
    return ess


def effective_sample_size(chain):
    """Effective sample size of a chain, by the autocorrelation estimate.

    A scalar chain gives one number. A chain of vectors gives the *minimum*
    over coordinates: the bottleneck coordinate governs how many independent
    draws the chain is worth. The estimator is Geyer's initial-positive-sequence
    estimate ``n / (1 + 2 sum rho_k)`` (see ``_ess_scalar``); it is used rather
    than a naive ``n / (1 + 2 rho_1)`` because the lag-1 autocorrelation alone
    badly overestimates the ESS of a slowly mixing sampler.

    DESIGN DECISION -- minimum over coordinates for a vector chain?
    Averaging the coordinates would report a healthy ESS while one coordinate is
    effectively frozen, which is exactly the failure a random walk shows in the
    low-variance direction of a correlated Gaussian. The minimum is the honest
    measure. The cost is that a vector chain costs one pass per coordinate.
    """
    # TODO: Scalar chain: Geyer's initial-positive-sequence estimate n / (1 + 2 sum of consecutive autocorrelation PAIRS), truncated at the first non-positive pair, clamped to [1, n] (the _ess_scalar helper does this). Vector chain: the minimum over coordinates. Returning the chain length regardless of autocorrelation is the planted bug.
    raise NotImplementedError("effective_sample_size")


def gradient_count(chain):
    """The number of target-gradient evaluations a sampler spent on ``chain``."""
    return getattr(chain, "gradients", 0)


def target_eval_count(chain):
    """The number of target evaluations a sampler spent on ``chain``."""
    return getattr(chain, "target_evals", len(chain))


# ---------------------------------------------------------------------------
# Demonstration
# ---------------------------------------------------------------------------

def _beta_pdf(x):
    """Density of Beta(2, 3) on (0, 1): ``12 x (1 - x)^2``."""
    if x <= 0.0 or x >= 1.0:
        return 0.0
    return 12.0 * x * (1.0 - x) ** 2


def _uniform_pdf(x):
    """Density of Uniform(0, 1)."""
    return 1.0 if 0.0 <= x <= 1.0 else 0.0


def _cauchy_logpdf(x):
    """log density of the standard Cauchy distribution."""
    return -math.log(math.pi) - math.log1p(x * x)


def _normal_logpdf(x, sigma):
    """log density of N(0, sigma^2)."""
    return -0.5 * (x / sigma) ** 2 - math.log(sigma) - 0.5 * math.log(2.0 * math.pi)


def _heavy_logpdf(x, alpha=0.5):
    """log density of ``(alpha/2) (1 + |x|)^(-(1 + alpha))``.

    A symmetric power law with tail ``|x|^(-(1 + alpha))``; with ``alpha = 0.5``
    the tail exponent is 1.5, heavier than the Cauchy's 2, so it dominates the
    Cauchy target.
    """
    return math.log(alpha / 2.0) - (1.0 + alpha) * math.log1p(abs(x))


def _heavy_sample(rng, alpha=0.5):
    """One draw from ``_heavy_logpdf`` by inverse transform."""
    u = rng.random()
    if u < 0.5:
        return -(2.0 * u) ** (-1.0 / alpha) + 1.0
    return (2.0 * (1.0 - u)) ** (-1.0 / alpha) - 1.0


def _correlated_targets(rho):
    """``(log_target, grad_log_target)`` for N(0, [[1, rho], [rho, 1]])."""
    det = 1.0 - rho * rho

    def log_target(x):
        a, b = x
        return -0.5 * (a * a - 2.0 * rho * a * b + b * b) / det

    def grad_log_target(x):
        a, b = x
        return [-(a - rho * b) / det, -(b - rho * a) / det]

    return log_target, grad_log_target


def demo():
    """Print the measurements this module promises."""
    rng = random.Random(20261101)
    M = 16.0 / 9.0
    chain = rejection_sample(_beta_pdf, _uniform_pdf, lambda g: g.random(), M,
                             40000, rng)
    mean = sum(chain) / len(chain)
    var = sum((x - mean) ** 2 for x in chain) / len(chain)
    print("Rejection sampling, Beta(2, 3) target via Uniform(0, 1), M = 16/9")
    print(f"  sample mean {mean:.4f} (target 0.4000), variance {var:.4f} "
          "(target 0.0400)")
    print(f"  acceptance rate {len(chain) / chain.proposals:.4f} "
          f"(target 1/M = {1.0 / M:.4f})")

    rng = random.Random(20261102)
    est = importance_sample(
        lambda x: -0.5 * x * x - 0.5 * math.log(2.0 * math.pi),
        lambda x: -0.5 * x * x - 0.5 * math.log(2.0 * math.pi),
        lambda g: g.gauss(0.0, 1.0),
        lambda x: x * x, 20000, rng)
    print("Importance sampling, E[X^2] of N(0, 1) with a N(0, 1) proposal")
    print(f"  plain estimate {est['estimate']:.4f} (unbiased, target 1.0)")
    print(f"  self-normalised {est['self_normalised']:.4f}, ESS {est['ess']:.0f}")

    rho = 0.95
    log_target, grad = _correlated_targets(rho)
    rng = random.Random(20261103)
    hmc_chain = hmc(log_target, grad, 0.28, 12, [0.0, 0.0], 1200, rng)
    rng = random.Random(20261104)
    mh_chain = metropolis_hastings(
        log_target,
        lambda x, g: [x[0] + 0.28 * g.gauss(0.0, 1.0),
                      x[1] + 0.28 * g.gauss(0.0, 1.0)],
        [0.0, 0.0], 13 * 1200, rng)
    h_ess = effective_sample_size(hmc_chain[200:])
    m_ess = effective_sample_size(mh_chain[200:])
    h_grad = gradient_count(hmc_chain)
    m_eval = target_eval_count(mh_chain)
    print(f"Correlated 2-D Gaussian, rho = {rho}")
    print(f"  HMC  ESS/gradient      = {h_ess / h_grad:.5f} "
          f"({h_ess:.0f} over {h_grad} gradients)")
    print(f"  RW-MH ESS/target eval  = {m_ess / m_eval:.5f} "
          f"({m_ess:.0f} over {m_eval} evaluations)")

    rng = random.Random(20261105)
    invalid = importance_sample(
        _cauchy_logpdf, lambda x: _normal_logpdf(x, 1.0),
        lambda g: g.gauss(0.0, 1.0), lambda x: 1.0 / (1.0 + x * x), 4000, rng)
    rng = random.Random(20261106)
    valid = importance_sample(
        _cauchy_logpdf, _heavy_logpdf, _heavy_sample,
        lambda x: 1.0 / (1.0 + x * x), 4000, rng)
    print("Importance sampling of E[1/(1 + X^2)] for a Cauchy target (0.5)")
    print(f"  N(0, 1) proposal  (light): estimate {invalid['estimate']:.4f} "
          f"(self-normalised {invalid['self_normalised']:.4f}), "
          f"max weight {max(invalid['weights']):.0f}, ESS {invalid['ess']:.0f}")
    print(f"  power-law proposal (heavy): estimate {valid['estimate']:.4f} "
          f"(self-normalised {valid['self_normalised']:.4f}), "
          f"max weight {max(valid['weights']):.1f}, ESS {valid['ess']:.0f}")


if __name__ == "__main__":
    demo()
