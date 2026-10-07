# Markov Chains and MCMC From Scratch

The stationary distribution of a finite Markov chain as the left eigenvector of
`P` for eigenvalue 1, and the two workhorse samplers -- Metropolis-Hastings and
Gibbs -- in pure Python (standard library only).

Node `probability-07-markov-chains-mcmc` of the
[skill tree](../../../skill-tree/README.md), in the `probability` track. Source:
Blitzstein & Hwang, *Introduction to Probability* (2nd ed.), **chapter 11**
(Markov chains) and **chapter 12** (Markov chain Monte Carlo). The ideas are
restated here, not copied.

The idea the node turns on: **a long run of a chain *is* its stationary
distribution, but only when the chain actually converges to it.** The
acceptance criterion is a measurement: the empirical distribution of a long
trajectory matches the stationary distribution. The two limit cases are where
the natural reading fails. A periodic chain has a perfectly good stationary
distribution but its distribution at time `n` never settles -- so a convergence
check that reads a single power of `P` is wrong. A bimodal target has a
stationary distribution a random-walk sampler *can* reach, but a tiny step never
crosses the gap, so the sample describes one mode and lies about the rest.

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| Stationary distribution | solve `pi P = pi` with `sum pi = 1` by elimination | `mcmc.py` | 1 |
| Empirical distribution (accept) | long chain matches `pi` | `mcmc.py` | 2 |
| Metropolis-Hastings (accept) | accept with `min(1, target ratio)` | `mcmc.py` | 3 |
| Gibbs sampling | sweep every conditional | `mcmc.py` | 4 |
| Limit cases | periodic chain; bimodal target | `mcmc.py` | 5 |

## How to use this directory

`mcmc.py` is a **template**: each function you write keeps its signature and
docstring, has a `TODO` with a hint, and raises `NotImplementedError`. The
`_matmul` helper and the demo scaffolding stay implemented. `solutions/` holds a
working version for when you are stuck, or to compare afterwards.

```bash
cd math/probability/07-markov-chains-mcmc
python3 check.py        # what to build next; stops at the first gap
python3 check.py 3      # one step
python3 check.py 3 5    # a range
python3 check.py --all  # everything
```

`check.py` runs 5 checks against **your** code and never imports `solutions/`.
Its reference values are independent: the stationary distributions by an exact
`fractions.Fraction` elimination, the empirical distribution by counting, and
the target moments from the closed form. The acceptance criterion is step 2 --
the empirical distribution of a long, seeded chain agrees with `pi` -- repeated
for Metropolis-Hastings (step 3, mean and variance of a known target) and Gibbs
(step 4, two marginal means, two variances and the correlation sign).

## Mutation table

The checker was itself tested: five classic bugs were planted in copies of the
solution -- and one in the checker -- and each must be caught by the step named.
Run `python3 ../../../.claude/skills/graded-module/scripts/mutate.py . _build/mutations.py`.

| Planted bug | Caught by |
|---|---|
| stationary distribution uses the right eigenvector (`P[j][i]`) | step 1 |
| simulated chain applies `P^T` (walks the column, not the row) | step 2 |
| Metropolis-Hastings drops the `min(0, .)` floor (accepts every step) | step 3 |
| Gibbs sweeps only the first coordinate | step 4 |
| bimodal limit case assumes the small step explores both modes | step 5 |

The last row mutates `check.py`: when the "small" step is made large, the step
that must be trapped is not, and the trapped assertion fires. The checker also
guards that the small step is genuinely smaller than the gap, so a checker that
assumes exploration cannot pass silently.

## Design decisions, named

Each function's docstring names the alternatives and the cost of the choice. In
short:

- **`stationary_distribution` solves the linear system `pi P = pi`, never a
  power of `P`.** Iterating `P` (or reading a column of `P^n`) converges only
  for an aperiodic chain; on `[[0,1],[1,0]]` the powers alternate and never
  settle. Gaussian elimination with the normalisation `sum pi = 1` is exact at
  any period. The cost is an `O(n^3)` solve.
- **It is the LEFT eigenvector.** `P[i][j]` is `P(i -> j)`, so equation `j` is
  `sum_i pi_i P[i][j] = pi_j`. Building the equations from `P[j][i]` solves the
  right eigenvector `P v = v`, which for a row-stochastic matrix is uniform --
  the planted bug.
- **`simulate_chain` walks the row `P[current]`.** The column `P[.][current]`
  is the transposed chain, whose stationary distribution is the right
  eigenvector (uniform for the checker's chain), not `pi`.
- **`metropolis_hastings` accepts on `log U < min(0, log_target(y) -
  log_target(x))`.** The log form avoids underflow; the `min(0, .)` floor is
  what makes uphill moves always acceptable and keeps the chain targeting the
  right density. Keeping only the `0` accepts every step and turns the chain
  into an unconstrained random walk.
- **`gibbs_sampling` sweeps every coordinate in place.** Redrawing only the
  first freezes the rest and the sample describes a line; sweeping in place
  (systematic scan) is a valid kernel and is what makes the marginal variances
  come out right.
- **The limit cases are constructed, not hoped for.** The periodic chain is
  the exact `[[0,1],[1,0]]`; the bimodal target is a fixed mixture with a
  known gap, and the tiny step is asserted to be smaller than the gap.

## Questions to answer before reading the solutions

1. Write the two equations of `pi P = pi` for `P = [[1/2, 1/2], [1/4, 3/4]]`.
   Which equation is redundant, and why? Solve them with `sum pi = 1`. What does
   the right eigenvector `P v = v` give, and why is it *not* `pi`?
2. For the periodic chain `[[0,1],[1,0]]`, compute `P^n`. Show that `pi =
   (1/2, 1/2)` is stationary, yet `P^n` does not converge. What does the state
   distribution at time `n` look like as `n` grows, and how would a checker that
   compares `P^n` to `pi` at a single `n` be fooled?
3. Why does the empirical distribution of a long run converge to `pi` even
   though the time-`n` distribution does not? What property of the chain makes
   the empirical average converge, and why is periodicity not enough to break
   it?
4. In `metropolis_hastings`, the term `log_target(y) - log_target(x)` is the log
   of the density ratio. Why is the acceptance `min(1, ratio)`, and why is the
   clamp to `1` essential? What chain do you get if you always accept?
5. A Gibbs sweep updates each coordinate from its conditional given the others.
   Why must *every* coordinate be redrawn? If coordinate 2 is never updated,
   which marginal mean, which variance and which correlation does the sample get
   wrong?
6. For the bimodal mixture `0.5 N(-4, 0.5^2) + 0.5 N(4, 0.5^2)`, roughly how
   many random-walk steps of size `s` does it take to cross the gap? When is the
   sample's mean a fair estimate of the mixture mean, and when is it the mean of
   a single mode?

## Limits

- Discrete, finite state spaces only for the chain: `P` is an `n x n` matrix and
  `stationary_distribution` returns a length-`n` vector. Chains on countable or
  continuous spaces are later nodes.
- The linear solve assumes the chain is irreducible: a reducible chain has more
  than one stationary distribution and the system is singular, which raises
  rather than guessing one.
- Metropolis-Hastings is checked with a symmetric random-walk proposal only
  (`q(y|x) = q(x|y)`); the asymmetric Metropolis correction and independent
  samplers are not exercised here.
- Gibbs is checked on a two-variable normal with known conditionals. The
  conditionals are supplied by the caller, so the sampler is general, but the
  checker's tolerance is tuned to that model.
- The simulated checks are seeded (`random.Random`) and compare within `0.01`
  (empirical distribution), `0.05`-`0.10` (target moments) and a sign test
  (correlation). The exact steps (1 and the algebra of 5) are what pin the
  answers; the simulations are what show the samplers agree.
