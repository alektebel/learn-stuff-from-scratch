"""Markov chains and MCMC from scratch: the stationary distribution of a finite
irreducible chain as the left eigenvector of ``P`` for eigenvalue 1, and the two
workhorse samplers, Metropolis-Hastings and Gibbs.

Implements the Markov-chain material of Blitzstein & Hwang, *Introduction to
Probability* (2nd ed.), chapter 11 (Markov chains) and chapter 12 (Markov chain
Monte Carlo). The ideas are restated here, never copied.

The acceptance criterion of this node is a measurement, not an identity: the
*empirical* distribution of a long run of the chain must agree with the
stationary distribution. The stationary distribution is found by solving the
linear system ``pi P = pi`` with ``sum pi = 1`` -- that is, as the *left*
eigenvector of ``P`` for the eigenvalue 1 -- by Gaussian elimination. A power of
``P`` is deliberately not used on its own: it converges only for an aperiodic
chain, so it silently fails on the first limit case. The second limit case is a
bimodal target: a random-walk Metropolis-Hastings with a tiny step never crosses
the gap between the modes, so the sample describes one mode and lies about the
other.

    python3 mcmc.py    # prints the measurements this file promises
"""

import math
import random

__all__ = [
    "stationary_distribution",
    "matrix_power",
    "simulate_chain",
    "empirical_distribution",
    "metropolis_hastings",
    "gibbs_sampling",
    "target_mean_var",
]


# ---------------------------------------------------------------------------
# The stationary distribution of a finite chain
# ---------------------------------------------------------------------------

def stationary_distribution(P):
    """The stationary distribution of ``P`` as the left eigenvector of ``P``.

    ``P`` is a list of ``n`` rows, each a list of ``n`` transition
    probabilities, so ``P[i][j] = P(X_{t+1} = j | X_t = i)``. The stationary
    distribution ``pi`` satisfies ``pi P = pi`` and ``sum_i pi_i = 1``.

    DESIGN DECISION -- solve ``pi P = pi`` as a linear system, not by iterating
    ``P``?
    The equation ``sum_i pi_i P[i][j] = pi_j`` is ``n`` linear equations in
    ``pi``; one of them is redundant (the rows of ``P`` sum to 1), so the last
    is replaced by the normalisation ``sum pi = 1`` and the system is solved by
    Gaussian elimination. Iterating ``P`` (or reading a column of ``P^n``)
    converges to the WRONG answer whenever the chain is periodic: for
    ``[[0, 1], [1, 0]]`` the powers alternate between the identity and ``P``
    and never settle. The cost is an ``O(n^3)`` solve where a simulation would
    be ``O(n^2)`` per step, negligible for the small chains here.
    """
    n = len(P)
    # Augmented system A x = b, unknown x = pi. Equation j says (pi P)_j = pi_j,
    # i.e. sum_i pi_i (P[i][j] - delta_ij) = 0.
    A = []
    for j in range(n):
        row = [P[i][j] for i in range(n)]
        row[j] -= 1.0
        row.append(0.0)
        A.append(row)
    # The rows of P sum to 1, so one equation is redundant; replace the last
    # with the normalisation sum_i pi_i = 1.
    A[-1] = [1.0] * n + [1.0]

    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(A[r][col]))
        A[col], A[pivot] = A[pivot], A[col]
        pv = A[col][col]
        if pv == 0.0:
            raise ValueError("the linear system is singular; P is not irreducible")
        for c in range(col, n + 1):
            A[col][c] /= pv
        for r in range(n):
            if r != col and A[r][col] != 0.0:
                factor = A[r][col]
                for c in range(col, n + 1):
                    A[r][c] -= factor * A[col][c]

    pi = [A[i][n] for i in range(n)]
    total = sum(pi)
    return [x / total for x in pi]


def matrix_power(P, n):
    """``P`` raised to the integer power ``n`` (``n = 0`` is the identity).

    DESIGN DECISION -- an explicit repeated product, not a diagonalisation?
    The checker uses this only to expose periodicity: it needs the exact powers
    of a small matrix, and the repeated product is exact for integer and float
    entries alike. Diagonalising would need complex arithmetic for a real chain
    with complex eigenvalues and would round. The cost is ``O(n^3 log power)``,
    which is irrelevant at the sizes here.
    """
    size = len(P)
    result = [[1.0 if i == j else 0.0 for j in range(size)] for i in range(size)]
    base = [list(row) for row in P]
    power = n
    while power > 0:
        if power & 1:
            result = _matmul(result, base)
        base = _matmul(base, base)
        power >>= 1
    return result


def _matmul(A, B):
    """The matrix product ``A B`` for square lists of lists (helper)."""
    n = len(A)
    m = len(B[0])
    inner = len(B)
    return [[sum(A[i][k] * B[k][j] for k in range(inner))
             for j in range(m)] for i in range(n)]


# ---------------------------------------------------------------------------
# Simulating a chain
# ---------------------------------------------------------------------------

def simulate_chain(P, state, steps, rng):
    """A trajectory of ``steps + 1`` states of the chain, starting at ``state``.

    Each step draws ``U`` uniform and walks the cumulative distribution of the
    CURRENT row ``P[state]`` -- the row indexed by the state the chain is in.
    The initial state is included, so ``len(result) == steps + 1``.

    DESIGN DECISION -- walk the row ``P[state]``, never the column?
    ``P[i][j]`` is the probability of moving FROM ``i`` TO ``j``; drawing the
    next state from ``P[state]`` is the definition of the chain. Reading the
    column ``P[.][state]`` walks the transposed chain, whose stationary
    distribution is the right eigenvector of ``P`` -- uniform for the
    non-symmetric chain the checker uses -- and the empirical distribution then
    disagrees with ``pi``. The cost is that a chain with a heavy row is
    ``O(n)`` per step rather than a precomputed alias table.
    """
    states = [state]
    current = state
    for _ in range(steps):
        u = rng.random()
        acc = 0.0
        for j, p in enumerate(P[current]):
            acc += p
            if u < acc:
                current = j
                break
        states.append(current)
    return states


def empirical_distribution(states, n_states):
    """The fraction of ``states`` spent in each of ``0 .. n_states - 1``."""
    counts = [0] * n_states
    for s in states:
        counts[s] += 1
    total = len(states)
    return [c / total for c in counts]


# ---------------------------------------------------------------------------
# Metropolis-Hastings
# ---------------------------------------------------------------------------

def metropolis_hastings(log_target, proposal, x0, steps, rng):
    """Metropolis-Hastings with a symmetric proposal; returns ``steps + 1`` states.

    ``log_target`` is any callable ``x -> log(unnormalised density)`` and
    ``proposal`` is a callable ``(x, rng) -> y`` satisfying
    ``q(y | x) = q(x | y)`` (symmetric, e.g. a normal random walk). A proposal
    ``y`` is accepted with probability ``min(1, target(y) / target(x))``; the
    returned list starts at ``x0``.

    DESIGN DECISION -- accept on ``log U < min(0, log_target(y) - log_target(x))``
    rather than forming the ratio?
    The acceptance probability is ``min(1, exp(log_target(y) - log_target(x)))``.
    Working in logs keeps a very small target from underflowing to zero, and
    taking ``log`` of a uniform draw replaces the comparison with the ratio.
    The ``min(0, .)`` floor is what makes an uphill move always accepted while a
    downhill move is accepted only sometimes; removing it and keeping only the
    ``0`` accepts EVERY step, turning the chain into an unconstrained random
    walk with no stationary distribution. The cost is one ``log`` per step.
    """
    x = x0
    log_x = log_target(x)
    samples = [x]
    for _ in range(steps):
        y = proposal(x, rng)
        log_y = log_target(y)
        if math.log(rng.random()) < min(0.0, log_y - log_x):
            x = y
            log_x = log_y
        samples.append(x)
    return samples


# ---------------------------------------------------------------------------
# Gibbs sampling
# ---------------------------------------------------------------------------

def gibbs_sampling(cond_samplers, x0, steps, rng):
    """Gibbs sampling: each sweep redraws every coordinate from its conditional.

    ``cond_samplers`` is a list of callables, one per coordinate; the ``i``-th is
    called as ``sampler(x, rng) -> value`` and must draw ``x[i]`` from its
    distribution given all the OTHER coordinates as they currently stand. One
    sweep updates every coordinate in order (a systematic-scan Gibbs sweep); the
    returned list holds ``steps + 1`` state vectors, starting at ``x0``.

    DESIGN DECISION -- update coordinates in place on a copy, all of them?
    A Gibbs sweep must redraw EVERY coordinate from the conditional given the
    rest; redrawing only the first leaves the others frozen at ``x0`` and the
    sample describes a line, not the target. Updating in place (rather than from
    a snapshot of the whole vector) is the standard systematic scan: later
    coordinates condition on the already-updated earlier ones, which is still a
    valid transition kernel. The cost is that a sweep is sequential and cannot
    be vectorised.
    """
    x = list(x0)
    samples = [list(x)]
    for _ in range(steps):
        for i, sampler in enumerate(cond_samplers):
            x[i] = sampler(x, rng)
        samples.append(list(x))
    return samples


# ---------------------------------------------------------------------------
# Moments of a sample
# ---------------------------------------------------------------------------

def target_mean_var(samples):
    """``(mean, variance)`` of a list of scalars (population variance)."""
    n = len(samples)
    mean = sum(samples) / n
    variance = sum((s - mean) ** 2 for s in samples) / n
    return mean, variance


# ---------------------------------------------------------------------------
# Demonstration
# ---------------------------------------------------------------------------

def _correlation(xs, ys):
    """Pearson correlation of two equal-length lists (demo/limit use only)."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    if sxx == 0.0 or syy == 0.0:
        return 0.0
    return sxy / math.sqrt(sxx * syy)


def _bimodal_log_target(x):
    """log density of 0.5 N(-4, 0.5^2) + 0.5 N(4, 0.5^2), in log space."""
    a = -0.5 * ((x + 4.0) / 0.5) ** 2
    b = -0.5 * ((x - 4.0) / 0.5) ** 2
    m = max(a, b)
    return m + math.log(0.5 * math.exp(a - m) + 0.5 * math.exp(b - m))


def demo():
    """Print the measurements this module promises."""
    two_state = [[0.5, 0.5], [0.25, 0.75]]
    three_state = [[0.5, 0.25, 0.25],
                   [0.5, 0.0, 0.5],
                   [0.25, 0.25, 0.5]]
    print("Stationary distributions (left eigenvector of P, by elimination)")
    print(f"  2-state P = {two_state}")
    print(f"    pi = {[round(x, 6) for x in stationary_distribution(two_state)]}")
    print(f"  3-state P = {three_state}")
    print(f"    pi = {[round(x, 6) for x in stationary_distribution(three_state)]}")

    periodic = [[0.0, 1.0], [1.0, 0.0]]
    print("Periodic chain [[0,1],[1,0]]: stationary but never converges")
    print(f"  pi                    = {stationary_distribution(periodic)}")
    print(f"  P^50 (even)           = {matrix_power(periodic, 50)}")
    print(f"  P^51 (odd)            = {matrix_power(periodic, 51)}")

    rng = random.Random(20241107)
    states = simulate_chain(three_state, 0, 100000, rng)
    empirical = empirical_distribution(states[500:], 3)
    print("Empirical distribution of a 100000-step chain")
    print(f"  empirical = {[round(x, 4) for x in empirical]}")
    print(f"  pi        = {[round(x, 4) for x in stationary_distribution(three_state)]}")

    rng = random.Random(20241108)
    normal = metropolis_hastings(
        lambda x: -0.5 * x * x,
        lambda x, g: x + g.gauss(0.0, 1.0), 0.0, 100000, rng)
    mean, var = target_mean_var(normal[1000:])
    print("Metropolis-Hastings on a standard normal")
    print(f"  sample mean = {mean:.4f}   (target 0.0)")
    print(f"  sample var  = {var:.4f}   (target 1.0)")

    rho = 0.7
    spread = math.sqrt(1.0 - rho * rho)
    rng = random.Random(20241109)
    gibbs = gibbs_sampling(
        [lambda x, g: g.gauss(rho * x[1], spread),
         lambda x, g: g.gauss(rho * x[0], spread)],
        [0.0, 0.0], 100000, rng)[1000:]
    xs = [s[0] for s in gibbs]
    ys = [s[1] for s in gibbs]
    print("Gibbs sampling on a 2-D normal (rho = 0.7)")
    print(f"  mean(x), mean(y) = {sum(xs)/len(xs):.4f}, {sum(ys)/len(ys):.4f}")
    print(f"  var(x), var(y)   = {target_mean_var(xs)[1]:.4f}, "
          f"{target_mean_var(ys)[1]:.4f}")
    print(f"  corr(x, y)       = {_correlation(xs, ys):.4f}")

    print("Bimodal target: tiny step versus large step")
    for sigma in (0.02, 8.0):
        rng = random.Random(20241110)
        draws = metropolis_hastings(
            _bimodal_log_target,
            lambda x, g, s=sigma: x + g.gauss(0.0, s),
            -4.0, 100000, rng)[1000:]
        left = sum(1 for x in draws if x < 0.0) / len(draws)
        right = 1.0 - left
        print(f"  step {sigma:>4}: fraction left = {left:.4f}, right = {right:.4f}")


if __name__ == "__main__":
    demo()
