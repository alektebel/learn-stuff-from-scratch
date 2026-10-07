# Solutions — linear classification

`classification.py` is the reference implementation of the seven graded functions. Run
the checker against it by copying `classification.py` and `check.py` into one directory:

```bash
python3 check.py --all   # 5/5 passing
```

## Expected demo output

`python3 classification.py` from this directory prints:

```
Linear classification — measurements
  least squares weights : [+0.5027, +0.2653, +0.1975]
  Fisher direction      : [+7.7883, +5.7967]  threshold -0.0779
  perceptron            : [-1.0000, +1.2000, +1.0000]  (2 passes)
  logistic IRLS         : [-0.5745, +0.4664, +3.5395]  (4 Newton steps)
  logistic gradient desc: [-0.5745, +0.4664, +3.5395]  (459 steps at the same tol)
  Laplace MAP mean      : [-0.1174, +0.4341, +0.5871]
  Laplace posterior std : [0.7192, 0.9684, 1.8038]
  separable, no prior ||w|| at 4/8/12 Newton steps: 8.361, 17.977, 27.953
  separable, L2 prior  ||w|| = 1.194  (finite)
  LS boundary   clean -0.8826 -> outlier +20.1254  (shift 21.0080)
  logit boundary clean -0.0033 -> outlier -1.3988  (shift 1.3955)
```

What the lines show:

- **Least squares, Fisher and the perceptron** all separate the same 2-D data; the
  perceptron reaches zero mistakes after two passes (the convergence theorem).
- **IRLS versus gradient descent** on the same 8-point overlapping set and the same
  `1e-10` gradient tolerance: 4 Newton steps against 459 first-order steps, landing on
  the same weights. This is the accept criterion.
- **The Laplace fit** on that data with a prior variance of 4: the mean is the
  `ridge = 1/4` MAP, and the posterior standard deviations are the square roots of the
  inverse Hessian's diagonal.
- **The separable limit case**: with no prior, `||w||` grows 8.36 -> 17.98 -> 27.95 over
  4, 8 and 12 Newton steps (the likelihood keeps rising, there is no maximum); an L2
  prior settles it at `||w|| = 1.19`.
- **The outlier limit case**: moving a single point from `x ≈ 0` out to `x = 8` with the
  opposite label drags the least-squares boundary from `-0.88` to `+20.13` (shift 21.0)
  but only nudges the logistic boundary (shift 1.40), because the sigmoid saturates.

The numbers are double-precision and deterministic (no random draws anywhere), so the
checker can reproduce every measurement exactly.
