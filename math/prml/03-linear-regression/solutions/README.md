# Solutions — linear regression

`regression.py` is the reference implementation of the seven graded functions, plus the
given dense linear algebra. Run the checker against it by copying `regression.py` and
`check.py` into one directory:

```bash
python3 check.py --all   # 5/5 passing
```

## Expected demo output

`python3 regression.py` from this directory prints:

```
Basis-function regression — measurements
  MLE on an exact quadratic: [1.0, -2.0, 0.5]  (expected [1, -2, 0.5])
  ridge alpha=1:            [0.968311, -1.761006, 0.454601]  ||w||: MLE 2.2913 -> ridge 2.0604
  posterior mean (alpha=0.5, beta=25.0): [0.999447, -1.994586, 0.498788]
  posterior std: [0.066975, 0.073579, 0.135515]
  predictive variance at x = [0, .5, 1, 1.5, 2, 3]: [0.04449, 0.04361, 0.05475, 0.11922, 0.3059, 1.45906]  (noise floor 0.04000)
  evidence over a degree-5 basis on noisy quadratic data: alpha=1, beta=31.6228 (true beta = 25)
  limit case (5 points, 8 basis functions): MLE = None
  the same under a Bayesian posterior: finite mean [1.01, -1.764, 0.335, -0.345, 0.106, 0.009, 0.049, 0.098], trace(S_N) = 3.7810
```

What the lines show:

- MLE on noiseless quadratic data recovers `[1, -2, 0.5]` exactly.
- Ridge `alpha = 1` shrinks the weight norm from 2.2913 to 2.0604.
- The posterior for `(alpha, beta) = (0.5, 25)` is close to the exact quadratic, with a
  wider interval on the quadratic coefficient.
- The predictive variance sits at the noise floor `1/beta = 0.04` inside the data and
  grows by orders of magnitude outside it.
- Evidence maximisation on data whose true noise precision is `25` selects
  `beta = 31.6` (the grid's `10^1.5`), the closest grid point, and `alpha = 1`, which is
  interior.
- With 5 points and 8 basis functions the MLE is `None`; the Bayesian posterior is still
  a proper Gaussian.

The exact floating-point digits depend on the platform; the qualitative behaviour and the
`None` for the limit case do not.
