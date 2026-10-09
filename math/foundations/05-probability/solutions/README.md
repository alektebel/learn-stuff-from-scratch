# Probability and Distributions From Scratch — Solutions

A complete version of the template in the parent directory. Pure Python 3, standard
library only. Run it from the module directory:

```bash
python3 solutions/gaussians.py
```

Expected output:

```
Multivariate Gaussians from scratch — measurements
  sampling   N = 20000  max|mean−μ| = 0.0084  max|cov−Σ| = 0.0125
  linear map μ_y = [-0.50, 1.00]  max|Σ_y−AΣAᵀ| = 0.0e+00
  product    μ = 0.3333  σ² = 0.6667  (below both 1 and 2)
  conditional μ_{a|b} = [0.162, -0.028]  var = [0.747, 0.814]  (below the marginal 1.000)
  change-var ∫ p_Y dy = 1.000000  (Jacobian included)
  near-singular det Σ = 0 (underflows)  log p = -6249626.372 (Cholesky path)
```

(The sampling line uses a fixed seed; it is reproducible.)

Three lines carry the chapter:

- **sampling** — 20 000 draws of a correlated 2-D Gaussian have sample mean and
  covariance within the Monte-Carlo error of `μ` and `Σ`; the draws are `μ + Lz`, and `L`
  is what puts the correlation in.
- **change-var** — the log-normal density built from the standard normal integrates to
  `1.000000`. Remove the Jacobian `1/y` and the same integral is `e^{1/2} ≈ 1.649`.
- **near-singular** — the covariance's determinant is `2e-328`, which rounds to `0.0` in
  double precision, yet the log density is a finite `-6 249 626.372` because it is
  computed from the Cholesky pivots, `log det Σ = 2 Σ log Lᵢᵢ`, never from `det Σ`.

To grade yourself, run the checker against these files in a scratch directory:

```bash
cd math/foundations/05-probability
tmp=$(mktemp -d)
cp solutions/*.py check.py "$tmp"/
(cd "$tmp" && python3 check.py --all)   # 10/10 passing
```
