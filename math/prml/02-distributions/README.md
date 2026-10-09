# Probability distributions, conjugacy and density estimation

The Beta-Bernoulli and Dirichlet-multinomial conjugate updates, the maximum-likelihood
Gaussian and its conjugate prior, the exponential-family form, and nonparametric density
estimation, from scratch. Implements chapter 2 of Bishop, *Pattern Recognition and
Machine Learning*, and the matching material in Murphy, *Probabilistic Machine Learning:
An Introduction* (`bishop:2`, `murphy1:3`; the argument is restated here, never copied).

**Status: not built.** `distributions.py` holds the stubs; `check.py` grades them. This
file describes the work; `solutions/` is the reference.

## What you build

`distributions.py`, fifteen graded functions. The Gaussian-kernel helper `_gaussian_kernel`
and the demo are given.

| Function | What it does |
|---|---|
| `beta_bernoulli_update(alpha, beta, heads, tails)` | the Beta posterior parameters |
| `beta_mean(alpha, beta)` | the mean of a Beta distribution |
| `dirichlet_multinomial_update(alpha, counts)` | the Dirichlet posterior concentrations |
| `gaussian_mle(xs)` | the sample mean and the `1/N` (biased) MLE variance |
| `gaussian_sequential_update(posterior, x)` | one online conjugate update of a Gaussian mean |
| `gaussian_posterior(mu0, sigma0, sigma, xs)` | the closed-form batch posterior `(mean, precision)` |
| `sufficient_stats(xs, family)` | `(n, sum)` for Bernoulli, `(n, sum, sum_sq)` for Gaussian |
| `gaussian_from_sufficient_stats(stats)` | recover `(mean, variance)` from the Gaussian stats |
| `natural_parameters(stats, family, sigma)` | the natural parameter the statistics imply |
| `log_partition(eta, family, sigma)` | the log-partition `A(eta)` |
| `log_partition_gradient(eta, family, sigma)` | `A'(eta)`, the mean |
| `exponential_family_stats(xs, family, sigma)` | the bundle `{stats, eta, mean, log_partition}` |
| `histogram_density(xs, edges)` | per-bin `count / (n * width)` |
| `kde(xs, x, h)` | the Gaussian kernel density estimate |
| `knn_density(xs, x, k)` | the k-nearest-neighbour density estimate |

## Running it

```bash
python3 check.py        # every step, stopping at the first one not written
python3 check.py 3      # just step 3
python3 check.py --all  # do not stop at the first gap
```

A step that raises `NotImplementedError` is reported as **TODO**, not a failure. A step
that asserts and fails is a **FAIL**; an exception is an **ERROR**. The checks import your
`distributions.py`, never `solutions/`.

## The checks

| Step | What it pins down |
|---|---|
| 1 | the conjugate updates against hand values: `Beta(1,1) + 3H/1T -> Beta(4,2)` (mean `2/3`), `Dirichlet(1,1,1) + [2,1,1] -> [3,2,2]` |
| 2 | the accept criterion: sequential and batch Gaussian posteriors agree to `1e-12` on the same data, the batch one matching an independently computed precision-weighted form, and the sequential one being order-independent |
| 3 | the accept criterion: by simulating 40000 samples of size 8, `E[MLE variance] = (N-1)/N * sigma^2` while the `1/(N-1)` variance is unbiased |
| 4 | exponential family: sufficient statistics reproduce the parameters, `A'(eta)` equals the mean, and `A(eta) = log(1 + e^eta)` |
| 5 | the limit cases: the Bernoulli MLE after 3 heads in 3 tosses is exactly 1 while `Beta(1,1)` gives posterior mean `4/5`; the KDE kernel and `1/(n h)` both required (hand value and unit integral); a too-small bandwidth is spiky, a too-large one oversmooth |

## Design decisions

- **Beta-Bernoulli returns `(alpha, beta)`, not a probability.** The parameters are the
  state; the mean is a separate function. Returning the mean would discard the
  concentration, which is the lesson of the update.
- **`gaussian_mle` uses `1/N`.** The bias is the point: `E[variance] = (N-1)/N sigma^2`.
  The unbiased estimator is the `1/(N-1)` version, kept out of the module on purpose.
- **The sequential Gaussian state is `(mu, tau, sigma)` with `tau` a precision.** The
  update is additive in precision, so it is order-independent and agrees with the batch
  closed form to round-off.
- **KDE keeps the kernel and the `1/(n h)` normalisation as separate pieces.** Dropping
  either is a distinct, visible bug; the checker pins both with a hand value and a unit
  integral rather than only a shape statistic (a scale factor cancels in a ratio).
- **The Gaussian uses `sigma = 1.0` by default in the exponential-family helpers.** The
  node is about the form, not the scale; `sigma` is an explicit argument where it matters.

## Limit cases

- **Three heads in three tosses.** The maximum-likelihood Bernoulli estimate is
  `p = 1` with no notion of doubt. A `Beta(1,1)` prior adds one success and one failure,
  giving `Beta(4,1)` and a posterior mean of `4/5`. That gap is regularisation.
- **The KDE bandwidth.** With `h = 0.15` on ten points at the integers the peak-to-midpoint
  ratio is about 129 (all mass on the data, high variance); with `h = 4` it is about 1
  (a nearly flat estimate, low variance and large bias). The two failure modes bracket the
  useful bandwidth.
- **Three identical points.** The MLE variance is exactly 0 because it divides by `N`;
  the unbiased variance is also 0 here, but the simulation shows the two only agree in
  expectation for large `N`.

## Mutation coverage

`_build/mutations.py` plants one classic bug per mechanism; each is an exact edit to a
copy of the solutions and must be caught by the named step
(`python3 .claude/skills/graded-module/scripts/mutate.py math/prml/02-distributions math/prml/02-distributions/_build/mutations.py`).

| Bug | Step |
|---|---|
| Beta update adds heads to `beta` and tails to `alpha` (swapped) | 1 |
| Dirichlet update forgets the prior (returns the counts only) | 1 |
| Gaussian sequential update uses a plain average that ignores the prior precision | 2 |
| `gaussian_mle` divides by `N-1` instead of `N` (no bias) | 3 |
| KDE drops the `1/(n h)` normalisation | 5 |
| KDE drops the Gaussian kernel | 5 |

## Questions

Answers are not given. Work them out from the code and the definitions.

1. Why does the Beta-Bernoulli update never need the likelihood's normalising constant?
   What would change if the observations were not exchangeable?
2. The sequential and the batch Gaussian posterior agree. Which quantity makes the
   sequential update additive, and why does that make the order of observations irrelevant?
3. Show that `E[(1/N) sum (x_i - mean)^2] = (N-1)/N sigma^2`. Where exactly does the
   `N-1` come from, and what does `1/(N-1)` instead estimate?
4. The log-partition gradient equals the mean. Verify it for the Bernoulli by
   differentiating `A(eta) = log(1 + e^eta)`, and for the Gaussian.
5. A histogram integrates to one only because of the `1/width` factor. Is a KDE with a
   fixed bandwidth a probability density for every finite sample? Why does the kNN
   estimator behave differently near the edges of the data?

## Limits

- The Gaussian here has a *known* observation variance. Learning both the mean and the
  variance of a Gaussian, and its conjugate normal-inverse-gamma prior, is out of scope.
- `knn_density` is one-dimensional. In `d` dimensions the ball volume is different and
  the estimator suffers the curse of dimensionality; the module only needs the 1-D case.
- The step-3 check is a Monte Carlo estimate: the bias is shown to within a few percent
  over 40000 samples with a fixed seed, not proved symbolically.
- Everything is double precision; no `Fraction` oracle is used because the conjugate
  updates are exact in floating point and the bias check is deliberately a simulation.
