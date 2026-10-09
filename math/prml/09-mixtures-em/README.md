# Mixture models and the EM algorithm

K-means, the expectation-maximisation algorithm for a univariate Gaussian mixture,
and EM for a mixture of Bernoullis, from scratch. Implements chapter 9 of Bishop,
*Pattern Recognition and Machine Learning* (`bishop:9`), and the matching material in
Murphy, *Probabilistic Machine Learning: An Introduction* (`mml:11`; the argument is
restated here, never copied).

**Status: not built.** `mixtures.py` holds the stubs; `check.py` grades them. This file
describes the work; `solutions/` is the reference.

## What you build

`mixtures.py`, seven graded functions. The helpers `_gmm_loglikelihood` and
`_log_bernoulli_mixture`, plus the demo, are given.

| Function | What it does |
|---|---|
| `gaussian_logpdf(x, mu, var)` | univariate Gaussian log density |
| `kmeans(xs, k, rng, maxit)` | Lloyd's algorithm; returns `(centroids, assignments)` |
| `gmm_e_step(xs, weights, mus, vars)` | responsibilities `P(component j | x_i)` |
| `gmm_m_step(xs, resp, var_floor)` | weights, means, variances from responsibilities |
| `gmm_em(xs, k, rng, maxit, var_floor, init)` | EM; returns parameters and the log-likelihood sequence |
| `gmm_em_best(xs, k, rng, restarts, ...)` | keep the best of several restarts |
| `bernoulli_mixture_em(xs, k, rng, maxit)` | EM for a mixture of Bernoullis |

## Running it

```bash
python3 check.py        # every step, stopping at the first one not written
python3 check.py 3      # just step 3
python3 check.py --all  # do not stop at the first gap
```

A step that raises `NotImplementedError` is reported as **TODO**, not a failure. A step
that asserts and fails is a **FAIL**; an exception is an **ERROR**. The checks import
your `mixtures.py`, never `solutions/`.

## The checks

| Step | What it pins down |
|---|---|
| 1 | K-means on three well-separated 1-D clusters (at `-10, 0, 10`) recovers the centroids and puts exactly three points in each |
| 2 | the accept criterion: the GMM log-likelihood sequence returned by `gmm_em` has one entry per iteration and never decreases (to `1e-9`) on a fixed synthetic set |
| 3 | the accept criterion: EM recovers the true means `-6, 0, 6` and equal weights to tolerance, matched component-wise by sorting the means (up to label permutation) |
| 4 | the Bernoulli-mixture EM recovers component probabilities `[0.9,0.1,0.9]` and `[0.1,0.9,0.1]` up to permutation and improves the likelihood |
| 5 | the limit cases: `gaussian_logpdf` grows without bound as the variance shrinks; with `var_floor` every fitted variance is at the floor and the likelihood is bounded, while `var_floor=0.0` collapses the variance; and a symmetric bad initialisation is stuck at a worse log-likelihood than the best of eight restarts |

## Design decisions

- **K-means returns `(centroids, assignments)`.** The assignment is the E-step and the
  centroid the M-step; returning only one hides half of the recursion.
- **The mixture is univariate with list parameters.** The node is the EM recursion, not
  vectorised linear algebra; full covariances are a later chapter.
- **The M-step takes an explicit `var_floor`.** The unconstrained mixture likelihood is
  improper — a component on one point sends the variance to zero and the likelihood to
  `+inf`. The floor makes the objective proper, at the price of exact-M-step
  monotonicity once the floor becomes active.
- **`gmm_em` accepts an optional `init`.** Restarts and the deliberately-bad-
  initialisation limit case need to control the starting means reproducibly; deriving
  that from the RNG alone is not stable.
- **Responsibilities and the likelihood are computed in log space** with the
  max-subtraction trick. Gaussian densities underflow fast, and the log form costs only
  a few `exp` calls.

## Limit cases

- **A component collapsing onto one point.** The log-density at the mean is
  `-0.5 log(2 pi var)`; as `var -> 0` it diverges to `+inf`. On `[0,0,0,0,0,100]` with
  two components, the second owns the lone point: without a floor its variance is
  `1e-12`, with `var_floor=0.5` it is `0.5` and the likelihood is bounded.
- **A poor local optimum.** With all three means initialised at `0` the mixture is
  symmetric and EM cannot break the tie; it stays at the single-Gaussian fit. Random
  restarts from K-means find a clearly better optimum. On the synthetic three-cluster
  data the stuck fit is around `-317` and the best of eight restarts around `-174`.

## Mutation coverage

`_build/mutations.py` plants one classic bug per mechanism; each is an exact edit to a
copy of the solutions and must be caught by the named step
(`python3 .claude/skills/graded-module/scripts/mutate.py math/prml/09-mixtures-em math/prml/09-mixtures-em/_build/mutations.py`).

| Bug | Step |
|---|---|
| M-step does not normalise responsibilities into weights | 3 |
| E-step uses the prior instead of the posterior | 3 |
| variance floor is not applied (collapse) | 5 |
| log-likelihood sequence is overwritten instead of tracked | 2 |
| restart comparison keeps the first result instead of the best | 5 |

## Questions

Answers are not given. Work them out from the code and the definitions.

1. Show that one EM iteration cannot decrease the log-likelihood, and identify exactly
   where the proof uses that the M-step maximises rather than merely increases.
2. The E-step responsibilities and the log-likelihood share the same quantities. Why is
   it the *posterior* and not the prior that appears in the M-step, and what happens to
   the update if you substitute the prior?
3. Why does the log-density blow up as a component's variance tends to zero? Which
   term of the log-likelihood is unbounded, and why does a floor make the objective
   proper?
4. On data drawn from three well-separated Gaussians, the global optimum has three
   components. Construct an initialisation that is a stationary point of EM but not the
   global optimum. Why can EM not leave it?
5. The Bernoulli-mixture M-step averages bits by responsibility. Confirm that this is
   the maximiser of the expected complete-data log-likelihood, and say what replaces the
   variance floor for the Bernoulli parameters.

## Limits

- The Gaussian mixture is univariate with diagonal (scalar) covariances. Multivariate
  full covariances and the `K`-means-to-EM generalisation are out of scope.
- The step-2 monotonicity guarantee holds while the variance floor is inactive; once a
  component is clamped the objective is a constrained one and monotonicity of the
  *floored* objective is only observed numerically.
- The limit cases are demonstrated deterministically on hand-built data with fixed
  seeds, not proved symbolically.
