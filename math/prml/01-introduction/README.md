# Curve fitting, bias-variance and decision theory

Polynomial curve fitting, the bias-variance decomposition and decision theory, from
scratch. Implements chapter 1 of Bishop, *Pattern Recognition and Machine Learning*, and
the matching material in Murphy, *Probabilistic Machine Learning: An Introduction*
(the argument is restated here, never copied).

**Status: not built.** `intro.py` holds the stubs; `check.py` grades them. This file
describes the work; `solutions/` is the reference.

## What you build

`intro.py`, ten graded functions; the target function and the demo are given.

| Function | What it does |
|---|---|
| `poly_features(x, degree)` | the feature vector `[1, x, ..., x^degree]` |
| `solve_linear(A, b)` | Gaussian elimination with partial pivoting |
| `poly_fit(xs, ts, degree, lam)` | least-squares weights, with an L2 penalty `lam` |
| `poly_predict(weights, x)` | evaluate the fitted polynomial |
| `squared_error(weights, xs, ts)` | mean squared error |
| `bias_variance(degree, ...)` | the decomposition by simulating many training sets |
| `min_risk_decision(p, loss)` | the action of least expected loss |
| `entropy(p)` | Shannon entropy, in nats |
| `kl_divergence(p, q)` | the Kullback-Leibler divergence |
| `mutual_information(joint)` | the mutual information of a joint pmf |

## Running it

```bash
python3 check.py        # every step, stopping at the first one not written
python3 check.py 3      # just step 3
python3 check.py --all  # do not stop at the first gap
```

A step that raises `NotImplementedError` is reported as **TODO**, not a failure. A step
that asserts and fails is a **FAIL**; an exception is an **ERROR**. The checks import your
`intro.py`, never `solutions/`.

## The checks

| Step | What it pins down |
|---|---|
| 1 | `poly_features`, an exact quadratic recovered to 1e-8, `poly_predict` and `squared_error` against the checker's own evaluator |
| 2 | the limit case: degree-9 on 10 noisy points has ~zero training error and large test error, and ridge (`lam = 1e-5`) cuts the test error by more than 4x |
| 3 | the accept criterion: the simulated expected test error equals `bias^2 + variance + noise`, and bias falls while variance rises with model flexibility |
| 4 | minimum-risk decisions: the boundary at `p = 0.5` for a symmetric loss, and moved to `p = 1/11` for an asymmetric loss |
| 5 | entropy (non-negative, `ln 2` at the fair coin), KL (non-negative, zero iff equal), mutual information (zero iff independent) |

## Design decisions

- **Normal equations with Gaussian elimination, not QR.** The lesson is the shape of the
  fit, not numerical linear algebra (that is another node). Partial pivoting keeps the
  degree-9 case stable; the exact low-degree case is recovered to 1e-10.
- **The L2 penalty does not touch the bias term.** Penalising the intercept would make the
  fit depend on the origin of the target; standard ridge leaves `w_0` alone.
- **The expected test error is measured, not read off.** The identity
  `error = bias^2 + variance + noise` is only meaningful because the checker measures the
  left side with fresh test noise and the right side from the training statistics.
- **Ties go to action 0.** A deterministic rule matters when the two expected losses are
  equal (the symmetric boundary).
- **`0 log 0 = 0`.** Entropy and KL skip zero-probability terms, which is both the
  convention and the numerically safe form.

## Limit cases

- **Degree-9 on 10 noisy points.** The polynomial interpolates the training set
  (training error ~1e-9) but the noise it fits is not in the test set: test error ~0.59.
  Ridge `lam = 1e-5` brings it down to ~0.04.
- **An asymmetric loss moves the boundary.** With a symmetric loss the frontier is
  `p = 0.5`; when action 0 costs 10 on class 1 while action 1 costs 1 on class 0, the
  frontier is `p = 1/11`. The optimal action, not the posterior, is what is asked for.

## Mutation coverage

`_build/mutations.py` plants one classic bug per mechanism; each is an exact edit to a
copy of the solutions and must be caught by the named step
(`python3 .claude/skills/graded-module/scripts/mutate.py math/prml/01-introduction math/prml/01-introduction/_build/mutations.py`).

| Bug | Step |
|---|---|
| `poly_features` drops the constant term | 1 |
| `poly_fit` ignores `lam` (no ridge) | 2 |
| `bias_variance` measures variance about the true function, folding in the bias | 3 |
| `min_risk_decision` ignores the loss matrix and uses `p = 0.5` | 4 |
| `kl_divergence` flips the ratio inside the log | 5 |
| `entropy` drops the minus sign | 5 |

## Questions

Answers are not given. Work them out from the code and the definitions.

1. Why does the degree-9 fit have such a small training error yet a huge test error? What
   exactly is it fitting that does not generalise?
2. The identity is `expected error = bias^2 + variance + noise`. Which term does ridge
   change, and why does increasing `lam` eventually make the test error rise again?
3. Why is the bias-variance identity only a statement about the *expected* error, and why
   does the simulation need many training sets to show it?
4. With a symmetric loss the decision boundary is at `p = 0.5`. Show that the asymmetric
   loss `[[0, 10], [1, 0]]` moves it to `p = 1/11`.
5. Mutual information is `I(X; Y) = KL(p(x, y) || p(x) p(y))`. Why does that make it zero
   exactly when `X` and `Y` are independent?

## Limits

- The degree-9 fit is numerically fragile without regularisation: the normal equations
  square the condition number of the Vandermonde-like design matrix, so training error is
  ~1e-9 rather than exactly zero. Ridge is what makes the case well posed.
- `bias_variance` is a Monte Carlo estimate: the identity holds only to within sampling
  error, which is why the check uses a fixed seed and a tolerance.
- `min_risk_decision` is the two-class, two-action case. More classes or actions need the
  general expected-loss minimiser, which is out of scope.
