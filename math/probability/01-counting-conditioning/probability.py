"""Counting, conditional probability and Bayes' rule, from scratch.

Implements the first two chapters of Blitzstein & Hwang, *Introduction to
Probability* (2nd ed.): the multiplication principle and binomial coefficients
(ch. 1), and conditional probability, the law of total probability and Bayes'
rule (ch. 2). The argument is restated here, never copied.

The module's contract is the skill-tree acceptance criterion: every probability
is computed twice -- once exactly with ``fractions.Fraction`` by counting, and
once by Monte-Carlo simulation with an explicitly seeded ``random.Random`` --
and the two must agree to within four standard errors at 10**5 trials. The exact
Fraction is the oracle; the simulation is the independent check that the
combinatorial argument used the right sample space. A counting mistake (a
missing division, an overlap counted twice) passes neither.

DESIGN DECISION -- exact fractions, or floating point?
Floating point is faster and needs no division logic, but it destroys the very
thing the module teaches: you cannot tell a wrong sample space from rounding.
**Chosen: ``Fraction`` end to end for the exact answers.** The cost is slower
arithmetic and the need to keep inputs exact (``Fraction(1, 100)``, not the float
``0.01``) or the denominator carries a power of two and never cancels.

DESIGN DECISION -- build counting from scratch, or call ``math.comb``?
``math.comb`` is correct and instant. **Chosen: build ``falling_factorial`` and
``binomial_coefficient`` from the multiplication principle**, because chapter 1
*is* the multiplication principle; delegating it would hide where the factors
and the divisions come from. ``check.py`` still uses ``math.comb`` as its
independent oracle, which is exactly the point of not using it here.

DESIGN DECISION -- who owns the random number generator?
A module-level ``random`` call makes results depend on every other call made
before it, so a check cannot fix a seed and reproduce a number. **Chosen: every
simulation constructs its own ``random.Random(seed)``**, so the same arguments
always give the same answer and the checker can compare against a known-wrong
value without the test order mattering. Cost: the caller must pass a seed.

DESIGN DECISION -- what should a simulation return?
A float is conventional; a Fraction can be compared to the exact answer with no
tolerance at all, which would be the wrong test (simulations are never exact).
**Chosen: ``Fraction(wins, trials)``.** The checker converts to float once and
measures the gap in standard errors, so the simulation never has to round early
and the acceptance rule stays explicit.

DESIGN DECISION -- how to model the Monty Hall host who does not know?
Treating the host as omniscient gives 2/3 for switching in both variants and
hides the lesson. **Chosen: an unknowing host opens one of the two unpicked
doors at random and the game is conditioned on that door hiding a goat** (if he
reveals the car there is nothing to decide). Under that conditioning the two
remaining doors are symmetric and switching wins 1/2. The contrast with the
knowing host's 2/3 is the limit case the node asks for.

    python3 probability.py      # prints the measurements this file promises
"""

from collections import Counter
from fractions import Fraction
import random


# ---------------------------------------------------------------------------
# Counting (chapter 1)
# ---------------------------------------------------------------------------

def falling_factorial(n, k):
    """The number of ways to pick k ordered distinct items from n: P(n, k) = n!/(n-k)!.

    Also written ``n(n-1)...(n-k+1)``: the multiplication principle, one factor
    per position. Returns 0 when k > n (there is no such selection) and 1 when
    k == 0 (one empty selection).
    """
    # TODO: The multiplication principle: multiply exactly k descending factors n·(n−1)···(n−k+1). Return 0 when k > n or k < 0, and 1 when k == 0.
    raise NotImplementedError("falling_factorial")


def binomial_coefficient(n, k):
    """The number of k-element subsets of an n-element set: C(n, k) = n!/(k!(n-k)!).

    Computed from the multiplication principle as P(n, k) / k!, with the division
    folded into the product so every partial result stays an exact integer.
    Returns 0 unless 0 <= k <= n. Uses the symmetry C(n, k) = C(n, n-k) to keep
    the loop short.
    """
    # TODO: C(n, k) = P(n, k)/k!. Fold the division into the product (multiply, then integer-divide by i+1) so every partial result stays exact. Return 0 outside 0 <= k <= n; use C(n, n−k) to keep the loop short.
    raise NotImplementedError("binomial_coefficient")


def poker_two_pair_probability():
    """P(a 5-card poker hand is exactly two pairs), by counting.

    Sample space: all C(52, 5) hands. Favourable: choose the two ranks that pair
    up, C(13, 2); choose two of the four suits for each pair, C(4, 2)**2; choose
    the fifth card from the 11 ranks not used and 4 suits, 11*4 = 44. Divide the
    favourable count by the sample space -- the step that a bare count omits.
    """
    # TODO: Favourable hands: C(13,2) ways to pick the two paired ranks, C(4,2)² suit choices, and 44 kickers (11 unused ranks × 4 suits). Divide by C(52,5) — a count is not a probability.
    raise NotImplementedError("poker_two_pair_probability")


def poker_at_least_one_ace_probability():
    """P(a 5-card hand contains at least one ace), by inclusion-exclusion.

    Summing C(4, 1) C(51, 4) over "hands whose first chosen card is an ace"
    counts a hand with j aces j times. Inclusion-exclusion corrects each overlap:
    A1 + A2 + A3 + A4 - (pairs) + (triples) - (all four), where the overlaps are
    the hands containing a *fixed* set of aces. Equivalently 1 - C(48, 5)/C(52, 5).
    """
    # TODO: Inclusion-exclusion over the four aces: C(4,1)C(51,4) − C(4,2)C(50,3) + C(4,3)C(49,2) − C(4,4)C(48,1), divided by C(52,5). The naive first term counts hands with two aces twice. The complement 1 − C(48,5)/C(52,5) is equivalent.
    raise NotImplementedError("poker_at_least_one_ace_probability")


# ---------------------------------------------------------------------------
# Conditional probability and Bayes (chapter 2)
# ---------------------------------------------------------------------------

def total_probability(priors, likelihoods):
    """The law of total probability: P(E) = Σ_i P(H_i) P(E | H_i).

    ``priors`` are the probabilities of a partition of the sample space (they sum
    to 1); ``likelihoods`` are P(E | H_i). Every term must be included -- dropping
    one is dropping a way for E to happen.
    """
    # TODO: Σ_i P(H_i)·P(E | H_i) over the whole partition. Convert every input with Fraction first so float prefixes do not creep in. Drop no term.
    raise NotImplementedError("total_probability")


def bayes_posterior(priors, likelihoods, index):
    """Bayes' rule: P(H_index | E) = P(H_index) P(E | H_index) / P(E).

    The denominator is the law of total probability over *every* case, not only
    the one in the numerator. Omitting the other terms -- classically the
    false-positive term of a diagnostic test -- makes the posterior 1.
    """
    # TODO: P(H_index)·P(E | H_index) divided by the law of total probability over EVERY case (call total_probability). Using only the numerator's case makes the posterior 1.
    raise NotImplementedError("bayes_posterior")


def diagnostic_posterior(prevalence, sensitivity, specificity):
    """P(disease | positive test) for a test with the given error rates.

    Two cases: diseased (prior ``prevalence``) and healthy (prior 1 - prevalence).
    The likelihood of a positive is ``sensitivity`` when diseased and
    ``1 - specificity`` when healthy -- the false-positive term that the base-rate
    problem is about. Exactness needs Fraction inputs.
    """
    # TODO: Two cases: [prevalence, 1 − prevalence] with likelihoods [sensitivity, 1 − specificity]. Defer to bayes_posterior on index 0; the false-positive term is 1 − specificity.
    raise NotImplementedError("diagnostic_posterior")


# ---------------------------------------------------------------------------
# Monty Hall (the limit case): a knowing host and an unknowing one
# ---------------------------------------------------------------------------

def monty_hall_probability(switch, host_knows):
    """P(win) in Monty Hall, exactly, for a knowing or an unknowing host.

    You pick one of three doors; the host opens one of the other two, revealing a
    goat; you may switch to the last closed door or stay.

    * ``host_knows`` True: the host never opens the car, so if you initially
      picked a goat (probability 2/3) the switch door holds the car. Switching
      wins 2/3, staying 1/3.
    * ``host_knows`` False: the host opens one of the two unpicked doors at
      random. Condition on his door hiding a goat: P(goat revealed) = 2/3, and
      the car sits behind the stay door in 1/3 of the joint and behind the switch
      door in 1/6 + 1/6 = 1/3. Both are 1/2. The host's knowledge, not the
      switching, is what created the 2/3.
    """
    # TODO: Knowing host: 2/3 for switching, 1/3 for staying. Unknowing host: condition on the reveal showing a goat — the two closed doors are symmetric, so 1/2 either way.
    raise NotImplementedError("monty_hall_probability")


# ---------------------------------------------------------------------------
# Simulations: the independent check, one seeded generator per call
# ---------------------------------------------------------------------------

def simulate_two_pair(trials, seed=0):
    """Monte-Carlo estimate of :func:`poker_two_pair_probability`.

    Deals ``trials`` 5-card hands by ``rng.sample(range(52), 5)``, where card
    ``c`` has rank ``c // 4`` and suit ``c % 4``, and counts hands whose rank
    multiplicities are exactly {2, 2, 1}. Returns ``Fraction(wins, trials)``.
    """
    # TODO: Deal with rng.sample(range(52), 5); card c has rank c // 4. Count hands whose rank multiplicities are exactly [2, 2, 1]. Return Fraction(wins, trials).
    raise NotImplementedError("simulate_two_pair")


def simulate_at_least_one_ace(trials, seed=0):
    """Monte-Carlo estimate of :func:`poker_at_least_one_ace_probability`.

    Counts dealt hands containing any ace (rank 0). Returns ``Fraction``.
    """
    # TODO: Deal 5 cards and count the hands containing any rank-0 (ace) card. Return Fraction.
    raise NotImplementedError("simulate_at_least_one_ace")


def simulate_diagnostic(prevalence, sensitivity, specificity, trials, seed=0):
    """Monte-Carlo estimate of :func:`diagnostic_posterior`.

    Draws disease and test independently for ``trials`` people, keeps the ones
    who test positive, and returns the fraction of *those* who are diseased.
    The false-positive term is produced by the simulation, not assumed, which is
    why it catches a Bayes denominator that forgot it.
    """
    # TODO: Per person draw disease with probability prevalence, then the test result with sensitivity or 1 − specificity. Return true positives / positives (the posterior).
    raise NotImplementedError("simulate_diagnostic")


def simulate_monty_hall(switch, host_knows, trials, seed=0):
    """Monte-Carlo estimate of :func:`monty_hall_probability`.

    Per round: place the car, pick a door, and let the host open one of the other
    two -- a goat if he knows, uniformly at random if he does not. In the
    unknowing case, a round where he reveals the car is discarded, because the
    exact answer conditions on the game continuing. Returns ``Fraction``.
    """
    # TODO: Place car and pick; the knowing host opens a goat among the other doors, the unknowing host opens one at random and the round is DISCARDED if it shows the car. Condition the win rate on completed rounds only.
    raise NotImplementedError("simulate_monty_hall")


if __name__ == "__main__":
    import math

    TRIALS = 100_000

    def line(name, exact, simulated, trials=TRIALS):
        p = float(exact)
        se = math.sqrt(p * (1.0 - p) / trials)
        gap = abs(p - float(simulated))
        flag = "ok" if gap <= 4.0 * se else "OUTSIDE 4 SE"
        print(f"  {name:<26} exact {p:.4f}  sim {float(simulated):.4f}"
              f"  gap {gap:.4f}  4SE {4.0 * se:.4f}  {flag}")

    print("Counting & conditioning from scratch — exact vs 10^5-trial simulation")
    line("two pair", poker_two_pair_probability(), simulate_two_pair(TRIALS, seed=1))
    line("at least one ace", poker_at_least_one_ace_probability(),
         simulate_at_least_one_ace(TRIALS, seed=2))

    prevalence, sens, spec = Fraction(1, 100), Fraction(95, 100), Fraction(90, 100)
    print(f"  base rate                  prevalence {float(prevalence):.2%}"
          f"  sensitivity {float(sens):.0%}  specificity {float(spec):.0%}")
    print(f"  {'diagnostic posterior':<26} P(disease | +) = "
          f"{float(diagnostic_posterior(prevalence, sens, spec)):.4f}"
          "   (the intuitive answer is the sensitivity, 0.95)")
    line("diagnostic posterior", diagnostic_posterior(prevalence, sens, spec),
         simulate_diagnostic(prevalence, sens, spec, TRIALS, seed=3))

    print("  Monty Hall")
    for host_knows in (True, False):
        for switch in (False, True):
            exact = monty_hall_probability(switch, host_knows)
            simulated = simulate_monty_hall(switch, host_knows, TRIALS, seed=4)
            who = "knowing" if host_knows else "unknowing"
            act = "switch" if switch else "stay"
            line(f"  {who} host, {act}", exact, simulated)
