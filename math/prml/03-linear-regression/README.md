# Linear regression: least squares and the Bayesian evidence

Basis-function regression from maximum likelihood to Bayesian model selection, from
scratch. Implements chapter 3 of Bishop, *Pattern Recognition and Machine Learning*
(linear models for regression), and the matching material in Murphy,
*Probabilistic Machine Learning: An Introduction* (`bishop:3`, `mml:9`). The argument is
restated here, never copied.

**Status: not built.** `regression.py` holds the stubs; `check.py` grades them. This
file describes the work; `solutions/` is the reference.

## What you build

`regression.py`, seven graded functions. The dense linear algebra (`solve_linear`,
`inverse`, `log_det`, `_gram`, `_rhs`) and the demo are given: they are infrastructure,
not the regression itself.

| Function | What it does |
|---|---|
| `design_matrix(xs, basis)` | the `N x M` matrix `Phi[i][j] = basis[j](x_i)` |
| `mle_weights(Phi, ts)` | least squares: solve `Phi^T Phi w = Phi^T t` |
| `ridge_weights(Phi, ts, alpha)` | regularised least squares: `(alpha I + Phi^T Phi) w = Phi^T t` |
| `bayesian_posterior(Phi, ts, alpha, beta)` | the posterior `(m_N, S_N)` over the weights |
| `predictive_distribution(Phi_grid, post_mean, post_cov, beta)` | predictive mean and variance at new inputs |
| `log_evidence(Phi, ts, alpha, beta)` | the log marginal likelihood |
| `maximise_evidence(Phi, ts, alphas, betas)` | the `(alpha, beta)` of largest evidence |

`basis` is a list of one-argument callables, so the same code handles a polynomial
basis (`[lambda x, k=k: x ** k for k in range(degree + 1)]`) and a Gaussian radial
basis.

## Running it

```bash
python3 check.py        # every step, stopping at the first one not written
python3 check.py 3      # just step 3
python3 check.py --all  # do not stop at the first gap
```

A step that raises `NotImplementedError` is reported as **TODO**, not a failure. A step
that asserts and fails is a **FAIL**; an exception is an **ERROR**. The checks import your
`regression.py`, never `solutions/`.

## The checks

| Step | What it pins down |
|---|---|
| 1 | `design_matrix` shape/content; MLE recovers an exact quadratic to `1e-7`; ridge shrinks the weights (`||w_ridge|| < ||w_mle||`, and more so for a larger `alpha`) and matches an independent ridge solve |
| 2 | the posterior mean equals the ridge solution with `lambda = alpha / beta`, the covariance is `(alpha I + beta Phi^T Phi)^{-1}`, and the mean tends to the MLE as `beta -> infinity` |
| 3 | **ACCEPT**: inside the data the predictive variance sits at/above the noise floor `1/beta`; moving away it increases strictly and is far above the floor |
| 4 | `log_evidence` matches the checker's independent value (including the Occam term); evidence maximisation recovers the true noise precision `beta = 25` to within a factor of 2, and does not pick the most flexible model |
| 5 | **LIMIT CASE**: with 5 points and 8 basis functions the MLE is ill-posed (`None`) while the Bayesian posterior mean and covariance stay finite, symmetric and positive on the diagonal |

The checker carries its own `_solve`, `_inverse`, `_log_det`, `_ridge` and
`_log_evidence`, so the numeric comparisons are against an independent implementation,
not against a restatement of yours.

## Design decisions

- **`mle_weights` returns `None` on singular normal equations.** With fewer points than
  basis functions the least-squares answer is not unique, so returning one of the
  infinitely many solutions would be a silent lie. The alternative (raise) pushes the
  same decision into every caller's `try`; `None` keeps it explicit.
- **The basis is a list of callables, not a fixed polynomial.** The lesson is that the
  model is linear in the weights, not in the inputs, so the same routines must serve
  polynomials and radial functions without branching.
- **Every weight is penalised; there is no unpenalised intercept.** The standard ridge
  system is `(alpha I + Phi^T Phi)`, so `alpha > 0` is also what keeps the posterior well
  defined in the limit case.
- **The evidence uses a direct log-determinant, not a Cholesky or an eigendecomposition.**
  `S_N^{-1}` is symmetric positive definite; elimination with partial pivoting is the
  least code and reuses `solve_linear`. The `alpha I` term is what keeps it conditioned.
- **Hyperparameters by exhaustive grid, not by Newton updates.** The update equations are
  elegant but hide the shape of the evidence surface, which is the point. A grid makes the
  maximum visibly interior and reproducible by the checker.

## Limit cases

- **More basis functions than data points.** Five points, eight polynomial basis
  functions: `Phi^T Phi` is singular, so `mle_weights` returns `None`. The Bayesian
  posterior is still a proper Gaussian because `alpha I` bounds `S_N^{-1}` below, and its
  mean stays finite (and would shrink to 0 as `alpha` grows).
- **Test points far from the data.** A degree-5 basis fit on `[-0.6, 0.6]` shows the
  predictive variance rising from ~0.045 at the centre to ~1.5 at `x = 3` and far beyond,
  while the observation-noise floor is `1/beta = 0.04`.

## Mutation coverage

`_build/mutations.py` plants one classic bug per mechanism; each is an exact edit to a
copy of the solutions and must be caught by the named step
(`python3 .claude/skills/graded-module/scripts/mutate.py math/prml/03-linear-regression math/prml/03-linear-regression/_build/mutations.py`).

| Bug | Step |
|---|---|
| `ridge_weights` adds `alpha` to the wrong side (`Phi^T Phi - alpha I`) | 1 |
| `bayesian_posterior` forgets the `beta` factor on `Phi^T Phi` | 2 |
| `predictive_distribution` drops the `1/beta` observation-noise term | 3 |
| `log_evidence` omits the `+1/2 ln|S_N|` Occam term | 4 |
| `mle_weights` treats the singular system as well posed | 5 |

## Questions

Answers are not given. Work them out from the code and the definitions.

1. Why does the posterior mean equal the ridge solution with `lambda = alpha / beta`?
   What happens to that correspondence as `beta -> infinity`?
2. The predictive variance is `1/beta + phi^T S_N phi`. Which term makes it grow away
   from the data, and why does a Gaussian radial basis behave differently from a
   polynomial basis far away?
3. `log_evidence` contains `+1/2 ln|S_N|`. Why is that called the Occam factor, and
   which way does it push the chosen `alpha`?
4. In the limit case (`n < m`) the MLE is not unique but the posterior is. Which line of
   `bayesian_posterior` is responsible, and what is the posterior mean as `alpha -> 0`?
5. Why is the model "linear" even when the basis functions are `sin`, `exp` or radial?

## Limits

- The grid over `(alpha, beta)` is linear in its size; a fine grid is slow. The textbook's
  fixed-point updates converge faster but need their own convergence check, which is out
  of scope here.
- `log_evidence` assumes a zero-mean isotropic Gaussian prior `N(0, alpha^{-1} I)`. A
  general prior precision matrix would need its own log-determinant.
- Numerical determinants come from floating-point elimination; badly scaled bases can
  lose digits. The `alpha I` term and the moderate degrees used here keep the cases
  conditioned.
