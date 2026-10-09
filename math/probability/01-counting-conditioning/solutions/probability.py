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
    if k < 0 or k > n:
        return 0
    result = 1
    for i in range(k):
        result *= n - i
    return result


def binomial_coefficient(n, k):
    """The number of k-element subsets of an n-element set: C(n, k) = n!/(k!(n-k)!).

    Computed from the multiplication principle as P(n, k) / k!, with the division
    folded into the product so every partial result stays an exact integer.
    Returns 0 unless 0 <= k <= n. Uses the symmetry C(n, k) = C(n, n-k) to keep
    the loop short.
    """
    if k < 0 or k > n:
        return 0
    k = min(k, n - k)
    result = 1
    for i in range(k):
        result = result * (n - i) // (i + 1)
    return result


def poker_two_pair_probability():
    """P(a 5-card poker hand is exactly two pairs), by counting.

    Sample space: all C(52, 5) hands. Favourable: choose the two ranks that pair
    up, C(13, 2); choose two of the four suits for each pair, C(4, 2)**2; choose
    the fifth card from the 11 ranks not used and 4 suits, 11*4 = 44. Divide the
    favourable count by the sample space -- the step that a bare count omits.
    """
    total = binomial_coefficient(52, 5)
    pairs = binomial_coefficient(13, 2) * binomial_coefficient(4, 2) ** 2
    kicker = 11 * 4
    return Fraction(pairs * kicker, total)


def poker_at_least_one_ace_probability():
    """P(a 5-card hand contains at least one ace), by inclusion-exclusion.

    Summing C(4, 1) C(51, 4) over "hands whose first chosen card is an ace"
    counts a hand with j aces j times. Inclusion-exclusion corrects each overlap:
    A1 + A2 + A3 + A4 - (pairs) + (triples) - (all four), where the overlaps are
    the hands containing a *fixed* set of aces. Equivalently 1 - C(48, 5)/C(52, 5).
    """
    total = binomial_coefficient(52, 5)
    # |A_i| = C(51, 4): fix ace i, choose the other four cards from the other 51.
    favourable = (binomial_coefficient(4, 1) * binomial_coefficient(51, 4)
                  - binomial_coefficient(4, 2) * binomial_coefficient(50, 3)
                  + binomial_coefficient(4, 3) * binomial_coefficient(49, 2)
                  - binomial_coefficient(4, 4) * binomial_coefficient(48, 1))
    return Fraction(favourable, total)


# ---------------------------------------------------------------------------
# Conditional probability and Bayes (chapter 2)
# ---------------------------------------------------------------------------

def total_probability(priors, likelihoods):
    """The law of total probability: P(E) = Σ_i P(H_i) P(E | H_i).

    ``priors`` are the probabilities of a partition of the sample space (they sum
    to 1); ``likelihoods`` are P(E | H_i). Every term must be included -- dropping
    one is dropping a way for E to happen.
    """
    if len(priors) != len(likelihoods):
        raise ValueError("priors and likelihoods must have the same length")
    total = Fraction(0)
    for prior, likelihood in zip(priors, likelihoods):
        total += Fraction(prior) * Fraction(likelihood)
    return total


def bayes_posterior(priors, likelihoods, index):
    """Bayes' rule: P(H_index | E) = P(H_index) P(E | H_index) / P(E).

    The denominator is the law of total probability over *every* case, not only
    the one in the numerator. Omitting the other terms -- classically the
    false-positive term of a diagnostic test -- makes the posterior 1.
    """
    if len(priors) != len(likelihoods):
        raise ValueError("priors and likelihoods must have the same length")
    if not 0 <= index < len(priors):
        raise IndexError("index is not a case")
    evidence = total_probability(priors, likelihoods)
    if evidence == 0:
        raise ValueError("the evidence has probability zero; the posterior is undefined")
    return Fraction(priors[index]) * Fraction(likelihoods[index]) / evidence


def diagnostic_posterior(prevalence, sensitivity, specificity):
    """P(disease | positive test) for a test with the given error rates.

    Two cases: diseased (prior ``prevalence``) and healthy (prior 1 - prevalence).
    The likelihood of a positive is ``sensitivity`` when diseased and
    ``1 - specificity`` when healthy -- the false-positive term that the base-rate
    problem is about. Exactness needs Fraction inputs.
    """
    priors = [Fraction(prevalence), 1 - Fraction(prevalence)]
    likelihoods = [Fraction(sensitivity), 1 - Fraction(specificity)]
    return bayes_posterior(priors, likelihoods, 0)


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
    if host_knows:
        return Fraction(2, 3) if switch else Fraction(1, 3)
    return Fraction(1, 2)


# ---------------------------------------------------------------------------
# Simulations: the independent check, one seeded generator per call
# ---------------------------------------------------------------------------

def simulate_two_pair(trials, seed=0):
    """Monte-Carlo estimate of :func:`poker_two_pair_probability`.

    Deals ``trials`` 5-card hands by ``rng.sample(range(52), 5)``, where card
    ``c`` has rank ``c // 4`` and suit ``c % 4``, and counts hands whose rank
    multiplicities are exactly {2, 2, 1}. Returns ``Fraction(wins, trials)``.
    """
    rng = random.Random(seed)
    wins = 0
    for _ in range(trials):
        hand = rng.sample(range(52), 5)
        counts = Counter(card // 4 for card in hand)
        if sorted(counts.values(), reverse=True) == [2, 2, 1]:
            wins += 1
    return Fraction(wins, trials)


def simulate_at_least_one_ace(trials, seed=0):
    """Monte-Carlo estimate of :func:`poker_at_least_one_ace_probability`.

    Counts dealt hands containing any ace (rank 0). Returns ``Fraction``.
    """
    rng = random.Random(seed)
    wins = 0
    for _ in range(trials):
        hand = rng.sample(range(52), 5)
        if any(card // 4 == 0 for card in hand):
            wins += 1
    return Fraction(wins, trials)


def simulate_diagnostic(prevalence, sensitivity, specificity, trials, seed=0):
    """Monte-Carlo estimate of :func:`diagnostic_posterior`.

    Draws disease and test independently for ``trials`` people, keeps the ones
    who test positive, and returns the fraction of *those* who are diseased.
    The false-positive term is produced by the simulation, not assumed, which is
    why it catches a Bayes denominator that forgot it.
    """
    rng = random.Random(seed)
    p = float(prevalence)
    sens = float(sensitivity)
    spec = float(specificity)
    positives = true_positives = 0
    for _ in range(trials):
        diseased = rng.random() < p
        if diseased:
            positive = rng.random() < sens
        else:
            positive = rng.random() < (1.0 - spec)
        if positive:
            positives += 1
            if diseased:
                true_positives += 1
    if positives == 0:
        raise ValueError("no positive tests in this run; raise the prevalence or the trials")
    return Fraction(true_positives, positives)


def simulate_monty_hall(switch, host_knows, trials, seed=0):
    """Monte-Carlo estimate of :func:`monty_hall_probability`.

    Per round: place the car, pick a door, and let the host open one of the other
    two -- a goat if he knows, uniformly at random if he does not. In the
    unknowing case, a round where he reveals the car is discarded, because the
    exact answer conditions on the game continuing. Returns ``Fraction``.
    """
    rng = random.Random(seed)
    wins = played = 0
    for _ in range(trials):
        car = rng.randrange(3)
        pick = rng.randrange(3)
        others = [door for door in range(3) if door != pick]
        if host_knows:
            goats = [door for door in others if door != car]
            opened = rng.choice(goats)
        else:
            opened = rng.choice(others)
            if opened == car:
                continue
        played += 1
        final = [door for door in range(3) if door != pick and door != opened][0]
        if (final == car) == switch:
            wins += 1
    if played == 0:
        raise ValueError("no completed rounds; raise the trials")
    return Fraction(wins, played)


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
