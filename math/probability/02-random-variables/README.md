# Random Variables From Scratch

PMFs and CDFs of the standard discrete distributions, and expectation with linearity and
indicator random variables, in pure Python (standard library only). Every distribution is
written twice — exactly with `fractions.Fraction` (Poisson in float, because `e^-λ` is
irrational) and independently by seeded Monte-Carlo simulation.

Node `probability-02-random-variables` of the [skill tree](../../../skill-tree/README.md),
in the `probability` track, after `probability-01-counting-conditioning`. Sources:
Blitzstein & Hwang, *Introduction to Probability* (2nd ed.), **chapter 3** (discrete
random variables and the named distributions) and **chapter 4** (expectation, variance,
linearity, indicator random variables). The ideas are restated here, not copied.

The idea the node turns on: **a distribution is a function on its support, and expectation
is a sum — so it is linear whether or not the variables are independent.** The two things
students get wrong and this module plants as bugs are the support (`Geometric` starting at
0 instead of 1) and the variance formula (`E[X²] − (E[X])²` with the square on the wrong
term).

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| Bernoulli | PMF/CDF, `mean = p`, `var = p(1−p)` | `random_variables.py` | 1 |
| Binomial | `C(n,k) pᵏ (1−p)ⁿ⁻ᵏ`, `mean = np` | `random_variables.py` | 2 |
| Geometric | support `{1,2,…}`, `pmf(1)=p`, `mean = 1/p` | `random_variables.py` | 3 |
| Negative Binomial | trials to `r` successes, `mean = r/p` | `random_variables.py` | 4 |
| Poisson | `e^-λ λᵏ/k!` in float, `mean = var = λ` | `random_variables.py` | 5 |
| Linearity / indicators | `E[ΣIᵢ] = Σ E[Iᵢ]`, no independence | `random_variables.py` | 6 |
| Dependence (limit case) | fixed points: covariance terms make `var = 1` | `random_variables.py` | 7 |
| Poisson ≈ Binomial | total variation distance shrinks like `p` | `random_variables.py` | 8 |
| Simulation | seeded `random.Random`, raw draws returned | `random_variables.py` | 1–7 |

## How to use this directory

`random_variables.py` is a **template**: each function you write keeps its signature and
docstring, has a `TODO` with a hint, and raises `NotImplementedError`. `solutions/` holds a
working version for when you are stuck, or to compare afterwards.

```bash
cd math/probability/02-random-variables
python3 check.py        # what to build next; stops at the first gap
python3 check.py 3      # one step
python3 check.py 3 5    # a range
python3 check.py --all  # everything
```

`check.py` runs 8 checks against **your** code and never imports `solutions/`. Every
reference PMF, mean and variance is computed inside `check.py` from `math.comb` and
`Fraction` (Poisson from `math.exp`), and the limit case is also brute-forced over all `n!`
permutations for small `n`, so the checker never asks your code what the right answer is.

The acceptance rule from the node is enforced literally. At `TRIALS = 100_000`:

- the exact **mean** must sit within `4·sqrt(Var(X)/N)` of the sample mean;
- the exact **variance** must sit within four standard errors of the sample variance,
  where that standard error is estimated from the sample fourth central moment
  (`sqrt((m₄ − s⁴)/N)`);
- the **Poisson approximation error** must fall by roughly a factor of 10 per factor of 10
  in `n` at fixed `n p`, and `error / p` must stay constant to within 20%.

The simulations are seeded, so a failure is reproducible rather than flaky.

## Mutation table

The checker was itself tested: six classic bugs were planted in copies of the solution and
each must be caught by the step named. Run
`python3 ../../../.claude/skills/graded-module/scripts/mutate.py . _build/mutations.py`.

| Planted bug | Caught by |
|---|---|
| variance squares `second_moment − mean` instead of `mean` | step 1 |
| Geometric pmf support starts at 0 (`(1−p)ᵏ p`) | step 3 |
| Geometric mean one too small (shifted support, `1/p − 1`) | step 3 |
| Negative Binomial uses `C(k, r)` instead of `C(k−1, r−1)` | step 4 |
| Poisson approximation uses `λ = p`, not `λ = n p` | step 8 |
| fixed-point variance drops the covariances (assumes independence) | step 7 |

The last two are the node's named limit cases seen from opposite sides: one corrupts an
exact formula, the other corrupts the approximation the formula is about. Steps 3 and 7
each check the exact value *and* the simulation, so a formula bug and a sampling bug
cannot hide behind each other.

## Design decisions, named

Each function's docstring names the alternatives and the cost of the choice. In short:

- **Exact `Fraction` for rational distributions, float only for Poisson.** Off-by-one
  support errors and rounding must not look alike, which is exactly what the Geometric
  mutation exploits. Cost: `Fraction` arithmetic is slower, and inputs must be exact
  (`Fraction(1, 3)`, not `0.333`).
- **Geometric and Negative Binomial count trials, not failures.** The other convention
  shifts every mean by one. `pmf(1) == p` and `mean == 1/p` pin the choice. Cost: the same
  names mean different numbers in other books, so the docstrings say which.
- **Variance through `variance_from_moments(mean, second)`.** Forcing the second moment to
  be passed explicitly makes the misplaced square a one-line mutation the checker catches.
  Cost: an extra helper and a risk of cancellation, avoided by keeping exact moments.
- **Linearity of expectation with dependent indicators.** The fixed points of a random
  permutation is the limit case: `E` is 1 by linearity, but the variance is 1 only if the
  covariance terms are kept; the independence-only value is `(n−1)/n`.
- **Simulations return raw draws, not a single summary.** One list lets the checker compute
  mean, variance and the variance's own standard error. Cost: `10⁵` small ints per call.
- **Poisson approximation measured by total variation distance.** Pointwise comparison is
  weak; the global distance is `O(n p²)` by Le Cam, so the checker can require the
  predicted `1/n` decay.

## Questions to answer before reading the solutions

1. `Geometric(p)` counts trials. Why is `pmf(1) = p` and not `(1−p)p`? If you instead count
   failures before the first success, which of `pmf`, `cdf`, `mean`, `variance` change, and
   by how much does the mean move?
2. `Var(X) = E[X²] − (E[X])²`. For a Bernoulli with `p = 1/2` both moments are `1/2`. What
   does `(E[X²] − E[X])²` give, and why is it not a coincidence that it collapses?
3. The number of fixed points of a random permutation has the *same mean* as `Binomial(n,
   1/n)` but a different distribution. Which quantity separates them, and what is the
   independence-only value of that quantity?
4. `E[X + Y] = E[X] + E[Y]` needs no independence, but `Var(X + Y) = Var(X) + Var(Y)` does.
   Where does the missing `2 Cov(X, Y)` come from in the fixed-point case, and why is it
   positive?
5. The checker estimates the standard error of the sample variance from the sample fourth
   central moment. When the distribution is an indicator (`(X−μ)²` constant), that estimate
   is 0. Does the four-SE rule still make sense, and what does the checker fall back on?

## Limits

- Only the named *discrete* distributions. Continuous distributions (where a probability is
  an integral) and the change-of-variables formula are left out.
- Poisson moments are float, so the Poisson checks use a `1e-12` tolerance where the
  rational distributions use exact `Fraction` equality.
- The Poisson approximation is checked at `λ = 1` only; the fuller Poisson limit theorem
  (and the error bound's proof) is `probability-03`, the limit theorems node.
- The variance standard error is the asymptotic one from the sample fourth moment, not an
  exact finite-sample interval; at `10⁵` trials it is more than tight enough to catch the
  planted support and moment bugs.
- No joint distributions or generating functions — this node is the marginal PMF, mean and
  variance. Independence of several variables is `probability-04`.
