# Neural networks from scratch

Backpropagation derived by hand for a two-layer network, the exact Hessian by finite
differences of the gradient, its outer-product (Gauss-Newton) approximation, and two
regularisers: weight decay and early stopping. Pure standard library, no numpy.

Source: Bishop, *Pattern Recognition and Machine Learning*, chapter 5 (Neural Networks).
This module restates the ideas; it copies no text from the book.

## Run it

```sh
python3 check.py        # stop at the first unimplemented step
python3 check.py --all  # run every check
```

`neural.py` is the template. Fill in the functions marked `NotImplementedError`; the
checker tests your code and never imports `solutions/`.

## The network

Input `x` -> hidden `z1 = W1 x + b1`, `a1 = tanh(z1)` -> linear output `y = W2 a1 + b2`.
Loss is squared error `E = 1/2 sum_n ||y_n - t_n||^2`. Parameters live in a dict of
nested lists (`W1`, `b1`, `W2`, `b2`) with helpers to flatten and unflatten them.

## The five checks

1. **Backpropagation.** The analytic gradient from the chain rule matches central finite
   differences (`max relative error ~1e-6`). `numerical_gradient` must be central too.
2. **Exact Hessian.** Finite-differencing the analytic gradient gives a symmetric matrix
   that agrees with second differences of the loss (a consistency check).
3. **Accept — outer product near a minimum.** With small residuals the Gauss-Newton
   approximation `sum_n J_n^T J_n` is close to the exact Hessian. Because the dropped
   term is `sum_n sum_k r_{n,k} d^2 r_{n,k}`, small residuals mean small error.
4. **Regularisation.** L2 weight decay shrinks `||w||` and lowers held-out loss; early
   stopping halts on a rising validation loss while the training loss is still falling.
5. **Limit case — far from a minimum.** Deliberately large residuals make the outer
   product much worse than near the minimum: the approximation is not "just as good"
   away from where it is valid.

## Mutation coverage

`_build/mutations.py` plants one classic bug per mechanism; each is an exact edit to a
copy of the solutions and must be caught by the named step
(`python3 .claude/skills/graded-module/scripts/mutate.py math/prml/05-neural-networks math/prml/05-neural-networks/_build/mutations.py`).

| Bug | Step |
|---|---|
| backprop drops the `tanh'` factor in the hidden layer | 1 |
| `numerical_gradient` uses a one-sided difference | 1 |
| outer-product Jacobian uses the activation `a1` instead of `tanh'` | 3 |
| weight decay is subtracted from the gradient and grows the weights | 4 |
| outer-product Hessian silently returns the exact Hessian | 5 |

## Questions

Answers are not given. Work them out from the code and the definitions.

1. Derive `delta1 = (W2^T delta2) * (1 - a1^2)` from the chain rule. Where exactly does
   `tanh'` enter, and why is dropping it silent in the forward pass?
2. The exact Hessian is `sum_n J_n^T J_n + sum_n sum_k r_{n,k} d^2 r_{n,k}`. Which term
   does the Gauss-Newton approximation drop, and why is that term negligible at a
   minimum but not far from one?
3. The Gauss-Newton matrix is positive semidefinite. What does that imply for the
   direction it gives, and why can that be an advantage even when the exact Hessian has a
   negative eigenvalue?
4. Weight decay and early stopping both regularise. Do they penalise the same thing?
   Construct a case where one helps and the other does not.
5. Finite-differencing the gradient costs `2P` backprop calls and has an `eps`-dependent
   error. What is the optimal `eps` balance, and how does a forward-mode Jacobian avoid
   it?

## Limits

- One hidden layer with a `tanh` nonlinearity and a linear output; deeper nets, other
  activations and softmax/cross-entropy are out of scope.
- The exact Hessian is finite-difference based, so it is approximate to `eps` and does
  not scale to large parameter counts.
- The outer-product approximation is only studied as a Hessian approximation; no
  Gauss-Newton training loop is implemented.
- Weight decay and early stopping are demonstrated deterministically on hand-built data
  with fixed seeds, not proved.

## Files

- `neural.py` — the template you implement.
- `check.py` — the grader (own finite differences, no solution imports).
- `solutions/` — a reference implementation and its notes.
- `_build/` — hints for template generation and planted bugs for mutation testing.
