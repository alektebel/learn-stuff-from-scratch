# Conditional Expectation From Scratch

Adam's law and Eve's law, `E[Y | X]` as the best predictor of `Y` in squared
error, and the two-stage (hierarchical) model where the naive variance is too
small, in pure Python (standard library only). Exact when the joint is written
with `fractions.Fraction`, so every identity is checked with `==`, not a
tolerance.

Node `probability-06-conditional-expectation` of the
[skill tree](../../../skill-tree/README.md), in the `probability` track, after
`probability-04-joint`. Source: Blitzstein & Hwang, *Introduction to
Probability* (2nd ed.), **chapter 9** (conditional expectation; the law of total
expectation and the law of total variance). The ideas are restated here, not
copied.

The idea the node turns on: **conditioning is an operation on a whole function of
`X`, and `E[Y | X]` is the one that minimises squared error.** The acceptance
criterion is an inequality, not an equation: as a function of `X`, `E[Y | X]`
must score no worse than every other predictor `g(X)`, and strictly better than
the best constant when `Y` really depends on `X`. The limit case is where the
natural reading of the variance fails: a hierarchy of groups has spread *between*
the group means as well as *within* them, and the within-group term alone
understates `Var(Y)`.

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| Conditional mean and variance | normalise a joint row by `P(X = x)` | `cond.py` | 1 |
| Adam's law | `E[Y] = Σₓ P(X=x) E[Y|X=x]` | `cond.py` | 2 |
| Eve's law | `Var(Y) = E[Var(Y|X)] + Var(E[Y|X])` | `cond.py` | 3 |
| Best predictor | `E[(Y - g(X))²]`; `E[Y|X]` minimises it | `cond.py` | 4 |
| Hierarchical model (limit case) | within + between, reconstruction | `cond.py` | 5 |

## How to use this directory

`cond.py` is a **template**: each function you write keeps its signature and
docstring, has a `TODO` with a hint, and raises `NotImplementedError`. The
joint-handling helpers, the samplers and `demo()` stay implemented.
`solutions/` holds a working version for when you are stuck, or to compare
afterwards.

```bash
cd math/probability/06-conditional-expectation
python3 check.py        # what to build next; stops at the first gap
python3 check.py 3      # one step
python3 check.py 3 5    # a range
python3 check.py --all  # everything
```

`check.py` runs 5 checks against **your** code and never imports `solutions/`.
Its reference values are independent: conditional means and variances by
normalising the joint row directly, `E[Y]` and `Var(Y)` by summing the joint, and
the two Eve components by walking the conditioning values. The node's acceptance
rule is enforced against a best constant, a linear predictor, a quadratic
predictor and a seeded random predictor, with a strict win over the best
constant. The checker defines the best predictor through *your*
`conditional_expectation`, so a wrong conditional mean cannot pass by hiding.

## Mutation table

The checker was itself tested: five classic bugs were planted in copies of the
solution -- and one in the checker -- and each must be caught by the step named.
Run `python3 ../../../.claude/skills/graded-module/scripts/mutate.py . _build/mutations.py`.

| Planted bug | Caught by |
|---|---|
| conditional divides by the row count, not `P(X = given)` | step 1 |
| Adam's law averages the conditionals unweighted | step 2 |
| Eve's law drops the `Var(E[Y|X])` term | step 3 |
| best-predictor check compares to a single constant only | step 4 |
| hierarchical limit case ignores the between-group variance | step 5 |

The last row mutates `check.py`: the check must compare against more than one
predictor, so when the linear, quadratic and random challengers are removed the
richness guard fires. That guard is what makes the acceptance step a real
acceptance step rather than a check that one constant is beaten.

## Design decisions, named

Each function's docstring names the alternatives and the cost of the choice. In
short:

- **Divide by `P(X = given)`, never by the count or by 1.** The conditional pmf
  sums to 1; dividing by the row count makes its entries *average* to 1, and
  dividing by 1 leaves a sub-probability. Step 1 pins both failures with exact
  hand values.
- **`conditional_variance` uses the second moment, `E[Y²|X] - (E[Y|X])²`.** It
  reuses the same normalisation as `conditional_expectation` and stays exact for
  rational inputs; the deviation form would need the conditional pmf first and
  round twice.
- **Adam's law weights each conditional mean by `P(X = x)`.** The unweighted
  average is correct only when the conditioning values are equally likely, which
  is exactly the skew the checker removes.
- **`eve_law` returns the two components separately, not just their sum.** The
  identity is the point, and the limit case needs to show which term the naive
  reading drops. `direct` is computed from the joint alone, so it is an
  independent estimate of the same quantity.
- **The predictor is a callable, not a table of values.** The checker can pass
  `conditional_expectation` itself, a line, or a seeded random function without
  the module knowing their shapes.
- **The hierarchy is solved in closed form, not simulated.** Binomial counts give
  `E[Y|X] = nq` and `Var(Y|X) = nq(1-q)` exactly; the checker's sampler is the
  independent confirmation, not the definition.
- **Exact rationals where the node is algebraic.** A `Fraction` joint flows
  through every sum without rounding, so step 1-3's identities are `==`, not
  `abs(...) < tol`.

## Questions to answer before reading the solutions

1. Why is the denominator of the conditional pmf `P(X = given)` and not the
   number of outcomes? Show that dividing the row `P(X=0,Y=·)` by its count makes
   its entries average to 1, and dividing by 1 makes it sum to `P(X = 0)`.
   Which check catches each?
2. On the hand joint `{(0,0):1/2, (0,1):1/4, (1,0):1/4}` compute `E[Y]` two
   ways: from the joint, and as `Σₓ P(X=x) E[Y|X=x]`. What does the unweighted
   average `(E[Y|X=0] + E[Y|X=1])/2` give, and why is it wrong?
3. Compute `Var(Y)`, `E[Var(Y|X)]` and `Var(E[Y|X])` for the same joint. Which
   term is the within-group variance and which the between-group variance? If
   someone reports only `E[Var(Y|X)]`, is their spread too big or too small, and
   by how much here?
4. `E[Y|X]` minimises `E[(Y - g(X))²]`. Why does the optimum depend only on the
   joint and not on how clever `g` is? On the nonlinear joint, the best constant
   scores `2/9` and `E[Y|X]` scores `1/6`; what feature of the conditional means
   makes the constant lose?
5. In the nonlinear joint, a quadratic predictor fits the conditional means
   exactly and so ties `E[Y|X]`. Why must the acceptance rule be `≤` and not
   strict for every predictor, while it is strict against the best constant?
6. In the hierarchy, `Var(Y) = E[Var(Y|X)] + Var(E[Y|X])`. If `q0 = q1`, which
   term vanishes, and does the model still have any spread? Why is a two-stage
   model the smallest one that can show the missing term?

## Limits

- Two variables only: the joint is over `(X, Y)`, and the predictor is a function
  of the single variable `X`.
- Discrete distributions only. Conditional densities, `E[Y|X]` for continuous
  `X`, and the conditional expectation as a random variable with its own law are
  later nodes.
- The best predictor is checked against a finite, named set of challengers
  (constant, linear, quadratic, seeded random). It cannot enumerate every
  function; the mathematics that `E[Y|X]` is optimal is the reason the inequality
  must hold, and the checker demonstrates it on those shapes.
- The hierarchy is the two-group Bernoulli-mixture of binomials. Other
  hierarchical families (Poisson-Beta, normal-normal) share the decomposition
  but are not parameterised here.
- The simulated checks are seeded (`random.Random`) and compare within `0.02` to
  `0.05`; the exact steps are what pin the identities, the simulations are what
  show the sampler and the closed form agree.
