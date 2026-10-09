# Random Variables From Scratch — Solutions

A complete version of the template in the parent directory. Pure Python 3, no
dependencies. Run it from the module directory:

```bash
python3 solutions/random_variables.py
```

Expected output (Monte-Carlo numbers are seed-fixed; the exact values never change):

```
Random variables from scratch — exact vs 10^5-trial simulation
  Bernoulli(1/2)         mean   0.5000 sim   0.5004   var   0.2500 sim   0.2500
  Binomial(20,1/2)       mean  10.0000 sim  10.0015   var   5.0000 sim   5.0034
  Geometric(1/3)         mean   3.0000 sim   3.0082   var   6.0000 sim   6.0525
  NegBinom(4,1/3)        mean  12.0000 sim  11.9936   var  24.0000 sim  23.7568
  Poisson(3)             mean   3.0000 sim   2.9968   var   3.0000 sim   3.0008
  line-up: fixed points of a random permutation (dependent indicators)
  n = 2                  mean   1.0000 sim   1.0027   var   1.0000 sim   1.0000
  n = 5                  mean   1.0000 sim   1.0023   var   1.0000 sim   1.0086
  n = 50                 mean   1.0000 sim   0.9984   var   1.0000 sim   0.9989
  the independence-only variance would be (n-1)/n = 0.8000; the truth is 1.0000
  Poisson approximation to Binomial, total variation distance (n p = 1)
    n =   10, p = 0.1000   TV = 0.029312
    n =  100, p = 0.0100   TV = 0.002775
    n = 1000, p = 0.0010   TV = 0.000276
```

Three lines carry the module:

- **Geometric(1/3) mean = 3**, exactly `1/p`. The failures-before-success convention
  would print 2; the template's `pmf(1) == p` check and the `4-SE` band on a sample of
  100 000 draws both pin the support at 1.
- **Fixed points mean = 1 for every n**, including `n = 2, 5, 50`. The indicators are
  dependent (no permutation of `n >= 2` elements has only one fixed point), yet linearity
  needs no independence. The independence-only *variance* `(n-1)/n = 0.8` at `n = 5` is
  not what the simulation shows; the truth is 1.
- **Poisson approximation total variation 0.0293, 0.00278, 0.000276** for `n = 10, 100,
  1000` with `n p = 1`. Each tenfold increase in `n` cuts the error roughly tenfold:
  Le Cam's bound is `O(n p^2) = O(p)`, so the error is proportional to `p`, not constant.

The exact value `E[X^2] - (E[X])^2` is deliberately split across
`variance_from_moments` in the template: putting the square on the difference instead of
on the mean collapses Bernoulli's variance to 0, which is the first planted bug.

To grade yourself, run the checker against these files in a scratch directory:

```bash
cd math/probability/02-random-variables
tmp=$(mktemp -d)
cp solutions/*.py check.py "$tmp"/
(cd "$tmp" && python3 check.py --all)   # 8/8 passing
```
