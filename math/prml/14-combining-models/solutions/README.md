# Solutions — combining models

`combine.py` is the reference implementation of the eleven graded functions. Run
the checker against it by copying `combine.py` and `check.py` into one directory:

```bash
python3 check.py --all   # 5/5 passing
```

Everything is standard library only (`math`, `random`) and deterministic: the
bagging data is generated from fixed seeds, so the checker can reproduce every
measurement.

## Expected demo output

`python3 combine.py` from this directory prints:

```
CART
  fit: [0, 0, 0, 0, 1, 1, 1, 1] (want [0, 0, 0, 0, 1, 1, 1, 1] )
  best split: (0, 2.5, 0.0) vs parent gini 0.5

AdaBoost (3x3 diagonal grid, weak stumps)
  errors : [0.2222, 0.1429, 0.2292, 0.2801, 0.1971, 0.278, 0.3227, 0.2679, 0.2342, 0.2514]
  alphas : [0.6264, 0.8959, 0.6065, 0.472, 0.7023, 0.4772, 0.3707, 0.5026, 0.5922, 0.5456]
  train  : [0.2222222222222222, 0.2222222222222222, 0.1111111111111111, 0.1111111111111111, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
  bound  : prod 2 sqrt(eps(1-eps)) = 0.190624
  exp    : exp(-2 sum gamma^2)   = 0.25402

Bagging (noisy 1-D threshold)
  single tree test error : 0.302
  bagged  test error     : 0.280

LIMIT: AdaBoost under label noise
  final training error  : 0.0 (overfits noise)
  max sample weight     : 0.3192 (uniform would be 0.1000)
  weight on noise points: 0.5
  noise indices         : [1, 7] weights [0.1808, 0.3192]
```

What the lines show:

- **CART** fits the two clusters exactly with one feature-0 cut at threshold 2.5,
  dropping the impurity from the parent's `0.5` to `0.0`.
- **AdaBoost** on the 3x3 diagonal grid: no single axis-aligned stump beats 50%,
  so the first rounds only reach 2/9. The combined training error falls
  `0.222 -> 0.111 -> 0.0` and stays there. The product bound is `0.1906`, below
  the looser exponential bound `0.2540`.
- **Bagging** 25 depth-6 trees on 200 noisy training points lowers the held-out
  error from `0.302` (one overfit tree) to `0.280`: averaging bootstrap trees
  cancels some of the variance.
- **The limit case**: two points are mislabelled. Boosting drives their weights
  from `0.1` (uniform) up to `0.18` and `0.32`, over half the total mass, while
  the boosted classifier still scores 0 training error — it has fit the noise.

## Notes

- The checker's `_weights_ref` re-derives the AdaBoost weights from the returned
  stumps and alphas, so a solution that forgets to renormalise is caught even
  though the per-round errors stay scale-invariant.
- `best_split` computes midpoint thresholds per feature; on the lopsided-weight
  set the weighted optimum is at `1.5`, while the plain-count optimum sits at
  `0.5`, which is what step 1 exploits.
