# Solutions — Joint Distributions From Scratch

`joint.py` is the complete implementation. Run its demo:

```bash
python3 joint.py
```

Expected output (fixed seed, so it is reproducible):

```
Joint distributions from scratch
  joint over X in {-2,-1,1,2}, Y = X^2
    marginal(Y)  = {4: 0.5, 1: 0.5}
    P(Y|X=-2)    = {4: 1.0}   (degenerate: a point mass)
    P(Y|X= 1)    = {1: 1.0}
    Cov(X, Y)    = +0.000e+00   corr = +0.000e+00
    ... and yet Y is a function of X: zero correlation, full dependence
  multinomial_pmf([2, 1, 1], [0.5, 0.25, 0.25]) = 0.187500
  bivariate_normal_pdf(mu) = 0.120310  (1/(2 pi sqrt(det)) = 0.120310)
  sample_covariance convergence to the analytic covariance
    n =    100   var_x = 1.2023   cov_xy = 0.7495   var_y = 2.0049
    n =   1000   var_x = 0.9706   cov_xy = 0.4892   var_y = 2.1575
    n =  10000   var_x = 1.0106   cov_xy = 0.4924   var_y = 2.0457
    n = 200000   var_x = 0.9987   cov_xy = 0.4950   var_y = 1.9911
    analytic        var_x = 1.0000   cov_xy = 0.5000   var_y = 2.0000
```

The last block is the node's acceptance criterion: the sample covariance matrix
of the seeded bivariate-normal draw converges to the analytic
`[[1, 0.5], [0.5, 2]]`. The demo's first block is the limit case: `marginal(Y)`
is spread over `{1, 4}` while every `P(Y | X = x)` is a point mass, and yet
`Cov(X, Y) = 0`.

## Run the checker against these solutions

From a temporary directory holding a copy of `joint.py` and `check.py`:

```bash
python3 check.py --all
```

All five steps report `PASS`. To exercise the planted bugs, run
`python3 ../../../.claude/skills/graded-module/scripts/mutate.py . _build/mutations.py`
from inside the module directory.

## What is deliberately left out

The helper `_standard_normal_pair` (Box-Muller) is scaffolding, not a graded
deliverable; `make_templates.py` leaves it and `demo()` intact. See
`../README.md` for the design decisions and the questions the module asks
before you read this file.
