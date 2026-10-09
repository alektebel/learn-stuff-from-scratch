# Kernels and Gaussian processes from scratch

Kernel methods and Gaussian process regression from the inside out: what makes a
kernel valid, how the Gram matrix encodes it, and how conditioning a Gaussian
prior on data gives interpolation and a closed-form evidence for choosing
hyperparameters. Implements chapter 6 of Bishop, *Pattern Recognition and Machine
Learning* (kernel methods), and the matching material in Murphy, *Probabilistic
Machine Learning: An Introduction* (Gaussian processes) (`bishop:6`, `murphy1:17`).
The argument is restated here, never copied.

**Status: not built.** `kernels.py` holds the stubs; `check.py` grades them. This
file describes the work; `solutions/` is the reference.

## What you build

`kernels.py`, nine graded functions. The dense linear solve (`solve`), the Jacobi
eigenvalues (`_symmetric_eigenvalues`), the forward/back substitution
(`_chol_solve`), the jitter fallback (`cholesky_with_fallback`), the shared
covariance builder (`_observation_covariance`) and the demo are given: they are
infrastructure, not the GP itself.

| Function | What it does |
|---|---|
| `linear_kernel(variance, offset)` | the kernel `k(x, y) = variance (x y + offset)` as a closure |
| `polynomial_kernel(degree, scale, offset, variance)` | `variance (scale x y + offset)^degree` |
| `rbf_kernel(length_scale, variance)` | `variance exp(-(x - y)^2 / (2 length_scale^2))` |
| `gram_matrix(kernel, xs)` | the symmetric matrix `K_ij = k(x_i, x_j)` |
| `is_psd(K, tol)` | validity, by the smallest eigenvalue |
| `cholesky(K, jitter)` | lower-triangular `L` with `L L^T = K + jitter I` |
| `gp_posterior(xs_train, ys_train, xs_test, kernel, noise)` | the posterior mean and (latent) variance |
| `gp_log_marginal_likelihood(xs, ys, kernel, noise)` | the log evidence `ln p(y | X)` |
| `log_marginal_gradient_fd(xs, ys, kernel, params, noise, h)` | finite-difference evidence gradient w.r.t. the hyperparameters |

A kernel is a two-argument callable `k(x, y)`. `log_marginal_gradient_fd` takes a
*kernel factory* `kernel(params) -> k(x, y)` so a perturbed parameter vector
builds the perturbed kernel.

## Running it

```bash
python3 check.py        # every step, stopping at the first one not written
python3 check.py 3      # just step 3
python3 check.py --all  # do not stop at the first gap
```

A step that raises `NotImplementedError` is reported as **TODO**, not a failure. A
step that asserts and fails is a **FAIL**; an exception is an **ERROR**. The checks
import your `kernels.py`, never `solutions/`.

## The checks

| Step | What it pins down |
|---|---|
| 1 | each kernel's values match an independent reference (the RBF exponent uses the **squared** distance); each Gram matrix is symmetric and PSD; the Gram matrix of a sum of kernels is the sum of Gram matrices, and of a product is the Schur product, both PSD |
| 2 | `cholesky` is lower-triangular and reconstructs `K`; on noise-free data the GP posterior mean reproduces the training targets to `1e-9`; with nonzero noise the mean equals an independent `K_* (K + noise I)^{-1} y` |
| 3 | the posterior variance collapses towards the observation noise at training inputs, increases strictly moving away from the data, and approaches the prior variance `k(x, x)` far out |
| 4 | **ACCEPT**: `gp_log_marginal_likelihood` matches the checker's independent evidence, and `log_marginal_gradient_fd` matches the checker's independent central differences at two parameter settings |
| 5 | **LIMIT CASES**: (a) the invalid kernel `k(x, y) = -x y` gives a Gram matrix with a negative eigenvalue that `is_psd` rejects; (b) a duplicated input makes the Gram matrix PSD but singular, so `cholesky` fails without jitter and succeeds with it |

The checker carries its own kernel values, Gram matrix, Gaussian elimination,
log-determinant, log-evidence and eigenvalue routine, so the numeric comparisons
are against an independent implementation, not against a restatement of yours.

## Design decisions

- **A kernel is a callable, not a matrix.** The same GP code serves any kernel;
  the Gram matrix is just where the callable is sampled. `gram_matrix` fills both
  triangles from one value so symmetry is exact, not approximate.
- **Validity is checked by eigenvalues, not by Cholesky.** A Cholesky test is
  cheap but needs a jitter to be usable, and the jitter is exactly what turns a
  singular or slightly negative Gram matrix into an accepted one. The Jacobi
  eigenvalues give the margin directly, so `tol` is honest.
- **`cholesky` refuses rather than silently regularises.** A zero pivot is
  information: the Gram matrix is rank-deficient (duplicated inputs). The caller
  decides how much jitter to add; `cholesky_with_fallback` is one such policy.
- **The evidence is computed from the Cholesky factor.** `ln |C| = 2 sum ln L_ii`
  reuses the factor already built for `C^{-1} y`, and keeps every quantity
  positive, avoiding a separate determinant sign.
- **Hyperparameters by finite differences, not by an analytic formula.** The
  gradient check is then about differentiating the evidence, not about a second
  hand-derived expression; central differences give `O(h^2)` accuracy.

## Limit cases

- **An invalid kernel.** `k(x, y) = -x y` is negative semi-definite, so its Gram
  matrix has a negative eigenvalue and `is_psd` must say `False`. Symmetry alone
  does not make a kernel.
- **PSD in theory, singular numerically.** Training twice at the same input makes
  two rows and columns identical: the Gram matrix is PSD with a zero eigenvalue
  but has no exact Cholesky factor. Without jitter `cholesky` raises; with a
  diagonal jitter the factor (and the posterior) exists at the cost of a small
  approximation.

## Mutation coverage

`_build/mutations.py` plants one classic bug per mechanism; each is an exact edit
to a copy of the solutions and must be caught by the named step
(`python3 .claude/skills/graded-module/scripts/mutate.py math/prml/06-kernels-gps math/prml/06-kernels-gps/_build/mutations.py`).

| Bug | Step |
|---|---|
| `rbf_kernel` omits the square (uses the distance, not squared) | 1 |
| `cholesky` returns the upper factor without conjugating | 2 |
| `gp_posterior` drops the noise term in the training covariance | 2 |
| `is_psd` accepts a matrix with a negative eigenvalue | 5 |
| the jitter limit case removes the jitter, claiming a singular system solvable | 5 |

## Questions

Answers are not given. Work them out from the code and the definitions.

1. `gram_matrix` is symmetric by construction, yet `is_psd` still needs an
   eigen-decomposition. Why is symmetry not enough for a valid kernel?
2. The RBF Gram matrix is positive definite for distinct inputs. What does a
   duplicated input do to its eigenvalues, and why does the RBF prior then put no
   probability back on distinguishing the two?
3. The GP posterior mean is `K_* (K + noise I)^{-1} y`. Where does the noise term
   sit in the limit `noise -> 0`, and what happens to the predictive variance at a
   training input?
4. Why does the evidence gradient operate on a kernel *factory* rather than on a
   fixed kernel? What would a non-factory design force the caller to do?
5. Far from the data the posterior variance returns to `k(x, x) = variance`, not
   to infinity. What in the model bounds it?

## Limits

- Everything here is one-dimensional and dense. A realistic GP needs a sparse or
  inducing-point approximation to `K^{-1}`, and multivariate inputs (`x` becomes
  a vector, the kernel a dot product) are out of scope.
- The finite-difference gradient costs two full evidence evaluations per
  hyperparameter and its accuracy is limited by the choice of `h`. An analytic
  gradient (which the check would compare against) is cheaper and more accurate.
- No optimisation loop over the hyperparameters is included: `log_marginal_gradient_fd`
  produces the gradient; connecting it to a line search is left to the reader.
