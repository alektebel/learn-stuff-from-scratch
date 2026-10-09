# Linear classification: least squares, Fisher, the perceptron and logistic regression

Linear models for classification from scratch. Implements chapter 4 of Bishop,
*Pattern Recognition and Machine Learning* (`bishop:4`). The argument is restated here,
never copied: least-squares classification, Fisher's linear discriminant, the perceptron,
logistic regression by maximum likelihood, and the Laplace approximation for the
Bayesian version.

**Status: not built.** `classification.py` holds the stubs; `check.py` grades them. This
file describes the work; `solutions/` is the reference.

## What you build

`classification.py`, seven graded functions. The dense linear algebra (`_design`,
`_dot`, `_solve`, `_inverse`, `_gram`), the first-order gradient helper (`_gradient`),
the fixed data builders and the demo are given: they are infrastructure, not the
classifier itself.

| Function | What it does |
|---|---|
| `sigmoid(z)` | the logistic link `1 / (1 + exp(-z))`, stable in both tails |
| `least_squares_classifier(Xs, ts)` | linear discriminant by least squares on 0/1 targets |
| `fisher_lda(Xs, ts)` | Fisher's direction `S_W^{-1}(m_1 - m_0)` and the midpoint threshold |
| `perceptron(Xs, ts, maxit)` | the mistake-driven update; weights and passes used |
| `logistic_irls(Xs, ts, maxit, tol, ridge)` | logistic regression by IRLS (Newton); weights and steps |
| `logistic_gradient_descent(Xs, ts, lr, maxit, tol)` | the baseline for the iteration comparison |
| `laplace_logistic(Xs, ts, prior_var)` | MAP weights and the Gaussian posterior covariance |

Every linear model carries an explicit bias column, so the returned weight vector is
`[bias, w_1, ...]`, one longer than the feature dimension.

## Running it

```bash
python3 check.py        # every step, stopping at the first one not written
python3 check.py 3      # just step 3
python3 check.py --all  # do not stop at the first gap
```

A step that raises `NotImplementedError` is reported as **TODO**, not a failure. A step
that asserts and fails is a **FAIL**; an exception is an **ERROR**. The checks import your
`classification.py`, never `solutions/`.

## The checks

| Step | What it pins down |
|---|---|
| 1 | on separable anisotropic 2-D data, least squares, Fisher and the perceptron all classify every training point correctly; Fisher's direction equals the checker's own `S_W^{-1}(m_1 - m_0)`; the perceptron stops before `maxit` |
| 2 | logistic IRLS on a small non-separable set matches an independent Newton fit: identical weights, identical predicted probabilities, and a vanishing gradient at the solution |
| 3 | **ACCEPT**: at the same gradient tolerance IRLS reaches the optimum in far fewer iterations than gradient descent (and in at most a dozen Newton steps); the two optimisers land on the same weights |
| 4 | **ACCEPT**: the Laplace approximation's mean equals the MAP estimate (to `1e-9`) and its covariance is the inverse Hessian at the MAP |
| 5 | **LIMIT CASES**: (a) on linearly separable data the unregularised logistic weights grow without bound (no maximum) while an L2 prior settles them; (b) an injected far outlier wrecks the least-squares boundary but barely moves the logistic boundary |

The checker carries its own `_solve`, `_inverse`, `_fisher_reference` and
`_logistic_newton`, so the numeric comparisons are against an independent
implementation, not against a restatement of yours.

## Design decisions

- **0/1 targets in the public API, +1/-1 inside the perceptron.** Bishop's chapter uses
  `t ∈ {0,1}`; only the perceptron update needs the sign, so it converts internally.
- **An explicit bias column everywhere.** A boundary that may not pass through the
  origin needs one; the cost is one extra weight entry.
- **Fisher's `S_W` inverted by the same Gauss-Jordan/elimination `_solve` as everywhere
  else.** A singular scatter raises rather than returning a pseudo-inverse direction.
- **An L2 prior exposed as `ridge`, the last argument of `logistic_irls`.** It is the
  one number between the separable limit case (no prior, divergence) and the fix (a prior,
  finite MAP).
- **Convergence by the gradient norm in both optimisers.** The iteration comparison is
  only meaningful if both count the same stopping quantity.
- **Laplace fitted with `maxit=200, tol=1e-13` internally** so its mean is the MAP to
  well below the `1e-9` the check demands.

## Mutation table

Every planted bug in `_build/mutations.py` is caught by the step it names:

| Mutation | Caught by |
|---|---|
| `sigmoid` is the rational `z/(1+|z|)` | step 2 (probabilities diverge from the Newton reference) |
| Fisher drops the within-class scatter (plain difference of means) | step 1 (direction mismatch against `S_W^{-1}Δm`) |
| IRLS drops the `p(1-p)` factor from the Hessian | step 3 (far more than a dozen iterations) |
| the Laplace mean is set to zero | step 4 (mean not equal to the MAP) |
| the unregularised run carries a default L2 prior | step 5 (the separable `||w||` no longer grows) |

## Open questions (no answers here)

- Why does the least-squares classifier on 0/1 targets give a different direction from
  Fisher's rule, and when do they coincide?
- The perceptron converges in finitely many passes on separable data; what does it do on
  the outlier data of step 5(b), and why is that not a contradiction?
- IRLS is Newton's method on the log-likelihood. Why does the Hessian come out positive
  definite for every `w`, so no line search is needed?
- On separable data the unregularised likelihood has no maximum. What exactly happens to
  the IRLS iteration, and why does a prior of any positive precision fix it?
- The Laplace approximation replaces the posterior with a Gaussian at its mode. Where is
  that approximation worst, and how does the posterior variance change with `prior_var`?
