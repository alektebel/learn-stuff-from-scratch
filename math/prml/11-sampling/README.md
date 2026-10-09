# Sampling methods

Rejection sampling, importance sampling, the Markov-chain workhorses
Metropolis-Hastings and Gibbs, and Hamiltonian Monte Carlo, from scratch.
Implements chapter 11 of Bishop, *Pattern Recognition and Machine Learning*
("Sampling Methods"); the argument is restated here, never copied. The matching
material is Murphy, *Probabilistic Machine Learning: An Introduction*, chapter 11
(`bishop:11`, `murphy1:11`).

**Status: not built.** `sampling.py` holds the stubs; `check.py` grades them. This
file describes the work; `solutions/` is the reference.

## What you build

`sampling.py`, six graded functions. The `Chain` container, the vector helpers,
the autocorrelation helpers and the cost reporters are given.

| Function | What it does |
|---|---|
| `rejection_sample(target_pdf, proposal_pdf, propose, M, n, rng)` | `n` exact samples from the target by accepting candidates with `u * M * q <= p` |
| `importance_sample(target_logpdf, proposal_logpdf, propose, f, n, rng)` | weighted estimate of `E[f(X)]`, plain and self-normalised, with raw weights and ESS |
| `metropolis_hastings(log_target, propose, x0, steps, rng)` | symmetric random-walk MH; `steps + 1` states and a target-evaluation count |
| `gibbs_sample(cond_samplers, x0, steps, rng)` | systematic-scan Gibbs; `steps + 1` state tuples |
| `hmc(log_target, grad_log_target, eps, L, x0, steps, rng)` | leapfrog HMC with a Metropolis correction, counting `L + 1` gradients per step |
| `effective_sample_size(chain)` | Geyer's initial-positive-sequence ESS; minimum over coordinates for a vector chain |

`gradient_count(chain)` and `target_eval_count(chain)` read the counters the
samplers attach, so the acceptance criterion can compare a gradient against a
target evaluation.

## Running it

```bash
python3 check.py        # every step, stopping at the first one not written
python3 check.py 3      # just step 3
python3 check.py --all  # do not stop at the first gap
```

A step that raises `NotImplementedError` is reported as **TODO**, not a failure. A
step that asserts and fails is a **FAIL**; an exception is an **ERROR**. The checks
import your `sampling.py`, never `solutions/`.

## The checks

| Step | What it pins down |
|---|---|
| 1 | rejection sampling from Beta(2, 3) via Uniform(0, 1): the sample mean and variance match `0.4` and `0.04`, and the acceptance rate matches `1/M = 9/16` |
| 2 | the accept criterion: over 400 independent runs the plain importance estimate of `E[X]` and `E[X^2]` is centred on `0` and `1` with a 2-sigma interval that covers them; with an unnormalised target only the self-normalised ratio recovers the mean, while the plain estimate carries the normaliser `exp(2.5)*sqrt(2*pi)` |
| 3 | the accept criterion: on a correlated Gaussian (`rho = 0.95`) HMC returns more than twice the effective sample size *per gradient* of a random-walk MH with the same evaluation budget, and its mean, variance and covariance are right |
| 4 | Metropolis-Hastings and Gibbs on the same correlated Gaussian (`rho = 0.7`) recover the zero means, unit variances and the covariance `rho` |
| 5 | the limit case: a Gaussian proposal for a Cauchy target has importance weights of infinite variance -- the largest weight grows with `n`, the ESS collapses, and the estimate does not converge -- while a power-law proposal at least as heavy-tailed as the target is stable |

## Design decisions

- **The cost of a run is carried on the returned `Chain`.** A global counter
  would let two compared samplers contaminate each other's budgets. The
  container is a `list` subclass, so samples behave as ordinary lists.
- **`importance_sample` returns both the plain and the self-normalised
  estimator.** A single function cannot be both unbiased for a normalised target
  and consistent for an unnormalised one; returning both makes the trade the
  lesson instead of a hidden assumption.
- **`effective_sample_size` uses Geyer's initial-positive-sequence estimate and
  the minimum over coordinates.** The lag-1 autocorrelation alone badly
  overestimates the ESS of a slow sampler, and averaging coordinates hides a
  frozen direction. The estimator is capped at 1000 lags for cost.
- **HMC uses leapfrog, not Euler.** The Metropolis acceptance compares true
  Hamiltonians, so the proposal must be volume-preserving and reversible;
  leapfrog is, explicit Euler is not. The price is an `L + 1`-th gradient (the
  closing half kick) per step.
- **The rejection test is written `u * M * q <= p`.** It never divides (so a
  zero proposal density is safe) and makes the invariant obvious: `u * M * q` is
  a uniform draw on `[0, M q]` that must fall under the target.

## Limit cases

- **A proposal lighter-tailed than the target.** For a Cauchy target and a
  Gaussian proposal the ratio `w = p/q` behaves like `exp(x^2/2)/x^2`, whose
  second moment diverges. The largest weight grows with `n` (about 45 at
  `n = 1000`, 150 at `n = 4000` on average), the ESS falls to roughly a quarter
  of the draws, and the self-normalised estimate is biased at every finite `n`.
  A power-law proposal with tail `|x|^-1.5` bounds every weight near 2 and
  converges.
- **Rejection with `M` too small.** `M = sup p/q` is the whole correctness
  condition; a value below the supremum silently biases the sample toward the
  regions where `p/(M q) > 1`. The check pins the moments, not just the type.

## Mutation coverage

`_build/mutations.py` plants one classic bug per mechanism; each is an exact edit
to a copy of the solutions (or, for the infinite-variance limit case, to the
checker's own proposal) and must be caught by the named step
(`python3 .claude/skills/graded-module/scripts/mutate.py math/prml/11-sampling math/prml/11-sampling/_build/mutations.py`).

| Bug | Step |
|---|---|
| rejection sampling always accepts (drops the `u*M*q <= p` test) | 1 |
| importance weights are not normalised (the self-normalised estimator keeps them unnormalised) | 2 |
| HMC uses a forward Euler step with no momentum half-kick | 3 |
| `effective_sample_size` returns the chain length regardless of autocorrelation | 3 |
| the infinite-variance limit case uses a heavier-tailed proposal that is actually finite-variance | 5 |

## Questions

Answers are not given. Work them out from the code and the definitions.

1. Rejection sampling with `M = sup p/q` has acceptance probability exactly
   `1/M`. Why is the accepted sample distributed as `p` even though the proposal
   is `q`, and what happens to the acceptance rate as the proposal's tails get
   lighter?
2. The plain importance estimator is unbiased but the self-normalised one is
   not, yet the self-normalised one is preferred in practice. Why? Write down
   the leading bias term and its sign.
3. `effective_sample_size` divides `n` by an integrated autocorrelation. Why does
   summing consecutive lag *pairs* and stopping at the first non-positive pair
   behave better than summing single lags and stopping at the first negative one?
4. Leapfrog is the composition of a half kick, `L` drifts and `L - 1` full
   kicks, a closing half kick. Which two properties of this map make the
   Metropolis acceptance valid, and why does an explicit Euler step lose them?
5. On a highly correlated Gaussian, both random-walk MH and Gibbs move one
   coordinate at a time, but HMC moves along the correlation. Explain the
   effective-sample-size-per-gradient gap in those terms.

## Limits

- The targets are one- or two-dimensional and have known simple forms (Beta,
  normal, Student-t, Cauchy, correlated Gaussian). No general density on a
  manifold, and no constrained support beyond the Beta's interval.
- Everything is pure standard library (`math`, `random`), double precision. There
  is no `Fraction` oracle: the quantities are expectations, so the checks are
  simulations with fixed seeds, not exact arithmetic.
- Step 3 fixes the integrator step, trajectory length and budget; it measures a
  gap that holds for those settings, not a universally optimal HMC tuning.
- Step 5 demonstrates the infinite weight variance through the growth of the
  maximum weight and the collapse of the ESS over repeated runs, not by
  evaluating the divergent integral directly.
