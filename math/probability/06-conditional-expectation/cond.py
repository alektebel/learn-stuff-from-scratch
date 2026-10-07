"""Conditional expectation from scratch: Adam's law, Eve's law, ``E[Y | X]`` as
the best predictor in squared error, and the variance decomposition of a
hierarchical model.

Implements chapter 9 of Blitzstein & Hwang, *Introduction to Probability*
(2nd ed.): conditional expectation, the law of total expectation (Adam's law),
the law of total variance (Eve's law), and the fact that ``E[Y | X]`` minimises
the mean squared error among all functions of ``X``. The argument is restated
here, never copied.

The node's acceptance criterion is an inequality: ``E[Y | X]``, read as a
function of ``X``, has mean squared error no larger than any other predictor
``g(X)``. The limit case is a two-stage (hierarchical) model where the average
conditional variance ``E[Var(Y | X)]`` alone understates the spread of ``Y``:
the between-group variance ``Var(E[Y | X])`` is missing, and Eve's law restores
it. Exactness matters because the whole node is a set of algebraic identities;
a joint written with :class:`fractions.Fraction` is carried through without a
single rounding, so the checker can compare with ``==`` instead of a tolerance.

    python3 cond.py    # prints the measurements this file promises
"""

import random
from fractions import Fraction

__all__ = [
    "conditional_expectation",
    "conditional_variance",
    "adam_law",
    "eve_law",
    "best_predictor_mse",
    "hierarchical_moments",
]


# ---------------------------------------------------------------------------
# Joint pmf handling
# ---------------------------------------------------------------------------

def _iter_joint(joint):
    """Yield ``((x, y), p)`` for a dict ``{(x, y): p}`` or a matrix ``joint[i][j]``.

    The two containers are the same two the rest of the probability track uses:
    a dict keyed by ``(x, y)`` pairs, and a list of rows with
    ``joint[i][j] = P(X = i, Y = j)``. Reading both here means every function
    below is written once against a stream of weighted outcomes.
    """
    if isinstance(joint, dict):
        for (x, y), p in joint.items():
            yield (x, y), p
    else:
        for i, row in enumerate(joint):
            for j, p in enumerate(row):
                yield (i, j), p


def _x_support(joint):
    """The values of X that carry outcomes, in first-seen order."""
    if isinstance(joint, dict):
        seen = []
        for x in (key[0] for key in joint):
            if x not in seen:
                seen.append(x)
        return seen
    return list(range(len(joint)))


def _p_x(joint, x0):
    """The marginal P(X = x0)."""
    return sum(p for (x, _y), p in _iter_joint(joint) if x == x0)


def _conditional_terms(joint, given):
    """The row ``P(X = given, Y = y)`` as a list of ``(y, p)`` pairs."""
    if isinstance(joint, dict):
        terms = {}
        for (x, y), p in joint.items():
            if x == given:
                terms[y] = terms.get(y, 0) + p
        return list(terms.items())
    return list(enumerate(joint[given]))


# ---------------------------------------------------------------------------
# Conditional expectation and variance
# ---------------------------------------------------------------------------

def conditional_expectation(joint, given):
    """E[Y | X = ``given``] for a 2-D joint pmf.

    ``joint`` is a dict ``{(x, y): p}`` or a matrix ``joint[i][j]``. The answer
    is ``sum_y y * P(Y = y | X = given)``, i.e. the row of the joint normalised
    by the probability of the conditioning event.

    DESIGN DECISION -- divide by P(X = given), never by the number of outcomes
    and never by 1?
    The conditional pmf is ``P(X = x, Y = y) / P(X = x)``. Dividing by the row
    count averages the entries to 1 instead of summing them to 1; dividing by 1
    leaves the row as a sub-probability that sums to ``P(X = x)``. Both turn
    ``E[Y | X = x]`` into the wrong number, and step 1 of the checker compares
    against an exact hand value to catch them. The cost is that a conditioning
    event of probability zero raises instead of returning ``nan``.
    """
    # TODO: E[Y | X = given] = sum_y y P(Y = y | X = given). Normalise the row P(X = given, Y = y) by the marginal P(X = given) = sum_y P(X = given, Y = y). Never divide by the number of outcomes or by 1: the conditional pmf must sum to 1. Works for a dict {(x, y): p} and a matrix joint[i][j].
    raise NotImplementedError("conditional_expectation")


def conditional_variance(joint, given):
    """Var(Y | X = ``given``) = E[Y^2 | X = given] - (E[Y | X = given])^2.

    DESIGN DECISION -- the second moment, not ``sum (y - mean)^2``?
    Both are the definition; the second-moment form reuses
    :func:`conditional_expectation`'s normalisation exactly and stays exact for
    rational inputs. Building the deviation form would need the conditional pmf
    first (another pass) and would round twice. The cost is one extra sum, paid
    once per conditioning value.
    """
    # TODO: Var(Y | X = given) = E[Y^2 | X = given] - (E[Y | X = given])^2, with the same row normalised by P(X = given). The second moment is sum_y y^2 P(X = given, Y = y) / P(X = given).
    raise NotImplementedError("conditional_variance")


# ---------------------------------------------------------------------------
# Adam's law and Eve's law
# ---------------------------------------------------------------------------

def adam_law(joint):
    """Return ``(E[Y], sum_x P(X = x) E[Y | X = x])``.

    The law of total expectation (Adam's law): the unconditional mean is the
    ``P(X = x)``-weighted average of the conditional means.

    DESIGN DECISION -- weight each conditional by P(X = x), not average them
    equally?
    ``E[Y] = sum_x P(X = x) E[Y | X = x]``. An unweighted average of the
    conditionals is correct only when the conditioning values are equally
    likely; on any skewed joint it silently changes the answer, which is exactly
    the bug step 2 plants. The cost is carrying the marginal alongside the
    conditional, which is one more pass over the joint.
    """
    # TODO: Return (direct, law): direct = sum over outcomes of y * p; law = sum_x P(X = x) * E[Y | X = x]. Weight each conditional by the marginal P(X = x) -- averaging the conditionals unweighted is the planted bug.
    raise NotImplementedError("adam_law")


def eve_law(joint):
    """Return ``(Var(Y), E[Var(Y | X)], Var(E[Y | X]))``.

    The law of total variance (Eve's law):
    ``Var(Y) = E[Var(Y | X)] + Var(E[Y | X])``.

    DESIGN DECISION -- return the two components separately, not just their sum?
    The identity is the point, and the limit case needs each term on its own to
    show which one the naive reading drops. Collapsing to a single total would
    make the decomposition unobservable; the cost is a 3-tuple whose third entry
    is the between-group variance. ``direct`` is always computable from the joint
    alone, so the two are independent estimates of the same quantity.
    """
    # TODO: Return (Var(Y), E[Var(Y | X)], Var(E[Y | X])). Var(Y) directly from the joint; E[Var(Y|X)] = sum_x P(X=x) Var(Y|X=x); Var(E[Y|X]) = sum_x P(X=x) (E[Y|X=x] - E[Y])^2. The total equals the sum of the two components.
    raise NotImplementedError("eve_law")


# ---------------------------------------------------------------------------
# E[Y | X] as the best predictor in squared error
# ---------------------------------------------------------------------------

def best_predictor_mse(joint, predictor):
    """Mean squared error ``E[(Y - g(X))^2]`` of the predictor ``g``.

    ``predictor`` is any callable ``x -> number``. The theorem this node accepts
    is that ``g(x) = E[Y | X = x]`` attains the minimum over all such ``g``, so
    any predictor the checker tries must score no lower -- with strict
    inequality against the best constant whenever Y actually depends on X.

    DESIGN DECISION -- take ``g`` as a callable rather than a table of values?
    A callable lets the checker compare against ``conditional_expectation``
    itself, a fitted line, or a random function without the module knowing their
    shapes. The cost is that the predictor is called once per outcome instead of
    once per distinct x; the joint is small, so this is negligible.
    """
    # TODO: E[(Y - g(X))^2] = sum over outcomes of p * (y - predictor(x))^2. The predictor is any callable x -> number; E[Y | X] is the minimiser.
    raise NotImplementedError("best_predictor_mse")


# ---------------------------------------------------------------------------
# Hierarchical (two-stage) model
# ---------------------------------------------------------------------------

def hierarchical_moments(p, n, q0, q1):
    """Variance of a two-stage model, split by Eve's law.

    Stage 1: ``X ~ Bernoulli(p)`` (``P(X = 1) = p``). Stage 2:
    ``Y | X = 1 ~ Binomial(n, q1)`` and ``Y | X = 0 ~ Binomial(n, q0)``.
    Returns ``(Var(Y), E[Var(Y | X)], Var(E[Y | X]))``.

    DESIGN DECISION -- compute the decomposition in closed form, not by
    simulation?
    The counts are Binomial, so the conditional mean is ``n q`` and the
    conditional variance is ``n q (1 - q)``; the mixture moments then follow
    exactly. A simulation would only approximate the identity this node is
    about. The cost is that only this parameterised family is covered; the
    checker's sampler is the independent check that the closed form is right.
    """
    # TODO: X ~ Bernoulli(p), Y | X = 1 ~ Binomial(n, q1), Y | X = 0 ~ Binomial(n, q0). with = p n q1 (1-q1) + (1-p) n q0 (1-q0); between = p (1-p) (n q1 - n q0)^2; total = with + between. Return (total, with, between). Dropping 'between' is the planted bug.
    raise NotImplementedError("hierarchical_moments")


# ---------------------------------------------------------------------------
# Demonstration scaffolding (not part of the graded deliverables)
# ---------------------------------------------------------------------------

def _sample_joint(joint, trials, rng):
    """Draw ``trials`` (x, y) pairs from a joint pmf with a cumulative walk."""
    outcomes = list(_iter_joint(joint))
    cumulative = []
    acc = 0
    for xy, p in outcomes:
        acc = acc + p
        cumulative.append((acc, xy))
    draws = []
    for _ in range(trials):
        u = rng.random()
        for acc, xy in cumulative:
            if u <= acc:
                draws.append(xy)
                break
        else:
            draws.append(outcomes[-1][0])
    return draws


def _sample_binomial(n, q, rng):
    """Count successes in ``n`` Bernoulli(q) trials (for the demo only)."""
    return sum(1 for _ in range(n) if rng.random() < q)


def _sample_hierarchical(p, n, q0, q1, trials, rng):
    """Draw ``trials`` Y values from the two-stage model (for the demo only)."""
    draws = []
    for _ in range(trials):
        if rng.random() < p:
            draws.append(_sample_binomial(n, q1, rng))
        else:
            draws.append(_sample_binomial(n, q0, rng))
    return draws


def _variance(values):
    """Population variance of a list (for the demo only)."""
    n = len(values)
    mean = sum(values) / n
    return sum((v - mean) ** 2 for v in values) / n


def demo():
    """Print the measurements this module promises."""
    hand = {(0, 0): Fraction(1, 2), (0, 1): Fraction(1, 4),
            (1, 0): Fraction(1, 4)}

    print("Adam's law on the hand joint")
    direct, law = adam_law(hand)
    print(f"  E[Y] from the joint          = {direct}")
    print(f"  sum_x P(X = x) E[Y | X = x]  = {law}")

    print("Eve's law on the hand joint")
    var_y, within, between = eve_law(hand)
    print(f"  Var(Y) from the joint        = {var_y}")
    print(f"  E[Var(Y | X)]                = {within}")
    print(f"  Var(E[Y | X])                = {between}")
    print(f"  within + between             = {within + between}")

    nonlinear = {(0, 0): Fraction(1, 6), (0, 1): Fraction(1, 6),
                 (1, 0): Fraction(0), (1, 1): Fraction(1, 3),
                 (2, 0): Fraction(1, 6), (2, 1): Fraction(1, 6)}
    mse_eyx = best_predictor_mse(nonlinear, lambda x: conditional_expectation(nonlinear, x))
    mse_const = best_predictor_mse(nonlinear, lambda x: Fraction(2, 3))
    mse_line = best_predictor_mse(
        nonlinear, lambda x: Fraction(1, 4) * x + Fraction(1, 2))
    mse_quad = best_predictor_mse(
        nonlinear, lambda x: Fraction(-1, 2) * x * x + x + Fraction(1, 2))
    print("E[Y | X] as the best predictor (mean squared error)")
    print(f"  E[Y | X]          = {mse_eyx}")
    print(f"  best constant     = {mse_const}")
    print(f"  a linear fit      = {mse_line}")
    print(f"  quadratic fit     = {mse_quad}")

    p, n, q0, q1 = Fraction(1, 3), 6, Fraction(1, 5), Fraction(3, 5)
    total, within, between = hierarchical_moments(p, n, q0, q1)
    print("Hierarchical model, law of total variance")
    print(f"  total Var(Y)      = {total}")
    print(f"  E[Var(Y | X)]     = {within}   (the naive within-only spread)")
    print(f"  Var(E[Y | X])     = {between}")
    print(f"  total > within    = {total > within}")

    rng = random.Random(20241006)
    draws = _sample_hierarchical(1 / 3, 6, 1 / 5, 3 / 5, 200000, rng)
    print("Simulation of the same hierarchy (200000 draws)")
    print(f"  sample Var(Y)     = {_variance(draws):.4f}")
    print(f"  closed-form total = {float(total):.4f}")


if __name__ == "__main__":
    demo()
