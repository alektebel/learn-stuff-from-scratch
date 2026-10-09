# Variational inference

Mean-field variational inference from scratch: the evidence lower bound, coordinate
ascent for a univariate Gaussian with unknown mean and precision, a variational Gaussian
mixture, and the reverse-KL mode-seeking failure on a correlated Gaussian. Implements
chapter 10 of Bishop, *Pattern Recognition and Machine Learning* (`bishop:10`), and the
matching material in Murphy, *Probabilistic Machine Learning: Advanced Topics*
(`murphy2:10`; the argument is restated here, never copied).

**Status: not built.** `variational.py` holds the stubs; `check.py` grades them. This
file describes the work; `solutions/` is the reference.

## What you build

`variational.py`, seven graded functions. The helper `_digamma` and the demo are given.

| Function | What it does |
|---|---|
| `gaussian_logpdf(x, mu, var)` | univariate Gaussian log density |
| `elbo(xs, params, mu0, lambda0, a0, b0)` | the ELBO of the factorised Normal--Gamma fit |
| `mean_field_gaussian(xs, mu0, lambda0, a0, b0, maxit, tol)` | coordinate ascent for `q(mu) q(tau)`; returns `(params, elbos, bound)` |
| `log_evidence_known(xs, mu0, lambda0, a0, b0)` | exact Normal--Gamma log evidence, for comparison |
| `_gmm_elbo(xs, r, alpha, beta, m, a, b, ...)` | the variational Gaussian-mixture ELBO |
| `variational_gmm(xs, k, maxit, rng, ...)` | mean-field Gaussian mixture; returns `(elbos, resp)` |
| `correlated_gaussian_vb(rho, maxit, tol)` | reverse-KL fit of a correlated Gaussian; returns the fitted marginal variances |

The model for the first three is a Normal--Gamma conjugate pair:
`p(mu, tau) = N(mu | mu0, 1/(lambda0 tau)) Gamma(tau | a0, b0)`, with `tau` the precision.
The variational factorisation is `q(mu, tau) = q(mu) q(tau)`.

## Running it

```bash
python3 check.py        # every step, stopping at the first one not written
python3 check.py 3      # just step 3
python3 check.py --all  # do not stop at the first gap
```

A step that raises `NotImplementedError` is reported as **TODO**, not a failure. A step
that asserts and fails is a **FAIL**; an exception is an **ERROR**. The checks import
your `variational.py`, never `solutions/`.

## The checks

| Step | What it pins down |
|---|---|
| 1 | mean-field VI on 500 draws from `N(1, 4)` recovers the posterior mean and precision: `params["mu"]` near 1 and `E[tau] = a/b` near `1/4` |
| 2 | the accept criterion: the ELBO sequence returned by `mean_field_gaussian` has at least three entries and never decreases (to `1e-9`) on a fixed synthetic set |
| 3 | the accept criterion: the ELBO is a lower bound on the exact Normal--Gamma log evidence, which the checker recomputes itself; every recorded value, and the returned bound, sits below it |
| 4 | the variational GMM's ELBO never decreases, the responsibilities are distributions, and the fit recovers the well-separated means `-6, 0, 6` |
| 5 | the limit case: mean-field on a Gaussian with correlation `rho` understates each marginal variance to exactly `1 - rho^2 < 1`, and shrinks more as `rho` grows |

## Design decisions

- **The ELBO is written out in full, constants included.** The point of the module is
  the bound itself; leaving the normalising constants off would make the
  `ELBO <= log evidence` check meaningless.
- **The exact log evidence is part of the deliverable.** This conjugate model is the
  rare case where the marginal likelihood is available in closed form, so `ELBO <= log
  evidence` becomes a check rather than a slogan.
- **The `tau` shape is `a0 + (N+1)/2`, not `a0 + N/2`.** The extra `1/2` is the price of
  factorising `q(mu) q(tau)`: the mean-field posterior is not the exact posterior, and
  the ELBO is strictly below the evidence by the KL gap.
- **The variational GMM keeps `q(mu_j, tau_j)` as one Normal--Gamma factor**, not two.
  That is exact conjugate matching inside a component; the mean-field approximation is
  across components and assignments. The ELBO must include the `E[log pi_j]` coupling
  term, or the responsibility update is not the maximiser.
- **`correlated_gaussian_vb` returns the fitted marginal variances.** The reverse-KL
  optimum of a factorised fit is a closed form on a 2x2 target, so the limit case is a
  numeric comparison to the truth, not a simulation.

## Limit cases

- **Reverse KL is mode-seeking, not mass-covering.** Fitting `q(x1) q(x2)` to a target
  with unit marginals and correlation `rho` gives each factor the precision
  `diag(Sigma^-1) = 1/(1-rho^2)`, so the fitted marginal variance is `1 - rho^2`. At
  `rho = 0.9` that is `0.19` against a true marginal variance of `1`: the variational fit
  hides almost all the spread.
- **The bound is not the evidence.** On the synthetic Normal--Gamma data the ELBO is
  around `-722.918` and the exact evidence around `-722.917`; the small, strictly
  positive gap is the KL divergence the factorisation cannot remove.

## Mutation coverage

`_build/mutations.py` plants one classic bug per mechanism; each is an exact edit to a
copy of the solutions (the fourth to a copy of `check.py`) and must be caught by the
named step
(`python3 .claude/skills/graded-module/scripts/mutate.py math/prml/10-variational-inference math/prml/10-variational-inference/_build/mutations.py`).

| Bug | Step |
|---|---|
| q(tau) update drops the Gamma prior parameters | 2 |
| ELBO omits the entropy term | 3 |
| ELBO sequence is overwritten instead of tracked | 2 |
| the evidence bound uses `>=` instead of `<=` | 3 |
| correlated limit case claims mean-field matches the true marginal variances | 5 |

## Questions

Answers are not given. Work them out from the code and the definitions.

1. Show that one coordinate-ascent sweep cannot decrease the ELBO, and identify exactly
   what breaks when the q(tau) update forgets `a0` and `b0`.
2. The exact posterior of the Normal--Gamma model has `a = a0 + N/2`; the mean-field fit
   has `a = a0 + (N+1)/2`. Where does the extra `1/2` come from, and why does it make the
   ELBO strictly below the evidence?
3. The variational GMM responsibility is the softmax of `E[log pi_j] + 0.5 E[log tau_j]
   + ...`. Why must the `E[log pi_j]` coupling appear in the ELBO's `Z` term, and what
   goes wrong (monotonicity, recovery) if it is dropped?
4. A factorised Gaussian fit to a correlated target understates the variance. Derive the
   `1 - rho^2` result from `diag(Sigma^-1)`, and say what changes if the KL is taken the
   other way, `KL(p || q)`.
5. Why can the exact Normal--Gamma log evidence be written in closed form here, and
   which term of a general model blocks the same computation?

## Limits

- The Gaussian mixture is univariate with scalar covariances and a complete-data
  conjugate Normal--Gamma prior. Multivariate full covariances and a Dirichlet-process
  prior are out of scope.
- The ELBO sequences are observed to be monotone to floating-point tolerance over
  `maxit` sweeps; the guarantee is the coordinate-ascent argument, not a symbolic proof
  of the recorded numbers.
- The correlated limit case is a 2x2 closed form; higher-dimensional factorised fits
  understate variance by the same mechanism but have no single formula.
