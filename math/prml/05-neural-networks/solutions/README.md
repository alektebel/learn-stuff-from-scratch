# Reference solution and notes

`solutions/neural.py` is a complete implementation. Run its demo with
`python3 solutions/neural.py`; it prints the outer-product/exact Hessian error near a
minimum and far from one, plus a weight-decay and early-stopping summary.

## Backpropagation

With `r_n = y_n - t_n` and the output delta `delta2 = r_n`,

```
dW2 += delta2 a1^T          db2 += delta2
delta1 = (W2^T delta2) * (1 - a1^2)
dW1 += delta1 x^T           db1 += delta1
```

The `(1 - a1^2)` factor is `tanh'(z1)`. It is the only nonlinearity in the network, so
dropping it is silent: the forward pass still runs, only the gradient is wrong.

## Exact Hessian

The Hessian of `E` is computed without writing a single second derivative: central
finite differences of the analytic gradient,

```
H[:, j] = (grad(w + eps e_j) - grad(w - eps e_j)) / (2 eps).
```

Symmetric by construction to rounding, which check 2 verifies.

## Outer-product (Gauss-Newton) Hessian

Writing the residuals as `r(w)` and `J_n = d r_n / dw`,

```
H = sum_n J_n^T J_n  +  sum_n sum_k r_{n,k} * d^2 r_{n,k} / dw^2 .
```

The first term is the outer-product approximation; it drops the second. At a minimum the
residuals are small, so the second term is small and the approximation is good — this is
the *accept* criterion (check 3). Far from a minimum the residuals are large, the dropped
term dominates, and the approximation degrades — check 5 asserts this error grows.

## Weight decay and early stopping

The penalised objective is `E + 1/2 * weight_decay * ||w||^2`, so the update is
`w <- w - lr * (grad + weight_decay * w)`: the decay adds to the gradient and pulls the
weights toward zero. Early stopping holds out a validation split, keeps the weights at
the lowest validation loss, and stops when validation loss turns upward even though the
training loss is still falling.

## Expected output

```
$ python3 neural.py
Two-layer net from scratch (tanh hidden, linear output)

trained 3000 steps, loss 0.7934 -> 0.000340
near the minimum   : outer-product vs exact Hessian rel. error 2.329e-05
far from the minimum: outer-product vs exact Hessian rel. error 9.427e-01

||w|| without decay 6.328, with decay 4.477
early stopping: stopped at iteration 375 (best 373); val 2.3956 -> 0.3347
```
